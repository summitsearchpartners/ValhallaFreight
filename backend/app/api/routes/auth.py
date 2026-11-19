from datetime import datetime, timedelta, timezone
import hashlib
import logging
import smtplib
import time
from collections import defaultdict
from threading import Lock
from email.message import EmailMessage
from urllib.parse import quote
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from app.core.config import settings
from app.services.auth import hash_password
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    user.last_login_at = datetime.utcnow()
    user.last_seen_at = user.last_login_at
    from app.services.user_activity import add_activity
    add_activity(db,user,"login",path="/auth/login",status_code=200)
    db.commit()
    db.refresh(user)
    from app.services.muse_partner import has_access
    user.muse_partner_access=has_access(db,user)
    token = create_access_token(user.id, user.email, user.role)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


logger = logging.getLogger(__name__)

class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)

class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    password: str = Field(min_length=12, max_length=128)


def _password_version(user: User) -> str:
    return hashlib.sha256(user.password_hash.encode('utf-8')).hexdigest()


def _send_reset_email(address: str, link: str) -> None:
    message = EmailMessage()
    message['From'] = settings.smtp_from_email
    message['To'] = address
    message['Subject'] = 'Reset your Valhalla TMS password'
    message.set_content(
        'A password reset was requested for your Valhalla TMS account.\n\n'
        f'Open this link to set a new password (expires in 20 minutes):\n{link}\n\n'
        'If you did not request this, you can ignore this email.\n'
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


# Per-process abuse protection. Use an edge/distributed rate limiter for multiple workers.
_reset_attempts: dict[str, list[float]] = defaultdict(list)
_reset_lock = Lock()


def _allow_reset_attempt(key: str, limit: int) -> bool:
    now = time.monotonic()
    with _reset_lock:
        if len(_reset_attempts) > 5000:
            _reset_attempts.clear()
        recent = [t for t in _reset_attempts[key] if now - t < 900]
        if len(recent) >= limit:
            _reset_attempts[key] = recent
            return False
        recent.append(now)
        _reset_attempts[key] = recent
        return True


@router.post('/forgot-password')
def forgot_password(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    # Identical responses for unknown, inactive, or non-deliverable accounts.
    response = {'message': 'If the account has a valid email address and email delivery is configured, a reset link will be sent.'}
    email = payload.email.strip().lower()
    client_ip = request.client.host if request.client else 'unknown'
    if not _allow_reset_attempt('ip:' + client_ip, 10) or not _allow_reset_attempt('email:' + email, 3):
        return response
    user = db.query(User).filter(User.email == email, User.active.is_(True)).first()
    if not user or not settings.smtp_host or email.endswith('.local'):
        return response
    now = datetime.now(timezone.utc)
    token = jwt.encode({
        'sub': str(user.id), 'purpose': 'password_reset',
        'version': _password_version(user),
        'iat': now, 'exp': now + timedelta(minutes=20),
    }, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    base = settings.password_reset_base_url.rstrip('/')
    if not base.startswith('https://') and settings.environment.lower() not in ('development', 'local', 'test'):
        logger.error('Password reset base URL must use HTTPS in production')
        return response
    link = f'{base}/reset-password?token={quote(token, safe="")}'
    try:
        _send_reset_email(email, link)
    except Exception:
        logger.exception('Password reset email delivery failed')
    return response


@router.post('/reset-password')
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        claims = jwt.decode(payload.token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        if claims.get('purpose') != 'password_reset':
            raise ValueError('Wrong token purpose')
        user = db.query(User).filter(User.id == int(claims['sub']), User.active.is_(True)).first()
        if not user or claims.get('version') != _password_version(user):
            raise ValueError('Token already used or account changed')
    except (JWTError, ValueError, KeyError, TypeError, OverflowError):
        raise HTTPException(status_code=400, detail='This reset link is invalid or expired. Request a new link.')
    if len(payload.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=422, detail='Password must not exceed 72 bytes.')
    user.password_hash = hash_password(payload.password)
    db.commit()
    return {'message': 'Password updated. You can now sign in.'}

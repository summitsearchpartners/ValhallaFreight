from types import SimpleNamespace
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import User
from app.services.auth import decode_access_token

bearer = HTTPBearer(auto_error=False)

from app.db.session import get_db

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("purpose") not in (None,"access"):raise ValueError("Invalid bearer token purpose")
        user_id = int(payload.get("sub", "0"))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is unavailable")
    from app.services.muse_partner import has_access
    user.muse_partner_access=has_access(db,user)
    request.state.auth_user = SimpleNamespace(id=user.id, role=user.role, customer_id=user.customer_id, email=user.email, full_name=user.full_name)
    context = request.headers.get('X-Company-Id')
    if context:
        if user.role != 'admin':
            raise HTTPException(403, 'Only Valhalla Freight Admin can select another company context')
        try: company_id = int(context)
        except ValueError: raise HTTPException(422, 'Invalid company context')
        from app.models import Customer
        if not db.get(Customer, company_id): raise HTTPException(404, 'Company not found')
        request.state.integration_company_id = company_id
    workspace=request.headers.get('X-Portal-Workspace')
    if workspace:
        if workspace!='manufacturer' or user.role!='admin' or not context:raise HTTPException(403,'Invalid support workspace')
        from app.services.portal_access import require_session
        grant=require_session(db,user,request.headers.get('X-Portal-Session'),company_id,'manufacturer')
        request.state.support_company_id=company_id
        request.state.support_expires_at=grant.expires_at
    return user

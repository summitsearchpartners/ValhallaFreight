from datetime import datetime
import logging
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from app.models import UserActivity


def add_activity(db, user, action, *, path='', status_code=None, details=None):
    db.add(UserActivity(user_id=user.id, user_email=user.email, user_name=user.full_name,
        role=user.role, company_id=(details or {}).get('company_id',user.customer_id), action=action, path=path[:240],
        status_code=status_code, details=details or {}, created_at=datetime.utcnow()))


class ActivityMiddleware(BaseHTTPMiddleware):
    """Record authenticated API requests with outcomes, without bodies or query strings."""
    async def dispatch(self, request, call_next):
        code=500
        try:
            response=await call_next(request)
            code=response.status_code
            return response
        finally:
            user=getattr(request.state,'auth_user',None)
            engine=getattr(request.state,'activity_engine',None)
            if user and engine is not None and request.url.path.startswith('/api/v1') and request.url.path not in {'/api/v1/auth/me','/api/v1/auth/presence','/api/v1/auth/logout'} and not (request.method=='GET' and request.url.path.startswith('/api/v1/admin/users')):
                try:
                    with Session(engine) as db:
                        add_activity(db,user,'api_request',path=request.url.path,status_code=code,details={'method':request.method,'company_id':getattr(request.state,'integration_company_id',user.customer_id)})
                        db.commit()
                except Exception:
                    logging.getLogger(__name__).exception('Unable to persist user activity')

"""Server-side module policy; roles are always read from the database."""
from fastapi import Depends, HTTPException, Request
from app.api.deps import get_current_user, get_db
from sqlalchemy import text

from app.core.roles import BROKER_ROLES, COMPANY_ROLES, COMPANY_ADMIN_ROLES

def require_muse_admin(request: Request, user=Depends(get_current_user)):
    if user.role != 'admin' or getattr(request.state, 'support_company_id', None) is not None:
        raise HTTPException(403, 'Valhalla TMS Admin required to manage Muse Freight')
    return user


def internal_access(request: Request, user=Depends(get_current_user), db=Depends(get_db)):
    from app.services.commercial_privacy import customer_view
    path = request.url.path.removeprefix('/api/v1')
    if customer_view(request):
        if path.startswith('/pricing-rules'):
            raise HTTPException(403,'Broker pricing rules are private')
        if path.startswith('/finance') and not path.startswith(('/finance/customer-invoices','/finance/notifications')):
            raise HTTPException(403,'Carrier payables are managed by your broker')
    if user.role == 'admin':
        return user
    if user.role not in COMPANY_ROLES or not user.customer_id:
        raise HTTPException(403, 'Internal workspace access required')
    path = request.url.path.removeprefix('/api/v1')
    broker = user.role in BROKER_ROLES
    blocked = () if broker else ('/prospects', '/capacity', '/portal', '/carrier-360', '/finance/email-outbox')
    if path.startswith(blocked):
        raise HTTPException(403, 'This module is managed by your broker')
    tracking_refresh = user.role == 'broker' and request.method == 'POST' and (
        path.startswith('/integrations/dayton/shipments/') and path.endswith('/sync-tracking')
        and path.split('/')[-2].isdigit()
    )
    if path.startswith('/integrations') and user.role not in COMPANY_ADMIN_ROLES and not tracking_refresh:
        raise HTTPException(403, 'Company administrator required for integrations')
    # Shared carrier directory is required by Quote Studio; edits remain broker-only.
    if path.startswith('/carriers') and request.method != 'GET':
        raise HTTPException(403, 'Carrier administration requires broker access')
    if broker and path.startswith('/carrier-360') and request.method != 'GET':
        if user.role != 'broker_admin':
            raise HTTPException(403, 'Broker Admin required to manage carriers')
        parts = path.strip('/').split('/')
        if len(parts) > 1:
            from app.models import Carrier
            carrier = db.get(Carrier, int(parts[1])) if parts[1].isdigit() else None
            if not carrier:
                raise HTTPException(404, 'Carrier not found')
            if carrier.customer_id != user.customer_id:
                raise HTTPException(403, 'Shared carriers are managed by Valhalla TMS')
    if path.startswith('/customers') and request.method != 'GET':
        parts=path.strip('/').split('/')
        if len(parts)==1 and request.method=='POST':return user
        from app.models import Customer
        try:customer_id=int(parts[1])
        except (IndexError,ValueError):raise HTTPException(403,'Customer access denied')
        customer=db.get(Customer,customer_id)
        if not customer:raise HTTPException(404,'Customer not found')
        from app.db.tenant_scope import owns
        own_child=customer.manufacturer_id==user.customer_id or (broker and customer.id!=user.customer_id and owns(db,customer.id,user.customer_id))
        own_admin_setting=customer.id==user.customer_id and user.role in COMPANY_ADMIN_ROLES and len(parts)>2
        if not own_child and not own_admin_setting:raise HTTPException(403,'You can manage only customers in your company workspace')
    if path.startswith('/pricing-rules'):
        enabled = db.execute(text('SELECT show_pricing FROM company_workspace_settings WHERE customer_id=:id'), {'id':user.customer_id}).scalar()
        if not enabled and user.role != 'broker_admin':
            raise HTTPException(403, 'Pricing Engine is disabled for your company')
        if request.method != 'GET' and user.role not in COMPANY_ADMIN_ROLES:
            raise HTTPException(403, 'Company administrator required to manage pricing')
    return user

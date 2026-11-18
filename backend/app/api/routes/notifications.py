from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import MarginProtectionNotification, OperationalNotification

router = APIRouter(prefix='/notifications', tags=['Notifications'])


def _finance_row(n: MarginProtectionNotification):
    return {
        'key': f'finance:{n.id}', 'source': 'finance', 'id': n.id,
        'title': n.title, 'body': n.body, 'severity': n.severity,
        'status': n.status, 'created_at': n.created_at,
        'shipment_id': n.shipment_id,
        'target_path': f'/shipments/{n.shipment_id}' if n.shipment_id else '/finance',
    }


def _ops_row(n: OperationalNotification):
    return {
        'key': f'ops:{n.id}', 'source': 'ops', 'id': n.id,'notification_type':n.notification_type,
        'title': n.title, 'body': n.body, 'severity': n.severity,
        'status': n.status, 'created_at': n.created_at,
        'shipment_id': n.shipment_id,
        'customer_id': n.customer_id,
        'location_id': n.location_id,
        'target_path': n.target_path or (f'/customers/{n.customer_id}' if n.customer_id else '/'),
    }


@router.get('')
def list_notifications(audience: str = Query('internal'), db: Session = Depends(get_db)):
    finance = db.query(MarginProtectionNotification).filter(MarginProtectionNotification.audience == audience).order_by(MarginProtectionNotification.created_at.desc()).limit(50).all()
    ops = db.query(OperationalNotification).filter(OperationalNotification.audience == audience).order_by(OperationalNotification.created_at.desc()).limit(50).all()
    rows = [_finance_row(x) for x in finance] + [_ops_row(x) for x in ops]
    from app.models import SafeLoadCase
    request=db.info.get('request');user=getattr(request.state,'auth_user',None) if request else None
    allowed=user and user.role in {'admin','broker','broker_admin'} and getattr(request.state,'support_company_id',None) is None
    for row in rows:
        case=db.get(SafeLoadCase,row['shipment_id']) if allowed and row.get('notification_type')=='safe_load' and row.get('shipment_id') else None
        row['can_authorize_release']=bool(case and case.status=='rejected')
    rows.sort(key=lambda x: x['created_at'] or datetime.min, reverse=True)
    return rows[:75]


@router.post('/{source}/{notification_id}/read')
def mark_read(source: str, notification_id: int, db: Session = Depends(get_db)):
    if source == 'finance':
        item = db.get(MarginProtectionNotification, notification_id)
    elif source == 'ops':
        item = db.get(OperationalNotification, notification_id)
    else:
        raise HTTPException(404, 'Notification source not found')
    if not item:
        raise HTTPException(404, 'Notification not found')
    item.status = 'read'
    item.read_at = datetime.utcnow()
    db.commit()
    return {'ok': True}

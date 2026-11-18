from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException
from app.api.deps import get_db,get_current_user
from app.models import OperationRun,IntegrationConnection,Shipment,Quote,CarrierBill,Claim
from app.services.operations import connection_state
router=APIRouter(prefix='/operations',tags=['Operational Status'])

@router.get('/summary')
def summary(db=Depends(get_db),user=Depends(get_current_user)):
    connections=[connection_state(db,r) for r in db.query(IntegrationConnection).order_by(IntegrationConnection.provider).all()]
    shipments=db.query(Shipment).filter(Shipment.status.notin_(['delivered','cancelled','closed'])).all()
    attention=[]
    for s in shipments:
        if s.requested_delivery_at and s.requested_delivery_at<datetime.utcnow():attention.append({'title':f'{s.shipment_number}: delivery commitment overdue','reason':'No delivery recorded before the required delivery time.','path':f'/shipments/{s.id}'})
        elif not s.pro_number:attention.append({'title':f'{s.shipment_number}: carrier reference missing','reason':'Open the shipment to confirm dispatch and tracking.','path':f'/shipments/{s.id}'})
    for b in db.query(CarrierBill).filter(CarrierBill.status=='pending_review').limit(20).all():attention.append({'title':f'Carrier bill #{b.id} awaiting review','reason':'Review freight audit before approving payment.','path':'/finance'})
    # Only the latest outcome per job is actionable; successful retries clear old failures.
    latest={}
    for run in db.query(OperationRun).order_by(OperationRun.id.desc()).all():latest.setdefault((run.kind,run.integration_id,run.shipment_id),run)
    unresolved=[r for r in latest.values() if r.status=='failed']
    if unresolved:attention.append({'title':f'{len(unresolved)} operation(s) need review','reason':'Inspect failures and retry supported checks or tracking refreshes.','path':'/automation' if user.role not in {'manufacturer','manufacturer_admin'} else '/shipments'})
    for conn in connections:
        if conn['state'] in {'check_failed','credentials_required','check_stale','not_verified'} and user.role in {'admin','manufacturer_admin','broker_admin'}:attention.append({'title':f"{conn['provider']}: {conn['state'].replace('_',' ')}",'reason':'Configure credentials or run a live connection check.','path':'/integrations'})
    runs=db.query(OperationRun).order_by(OperationRun.id.desc()).limit(30).all()
    return {'checked_at':datetime.utcnow().isoformat()+'Z','api':'responding','database':'query_succeeded','connections':connections,'configured':sum(c['credentials_configured'] for c in connections),'verified':sum(c['connection_verified'] for c in connections),'healthy':sum(c['live_healthy'] for c in connections),'needs_review':len(unresolved),'attention':attention[:30],'runs':[{'id':r.id,'kind':r.kind,'status':r.status,'summary':r.summary,'finished_at':r.finished_at.isoformat()+'Z','retryable':r.retryable and latest.get((r.kind,r.integration_id,r.shipment_id)).id==r.id,'shipment_id':r.shipment_id} for r in runs]}

@router.post('/runs/{run_id}/retry')
async def retry(run_id:int,db=Depends(get_db),user=Depends(get_current_user)):
    if user.role not in {'admin','manufacturer_admin','broker_admin'}:raise HTTPException(403,'Administrator required to retry integrations')
    run=db.get(OperationRun,run_id)
    if not run:raise HTTPException(404,'Run not found')
    if not run.retryable or run.status!='failed':raise HTTPException(409,'This operation cannot be retried')
    newer=db.query(OperationRun).filter(OperationRun.kind==run.kind,OperationRun.integration_id==run.integration_id,OperationRun.shipment_id==run.shipment_id,OperationRun.id>run.id).first()
    if newer:raise HTTPException(409,'A newer execution already exists. Review its result before retrying.')
    from app.domains.integrations.routes import test,dayton_sync_shipment_tracking
    if run.kind=='connection_check' and run.integration_id:
        if not db.get(IntegrationConnection,run.integration_id):raise HTTPException(404,'Connection no longer exists')
        return await test(run.integration_id,db)
    if run.kind=='tracking_sync' and run.shipment_id:
        connection=db.get(IntegrationConnection,run.integration_id) if run.integration_id else None
        if not connection:raise HTTPException(409,'Original tracking connection is unavailable. Review the shipment before retrying.')
        request=db.info.get('request')
        if request and user.role=='admin':request.state.integration_company_id=connection.customer_id
        return await dayton_sync_shipment_tracking(run.shipment_id,db)
    raise HTTPException(409,'Open the source workspace to review this operation')

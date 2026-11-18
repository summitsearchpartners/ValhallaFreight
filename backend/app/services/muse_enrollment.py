from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Customer, MuseEnrollment, MuseCreditApplication, OperationalNotification, User
from app.integrations.secrets import encrypt_secret_payload
from app.services.muse_credit import TEMPLATE_SHA256
from app.services.email import queue_email


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def manufacturer(db, customer_id, lock=False):
    row=db.get(Customer,customer_id)
    if row is None:raise HTTPException(404,"Company not found")
    root_id=row.manufacturer_id or row.id
    query=select(Customer).where(Customer.id==root_id)
    if lock:query=query.with_for_update().execution_options(populate_existing=True)
    root=db.execute(query).scalar_one_or_none()
    if not root:raise HTTPException(404,"Manufacturer not found")
    return root


def enrollment(db, customer_id, lock=False, create=False):
    root=manufacturer(db,customer_id,lock)
    record=db.get(MuseEnrollment,root.id)
    if record is None and create:
        record=MuseEnrollment(customer_id=root.id,enabled=False,status="not_submitted",decision_note="")
        db.add(record);db.flush()
    return root,record


def status(db, customer_id):
    root,row=enrollment(db,customer_id)
    latest=db.query(MuseCreditApplication).filter_by(customer_id=root.id).order_by(MuseCreditApplication.id.desc()).first()
    return {
        "manufacturer_id":root.id,"manufacturer_name":root.name,
        "enabled":bool(row and row.enabled),"application_status":row.status if row else "not_submitted",
        "can_book":bool(row and row.enabled and row.status=="approved"),
        "decision_note":row.decision_note if row else "",
        "application_id":latest.id if latest else None,
    }


def require_enabled(db, customer_id, *, approved=False, lock=False):
    root,row=enrollment(db,customer_id,lock)
    if not row or not row.enabled:raise HTTPException(403,"Muse rates are not enabled for this manufacturer")
    if approved and row.status!="approved":raise HTTPException(403,"Muse must approve this manufacturer's credit application before booking")
    return root,row


def set_enabled(db, customer_id, value):
    root,row=enrollment(db,customer_id,lock=True,create=True)
    if root.id!=customer_id:raise HTTPException(422,"Set Muse access on the parent manufacturer's profile")
    row.enabled=value
    db.commit()
    return status(db,root.id)


def notify_muse(db, root, subject, body, related_type, related_id):
    db.add(OperationalNotification(audience="muse",notification_type=related_type,customer_id=root.id,
        severity="info",title=subject,body=body,target_path=f"/muse?manufacturer={root.id}"))
    from app.services.muse_partner import has_access
    recipients=[u.email for u in db.query(User).filter(User.role.in_(["broker_admin","muse_admin"]),User.active.is_(True)).all() if has_access(db,u)]
    queue_email(db,to_addresses=recipients,subject=subject,body=body,recipient_type="muse",
        related_type=related_type,related_id=str(related_id),customer_id=root.id)


def submit_application(db, customer_id, payload, user):
    root,row=require_enabled(db,customer_id,lock=True)
    if row.status in {"pending","approved"}:
        raise HTTPException(409,"An application is already pending or approved")
    app=MuseCreditApplication(customer_id=root.id,encrypted_payload=encrypt_secret_payload(payload),
        template_sha256=TEMPLATE_SHA256,submitted_by=user.id,status="pending")
    db.add(app);db.flush()
    row.status="pending";row.decision_note=""
    notify_muse(db,root,"Muse credit application ready for review",
        f"{root.name} submitted a credit application. Sign in to the Muse Portal to review it.",
        "muse_credit_application",app.id)
    db.commit()
    return status(db,root.id)


def decide(db, application_id, decision, note, user):
    app=db.get(MuseCreditApplication,application_id)
    if not app:raise HTTPException(404,"Application not found")
    root,row=require_enabled(db,app.customer_id,lock=True)
    db.refresh(app)
    if app.status!="pending" or row.status!="pending":raise HTTPException(409,"This application has already been reviewed")
    app.status=decision;app.decision_note=note;app.reviewed_by=user.id;app.reviewed_at=now()
    row.status=decision;row.decision_note=note
    db.add(OperationalNotification(audience="internal",notification_type="muse_credit_decision",customer_id=root.id,
        severity="success" if decision=="approved" else "warning",
        title=f"Muse application {decision}",body=f"{root.name}: {note or decision}.",
        target_path="/quotes"))
    db.commit()
    return status(db,root.id)

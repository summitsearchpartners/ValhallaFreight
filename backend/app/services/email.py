from __future__ import annotations
from datetime import datetime
import smtplib
from email.message import EmailMessage
from app.core.config import settings
from app.models import EmailOutbox

def queue_email(db, *, to_addresses:list[str], subject:str, body:str, recipient_type:str='internal', related_type:str='system', related_id:str|None=None, customer_id:int|None=None):
    addresses=sorted({str(x).strip() for x in to_addresses if x and '@' in str(x)})
    if not addresses:
        return None
    row=EmailOutbox(customer_id=customer_id,related_type=related_type,related_id=related_id,recipient_type=recipient_type,to_addresses=addresses,subject=subject,body=body,status='queued')
    db.add(row); db.flush()
    if not settings.smtp_host:
        row.status='captured'  # safe local/dev outbox; visible in Finance Center
        return row
    try:
        msg=EmailMessage(); msg['From']=settings.smtp_from_email; msg['To']=', '.join(addresses); msg['Subject']=subject; msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
            if settings.smtp_use_tls: smtp.starttls()
            if settings.smtp_username: smtp.login(settings.smtp_username,settings.smtp_password)
            smtp.send_message(msg)
        row.status='sent'; row.sent_at=datetime.utcnow()
    except Exception as exc:
        row.status='failed'; row.error=str(exc)
    return row

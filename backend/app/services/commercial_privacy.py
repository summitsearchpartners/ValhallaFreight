"""Customer-facing responses never contain broker buy prices or profit metrics."""
import re
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import json


def customer_view(request):
    if request is None:return False
    user=getattr(request.state,"auth_user",None)
    return bool(user and (user.role in {"manufacturer","manufacturer_admin","customer"} or
                         getattr(request.state,"support_company_id",None) is not None))


def customer_session(db):
    return customer_view(db.info.get("request"))


def protect_pricing_request(db,payload):
    if customer_session(db) and (getattr(payload,"quote_pricing_mode",None) is not None or
                                getattr(payload,"quote_pricing_value",None) is not None):
        raise HTTPException(403,"Quote pricing overrides are managed by your broker")


def _sensitive(key,value):
    name=re.sub(r"[^a-z0-9]","",key.lower())
    return (any(token in name for token in ("carriercost","grossprofit","markup","marginpct","gppct","gpimpact")) or
            name in {"gp","cost","fuel","basecharge","invoicecost","quotedcost","expectedcost","finalcost",
                     "expectedgp","finalgp","protectedgp","minimummargin","marginexceptions","marginexceptioncount","warnings"} or
            (name=="accessorials" and isinstance(value,(str,int,float))))


def public_payload(value):
    if isinstance(value,list):return [public_payload(item) for item in value]
    if not isinstance(value,dict):return value
    out={key:public_payload(item) for key,item in value.items() if not _sensitive(key,item)}
    if value.get("activity_type")=="margin_exception" or value.get("source")=="finance" or str(value.get("title") or "").startswith("Carrier invoice variance"):
        if "title" in out:out["title"]="Shipment billing review"
        for key in ("body","reason","detail"):
            if key in out:out[key]="Shipment billing requires review. Contact your broker for assistance."
    return out


class CommercialPrivacyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        response=await call_next(request)
        if not customer_view(request) or "application/json" not in response.headers.get("content-type",""):
            return response
        body=b"".join([chunk async for chunk in response.body_iterator])
        if not body:return Response(body,status_code=response.status_code,headers=dict(response.headers),background=response.background)
        data=json.loads(body)
        clean=json.dumps(public_payload(data),ensure_ascii=False,separators=(",",":")).encode()
        headers=dict(response.headers)
        headers.pop("content-length",None)
        headers["cache-control"]="private, no-store"
        return Response(clean,status_code=response.status_code,headers=headers,background=response.background)

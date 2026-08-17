from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from io import BytesIO
import math
import pandas as pd
from sqlalchemy.orm import Session
from app.models import Customer, Carrier, Shipment

HEADER_ALIASES = {
    "customer": ["customer", "customer_name", "account", "client"],
    "customer_code": ["customer_code", "account_code", "client_code"],
    "carrier_scac": ["carrier_scac", "scac", "carrier"],
    "shipment_number": ["shipment_number", "shipment", "load_number", "reference"],
    "status": ["status", "shipment_status"],
    "pro_number": ["pro_number", "pro", "pro_no"],
    "bol_number": ["bol_number", "bol", "bill_of_lading"],
    "origin_address": ["origin_address", "origin_street", "shipper_address"],
    "origin_city": ["origin_city", "shipper_city"],
    "origin_state": ["origin_state", "shipper_state"],
    "origin_zip": ["origin_zip", "origin_postal_code", "shipper_zip"],
    "destination_address": ["destination_address", "destination_street", "consignee_address"],
    "destination_city": ["destination_city", "consignee_city"],
    "destination_state": ["destination_state", "consignee_state"],
    "destination_zip": ["destination_zip", "destination_postal_code", "consignee_zip"],
    "customer_charge": ["customer_charge", "revenue", "customer_price", "invoice_amount"],
    "carrier_cost": ["carrier_cost", "expected_carrier_cost", "cost"],
    "final_carrier_cost": ["final_carrier_cost", "actual_carrier_cost", "final_cost"],
    "pickup_date": ["pickup_date", "ship_date"],
    "estimated_delivery": ["estimated_delivery", "estimated_delivery_date", "eta"],
    "delivered_at": ["delivered_at", "delivery_date", "delivered_date"],
}


def _clean_header(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def _value(row, mapping, key):
    col=mapping.get(key)
    if not col: return None
    val=row.get(col)
    if val is None: return None
    try:
        if pd.isna(val): return None
    except Exception: pass
    text=str(val).strip()
    return text if text else None


def _decimal(value):
    if value is None: return Decimal("0")
    text=str(value).replace("$","").replace(",","").strip()
    try: return Decimal(text)
    except Exception: return Decimal("0")


def _date(value):
    if not value: return None
    try:
        parsed=pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed): return None
        return parsed.date()
    except Exception: return None


def _datetime(value):
    if not value: return None
    try:
        parsed=pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed): return None
        return parsed.to_pydatetime()
    except Exception: return None


def read_file(filename: str, content: bytes) -> pd.DataFrame:
    lower=filename.lower()
    if lower.endswith(".csv"):
        return pd.read_csv(BytesIO(content))
    if lower.endswith((".xlsx",".xls")):
        return pd.read_excel(BytesIO(content))
    raise ValueError("Import must be a CSV, XLSX, or XLS file")


def import_shipments(db: Session, filename: str, content: bytes):
    df=read_file(filename,content)
    if df.empty:
        return {"imported":0,"skipped":0,"errors":["The uploaded file contains no rows"]}
    normalized={_clean_header(c):c for c in df.columns}
    mapping={}
    for target,aliases in HEADER_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[target]=normalized[alias]; break
    if not mapping.get("customer") and not mapping.get("customer_code"):
        return {"imported":0,"skipped":len(df),"errors":["A customer or customer_code column is required"]}

    imported=0; skipped=0; errors=[]
    for idx,row in df.iterrows():
        row_no=int(idx)+2
        customer=None
        code=_value(row,mapping,"customer_code")
        name=_value(row,mapping,"customer")
        if code:
            customer=db.query(Customer).filter(Customer.code.ilike(code)).first()
        if not customer and name:
            customer=db.query(Customer).filter(Customer.name.ilike(name)).first()
        if not customer:
            skipped+=1; errors.append(f"Row {row_no}: customer not found ({code or name or 'blank'})"); continue

        carrier=None
        scac=_value(row,mapping,"carrier_scac")
        if scac:
            carrier=db.query(Carrier).filter(Carrier.scac.ilike(scac)).first()

        supplied_number=_value(row,mapping,"shipment_number")
        if supplied_number and db.query(Shipment).filter(Shipment.shipment_number==supplied_number).first():
            skipped+=1; errors.append(f"Row {row_no}: shipment {supplied_number} already exists"); continue
        number=supplied_number or f"VFS-{datetime.utcnow():%y%m%d%H%M%S%f}"
        origin={
            "address1":_value(row,mapping,"origin_address") or "",
            "city":_value(row,mapping,"origin_city") or "",
            "state":(_value(row,mapping,"origin_state") or "").upper(),
            "postal_code":_value(row,mapping,"origin_zip") or "",
            "country":"US",
        }
        destination={
            "address1":_value(row,mapping,"destination_address") or "",
            "city":_value(row,mapping,"destination_city") or "",
            "state":(_value(row,mapping,"destination_state") or "").upper(),
            "postal_code":_value(row,mapping,"destination_zip") or "",
            "country":"US",
        }
        status=(_value(row,mapping,"status") or "booked").strip().lower().replace(" ","_")
        shipment=Shipment(
            shipment_number=number, customer_id=customer.id, carrier_id=carrier.id if carrier else None,
            status=status, pro_number=_value(row,mapping,"pro_number"), bol_number=_value(row,mapping,"bol_number"),
            origin=origin,destination=destination,handling_units=[],accessorials=[],
            carrier_cost=_decimal(_value(row,mapping,"carrier_cost")),
            customer_charge=_decimal(_value(row,mapping,"customer_charge")),
            final_carrier_cost=_decimal(_value(row,mapping,"final_carrier_cost")) if _value(row,mapping,"final_carrier_cost") is not None else None,
            pickup_date=_date(_value(row,mapping,"pickup_date")), estimated_delivery=_date(_value(row,mapping,"estimated_delivery")),
            delivered_at=_datetime(_value(row,mapping,"delivered_at")),
        )
        db.add(shipment); imported+=1
    db.commit()
    return {"imported":imported,"skipped":skipped,"errors":errors[:100]}

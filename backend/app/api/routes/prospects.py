from fastapi import APIRouter, UploadFile, File, HTTPException
import pandas as pd
from io import BytesIO
router = APIRouter(prefix="/prospects", tags=["Prospect Analysis"])
@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        df = pd.read_csv(BytesIO(raw)) if file.filename.lower().endswith('.csv') else pd.read_excel(BytesIO(raw))
    except Exception as e: raise HTTPException(400, f"Could not read file: {e}")
    cols={c.lower().strip():c for c in df.columns}
    def num(name):
        c=cols.get(name); return pd.to_numeric(df[c], errors='coerce') if c else pd.Series(dtype=float)
    spend=num('spend'); weight=num('weight'); charge=num('charge')
    annual_spend=float(spend.sum()) if not spend.empty else float(charge.sum()) if not charge.empty else 0
    shipments=int(len(df)); avg_weight=float(weight.mean()) if not weight.empty and len(weight.dropna()) else 0
    return {"shipments":shipments,"annual_spend":round(annual_spend,2),"avg_spend_per_shipment":round(annual_spend/shipments,2) if shipments else 0,"avg_weight":round(avg_weight,1),"columns":list(df.columns),"message":"Valhalla Freight prospect ingestion is active. Map additional source columns to unlock lane, class, carrier, accessorial and savings analysis."}

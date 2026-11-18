from fastapi import APIRouter,UploadFile,File,HTTPException,Form
from fastapi.responses import Response
import pandas as pd
import json,math
from io import BytesIO
router=APIRouter(prefix='/prospects',tags=['Prospect Analysis'])
FIELDS=['spend','weight','origin_zip','destination_zip','freight_class','carrier']
ALIASES={'spend':['spend','charge','freight_cost','total_charge','total cost'],'weight':['weight','weight_lbs','total_weight'],'origin_zip':['origin_zip','origin postal code'],'destination_zip':['destination_zip','destination postal code'],'freight_class':['freight_class','class'],'carrier':['carrier','carrier_name','scac']}

@router.get('/template')
def template():return Response('spend,weight,origin_zip,destination_zip,freight_class,carrier\n425.50,500,66061,45414,70,Example Carrier\n610.00,1200,66101,75201,85,Example Carrier\n',media_type='text/csv',headers={'Content-Disposition':'attachment; filename="Valhalla_Prospect_Template.csv"'})

async def read_history(file):
    name=(file.filename or '').lower()
    if not name.endswith(('.csv','.xlsx','.xls')):raise HTTPException(422,'Use CSV, XLSX or XLS freight history')
    raw=await file.read(10*1024*1024+1)
    if len(raw)>10*1024*1024:raise HTTPException(413,'File must be 10 MB or smaller')
    try:df=pd.read_csv(BytesIO(raw),dtype=object,nrows=50001) if name.endswith('.csv') else pd.read_excel(BytesIO(raw),dtype=object,nrows=50001)
    except Exception:raise HTTPException(422,'Unable to read this file. Use the CSV template or an Excel worksheet with a header row.')
    if df.empty or len(df)>50000:raise HTTPException(422,'Provide 1–50,000 shipment rows')
    df.columns=[str(c).strip() for c in df.columns]
    if len(set(df.columns))!=len(df.columns):raise HTTPException(422,'Column names must be unique')
    return df

def mapping_for(df,mapping):
    try:chosen=json.loads(mapping) if mapping else None
    except ValueError:raise HTTPException(422,'Column mapping must be valid JSON')
    if chosen is None:
        cols={c.lower():c for c in df.columns};chosen={k:next((cols[a] for a in ALIASES[k] if a in cols),'') for k in FIELDS}
    if not isinstance(chosen,dict) or any(k not in FIELDS or not isinstance(v,str) or v and v not in df.columns for k,v in chosen.items()):raise HTTPException(422,'Select source columns that exist in the uploaded file')
    values=[v for v in chosen.values() if v]
    if len(values)!=len(set(values)):raise HTTPException(422,'Map each source column only once')
    return chosen

def validate(df,chosen):
    issues=[]
    for key in ['spend','weight']:
        col=chosen.get(key)
        if not col:issues.append(f'Map a required {key} column');continue
        numeric=pd.to_numeric(df[col].astype(str).str.replace(r'[$,]','',regex=True),errors='coerce')
        bad=numeric.isna()|~numeric.map(lambda v:math.isfinite(v) if pd.notna(v) else False)|(numeric<0 if key=='spend' else numeric<=0)
        if bad.any():issues.append(f'{key}: invalid values on file rows '+', '.join(str(i+2) for i in list(df.index[bad])[:10])+(' (more rows omitted)' if int(bad.sum())>10 else ''))
    return issues

@router.post('/preview')
async def preview(file:UploadFile=File(...),mapping:str|None=Form(None)):
    df=await read_history(file);chosen=mapping_for(df,mapping);issues=validate(df,chosen)
    sample=df.head(10).astype(object).where(pd.notna(df.head(10)),None)
    return {'columns':list(df.columns),'mapping':chosen,'rows':len(df),'sample':sample.to_dict(orient='records'),'issues':issues,'valid':not issues}

@router.post('/analyze')
async def analyze(file:UploadFile=File(...),mapping:str|None=Form(None)):
    df=await read_history(file);chosen=mapping_for(df,mapping);issues=validate(df,chosen)
    if issues:raise HTTPException(422,'; '.join(issues))
    def numeric(key):return pd.to_numeric(df[chosen[key]].astype(str).str.replace(r'[$,]','',regex=True))
    spend=float(numeric('spend').sum());weight=float(numeric('weight').mean());rows=len(df)
    return {'shipments':rows,'spend_total':round(spend,2),'annual_spend':round(spend,2),'avg_spend_per_shipment':round(spend/rows,2),'avg_weight':round(weight,1),'columns':list(df.columns),'message':'Analysis covers only the uploaded rows. Spend and shipment counts are not annualized; no savings estimate is inferred without comparable rates.'}

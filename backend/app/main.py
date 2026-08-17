from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.services.seed import seed
from app.api.routes import customers, carriers, pricing, quotes, shipments, dashboard, prospects

app = FastAPI(title=settings.app_name, version="0.1.0", description="FreightForge LTL-first Transportation Management System")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db=SessionLocal()
    try: seed(db)
    finally: db.close()

@app.get("/health")
def health(): return {"status":"ok","service":"FreightForge API"}

app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(carriers.router, prefix="/api/v1")
app.include_router(pricing.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(shipments.router, prefix="/api/v1")
app.include_router(prospects.router, prefix="/api/v1")

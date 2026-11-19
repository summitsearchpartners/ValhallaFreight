import app.services.safe_load_custody
from app.api.routes import truckload,safe_load
import app.services.safe_load
from app.api.routes import muse_partner, portal_administration, muse, operations
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.db.schema_updates import apply_schema_updates
from app.services.seed import seed
from app.api.routes import portal_access, users, carriers, pricing, quotes, shipments, dashboard, prospects, auth, notifications, workspace
from app.domains.customers import routes as customers
from app.api.deps import get_current_user
from app.api.permissions import internal_access
import app.db.tenant_scope  # Register company isolation for request sessions
from app.domains.carriers import routes as carrier360
from app.domains.capacity import routes as capacity
from app.domains.finance import routes as finance
from app.domains.claims import routes as claims
from app.domains.integrations import routes as integrations
from app.domains.intelligence import routes as intelligence
from app.domains.portal import routes as portal

app = FastAPI(title=settings.app_name, version="0.19.28", description="Valhalla TMS Transportation Operating System")
from app.services.user_activity import ActivityMiddleware
from app.services.commercial_privacy import CommercialPrivacyMiddleware
app.add_middleware(ActivityMiddleware)
app.add_middleware(CommercialPrivacyMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(',')], allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Portal-Session-Invalid"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    apply_schema_updates(engine)
    db=SessionLocal()
    try:
        seed(db)
        from app.services.muse_partner import initialize
        initialize(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"status":"ok","service":"Valhalla TMS API"}

app.include_router(muse_partner.router, prefix="/api/v1")
app.include_router(portal_administration.router, prefix="/api/v1")
app.include_router(muse.router, prefix="/api/v1")
app.include_router(portal_access.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspace.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(customers.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(carriers.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(pricing.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(quotes.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(shipments.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(prospects.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(notifications.router, prefix="/api/v1", dependencies=[Depends(internal_access)])

app.include_router(carrier360.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(capacity.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(finance.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(claims.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(integrations.router, prefix="/api/v1", dependencies=[Depends(internal_access)])
app.include_router(intelligence.router, prefix="/api/v1", dependencies=[Depends(internal_access)])

app.include_router(portal.router, prefix="/api/v1")

app.include_router(operations.router,prefix="/api/v1",dependencies=[Depends(internal_access)])

app.include_router(truckload.router,prefix="/api/v1")
app.include_router(safe_load.router,prefix="/api/v1")

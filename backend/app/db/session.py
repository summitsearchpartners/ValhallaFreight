from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import Request
from app.core.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db(request: Request):
    db = SessionLocal()
    db.info["request"] = request
    request.state.activity_engine = db.get_bind()
    try:
        yield db
    finally:
        db.close()

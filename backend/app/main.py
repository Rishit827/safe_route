import inspect
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import Hazard, HazardVersion
from app.collectors.mock import collect_mock
from app.collectors.sachet import collect_sachet
from app.collectors.firms import collect_firms
from app.collectors.openmeteo import collect_openmeteo
from app.services.normalizer import upsert_hazard
from app.services.events import event_bus
from app.routers import public, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("saferoute")
scheduler = AsyncIOScheduler()

async def refresh_collectors():
    """Run each collector independently so one unavailable provider cannot stop others."""
    if settings.use_mock_data:
        batches = [("mock", collect_mock)]
    else:
        batches = [("sachet", collect_sachet), ("firms", collect_firms), ("openmeteo", collect_openmeteo)]
    errors, imported = [], 0
    for name, collector in batches:
        try:
            rows = collector()
            if inspect.isawaitable(rows):
                rows = await rows
            db = SessionLocal()
            try:
                for row in rows:
                    upsert_hazard(db, row)
                    imported += 1
                db.commit()
            finally:
                db.close()
        except Exception as exc:
            logger.exception("Collector %s failed", name)
            errors.append(f"{name}: {exc}")
    if imported:
        event_bus.publish("collector_refresh")
    return {"message": "Refresh complete", "imported": imported, "errors": errors}

def seed_database():
    db = SessionLocal()
    try:
        # Stable IDs and upsert make startup seeding idempotent.
        if settings.use_mock_data:
            for row in collect_mock():
                upsert_hazard(db, row)
        if db.get(HazardVersion, 1) is None:
            db.add(HazardVersion(id=1, version=1))
        db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is fine for a demo; use Alembic migrations for production schema evolution.
    Base.metadata.create_all(bind=engine)
    seed_database()
    scheduler.add_job(refresh_collectors, "interval", minutes=max(1, settings.collection_interval_minutes), id="collectors", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title=settings.app_name, version="1.0.0", description="SafeRoute emergency hazard and safe routing API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(public.router)
app.include_router(admin.router)

@app.get("/")
def root():
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/health"}

import asyncio, json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db, database_type
from app.models import Hazard
from app.schemas import RouteRequest, HazardOut
from app.services.scoring import scored_hazards
from app.services.routing import calculate_routes, RoutingError
from app.services.events import event_bus

router = APIRouter(prefix="/api", tags=["public"])

def _active(h):
    if h.expires_at is None:
        return True
    expires = h.expires_at
    # SQLite may return naive datetimes despite timezone=True; treat them as UTC.
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires > datetime.now(timezone.utc)

def _hazard_dict(scored):
    h = scored["hazard"]
    return {**{c.name: getattr(h, c.name) for c in h.__table__.columns if c.name != "metadata"},
            "final_score": scored["final_score"], "treatment": scored["treatment"]}

@router.get("/health")
def health():
    return {"status": "ok", "database": database_type(), "time": datetime.now(timezone.utc).isoformat()}

@router.get("/hazards")
def list_hazards(type: str | None = None, min_lat: float | None = None, max_lat: float | None = None,
                 min_lng: float | None = None, max_lng: float | None = None, db: Session = Depends(get_db)):
    query = db.query(Hazard).filter(Hazard.admin_status != "dismissed")
    if type: query = query.filter(Hazard.type == type)
    if min_lat is not None: query = query.filter(Hazard.lat >= min_lat)
    if max_lat is not None: query = query.filter(Hazard.lat <= max_lat)
    if min_lng is not None: query = query.filter(Hazard.lng >= min_lng)
    if max_lng is not None: query = query.filter(Hazard.lng <= max_lng)
    hazards = [h for h in query.all() if _active(h)]
    return [_hazard_dict(s) for s in scored_hazards(hazards) if s["treatment"] != "ignored"]

@router.get("/alerts")
def alerts(db: Session = Depends(get_db)):
    return [h for h in list_hazards(db=db) if h["source"] != "admin"]

@router.get("/hazards/version")
def hazards_version():
    return {"version": event_bus.version, "last_updated": event_bus.updated_at}

@router.get("/stream")
async def stream():
    async def events():
        async for queue in event_bus.subscribe():
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"event: hazards_changed\ndata: {json.dumps(item)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@router.post("/route")
async def route(request: RouteRequest, db: Session = Depends(get_db)):
    hazards = [h for h in db.query(Hazard).filter(Hazard.admin_status != "dismissed").all() if _active(h)]
    scored = scored_hazards(hazards)
    try:
        return await calculate_routes(request.start, request.end, scored)
    except RoutingError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Routing provider failed: {exc}")

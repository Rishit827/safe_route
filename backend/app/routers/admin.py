from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Hazard, AppSetting
from app.schemas import LoginRequest, TokenResponse, RateRequest, ConfirmRequest, VerifyRequest, SettingsUpdate
from app.auth import create_access_token, require_admin, verify_password, get_password_hash
from app.config import settings
from app.services.normalizer import upsert_hazard
from app.services.scoring import scored_hazards
from app.services.events import event_bus

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if body.username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    valid = verify_password(body.password, settings.admin_password_hash) if settings.admin_password_hash else body.password == settings.admin_password
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_access_token(body.username), "token_type": "bearer"}

@router.get("/hazards")
def admin_hazards(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return [{**{c.name: getattr(s["hazard"], c.name) for c in s["hazard"].__table__.columns if c.name != "metadata"},
             "final_score": s["final_score"], "treatment": s["treatment"]} for s in scored_hazards(db.query(Hazard).all())]

@router.post("/hazards/{hazard_id}/rate")
def rate_hazard(hazard_id: str, body: RateRequest, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    hazard = db.get(Hazard, hazard_id)
    if not hazard: raise HTTPException(status_code=404, detail="Hazard not found")
    hazard.admin_rating = body.rating
    hazard.updated_at = datetime.now(timezone.utc)
    db.commit()
    event_bus.publish("hazard_rated")
    return {"id": hazard.id, "rating": hazard.admin_rating, "treatment": scored_hazards([hazard])[0]["treatment"]}

@router.post("/hazards/{hazard_id}/confirm")
def confirm_hazard(hazard_id: str, body: ConfirmRequest, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    hazard = db.get(Hazard, hazard_id)
    if not hazard: raise HTTPException(status_code=404, detail="Hazard not found")
    hazard.admin_status = body.status
    hazard.updated_at = datetime.now(timezone.utc)
    if body.status == "confirmed": hazard.verified = True
    db.commit()
    event_bus.publish("hazard_confirmed")
    return {"id": hazard.id, "status": hazard.admin_status}

@router.post("/verify")
def verify(body: VerifyRequest, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    item = {"id": None, "external_id": None, "type": body.type, "title": body.title,
        "description": body.description or body.notes, "lat": body.lat, "lng": body.lng,
        "radius_m": body.radius_m, "source": "admin", "severity": body.rating,
        "confidence": 1.0, "admin_rating": body.rating, "verified": True,
        "admin_status": "confirmed", "metadata_json": {"notes": body.notes, "who_was_called": body.who_was_called}}
    hazard = upsert_hazard(db, item)
    db.commit()
    event_bus.publish("field_verification")
    return {"id": hazard.id, "verified": True, "rating": hazard.admin_rating}

@router.post("/refresh")
async def refresh(_: str = Depends(require_admin)):
    from app.main import refresh_collectors
    result = await refresh_collectors()
    return result

@router.get("/settings")
def get_admin_settings(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    row = db.get(AppSetting, "thresholds")
    return {"values": row.value if row else {"rain_threshold_mm": settings.openmeteo_rain_threshold_mm,
            "hazard_group_distance_m": settings.hazard_group_distance_m, "route_penalty_weight": settings.route_penalty_weight}}

@router.put("/settings")
def put_admin_settings(body: SettingsUpdate, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    allowed = {"rain_threshold_mm", "hazard_group_distance_m", "route_penalty_weight"}
    if set(body.values) - allowed:
        raise HTTPException(status_code=400, detail=f"Allowed keys: {sorted(allowed)}")
    row = db.get(AppSetting, "thresholds")
    if row is None: row = AppSetting(key="thresholds", value={}); db.add(row)
    row.value = body.values
    db.commit()
    return {"values": row.value, "note": "Stored settings; environment-backed collector settings take effect after restart."}

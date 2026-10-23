from datetime import datetime, timezone
from hashlib import sha256
from app.models import Hazard

def parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def stable_id(source: str, external_id: str | None, kind: str, lat: float, lng: float, title: str) -> str:
    raw = external_id or f"{source}|{kind}|{lat:.4f}|{lng:.4f}|{title}"
    return f"{source}_" + sha256(raw.encode()).hexdigest()[:24]

ADMIN_OWNED = {"admin_status", "admin_rating", "verified"}

def upsert_hazard(db, item: dict) -> Hazard:
    """Portable SQLAlchemy upsert implemented as select/update/insert."""
    external_id = item.get("external_id")
    hazard_id = item.get("id") or stable_id(item["source"], external_id, item["type"], item["lat"], item["lng"], item["title"])
    row = db.get(Hazard, hazard_id)
    if row is None and external_id:
        row = db.query(Hazard).filter(Hazard.external_id == external_id).one_or_none()
    payload = dict(item)
    payload["id"] = hazard_id
    payload["created_at"] = parse_time(payload.get("created_at")) or datetime.now(timezone.utc)
    payload["updated_at"] = datetime.now(timezone.utc)
    payload["expires_at"] = parse_time(payload.get("expires_at"))
    if row:
        for key, value in payload.items():
            if key in ("id", "created_at") or not hasattr(row, key):
                continue
            if key in ADMIN_OWNED and item.get("source") != "admin":
                continue  # collectors never overwrite what the admin decided
            setattr(row, key, value)
    else:
        row = Hazard(**payload)
        db.add(row)
    return row

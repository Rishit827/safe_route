import csv, io
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.collectors.base import fetch_text

async def collect_firms():
    if not settings.firms_map_key: return []
    min_lon, min_lat, max_lon, max_lat = settings.bbox
    # NASA FIRMS area API: adjust source endpoint if using a different active-fire dataset.
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{settings.firms_map_key}/VIIRS_SNPP_NRT/{min_lon},{min_lat},{max_lon},{max_lat}/2"
    text = await fetch_text(url)
    results = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            lat, lng = float(row["latitude"]), float(row["longitude"])
            confidence_raw = str(row.get("confidence", "nominal")).lower()
            confidence = float(confidence_raw)/100 if confidence_raw.isdigit() else {"high": .9, "h": .9, "nominal": .65, "n": .65, "low": .4, "l": .4}.get(confidence_raw, .5)
            brightness = float(row.get("bright_ti4", row.get("brightness", 300)) or 300)
            severity = 5 if brightness >= 400 or confidence >= .9 else 4 if brightness >= 350 else 3
            external = str(row.get("acq_date", "")) + ":" + str(row.get("acq_time", "")) + ":" + f"{lat:.4f}:{lng:.4f}"
            results.append({"id": "firms_"+external.replace(":", "_"), "external_id": "firms:"+external,
                "type": "fire", "title": "Satellite fire hotspot", "description": f"FIRMS brightness {brightness}; confidence {confidence:.2f}",
                "lat": lat, "lng": lng, "radius_m": 250, "source": "firms", "severity": severity,
                "confidence": confidence, "admin_status": "pending", "verified": False,
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                "metadata_json": {"brightness": brightness, "acq_date": row.get("acq_date")}})
        except (KeyError, ValueError, TypeError):
            continue
    return results

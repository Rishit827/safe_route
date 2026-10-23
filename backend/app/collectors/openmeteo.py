"""Open-Meteo rainfall collector for a configurable geographic bounding box."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.collectors.base import fetch_text

logger = logging.getLogger(__name__)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if number >= 0 else None
    except (TypeError, ValueError):
        return None


def _locations(data: Any) -> list[dict[str, Any]]:
    """Normalize Open-Meteo's single-location and multi-location response shapes."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        return [item for item in data["results"] if isinstance(item, dict)]
    if isinstance(data, dict):
        return [data]
    return []


async def collect_openmeteo() -> list[dict[str, Any]]:
    min_lon, min_lat, max_lon, max_lat = settings.bbox
    n = max(2, min(8, int(settings.region_grid_size)))
    points = [
        (min_lat + (max_lat - min_lat) * i / (n - 1),
         min_lon + (max_lon - min_lon) * j / (n - 1))
        for i in range(n) for j in range(n)
    ]
    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": "precipitation,rain,showers",
        "forecast_days": 1,
        "timezone": "UTC",
    }
    try:
        raw = await fetch_text(OPEN_METEO_URL, params=params)
        data = json.loads(raw)
    except Exception as exc:
        logger.warning("Open-Meteo request/JSON parsing failed: %s", exc)
        return []

    locations = _locations(data)
    if not locations:
        logger.warning("Open-Meteo returned no location results")
        return []
    threshold = max(0.0, float(settings.openmeteo_rain_threshold_mm))
    now = datetime.now(timezone.utc)
    expiry = (now + timedelta(hours=3)).isoformat()
    results: list[dict[str, Any]] = []

    for idx, loc in enumerate(locations):
        hourly = loc.get("hourly") or {}
        # precipitation is total water equivalent (rain + showers + snow); use it
        # when present and avoid double-counting the separate rain/showers fields.
        values = hourly.get("precipitation")
        if not isinstance(values, list):
            values = []
        valid_values = [value for value in (_number(v) for v in values) if value is not None]
        if not valid_values:
            rain = hourly.get("rain") if isinstance(hourly.get("rain"), list) else []
            showers = hourly.get("showers") if isinstance(hourly.get("showers"), list) else []
            valid_values = [sum(v for v in (_number(r), _number(s)) if v is not None)
                            for r, s in zip(rain, showers)]
        if not valid_values:
            continue
        peak = max(valid_values)
        if peak < threshold:
            continue

        # Use coordinates returned by the API, since it may normalize/round input.
        try:
            lat = float(loc.get("latitude", points[min(idx, len(points) - 1)][0]))
            lng = float(loc.get("longitude", points[min(idx, len(points) - 1)][1]))
        except (TypeError, ValueError):
            lat, lng = points[min(idx, len(points) - 1)]
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        peak_index = valid_values.index(peak)
        times = hourly.get("time") if isinstance(hourly.get("time"), list) else []
        peak_time = times[peak_index] if peak_index < len(times) else None
        severity = 5 if peak >= threshold * 3 else 4 if peak >= threshold * 2 else 3
        results.append({
            "id": f"openmeteo_{lat:.4f}_{lng:.4f}",
            "external_id": f"openmeteo:{lat:.4f}:{lng:.4f}",
            "type": "flood",
            "title": "Heavy rainfall / potential flood risk",
            "description": f"Open-Meteo forecast precipitation peak: {peak:.1f} mm in one hour",
            "lat": lat, "lng": lng, "radius_m": 1800,
            "source": "openmeteo", "severity": severity, "confidence": 0.45,
            "admin_status": "pending", "verified": False, "expires_at": expiry,
            "metadata_json": {
                "peak_precipitation_mm": peak,
                "peak_time_utc": peak_time,
                "threshold_mm": threshold,
                "forecast_hours": len(valid_values),
                "provider": "Open-Meteo",
                "note": "Forecast signal only; requires verification and is not proof of flooding.",
            },
        })
    logger.info("Open-Meteo collector produced %d rainfall-risk points from %d locations", len(results), len(locations))
    return results

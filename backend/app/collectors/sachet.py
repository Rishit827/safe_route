"""Collector/parser for the official NDMA SACHET India CAP/RSS feed."""
from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

from app.config import settings
from app.collectors.base import fetch_text

logger = logging.getLogger(__name__)
DEFAULT_SACHET_FEED = "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if _local(child.tag) == name.lower()]


def _text(node: ET.Element, name: str, default: str = "") -> str:
    found = _children(node, name)
    return (found[0].text or "").strip() if found else default


def _parse_time(value: str) -> str | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError, OverflowError):
            return None


def _coords_from_area(area: ET.Element) -> tuple[float, float, float] | None:
    """Return (lat, lon, radius_m) from CAP circle or polygon geometry."""
    circles = _children(area, "circle")
    for circle in circles:
        # CAP circle is latitude,longitude radius-in-km.
        numbers = re.split(r"[\s,]+", (circle.text or "").strip())
        if len(numbers) >= 3:
            try:
                lat, lon, radius_km = map(float, numbers[:3])
                if -90 <= lat <= 90 and -180 <= lon <= 180 and radius_km >= 0:
                    return lat, lon, max(100.0, radius_km * 1000)
            except ValueError:
                pass
    for polygon in _children(area, "polygon"):
        points: list[tuple[float, float]] = []
        for pair in re.split(r"\s+", (polygon.text or "").strip()):
            try:
                lat_s, lon_s = pair.split(",", 1)
                lat, lon = float(lat_s), float(lon_s)
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    points.append((lat, lon))
            except (ValueError, TypeError):
                continue
        if points:
            return (sum(p[0] for p in points) / len(points),
                    sum(p[1] for p in points) / len(points), 1000.0)
    # Some feeds expose geocoded coordinates as explicit latitude/longitude.
    lat_text, lon_text = _text(area, "latitude"), _text(area, "longitude")
    try:
        lat, lon = float(lat_text), float(lon_text)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon, 1000.0
    except ValueError:
        pass
    return None


def _severity(value: str) -> int:
    key = (value or "").strip().lower()
    if key in {"extreme", "red", "immediate"}:
        return 5
    if key in {"severe", "orange", "high"}:
        return 4
    if key in {"moderate", "yellow", "moderate risk"}:
        return 3
    if key in {"minor", "green", "low"}:
        return 2
    return 2


def _item(identifier: str, event: str, lat: float, lng: float, title: str,
          description: str, severity: str, expires: str | None,
          radius: float = 1000.0, sender: str = "", effective: str | None = None,
          area_desc: str = "") -> dict[str, Any]:
    e = f"{event} {title} {description}".lower()
    kind = "flood" if any(x in e for x in ("flood", "rain", "waterlogging", "inundation")) else \
           "fire" if any(x in e for x in ("fire", "wildfire", "forest fire")) else "other"
    safe_id = identifier.strip() or f"{lat:.5f}_{lng:.5f}_{event[:24]}"
    return {
        "id": f"sachet_{safe_id}", "external_id": f"sachet:{safe_id}",
        "type": kind, "title": title or event or "Official SACHET alert",
        "description": description or event or "Official disaster alert",
        "lat": lat, "lng": lng, "radius_m": radius, "source": "sachet",
        "severity": _severity(severity), "confidence": 0.9,
        "admin_status": "pending", "verified": False, "expires_at": _parse_time(expires or ""),
        "metadata_json": {"event": event, "sender": sender, "effective": _parse_time(effective or ""),
                          "area": area_desc, "official_source": "NDMA SACHET CAP/RSS"},
    }


def _parse_cap_alert(alert: ET.Element, index: int) -> list[dict[str, Any]]:
    identifier = _text(alert, "identifier", str(index))
    sender = _text(alert, "sender")
    expires = _text(alert, "expires")
    effective = _text(alert, "effective") or _text(alert, "onset")
    items = []
    infos = _children(alert, "info")
    for info in infos or [alert]:
        event = _text(info, "event", "Official alert")
        headline = _text(info, "headline", event)
        description = _text(info, "description", event)
        severity = _text(info, "severity", "Unknown")
        areas = _children(info, "area")
        for area in areas:
            coords = _coords_from_area(area)
            if not coords:
                continue
            lat, lng, radius = coords
            items.append(_item(identifier, event, lat, lng, headline, description, severity,
                               expires, radius, sender, effective, _text(area, "areadesc")))
    return items


def parse_sachet(text: str) -> list[dict[str, Any]]:
    """Parse NDMA RSS items containing CAP alerts, direct CAP XML, or JSON feeds."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if data is not None:
        raw = data if isinstance(data, list) else data.get("alerts", data.get("features", [])) if isinstance(data, dict) else []
        if isinstance(raw, dict):
            raw = [raw]
        output = []
        for i, alert in enumerate(raw):
            if not isinstance(alert, dict):
                continue
            props = alert.get("properties", alert)
            if not isinstance(props, dict):
                continue
            coords = props.get("coordinates") or props.get("geometry", {}).get("coordinates")
            lat, lng = props.get("lat", props.get("latitude")), props.get("lng", props.get("longitude"))
            if (lat is None or lng is None) and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                # GeoJSON is longitude, latitude; direct coordinate arrays may be lat, longitude.
                lng, lat = coords[0], coords[1]
            try:
                if lat is None or lng is None:
                    continue
                info = props.get("info", {})
                if isinstance(info, list):
                    info = info[0] if info else {}
                if not isinstance(info, dict):
                    info = {}
                output.append(_item(str(props.get("identifier", props.get("id", i))),
                    str(info.get("event", props.get("event", "Official alert"))), float(lat), float(lng),
                    str(info.get("headline", props.get("title", ""))), str(info.get("description", "")),
                    str(info.get("severity", props.get("severity", "Unknown"))),
                    info.get("expires", props.get("expires")), float(props.get("radius_m", 1000))))
            except (TypeError, ValueError):
                continue
        return output

    try:
        root = ET.fromstring(text.lstrip("\ufeff \n\r\t"))
    except ET.ParseError as exc:
        logger.warning("SACHET feed was not valid XML/CAP: %s", exc)
        return []

    output: list[dict[str, Any]] = []
    # Direct CAP document.
    if _local(root.tag) == "alert":
        output.extend(_parse_cap_alert(root, 0))
    else:
        # NDMA endpoint is RSS; item descriptions may contain an embedded CAP alert,
        # or the RSS item itself may contain CAP fields.
        for index, node in enumerate(n for n in root.iter() if _local(n.tag) in {"item", "entry", "alert"}):
            if _local(node.tag) == "alert":
                output.extend(_parse_cap_alert(node, index))
                continue
            embedded = []
            for child in node.iter():
                raw = child.text or ""
                if raw.lstrip().startswith("<") and "<alert" in raw.lower():
                    try:
                        embedded_root = ET.fromstring(raw)
                        embedded.extend(_parse_cap_alert(embedded_root, index))
                    except ET.ParseError:
                        pass
            if embedded:
                output.extend(embedded)
                continue
            # A few RSS variants expose CAP fields directly within item.
            output.extend(_parse_cap_alert(node, index))
    # Deduplicate items when RSS contains both an embedded alert and CAP fields.
    deduped, seen = [], set()
    for item in output:
        key = (item["external_id"], round(item["lat"], 5), round(item["lng"], 5))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


async def collect_sachet():
    url = (settings.sachet_feed_url or DEFAULT_SACHET_FEED).strip()
    try:
        text = await fetch_text(url, headers={"Accept": "application/rss+xml, application/xml, text/xml, */*"})
        alerts = parse_sachet(text)
        logger.info("SACHET collector parsed %d geolocated alerts from %s", len(alerts), url)
        return alerts
    except Exception as exc:
        # A broken/unavailable external feed must not crash all collectors.
        logger.warning("SACHET collection failed: %s", exc)
        return []

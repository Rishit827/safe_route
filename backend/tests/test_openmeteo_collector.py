import json
import pytest
from app.collectors import openmeteo


@pytest.mark.asyncio
async def test_openmeteo_multi_location_parses_peak_rain(monkeypatch):
    payload = [
        {"latitude": 31.5, "longitude": 74.8,
         "hourly": {"time": ["2026-10-22T01:00", "2026-10-22T02:00"], "precipitation": [5, 30]}},
        {"latitude": 31.6, "longitude": 74.9,
         "hourly": {"time": ["2026-10-22T01:00", "2026-10-22T02:00"], "precipitation": [0, 2]}},
    ]
    async def fake_fetch(url, params=None, headers=None, attempts=3):
        return json.dumps(payload)
    monkeypatch.setattr(openmeteo, "fetch_text", fake_fetch)
    monkeypatch.setattr(openmeteo.settings, "openmeteo_rain_threshold_mm", 25.0)
    results = await openmeteo.collect_openmeteo()
    assert len(results) == 1
    assert results[0]["lat"] == 31.5
    assert results[0]["lng"] == 74.8
    assert results[0]["severity"] == 3
    assert results[0]["metadata_json"]["peak_precipitation_mm"] == 30


@pytest.mark.asyncio
async def test_openmeteo_failure_returns_empty_list(monkeypatch):
    async def fake_fetch(url, params=None, headers=None, attempts=3):
        raise RuntimeError("network unavailable")
    monkeypatch.setattr(openmeteo, "fetch_text", fake_fetch)
    assert await openmeteo.collect_openmeteo() == []

# SafeRoute Backend

FastAPI backend for SafeRoute: hazard ingestion, admin review, hazard scoring, and normal-versus-safer route comparison.

## Architecture
- FastAPI exposes public read-only endpoints and JWT-protected admin endpoints.
- SQLAlchemy 2.x models use a single `DATABASE_URL` for SQLite or PostgreSQL.
- Independent async collectors ingest SACHET, NASA FIRMS, and Open-Meteo data; mock mode seeds deterministic demo hazards.
- Scoring cross-checks nearby hazards from independent sources, then applies admin ratings as authoritative.
- Shapely builds circular avoid polygons and checks route/hazard intersections.
- APScheduler refreshes external sources on a configurable interval; `/api/stream` provides SSE notifications.

## Requirements and setup
Python 3.11+ is recommended.

### Windows
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. Default local admin is `admin` / `change-this-password`; change both before any deployment. Mock mode is enabled by default and works without API keys or internet access for the data source. If routing has no ORS key, mock mode returns a clearly labelled straight-line stub route.

## Environment variables
See `.env.example`. Important settings:
- `USE_MOCK_DATA=true`: use seeded sample hazards; set false to run external collectors.
- `DATABASE_URL`: SQLite by default or PostgreSQL connection URL.
- `SACHET_FEED_URL`: CAP/XML or JSON feed URL; formats vary by provider, so adjust parsing in `app/collectors/sachet.py` if required.
- `FIRMS_MAP_KEY`: free NASA FIRMS map key.
- `ORS_API_KEY`: OpenRouteService API key.
- `REGION_BBOX`: `min_lon,min_lat,max_lon,max_lat`.
- `CORS_ORIGINS`: comma-separated frontend origins.
- `ADMIN_PASSWORD_HASH`: optional bcrypt hash; if blank, `ADMIN_PASSWORD` is used.

## Switching to PostgreSQL
1. Create a free database project at Supabase or Neon.
2. Copy its PostgreSQL connection string from the provider dashboard.
3. Set `DATABASE_URL` in `.env` to a SQLAlchemy-compatible URL, e.g. `postgresql+psycopg2://user:password@host:5432/dbname?sslmode=require`. Legacy `postgres://` and `postgresql://` prefixes are normalized automatically.
4. Restart the app. No code changes are needed. `psycopg2-binary` is included in `requirements.txt` and is only needed when using PostgreSQL.
5. Free application hosts often have ephemeral disks; SQLite database files may be wiped on redeploy. Use PostgreSQL for deployed environments where data must persist.

## Data collectors
- SACHET: `SACHET_FEED_URL` is intentionally configurable because the exact feed URL and schema can vary. The tolerant parser handles common CAP XML circle fields and common JSON alert/feature shapes.
- NASA FIRMS: uses the VIIRS SNPP NRT area CSV endpoint for the configured bounding box and recent two-day window.
- Open-Meteo: checks precipitation forecast points across the configured region. Threshold is a configurable peak hourly precipitation value, so calibrate it for your region and forecast product.
- Collectors have timeout/retry behavior, are isolated from each other, and do not run per user request.

## API endpoints
### Public
- `GET /api/health` — service and database type.
- `GET /api/hazards` — active hazards, optional `type`, `min_lat`, `max_lat`, `min_lng`, `max_lng`.
- `GET /api/alerts` — active non-admin-source alerts.
- `POST /api/route` — returns normal and safe route features plus warnings.
- `GET /api/hazards/version` — cheap version/last-updated poll endpoint.
- `GET /api/stream` — Server-Sent Events (`hazards_changed`) when this process updates hazard state.

### Admin (Bearer JWT required except login)
- `POST /api/admin/login`
- `GET /api/admin/hazards`
- `POST /api/admin/hazards/{id}/rate`
- `POST /api/admin/hazards/{id}/confirm`
- `POST /api/admin/verify`
- `POST /api/admin/refresh`
- `GET /api/admin/settings`
- `PUT /api/admin/settings`

### Example requests
Login:
```bash
curl -X POST http://localhost:8000/api/admin/login -H "Content-Type: application/json" -d '{"username":"admin","password":"change-this-password"}'
```
Rate a hazard (replace token and ID):
```bash
curl -X POST http://localhost:8000/api/admin/hazards/mock_blocked_bridge/rate -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{"rating":5}'
```
Request routes:
```bash
curl -X POST http://localhost:8000/api/route -H "Content-Type: application/json" -d '{"start":{"lat":31.6300,"lng":74.8700},"end":{"lat":31.6500,"lng":74.8900}}'
```

## Tests
```bash
pytest -q
```

## Production notes
This is a hackathon-ready baseline, not a certified emergency dispatch system. Validate every provider schema and routing behavior before real-world safety use. Use HTTPS, strong secrets, migrations with Alembic, monitoring, rate limiting, and a proper password/secret management system for deployment.

### SACHET and Open-Meteo collector configuration

- `SACHET_FEED_URL` defaults in `.env.example` to the official NDMA India CAP/RSS feed: `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml`. The collector also uses this URL when the setting is blank. SACHET alerts without usable location geometry are skipped rather than plotted at a guessed location.
- Open-Meteo is keyless for the standard forecast endpoint. The collector queries the configured `REGION_BBOX` using a grid of locations and compares the maximum hourly precipitation against `OPENMETEO_RAIN_THRESHOLD_MM`. Rainfall is a forecast risk signal, not proof that a road is flooded; alerts remain pending admin verification.
- To test collector parsing: `PYTHONPATH=. pytest -q tests/test_sachet_collector.py tests/test_openmeteo_collector.py`.

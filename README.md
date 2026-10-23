# 🛟 SafeRoute

**A human-verified emergency routing system.** SafeRoute collects hazard signals from official and satellite sources, lets an admin verify and rate them, and gives users a safer route that avoids confirmed danger zones, updated live on the map.

> Built for HackerWrath 3.0 · Problem Statement 2: Emergency Routing

**Live demo:** _add your Vercel URL here_ · **API docs:** _add your Render URL_`/docs`

---

## The problem

During floods, fires and road blockages, normal navigation apps keep sending people through danger because they don't know about local hazards. Raw data feeds alone are not enough either: satellite and weather signals are early warnings, not proof that a road is closed, and false closures waste response time.

## Our approach

SafeRoute combines automated data with **human verification**:

1. **Collect:** hazards are pulled from three independent sources.
2. **Verify:** an admin reviews each alert, or phones a local person and records a field-verified hazard.
3. **Rate:** the admin rates each hazard from 1 to 5.
4. **Route:** users see their normal route next to a safe route that bends around verified hazards.

| Rating | Treatment | Effect on routing |
|---|---|---|
| 1-2 | Flagged | Shown on the map only |
| 3-4 | Penalised | Avoided if a reasonable alternative exists |
| 5 | Blocked | Never crossed; the route is rebuilt around it |

## Data sources

| Source | What it gives us |
|---|---|
| **SACHET (NDMA)** | Official CAP alerts for India |
| **NASA FIRMS** | Satellite fire hotspots (VIIRS) |
| **Open-Meteo** | Rainfall forecast used as a flood-risk signal (no API key needed) |
| **OpenRouteService** | Road routing with avoid-polygons |
| **Admin field data** | Manually verified hazards, treated as authoritative |

When independent sources report the same hazard type close together, confidence increases. Admin ratings always override automated scores.

## Features

**User portal (`/user`)**
- Live map shared with the admin's decisions
- Pick start and destination, compare normal (red, dashed) vs safe (green) route
- View-only alerts list
- Personal settings stored on the device

**Admin portal (`/admin`)**
- Secure login (JWT)
- Map view of all hazards
- Alerts review: confirm or dismiss
- Field verification: add a hazard after personally confirming with a local contact
- 1-5 risk rating bar that drives the routing model
- Threshold settings and "pull live data now"

**Platform**
- Collectors run on a schedule, isolated from each other so one failing provider does not stop the rest
- Live updates via Server-Sent Events, with polling as a fallback
- Collectors never overwrite an admin's decision

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy 2, APScheduler, httpx, Shapely |
| Frontend | Next.js (React), Tailwind CSS, Leaflet |
| Database | SQLite (development), PostgreSQL (production) |
| Auth | JWT bearer tokens |
| Realtime | Server-Sent Events |

## Architecture

```
SACHET ─┐
FIRMS ──┼─► Collectors ─► Normalizer ─► Database ─► Scoring ─► Routing ─► REST API ─► Next.js
Open-Meteo ┘                              ▲                                   │
                                          └────── Admin ratings & field data ◄┘
                                                         SSE live updates ───►
```

## Repository structure

```
saferoute/
├── backend/               FastAPI service
│   ├── app/
│   │   ├── collectors/    SACHET, FIRMS, Open-Meteo, mock data
│   │   ├── routers/       public and admin endpoints
│   │   ├── services/      scoring, routing, geometry, normalizer, events
│   │   └── main.py
│   ├── data/              sample hazards for mock mode
│   ├── tests/
│   └── requirements.txt
└── frontend/              Next.js app
    ├── app/               / , /user , /admin
    ├── components/        map and UI parts
    └── lib/               API client and live-update hook
```

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local  # Windows: copy .env.example .env.local
npm run dev
```

App: http://localhost:3000

### Environment variables (backend)

| Variable | Purpose |
|---|---|
| `USE_MOCK_DATA` | `true` for sample hazards, `false` for live collectors |
| `DATABASE_URL` | SQLite by default, or a PostgreSQL URL |
| `ORS_API_KEY` | OpenRouteService key (needed for real routes) |
| `FIRMS_MAP_KEY` | NASA FIRMS map key |
| `SACHET_FEED_URL` | SACHET CAP/RSS feed (defaults to the NDMA feed) |
| `REGION_BBOX` | `min_lon,min_lat,max_lon,max_lat` area to monitor |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin login. **Change before deploying** |
| `JWT_SECRET` | Token signing secret. **Change before deploying** |
| `CORS_ORIGINS` | Allowed frontend URLs, comma separated |

### Environment variables (frontend)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL |
| `NEXT_PUBLIC_MAP_CENTER` | `lat,lng` of the map's starting view |
| `NEXT_PUBLIC_TILE_URL` | Map tile provider URL |

## API overview

**Public**
- `GET /api/health`
- `GET /api/hazards`
- `GET /api/alerts`
- `POST /api/route`
- `GET /api/stream` (live updates)

**Admin (Bearer token)**
- `POST /api/admin/login`
- `GET /api/admin/hazards`
- `POST /api/admin/hazards/{id}/rate`
- `POST /api/admin/hazards/{id}/confirm`
- `POST /api/admin/verify`
- `POST /api/admin/refresh`
- `GET` / `PUT /api/admin/settings`

## Demo walkthrough

1. Open `/user`, pick a start and destination, and see the normal and safe routes.
2. Open `/admin`, sign in, and review an incoming alert.
3. Confirm it and rate it **5**.
4. Return to `/user`: the safe route now bends around the blocked zone, live.

## Tests

```bash
cd backend
pytest -q
```

## Current limitations and roadmap

SafeRoute is a hackathon prototype, not a certified dispatch system. Honest limits and next steps:

- Single region and single admin account → multi-region, role-based access, audit log
- Coordinates picked on the map → address search and GPS
- No push notifications → SMS / WhatsApp alerts to affected users
- Rainfall is a forecast signal, not proof of flooding → add river-gauge and local sensor data
- In-process live updates → message broker for multi-server deployment
- Database tables created on startup → proper migrations

## Team

_Add team name and members here._

## License

_Add a license (for example MIT) if you plan to open-source this._

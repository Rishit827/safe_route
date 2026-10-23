# SafeRoute frontend (Next.js + Tailwind + Leaflet)
```
npm install
cp .env.example .env.local   # set NEXT_PUBLIC_API_URL to your backend
npm run dev                  # http://localhost:3000
```
- `/user` read-only map, red (normal) + green (safe) routes, alerts, personal settings
- `/admin` login, rate/confirm/dismiss hazards, field verification, alerts, settings
- Map provider: only `components/MapView.js` touches the map. Change `NEXT_PUBLIC_TILE_URL`, or swap the file for another library; props stay the same.
- Backend CORS_ORIGINS must include this site's URL.

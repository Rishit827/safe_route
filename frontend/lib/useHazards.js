import { useCallback, useEffect, useRef, useState } from "react";
import { API, api } from "./api";
// Live hazards: SSE push from the backend, plus a 5s poll as a safety net.
export function useHazards(admin) {
  const [hazards, setH] = useState([]), [err, setErr] = useState(""), [live, setLive] = useState(false), last = useRef("");
  const reload = useCallback(async () => {
    try { const d = await api(admin ? "/api/admin/hazards" : "/api/hazards", { admin }), s = JSON.stringify(d);
      if (s !== last.current) { last.current = s; setH(d); } setErr(""); } catch (e) { setErr(e.message); }
  }, [admin]);
  useEffect(() => {
    reload(); const t = setInterval(reload, 5000), es = new EventSource(API + "/api/stream");
    es.onopen = () => setLive(true); es.onerror = () => setLive(false); es.addEventListener("hazards_changed", reload);
    return () => { clearInterval(t); es.close(); };
  }, [reload]);
  return { hazards, err, live, reload };
}
export const sig = h => JSON.stringify(h.map(x => [x.id, x.treatment, x.admin_rating, x.admin_status, x.radius_m]));

"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useHazards, sig } from "@/lib/useHazards";
import { Header, Pill, ICON, btn, inp } from "@/components/ui";
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false, loading: () => <div className="grid h-full place-items-center text-slate-400">Loading map…</div> });
const parse = s => { const m = s.split(",").map(parseFloat); return m.length === 2 && m.every(n => !isNaN(n)) ? { lat: m[0], lng: m[1] } : null; };
const info = f => { const s = f?.properties?.summary; return s ? `${Math.round(s.duration / 60)} min, ${(s.distance / 1000).toFixed(1)} km` : ""; };

function Field({ label, color, point, active, onPick, onSet }) {
  const [t, setT] = useState("");
  useEffect(() => setT(point ? `${point.lat}, ${point.lng}` : ""), [point]);
  return (<div><label className="flex items-center gap-1.5 text-xs text-slate-400"><i style={{ background: color }} className="size-2.5 rounded-full" />{label}</label>
    <div className="mt-1 flex gap-2"><input className={inp} placeholder="lat, lng" value={t} onChange={e => setT(e.target.value)} onBlur={() => { const p = parse(t); if (p) onSet(p); }} />
      <button onClick={onPick} className={btn + (active ? "bg-sky-500 text-slate-950" : "bg-slate-800 hover:bg-slate-700")}>{active ? "Click map" : "Pick"}</button></div></div>);
}

export default function User() {
  const { hazards, live, err } = useHazards(false);
  const [tab, setTab] = useState("route"), [start, setStart] = useState(null), [end, setEnd] = useState(null), [pick, setPick] = useState(null);
  const [res, setRes] = useState(null), [busy, setBusy] = useState(false), [rerr, setRerr] = useState(""), [sel, setSel] = useState(null);
  const [prefs, setPrefs] = useState({ auto: true, flagged: true });
  useEffect(() => { try { const p = JSON.parse(localStorage.getItem("sr_prefs")); if (p) setPrefs(p); } catch {} }, []);
  const setPref = (k, v) => { const n = { ...prefs, [k]: v }; setPrefs(n); localStorage.setItem("sr_prefs", JSON.stringify(n)); };
  const go = async () => { if (!start || !end) return; setBusy(true);
    try { setRes(await api("/api/route", { method: "POST", body: { start, end } })); setRerr(""); } catch (e) { setRerr(e.message); } setBusy(false); };
  const hs = useMemo(() => sig(hazards), [hazards]);
  useEffect(() => { if (start && end && prefs.auto) go(); }, [start, end, hs]); // eslint-disable-line
  const shown = prefs.flagged ? hazards : hazards.filter(h => h.treatment !== "flagged");
  const routes = useMemo(() => res && { normal: res.normal_route, safe: res.safe_route }, [res]);
  const points = [start && { ...start, color: "#38bdf8", label: "Start" }, end && { ...end, color: "#a78bfa", label: "End" }].filter(Boolean);
  const alerts = hazards.filter(h => h.source !== "admin").sort((a, b) => b.severity - a.severity);
  const onMapClick = pick ? p => { (pick === "start" ? setStart : setEnd)(p); setPick(null); } : undefined;
  return (<><Header live={live} />
    <div className="flex h-[calc(100vh-56px)] flex-col lg:flex-row">
      <aside className="order-2 flex flex-col overflow-y-auto border-slate-800 lg:order-1 lg:w-[380px] lg:border-r">
        <div className="flex gap-1 border-b border-slate-800 p-2">{["route", "alerts", "settings"].map(t =>
          <button key={t} onClick={() => setTab(t)} className={btn + "capitalize " + (tab === t ? "bg-slate-800" : "text-slate-400 hover:text-white")}>{t}</button>)}</div>
        <div className="space-y-4 p-4">
          {err && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">Can't reach the server: {err}</p>}
          {tab === "route" && (<>
            <Field label="Start" color="#38bdf8" point={start} active={pick === "start"} onPick={() => setPick("start")} onSet={setStart} />
            <Field label="Destination" color="#a78bfa" point={end} active={pick === "end"} onPick={() => setPick("end")} onSet={setEnd} />
            <button onClick={go} disabled={!start || !end || busy} className={btn + "w-full bg-emerald-500 py-2 text-slate-950 hover:bg-emerald-400"}>{busy ? "Finding route…" : "Find safe route"}</button>
            {!start && !end && <p className="text-sm text-slate-400">Pick a start and destination on the map to compare the normal route with the safe one.</p>}
            {rerr && <p className="rounded-lg bg-red-500/10 p-3 text-sm text-red-300">{rerr}</p>}
            {res && (<div className="space-y-2 text-sm">
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs"><span className="flex items-center gap-1.5"><i className="h-1 w-5 rounded bg-red-500" />Normal {info(res.normal_route)}</span><span className="flex items-center gap-1.5"><i className="h-1 w-5 rounded bg-emerald-500" />Safe {info(res.safe_route)}</span></div>
              <div className={`rounded-lg p-3 ${res.route_changed ? "bg-emerald-500/10 text-emerald-200" : "bg-slate-800"}`}>
                {res.route_changed ? "The safe route goes around hazards on the normal route." : res.hazards_on_normal_route.length ? "Hazards on this route are only flagged, so the route is unchanged." : "No known hazards on the normal route."}</div>
              {res.warnings.map(w => <div key={w} className="rounded-lg bg-amber-500/10 p-3 text-amber-200">{w}</div>)}
              {res.hazards_on_normal_route.map(h => <div key={h.id} className="flex items-center justify-between rounded-lg bg-slate-900 p-2.5 ring-1 ring-slate-800"><span>{ICON[h.type]} {h.title}</span><Pill k={h.treatment} /></div>)}
              {res.safe_route.properties?.stub && <p className="text-xs text-slate-500">Demo stub route: the server has no routing key yet.</p>}</div>)}
          </>)}
          {tab === "alerts" && (<>{!alerts.length && <p className="text-sm text-slate-400">No active alerts.</p>}
            {alerts.map(h => <button key={h.id} onClick={() => setSel(h.id)} className="block w-full rounded-lg bg-slate-900 p-3 text-left ring-1 ring-slate-800 hover:ring-slate-600">
              <div className="flex items-start justify-between gap-2"><span className="font-medium">{ICON[h.type]} {h.title}</span><Pill k={h.treatment} /></div>
              <p className="mt-1 text-xs text-slate-400">{h.source} · severity {h.severity}/5{h.description ? ` · ${h.description}` : ""}</p></button>)}</>)}
          {tab === "settings" && (<div className="space-y-3 text-sm">
            {[["auto", "Update my route automatically when hazards change"], ["flagged", "Show flagged (low-risk) hazards on the map"]].map(([k, l]) =>
              <label key={k} className="flex items-center gap-3"><input type="checkbox" className="size-4 accent-emerald-500" checked={prefs[k]} onChange={e => setPref(k, e.target.checked)} />{l}</label>)}
            <p className="text-xs text-slate-500">These preferences stay on this device. Only the admin can change hazard data.</p></div>)}
        </div></aside>
      <div className="order-1 min-h-[50vh] flex-1 lg:order-2"><MapView hazards={shown} routes={routes} points={points} selectedId={sel} onSelect={setSel} onMapClick={onMapClick} /></div>
    </div></>);
}

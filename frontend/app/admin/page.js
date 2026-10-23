"use client";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { api, tok, API } from "@/lib/api";
import { useHazards } from "@/lib/useHazards";
import { Header, Pill, RatingBar, ICON, btn, inp } from "@/components/ui";
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false, loading: () => <div className="grid h-full place-items-center text-slate-400">Loading map…</div> });

function Login({ onOk }) {
  const [u, setU] = useState("admin"), [p, setP] = useState(""), [e, setE] = useState("");
  const submit = async ev => { ev.preventDefault(); try { const r = await api("/api/admin/login", { method: "POST", body: { username: u, password: p } }); tok.set(r.access_token); onOk(); } catch (x) { setE(x.message); } };
  return (<div className="grid min-h-[calc(100vh-56px)] place-items-center p-4"><form onSubmit={submit} className="w-full max-w-sm space-y-3 rounded-2xl bg-slate-900 p-6 ring-1 ring-slate-800">
    <h1 className="text-xl font-bold">Admin sign in</h1>
    <input className={inp} value={u} onChange={x => setU(x.target.value)} placeholder="Username" />
    <input className={inp} type="password" value={p} onChange={x => setP(x.target.value)} placeholder="Password" />
    {e && <p className="text-sm text-red-300">{e}</p>}
    <button className={btn + "w-full bg-sky-500 py-2 text-slate-950 hover:bg-sky-400"}>Sign in</button></form></div>);
}

function HazardCard({ h, act }) {
  const [busy, setBusy] = useState(false);
  const run = async (path, body) => { setBusy(true); try { await act(h.id, path, body); } catch (e) { alert(e.message); } setBusy(false); };
  return (<div className="space-y-2.5 rounded-xl bg-slate-900 p-3 ring-1 ring-slate-800">
    <div className="flex items-start justify-between gap-2"><div><div className="font-medium">{ICON[h.type]} {h.title}</div>
      <div className="text-xs text-slate-400">{h.source} · severity {h.severity}/5 · confidence {Math.round(h.confidence * 100)}% · {h.radius_m} m</div></div><Pill k={h.treatment} /></div>
    {h.description && <p className="text-xs text-slate-400">{h.description}</p>}
    <div className="flex items-center gap-2 text-xs"><Pill k={h.admin_status} />{h.verified && <span className="text-emerald-300">Field verified</span>}</div>
    <div className="flex gap-2"><button disabled={busy} onClick={() => run("/confirm", { status: "confirmed" })} className={btn + "bg-emerald-600 hover:bg-emerald-500"}>Confirm</button>
      <button disabled={busy} onClick={() => run("/confirm", { status: "dismissed" })} className={btn + "bg-slate-800 hover:bg-slate-700"}>Dismiss</button></div>
    <div><div className="mb-1 text-xs text-slate-400">Your rating</div><RatingBar value={h.admin_rating} disabled={busy} onPick={r => run("/rate", { rating: r })} /></div></div>);
}

function Verify({ loc, picking, setPicking, done }) {
  const [f, setF] = useState({ type: "flood", title: "", radius_m: 200, who_was_called: "", notes: "", rating: 3 }), [busy, setBusy] = useState(false), [e, setE] = useState("");
  const set = (k, v) => setF({ ...f, [k]: v });
  const submit = async () => { if (!loc) return setE("Pick the location on the map first."); setBusy(true);
    try { const r = await api("/api/admin/verify", { method: "POST", admin: true, body: { ...f, ...loc, radius_m: +f.radius_m } }); setE(""); setF({ ...f, title: "", notes: "", who_was_called: "" }); done(r.id); } catch (x) { setE(x.message); } setBusy(false); };
  return (<div className="space-y-2.5 rounded-xl bg-slate-900 p-3 ring-1 ring-sky-500/40">
    <div className="font-medium">Field verification</div>
    <input className={inp} placeholder="What did the local person confirm?" value={f.title} onChange={x => set("title", x.target.value)} />
    <div className="grid grid-cols-2 gap-2"><select className={inp} value={f.type} onChange={x => set("type", x.target.value)}>{["flood", "fire", "blockage", "other"].map(t => <option key={t}>{t}</option>)}</select>
      <input className={inp} type="number" value={f.radius_m} onChange={x => set("radius_m", x.target.value)} placeholder="Radius (m)" /></div>
    <input className={inp} placeholder="Who you called" value={f.who_was_called} onChange={x => set("who_was_called", x.target.value)} />
    <textarea className={inp} rows={2} placeholder="Notes" value={f.notes} onChange={x => set("notes", x.target.value)} />
    <RatingBar value={f.rating} onPick={r => set("rating", r)} />
    <button onClick={() => setPicking(!picking)} className={btn + (picking ? "bg-sky-500 text-slate-950" : "bg-slate-800 hover:bg-slate-700")}>{picking ? "Click the map…" : loc ? `Location ${loc.lat}, ${loc.lng}` : "Pick location on map"}</button>
    {e && <p className="text-sm text-red-300">{e}</p>}
    <button disabled={busy} onClick={submit} className={btn + "w-full bg-sky-500 py-2 text-slate-950 hover:bg-sky-400"}>Save verified hazard</button></div>);
}

function Settings() {
  const [v, setV] = useState(null), [msg, setMsg] = useState(""), [busy, setBusy] = useState(false);
  useEffect(() => { api("/api/admin/settings", { admin: true }).then(r => setV(r.values)).catch(e => setMsg(e.message)); }, []);
  const save = async () => { try { const r = await api("/api/admin/settings", { method: "PUT", admin: true, body: { values: Object.fromEntries(Object.entries(v).map(([k, x]) => [k, +x])) } }); setMsg(r.note); } catch (e) { setMsg(e.message); } };
  const pull = async () => { setBusy(true); try { const r = await api("/api/admin/refresh", { method: "POST", admin: true }); setMsg(`Imported ${r.imported} hazards. ${r.errors.join("; ")}`); } catch (e) { setMsg(e.message); } setBusy(false); };
  return (<div className="mx-auto max-w-md space-y-4 p-6">
    <h2 className="text-lg font-bold">Settings</h2>
    {v && Object.entries(v).map(([k, x]) => <label key={k} className="block text-sm text-slate-400">{k.replaceAll("_", " ")}<input className={inp + " mt-1"} type="number" step="any" value={x} onChange={e => setV({ ...v, [k]: e.target.value })} /></label>)}
    <div className="flex gap-2"><button onClick={save} className={btn + "bg-sky-500 text-slate-950 hover:bg-sky-400"}>Save settings</button>
      <button onClick={pull} disabled={busy} className={btn + "bg-slate-800 hover:bg-slate-700"}>{busy ? "Pulling…" : "Pull live data now"}</button></div>
    {msg && <p className="text-sm text-slate-300">{msg}</p>}<p className="text-xs text-slate-500">Backend: {API}</p></div>);
}

function Dash({ out }) {
  const { hazards, live, err, reload } = useHazards(true);
  const [tab, setTab] = useState("map"), [sel, setSel] = useState(null), [verify, setVerify] = useState(false), [loc, setLoc] = useState(null), [picking, setPicking] = useState(false);
  const act = async (id, path, body) => { await api(`/api/admin/hazards/${id}${path}`, { method: "POST", body, admin: true }); await reload(); };
  const rank = h => (h.admin_status === "pending" ? 0 : 1);
  const list = [...hazards].sort((a, b) => rank(a) - rank(b) || b.severity - a.severity);
  const h = hazards.find(x => x.id === sel), pending = hazards.filter(x => x.admin_status === "pending").length;
  return (<><Header live={live}>
    {["map", "alerts", "settings"].map(t => <button key={t} onClick={() => setTab(t)} className={btn + "capitalize " + (tab === t ? "bg-slate-800" : "text-slate-400 hover:text-white")}>{t}{t === "alerts" && pending ? ` (${pending})` : ""}</button>)}
    <button onClick={out} className={btn + "text-slate-400 hover:text-white"}>Sign out</button></Header>
    {err && <p className="bg-red-500/10 p-2 text-center text-sm text-red-300">{err}</p>}
    {tab === "map" && (<div className="flex h-[calc(100vh-56px)] flex-col lg:flex-row">
      <aside className="order-2 space-y-3 overflow-y-auto p-3 lg:order-1 lg:w-[400px]">
        <button onClick={() => { setVerify(!verify); setPicking(false); }} className={btn + "w-full bg-sky-500 py-2 text-slate-950 hover:bg-sky-400"}>{verify ? "Close field verification" : "+ Field verification"}</button>
        {verify && <Verify loc={loc} picking={picking} setPicking={setPicking} done={id => { setPicking(false); setLoc(null); setVerify(false); setSel(id); reload(); }} />}
        {h && <HazardCard key={h.id + h.updated_at} h={h} act={act} />}
        <div className="text-xs text-slate-400">{hazards.length} hazards · {pending} awaiting review</div>
        {list.map(x => <button key={x.id} onClick={() => setSel(x.id)} className={`flex w-full items-center justify-between gap-2 rounded-lg p-2.5 text-left text-sm ring-1 ${x.id === sel ? "bg-slate-800 ring-sky-500" : "bg-slate-900 ring-slate-800 hover:ring-slate-600"}`}>
          <span className="truncate">{ICON[x.type]} {x.title}</span><span className="flex shrink-0 gap-1.5"><Pill k={x.admin_status} /><Pill k={x.treatment} /></span></button>)}
      </aside>
      <div className="order-1 min-h-[50vh] flex-1 lg:order-2"><MapView hazards={hazards.filter(x => x.admin_status !== "dismissed")} points={loc && verify ? [{ ...loc, color: "#a78bfa", label: "New" }] : []} selectedId={sel} onSelect={setSel}
        onMapClick={picking ? p => { setLoc(p); setPicking(false); } : undefined} /></div></div>)}
    {tab === "alerts" && (<div className="mx-auto grid max-w-5xl gap-3 p-4 md:grid-cols-2">{list.filter(x => x.source !== "admin").map(x => <HazardCard key={x.id + x.updated_at} h={x} act={act} />)}
      {!list.some(x => x.source !== "admin") && <p className="text-slate-400">No alerts yet. Pull live data from Settings.</p>}</div>)}
    {tab === "settings" && <Settings />}</>);
}

export default function Admin() {
  const [ready, setReady] = useState(false), [authed, setAuthed] = useState(false);
  useEffect(() => { setAuthed(!!tok.get()); setReady(true); const f = () => setAuthed(false); window.addEventListener("sr-logout", f); return () => window.removeEventListener("sr-logout", f); }, []);
  if (!ready) return <Header />;
  return authed ? <Dash out={() => { tok.clear(); setAuthed(false); }} /> : <><Header /><Login onOk={() => setAuthed(true)} /></>;
}

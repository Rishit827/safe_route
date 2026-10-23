"use client";
import Link from "next/link";
export const ICON = { flood: "🌊", fire: "🔥", blockage: "🚧", other: "⚠️" };
const TONE = { blocked: "bg-red-500/20 text-red-300 ring-red-500/40", penalised: "bg-amber-500/20 text-amber-300 ring-amber-500/40",
  flagged: "bg-yellow-400/10 text-yellow-200 ring-yellow-400/30", ignored: "bg-slate-500/20 text-slate-300 ring-slate-500/30",
  confirmed: "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40", pending: "bg-sky-500/15 text-sky-300 ring-sky-500/30", dismissed: "bg-slate-500/20 text-slate-400 ring-slate-500/30" };
export const btn = "rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-sky-400 ";
export const inp = "w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm outline-none focus:border-sky-400";
export const Pill = ({ k, children }) => <span className={`rounded-full px-2 py-0.5 text-xs ring-1 ${TONE[k] || TONE.flagged}`}>{children ?? k}</span>;
export function Header({ live, children }) {
  return (<header className="sticky top-0 z-[1100] flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950 px-4">
    <div className="flex items-center gap-5"><Link href="/" className="font-bold">🛟 SafeRoute</Link>
      <nav className="flex gap-3 text-sm text-slate-400"><Link href="/user" className="hover:text-white">Map</Link><Link href="/admin" className="hover:text-white">Admin</Link></nav></div>
    <div className="flex items-center gap-3 text-sm">{live !== undefined && <span className="flex items-center gap-1.5 text-xs text-slate-400"><i className={`size-2 rounded-full ${live ? "bg-emerald-400" : "bg-slate-500"}`} />{live ? "Live" : "Polling"}</span>}{children}</div></header>);
}
const RC = ["", "bg-sky-500", "bg-sky-500", "bg-amber-500", "bg-amber-500", "bg-red-500"];
export function RatingBar({ value, onPick, disabled }) {
  return (<div><div className="grid grid-cols-5 gap-1.5">{[1, 2, 3, 4, 5].map(n =>
    <button key={n} disabled={disabled} onClick={() => onPick(n)} className={`rounded-md py-1.5 text-sm font-semibold ring-1 ring-slate-700 transition disabled:opacity-50 ${value === n ? RC[n] + " text-slate-950" : "bg-slate-800 hover:bg-slate-700"}`}>{n}</button>)}</div>
    <div className="mt-1 text-[11px] text-slate-500">1–2 flagged: shown only. 3–4 penalised: avoided if possible. 5 blocked: never crossed.</div></div>);
}

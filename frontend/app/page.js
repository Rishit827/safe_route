import Link from "next/link";
import { Header } from "@/components/ui";
export default function Home() {
  return (<><Header /><main className="mx-auto max-w-3xl space-y-8 p-8 pt-16">
    <h1 className="text-5xl font-bold leading-tight">The safest road,<br />not the fastest.</h1>
    <p className="max-w-xl text-slate-400">Routes are built around floods, fires and blockages that a person has checked on the ground.</p>
    <div className="grid gap-4 sm:grid-cols-2">
      <Link href="/user" className="rounded-xl bg-emerald-500 p-5 font-semibold text-slate-950 hover:bg-emerald-400">Find a safe route</Link>
      <Link href="/admin" className="rounded-xl bg-slate-800 p-5 font-semibold ring-1 ring-slate-700 hover:bg-slate-700">Admin portal</Link>
    </div></main></>);
}

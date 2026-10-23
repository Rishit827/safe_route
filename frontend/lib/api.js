export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const CENTER = (process.env.NEXT_PUBLIC_MAP_CENTER || "31.634,74.872").split(",").map(Number);
export const tok = { get: () => localStorage.getItem("sr_token"), set: t => localStorage.setItem("sr_token", t), clear: () => localStorage.removeItem("sr_token") };
export async function api(path, { method = "GET", body, admin } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (admin) headers.Authorization = `Bearer ${tok.get()}`;
  const r = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (r.status === 401 && admin) { tok.clear(); window.dispatchEvent(new Event("sr-logout")); }
  if (!r.ok) { let d = r.statusText; try { d = (await r.json()).detail || d; } catch {} throw new Error(typeof d === "string" ? d : JSON.stringify(d)); }
  return r.json();
}

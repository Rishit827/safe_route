"use client";
// The only file that touches the map library. Props: hazards, routes {normal,safe}, points, selectedId, onSelect, onMapClick.
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CENTER } from "@/lib/api";
const TILE = process.env.NEXT_PUBLIC_TILE_URL || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const COLOR = { blocked: "#ef4444", penalised: "#f59e0b", flagged: "#eab308", ignored: "#64748b" };
export default function MapView({ hazards = [], routes, points = [], selectedId, onSelect, onMapClick }) {
  const el = useRef(), map = useRef(), hz = useRef(), rt = useRef(), pt = useRef(), cb = useRef({}), hzRef = useRef([]);
  cb.current = { onSelect, onMapClick }; hzRef.current = hazards;
  useEffect(() => {
    const m = L.map(el.current).setView(CENTER, 13);
    L.tileLayer(TILE, { attribution: "© OpenStreetMap contributors", maxZoom: 19 }).addTo(m);
    hz.current = L.layerGroup().addTo(m); rt.current = L.featureGroup().addTo(m); pt.current = L.layerGroup().addTo(m);
    m.on("click", e => cb.current.onMapClick?.({ lat: +e.latlng.lat.toFixed(5), lng: +e.latlng.lng.toFixed(5) }));
    map.current = m; return () => m.remove();
  }, []);
  useEffect(() => { el.current.classList.toggle("pick", !!onMapClick); }, [onMapClick]);
  useEffect(() => {
    hz.current.clearLayers();
    hazards.forEach(h => {
      const c = COLOR[h.treatment] || COLOR.flagged, sel = h.id === selectedId, pick = e => { L.DomEvent.stopPropagation(e); cb.current.onSelect?.(h.id); };
      L.circle([h.lat, h.lng], { radius: h.radius_m, color: c, weight: sel ? 4 : 2, fillOpacity: sel ? .4 : .18 }).on("click", pick).addTo(hz.current);
      L.circleMarker([h.lat, h.lng], { radius: sel ? 9 : 6, color: "#fff", weight: 1.5, fillColor: c, fillOpacity: 1 }).bindTooltip(h.title).on("click", pick).addTo(hz.current);
    });
  }, [hazards, selectedId]);
  useEffect(() => {
    rt.current.clearLayers();
    const line = (f, color, dash) => L.geoJSON(f.geometry, { style: { color, weight: 6, opacity: .9, dashArray: dash } }).addTo(rt.current);
    if (routes?.normal) line(routes.normal, "#ef4444", "10 8");
    if (routes?.safe) line(routes.safe, "#22c55e");
    const b = rt.current.getBounds(); if (b.isValid()) map.current.fitBounds(b, { padding: [50, 50] });
  }, [routes]);
  useEffect(() => {
    pt.current.clearLayers();
    points.forEach(p => L.circleMarker([p.lat, p.lng], { radius: 9, color: "#fff", weight: 2, fillColor: p.color, fillOpacity: 1 }).bindTooltip(p.label, { permanent: true, direction: "top" }).addTo(pt.current));
  }, [JSON.stringify(points)]); // eslint-disable-line
  useEffect(() => { const h = hzRef.current.find(x => x.id === selectedId); if (h) map.current.flyTo([h.lat, h.lng], Math.max(map.current.getZoom(), 14)); }, [selectedId]);
  return <div ref={el} className="h-full w-full" />;
}

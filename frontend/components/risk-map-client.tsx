"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import type { RiskPoint } from "./risk-map";

const CHICAGO_CENTER: [number, number] = [41.8781, -87.6298];

function colorByRisk(risk: string): string {
  if (risk === "high") return "#ef4444";
  if (risk === "medium") return "#f59e0b";
  return "#22c55e";
}

function pseudoLatLng(area: number): [number, number] {
  const lat = CHICAGO_CENTER[0] + ((area % 7) - 3) * 0.015;
  const lng = CHICAGO_CENTER[1] + ((area % 11) - 5) * 0.02;
  return [lat, lng];
}

export function RiskMapClient({ points }: { points: RiskPoint[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: false,
    }).setView(CHICAGO_CENTER, 9.5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    markerLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const markerLayer = markerLayerRef.current;
    if (!map || !markerLayer) return;

    markerLayer.clearLayers();
    const latLngs: L.LatLngExpression[] = [];

    points.forEach((point) => {
      const [lat, lng] = pseudoLatLng(Number(point.community_area));
      latLngs.push([lat, lng]);

      const probability = Number(point.pred_prob ?? 0);
      const marker = L.circleMarker([lat, lng], {
        radius: 5 + Math.max(0, Math.min(1, probability)) * 9,
        color: colorByRisk(String(point.risk_level ?? "low")),
        fillColor: colorByRisk(String(point.risk_level ?? "low")),
        fillOpacity: 0.62,
        weight: 1.8,
      });

      marker.bindPopup(
        `<strong>Community ${point.community_area}</strong><br/>Risk: ${String(point.risk_level)}<br/>Probability: ${(probability * 100).toFixed(1)}%`,
      );
      marker.addTo(markerLayer);
    });

    if (latLngs.length > 1) {
      map.fitBounds(L.latLngBounds(latLngs).pad(0.2));
    } else if (latLngs.length === 1) {
      map.setView(latLngs[0], 11);
    } else {
      map.setView(CHICAGO_CENTER, 9.5);
    }
  }, [points]);

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

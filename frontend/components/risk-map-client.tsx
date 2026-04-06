"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { RiskPoint } from "./risk-map";

const CHICAGO_CENTER: [number, number] = [41.8781, -87.6298];
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

function colorByRisk(risk: string): string {
  if (risk === "high") return "#ef4444";
  if (risk === "medium") return "#f59e0b";
  return "#22c55e";
}

function collectLngLatPairs(node: unknown, out: Array<[number, number]>): void {
  if (!Array.isArray(node)) return;
  if (node.length >= 2 && typeof node[0] === "number" && typeof node[1] === "number") {
    out.push([node[0], node[1]]);
    return;
  }
  node.forEach((child) => collectLngLatPairs(child, out));
}

function geometryCenter(geometry: unknown): [number, number] | null {
  if (!geometry || typeof geometry !== "object") return null;
  const coords = (geometry as { coordinates?: unknown }).coordinates;
  const pairs: Array<[number, number]> = [];
  collectLngLatPairs(coords, pairs);
  if (!pairs.length) return null;
  let minLng = Number.POSITIVE_INFINITY;
  let maxLng = Number.NEGATIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;
  pairs.forEach(([lng, lat]) => {
    minLng = Math.min(minLng, lng);
    maxLng = Math.max(maxLng, lng);
    minLat = Math.min(minLat, lat);
    maxLat = Math.max(maxLat, lat);
  });
  return [(minLat + maxLat) / 2, (minLng + maxLng) / 2];
}

export function RiskMapClient({ points }: { points: RiskPoint[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const resizeCleanupRef = useRef<(() => void) | null>(null);
  const [centroids, setCentroids] = useState<Record<string, [number, number]>>({});

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const res = await fetch(`${API_BASE}/eda/geography/community-geojson`, { cache: "force-cache" });
        if (!res.ok) return;
        const payload = (await res.json()) as {
          data?: Array<{ geojson?: { features?: Array<{ properties?: Record<string, unknown>; geometry?: unknown }> } }>;
        };
        const featureRows = payload.data?.[0]?.geojson?.features ?? [];
        const next: Record<string, [number, number]> = {};
        featureRows.forEach((feature) => {
          const area = feature?.properties?.area_numbe;
          if (area === null || area === undefined) return;
          const center = geometryCenter(feature.geometry);
          if (!center) return;
          next[String(Number(area))] = center;
        });
        if (!cancelled && Object.keys(next).length > 0) {
          setCentroids(next);
        }
      } catch {
        // Keep map functional even when geojson endpoint is temporarily unavailable.
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || mapRef.current) return;

    const map = L.map(container, {
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
    const invalidate = () => map.invalidateSize({ pan: false, debounceMoveend: true });
    requestAnimationFrame(invalidate);
    const onWindowResize = () => invalidate();
    window.addEventListener("resize", onWindowResize);
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => invalidate());
      observer.observe(container);
    }
    resizeCleanupRef.current = () => {
      window.removeEventListener("resize", onWindowResize);
      observer?.disconnect();
    };

    return () => {
      resizeCleanupRef.current?.();
      resizeCleanupRef.current = null;
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const markerLayer = markerLayerRef.current;
    if (!map || !markerLayer) return;

    map.invalidateSize({ pan: false, debounceMoveend: true });
    markerLayer.clearLayers();
    const latLngs: L.LatLngExpression[] = [];

    points.forEach((point) => {
      const area = String(Number(point.community_area));
      const center = centroids[area];
      if (!center) return;
      const [lat, lng] = center;
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
  }, [points, centroids]);

  return (
    <div className="h-[420px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

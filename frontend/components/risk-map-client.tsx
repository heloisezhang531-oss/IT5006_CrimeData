"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import type { RiskPoint } from "./risk-map";

const CHICAGO_CENTER: [number, number] = [41.8781, -87.6298];
const DEFAULT_ZOOM = 9.1;
const ZOOM_IN_OFFSET = 1;
const MAX_AUTO_ZOOM = 19;
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

function safeInvalidate(map: L.Map | null, container?: HTMLDivElement | null): void {
  if (!map) return;
  if (container && !container.isConnected) return;
  const internal = map as unknown as { _loaded?: boolean; _mapPane?: unknown };
  if (!internal._loaded || !internal._mapPane) return;
  try {
    map.invalidateSize({ pan: false, debounceMoveend: true });
  } catch {
    // Ignore transient Leaflet lifecycle errors during unmount/remount.
  }
}

export function RiskMapClient({ points }: { points: RiskPoint[] }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerLayerRef = useRef<L.LayerGroup | null>(null);
  const resizeCleanupRef = useRef<(() => void) | null>(null);
  const [communityMeta, setCommunityMeta] = useState<Record<string, { center: [number, number]; name: string }>>({});

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
        const next: Record<string, { center: [number, number]; name: string }> = {};
        featureRows.forEach((feature) => {
          const area = feature?.properties?.area_numbe;
          if (area === null || area === undefined) return;
          const center = geometryCenter(feature.geometry);
          if (!center) return;
          const rawName = feature?.properties?.community;
          const name = typeof rawName === "string" && rawName.trim().length > 0 ? rawName.trim() : `Community ${Number(area)}`;
          next[String(Number(area))] = { center, name };
        });
        if (!cancelled && Object.keys(next).length > 0) {
          setCommunityMeta(next);
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
    }).setView(CHICAGO_CENTER, DEFAULT_ZOOM);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    markerLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    let disposed = false;
    let rafId: number | null = null;
    const invalidate = () => {
      if (disposed) return;
      safeInvalidate(map, container);
    };
    rafId = requestAnimationFrame(invalidate);
    const onWindowResize = () => invalidate();
    window.addEventListener("resize", onWindowResize);
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      observer = new ResizeObserver(() => invalidate());
      observer.observe(container);
    }
    resizeCleanupRef.current = () => {
      disposed = true;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
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
    const container = containerRef.current;
    if (!map || !markerLayer) return;

    safeInvalidate(map, container);
    markerLayer.clearLayers();
    const latLngs: L.LatLngExpression[] = [];

    points.forEach((point) => {
      const area = String(Number(point.community_area));
      const meta = communityMeta[area];
      if (!meta) return;
      const [lat, lng] = meta.center;
      latLngs.push([lat, lng]);

      const probability = Number(point.pred_prob ?? 0);
      const normalizedProb = Math.max(0, Math.min(1, probability));
      const marker = L.circle([lat, lng], {
        // Tuned for visible overlap without overwhelming the base map.
        radius: 560 + normalizedProb * 1800,
        color: colorByRisk(String(point.risk_level ?? "low")),
        fillColor: colorByRisk(String(point.risk_level ?? "low")),
        fillOpacity: 0.52,
        weight: 1.6,
      });

      const hardship = Number(point.hardship_index);
      const hardshipText = Number.isFinite(hardship) ? hardship.toFixed(2) : "N/A";
      const communityName = typeof point.community_name === "string" && point.community_name.trim().length > 0 ? point.community_name : meta.name;
      marker.bindTooltip(
        `<strong>${communityName}</strong><br/>Predicted Risk: ${(normalizedProb * 100).toFixed(1)}%<br/>Hardship Index: ${hardshipText}`,
        { sticky: true, direction: "top", opacity: 0.95 },
      );
      marker.addTo(markerLayer);
    });

    if (latLngs.length > 1) {
      map.fitBounds(L.latLngBounds(latLngs).pad(0.2));
      map.setZoom(Math.min(map.getZoom() + ZOOM_IN_OFFSET, MAX_AUTO_ZOOM));
    } else if (latLngs.length === 1) {
      map.setView(latLngs[0], 11 + ZOOM_IN_OFFSET);
    } else {
      map.setView(CHICAGO_CENTER, DEFAULT_ZOOM);
    }
  }, [points, communityMeta]);

  return (
    <div className="h-[420px] w-full overflow-hidden border border-machine-yellow/20 bg-void/50">
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}

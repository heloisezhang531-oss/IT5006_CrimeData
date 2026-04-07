"use client";

import { type MutableRefObject, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";

type ApiPayload<T> = {
  data: T[];
};

type PointRow = {
  latitude: number;
  longitude: number;
  community_area?: number;
};

type ChoroplethRow = {
  community_area: string | number;
  community_name?: string;
  crime_count: number;
  top_types?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";
const CHICAGO_CENTER: [number, number] = [41.8781, -87.6298];

async function fetchApi<T>(path: string): Promise<T[]> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) return [];
  const payload = (await res.json()) as ApiPayload<T>;
  return payload.data ?? [];
}

function colorByCount(value: number, max: number): string {
  if (!value || max <= 0) return "#f3f4f6";
  const ratio = Math.min(1, value / max);
  if (ratio > 0.85) return "#7f1d1d";
  if (ratio > 0.65) return "#b91c1c";
  if (ratio > 0.45) return "#dc2626";
  if (ratio > 0.25) return "#ef4444";
  if (ratio > 0.12) return "#f87171";
  return "#fecaca";
}

function normalizeCommunityArea(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(Number(value));
}

function isMapOperational(map: L.Map | null, container?: HTMLDivElement | null): map is L.Map {
  if (!map) return false;
  if (container && !container.isConnected) return false;
  const internal = map as unknown as { _loaded?: boolean; _mapPane?: unknown };
  return Boolean(internal._loaded && internal._mapPane);
}

function safeInvalidate(map: L.Map | null, container?: HTMLDivElement | null): void {
  if (!isMapOperational(map, container)) return;
  try {
    map.invalidateSize({ pan: false, debounceMoveend: true });
  } catch {
    // Ignore transient Leaflet lifecycle errors during unmount/remount.
  }
}

export function GeoDistributionClient({ years }: { years: number[] }) {
  const defaultLeft = years[0] ?? 2015;
  const defaultRight = years[years.length - 1] ?? 2024;

  const [pointYear, setPointYear] = useState(defaultRight);
  const [leftYear, setLeftYear] = useState(defaultLeft);
  const [rightYear, setRightYear] = useState(defaultRight);
  const [hardshipRows, setHardshipRows] = useState<Record<string, unknown>[]>([]);
  const [geojsonReady, setGeojsonReady] = useState(false);
  const [error, setError] = useState<string>("");

  const pointsMapRef = useRef<L.Map | null>(null);
  const pointsLayerRef = useRef<L.LayerGroup | null>(null);
  const pointContainerRef = useRef<HTMLDivElement | null>(null);
  const resizeCleanupRef = useRef<Array<() => void>>([]);

  const leftMapRef = useRef<L.Map | null>(null);
  const leftLayerRef = useRef<L.GeoJSON | null>(null);
  const leftContainerRef = useRef<HTMLDivElement | null>(null);

  const rightMapRef = useRef<L.Map | null>(null);
  const rightLayerRef = useRef<L.GeoJSON | null>(null);
  const rightContainerRef = useRef<HTMLDivElement | null>(null);

  const geojsonRef = useRef<Record<string, unknown> | null>(null);
  const hardshipPreview = useMemo(() => hardshipRows.slice(0, 12), [hardshipRows]);

  const bindResizeSync = (map: L.Map, container: HTMLDivElement) => {
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
    return () => {
      disposed = true;
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
      }
      window.removeEventListener("resize", onWindowResize);
      observer?.disconnect();
    };
  };

  useEffect(() => {
    if (pointContainerRef.current && !pointsMapRef.current) {
      const map = L.map(pointContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
        preferCanvas: true,
      }).setView(CHICAGO_CENTER, 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      pointsLayerRef.current = L.layerGroup().addTo(map);
      pointsMapRef.current = map;
      resizeCleanupRef.current.push(bindResizeSync(map, pointContainerRef.current));
    }
    if (leftContainerRef.current && !leftMapRef.current) {
      const map = L.map(leftContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
      }).setView(CHICAGO_CENTER, 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      leftMapRef.current = map;
      resizeCleanupRef.current.push(bindResizeSync(map, leftContainerRef.current));
    }
    if (rightContainerRef.current && !rightMapRef.current) {
      const map = L.map(rightContainerRef.current, {
        zoomControl: true,
        attributionControl: true,
        scrollWheelZoom: false,
      }).setView(CHICAGO_CENTER, 10);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      rightMapRef.current = map;
      resizeCleanupRef.current.push(bindResizeSync(map, rightContainerRef.current));
    }

    return () => {
      resizeCleanupRef.current.forEach((fn) => fn());
      resizeCleanupRef.current = [];
      const pointsMap = pointsMapRef.current;
      const leftMap = leftMapRef.current;
      const rightMap = rightMapRef.current;
      pointsMapRef.current = null;
      leftMapRef.current = null;
      rightMapRef.current = null;
      pointsLayerRef.current = null;
      leftLayerRef.current = null;
      rightLayerRef.current = null;
      try {
        pointsMap?.remove();
      } catch {
        // Ignore teardown race on removed pane/container.
      }
      try {
        leftMap?.remove();
      } catch {
        // Ignore teardown race on removed pane/container.
      }
      try {
        rightMap?.remove();
      } catch {
        // Ignore teardown race on removed pane/container.
      }
    };
  }, []);

  useEffect(() => {
    const run = async () => {
      try {
        const [geoRows, hardship] = await Promise.all([
          fetchApi<{ geojson: Record<string, unknown> }>("/eda/geography/community-geojson"),
          fetchApi<Record<string, unknown>>("/eda/geography/hardship-index"),
        ]);
        geojsonRef.current = geoRows[0]?.geojson ?? null;
        setGeojsonReady(Boolean(geojsonRef.current));
        setHardshipRows(hardship);
        setError(geojsonRef.current ? "" : "GeoJSON unavailable");
      } catch {
        setError("Failed to load map metadata.");
      }
    };
    run();
  }, []);

  useEffect(() => {
    const run = async () => {
      const rows = await fetchApi<PointRow>(`/eda/geography/points?year=${pointYear}&limit=12000`);
      const layer = pointsLayerRef.current;
      const map = pointsMapRef.current;
      const container = pointContainerRef.current;
      if (!layer || !map || !isMapOperational(map, container)) return;
      layer.clearLayers();
      const latLngs: L.LatLngExpression[] = [];
      rows.forEach((row) => {
        if (!Number.isFinite(row.latitude) || !Number.isFinite(row.longitude)) return;
        const marker = L.circleMarker([row.latitude, row.longitude], {
          radius: 2.4,
          color: "#b91c1c",
          fillColor: "#dc2626",
          fillOpacity: 0.42,
          weight: 0.8,
        });
        const communityArea = row.community_area ? `Community ${row.community_area}` : "Crime point";
        marker.bindTooltip(communityArea, { sticky: true });
        marker.addTo(layer);
        latLngs.push([row.latitude, row.longitude]);
      });
      safeInvalidate(map, container);
      try {
        if (latLngs.length > 1) {
          map.fitBounds(L.latLngBounds(latLngs).pad(0.15));
        } else {
          map.setView(CHICAGO_CENTER, 10);
        }
      } catch {
        // Ignore transient viewport updates on disposed map instances.
      }
    };
    run();
  }, [pointYear]);

  const renderChoropleth = (
    map: L.Map | null,
    layerRef: MutableRefObject<L.GeoJSON | null>,
    rows: ChoroplethRow[],
    container?: HTMLDivElement | null,
  ) => {
    const geojson = geojsonRef.current;
    if (!geojson || !isMapOperational(map, container)) return;
    safeInvalidate(map, container);
    if (layerRef.current) {
      try {
        map.removeLayer(layerRef.current);
      } catch {
        // Ignore stale layer detach on disposed map instances.
      }
      layerRef.current = null;
    }
    const lookup = new Map<string, ChoroplethRow>();
    rows.forEach((row) => lookup.set(normalizeCommunityArea(row.community_area), row));
    const maxCount = rows.reduce((acc, row) => Math.max(acc, Number(row.crime_count || 0)), 0);

    try {
      const layer = L.geoJSON(geojson as unknown as GeoJSON.GeoJsonObject, {
        style: (feature) => {
          const area = normalizeCommunityArea((feature?.properties as Record<string, unknown>)?.area_numbe);
          const row = lookup.get(area);
          const count = Number(row?.crime_count ?? 0);
          return {
            color: "#475569",
            weight: 0.8,
            fillOpacity: 0.68,
            fillColor: colorByCount(count, maxCount),
          };
        },
        onEachFeature: (feature, featureLayer) => {
          const area = normalizeCommunityArea((feature?.properties as Record<string, unknown>)?.area_numbe);
          const row = lookup.get(area);
          const communityName = row?.community_name ?? `Community ${area}`;
          const count = Number(row?.crime_count ?? 0);
          const topTypes = String(row?.top_types ?? "No data");
          featureLayer.bindPopup(
            `<strong>${communityName}</strong><br/>Crime Count: ${count}<br/>Top Types:<br/>${topTypes}`,
          );
          featureLayer.bindTooltip(
            `${communityName}<br/>Crime Count: ${count}<br/>Top Types: ${topTypes}`,
            { sticky: true },
          );
        },
      }).addTo(map);
      layerRef.current = layer;
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds.pad(0.05));
      } else {
        map.setView(CHICAGO_CENTER, 10);
      }
    } catch {
      // Ignore rendering races on disposed map instances.
    }
  };

  useEffect(() => {
    if (!geojsonReady) return;
    const run = async () => {
      const rows = await fetchApi<ChoroplethRow>(`/eda/geography/community-choropleth?year=${leftYear}`);
      renderChoropleth(leftMapRef.current, leftLayerRef, rows, leftContainerRef.current);
    };
    run();
  }, [leftYear, geojsonReady]);

  useEffect(() => {
    if (!geojsonReady) return;
    const run = async () => {
      const rows = await fetchApi<ChoroplethRow>(`/eda/geography/community-choropleth?year=${rightYear}`);
      renderChoropleth(rightMapRef.current, rightLayerRef, rows, rightContainerRef.current);
    };
    run();
  }, [rightYear, geojsonReady]);

  return (
    <div className="space-y-6">
      {error ? (
        <p className="border border-threat-red/40 bg-threat-red/10 px-4 py-2 text-xs uppercase tracking-[0.14em] text-threat-red">{error}</p>
      ) : null}

      <div className="glass-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-machine-yellow">
            Crime Incident Points by Year
          </h3>
          <select
            className="border border-machine-yellow/30 bg-void/70 px-3 py-1.5 text-xs uppercase tracking-[0.1em] text-system-white"
            value={pointYear}
            onChange={(e) => setPointYear(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
        <div className="h-[420px] w-full overflow-hidden border border-machine-yellow/20">
          <div ref={pointContainerRef} className="h-full w-full" />
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="glass-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-machine-yellow">
              Community Choropleth (Left)
            </h3>
            <select
              className="border border-machine-yellow/30 bg-void/70 px-3 py-1.5 text-xs uppercase tracking-[0.1em] text-system-white"
              value={leftYear}
              onChange={(e) => setLeftYear(Number(e.target.value))}
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="h-[460px] w-full overflow-hidden border border-machine-yellow/20">
            <div ref={leftContainerRef} className="h-full w-full" />
          </div>
        </div>
        <div className="glass-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-[0.14em] text-machine-yellow">
              Community Choropleth (Right)
            </h3>
            <select
              className="border border-machine-yellow/30 bg-void/70 px-3 py-1.5 text-xs uppercase tracking-[0.1em] text-system-white"
              value={rightYear}
              onChange={(e) => setRightYear(Number(e.target.value))}
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="h-[460px] w-full overflow-hidden border border-machine-yellow/20">
            <div ref={rightContainerRef} className="h-full w-full" />
          </div>
        </div>
      </div>

      <div className="glass-card p-4">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-machine-yellow">
          Hardship Index (Preview)
        </h3>
        <div className="overflow-auto border border-machine-yellow/20">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-machine-yellow/10 text-zinc-400">
              <tr>
                {hardshipPreview[0]
                  ? Object.keys(hardshipPreview[0]).slice(0, 6).map((col) => (
                      <th key={col} className="px-3 py-2 font-semibold">
                        {col}
                      </th>
                    ))
                  : null}
              </tr>
            </thead>
            <tbody>
              {hardshipPreview.map((row, idx) => (
                <tr key={idx} className="border-t border-machine-yellow/15">
                  {Object.keys(row)
                    .slice(0, 6)
                    .map((col) => (
                      <td key={col} className="px-3 py-2 text-zinc-300">
                        {String(row[col] ?? "-")}
                      </td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { DataTable } from "@/components/table";
import { GroupedBarCard, HeatmapGridCard, HorizontalStackedBarCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

type FilterRow = {
  age_min: number;
  age_max: number;
  categories: string[];
};

type DashboardRow = {
  kpi: { total_victims: number; domestic_cases: number; avg_age: number };
  demographics: Array<{ age_num: number; sex_code: string; count: number }>;
  relationships: Array<{ RELATIONSHIP_NAME: string; count: number }>;
  activity_heatmap: Array<{ activity: string; offense_category: string; count: number }>;
  raw_sample: Record<string, unknown>[];
};

export default function VictimRiskPage() {
  const [meta, setMeta] = useState<FilterRow | null>(null);
  const [ageMin, setAgeMin] = useState(0);
  const [ageMax, setAgeMax] = useState(90);
  const [selected, setSelected] = useState<string[]>([]);
  const [includeRaw, setIncludeRaw] = useState(false);
  const [dashboard, setDashboard] = useState<DashboardRow | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const filters = await apiGet<FilterRow>("/eda/victim/filters", {
          clientTtlMs: 8000,
          forceRefresh: reloadToken > 0,
        });
        if (cancelled) return;
        const row = filters.data[0];
        if (!row) {
          setMeta(null);
          setDashboard(null);
          setError("Victim filter endpoint returned no metadata.");
          setLoading(false);
          return;
        }
        setMeta(row);
        setAgeMin(row.age_min);
        setAgeMax(row.age_max);
        setSelected([]);
        if (filters.meta?.error) {
          setError(`Failed to load filter metadata: ${String(filters.meta.error)}`);
        }
      } catch {
        if (cancelled) return;
        setMeta(null);
        setDashboard(null);
        setError("Failed to load victim filters. Please check backend connection and retry.");
        setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  useEffect(() => {
    if (!meta) return;
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      const payload = {
        age_min: ageMin,
        age_max: ageMax,
        offense_categories: selected,
        include_raw_sample: includeRaw,
        raw_limit: 100,
      };
      try {
        const res = await apiPost<DashboardRow>("/eda/victim/dashboard", payload);
        if (cancelled) return;
        setDashboard(res.data[0] ?? null);
        if (res.meta?.error) {
          setError(`Dashboard request failed: ${String(res.meta.error)}`);
        } else if (!res.data?.length) {
          setError("No victim dashboard rows returned for current filters.");
        }
      } catch {
        if (cancelled) return;
        setDashboard(null);
        setError("Failed to load victim dashboard data. Please retry.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [meta, ageMin, ageMax, selected, includeRaw]);

  const demographicsByAge = useMemo(() => {
    const rows = dashboard?.demographics ?? [];
    const sexKeys = Array.from(new Set(rows.map((r) => r.sex_code || "U")));
    const byAge = Object.values(
      rows.reduce((acc, row) => {
        const age = String(row.age_num);
        if (!acc[age]) acc[age] = { age };
        acc[age][row.sex_code || "U"] = Number(row.count ?? 0);
        return acc;
      }, {} as Record<string, Record<string, number | string>>),
    ).sort((a, b) => Number(a.age) - Number(b.age));
    return { byAge, sexKeys };
  }, [dashboard]);

  const relationRows = (dashboard?.relationships ?? []).map((r) => ({
    relationship: String(r.RELATIONSHIP_NAME ?? "Unknown"),
    count: Number(r.count ?? 0),
  }));

  const heatRows = (dashboard?.activity_heatmap ?? []).map((r) => ({
    activity: String(r.activity ?? ""),
    offense: String(r.offense_category ?? ""),
    count: Number(r.count ?? 0),
  }));

  const kpi = dashboard?.kpi ?? { total_victims: 0, domestic_cases: 0, avg_age: 0 };
  const hasCharts = demographicsByAge.byAge.length > 0 || relationRows.length > 0 || heatRows.length > 0;
  const resetFilters = () => {
    if (!meta) return;
    setAgeMin(meta.age_min);
    setAgeMax(meta.age_max);
    setSelected([]);
    setIncludeRaw(false);
  };

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Victim Risk Analysis"
        title="Victim Risk Profiling Dashboard"
        description="Streamlit parity victim profiling view with age/category filters, KPI updates, relationship analysis, and activity-offense interaction heatmap."
        conclusion="Victim signal: combine demographic and relationship structures when planning victim-protection interventions."
      />

      <GlassPanel>
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-slate-700">Victim Filters</p>
            <div className="flex items-center gap-2">
              <button
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                onClick={resetFilters}
              >
                Reset
              </button>
              <button
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                onClick={() => setReloadToken((v) => v + 1)}
              >
                Reload
              </button>
            </div>
          </div>
          <div className="grid gap-5 lg:grid-cols-[1.1fr_1fr]">
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/70 p-4">
              <p className="text-sm font-semibold text-slate-700">Victim Age Range</p>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{ageMin}</span>
                <span>{ageMax}</span>
              </div>
              <input
                type="range"
                min={meta?.age_min ?? 0}
                max={meta?.age_max ?? 95}
                value={ageMin}
                onChange={(e) => setAgeMin(Math.min(Number(e.target.value), ageMax))}
                className="w-full"
              />
              <input
                type="range"
                min={meta?.age_min ?? 0}
                max={meta?.age_max ?? 95}
                value={ageMax}
                onChange={(e) => setAgeMax(Math.max(Number(e.target.value), ageMin))}
                className="w-full"
              />
            </div>
            <div className="space-y-3 rounded-2xl border border-slate-200 bg-white/70 p-4">
              <p className="text-sm font-semibold text-slate-700">Offense Categories</p>
              <select
                multiple
                className="h-40 w-full rounded-xl border border-slate-300 bg-white p-2 text-sm"
                value={selected}
                onChange={(e) => {
                  const values = Array.from(e.target.selectedOptions).map((opt) => opt.value);
                  setSelected(values);
                }}
              >
                {(meta?.categories ?? []).map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <label className="inline-flex items-center gap-2 text-sm text-slate-600">
                <input type="checkbox" checked={includeRaw} onChange={(e) => setIncludeRaw(e.target.checked)} />
                Show raw sample
              </label>
            </div>
          </div>
          {error ? <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p> : null}
        </div>
      </GlassPanel>

      {loading ? (
        <GlassPanel>
          <p className="text-sm text-slate-500">Analyzing victim risk data...</p>
        </GlassPanel>
      ) : !dashboard ? (
        <GlassPanel>
          <p className="text-sm text-slate-600">No victim dashboard payload returned from backend.</p>
        </GlassPanel>
      ) : !hasCharts ? (
        <GlassPanel>
          <p className="text-sm text-slate-600">
            No chart-ready victim rows are available for the current filter set. Try broadening age range, reducing category constraints, or reloading.
          </p>
        </GlassPanel>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <GlassPanel>
              <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Total Victims</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpi.total_victims.toLocaleString()}</p>
            </GlassPanel>
            <GlassPanel>
              <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Domestic Cases</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{kpi.domestic_cases.toLocaleString()}</p>
            </GlassPanel>
            <GlassPanel>
              <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Avg Victim Age</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{Number(kpi.avg_age ?? 0).toFixed(1)}</p>
            </GlassPanel>
          </div>
          <div className="grid gap-6 xl:grid-cols-2">
            <GlassPanel>
              <h2 className="mb-4 text-lg font-semibold">Victim Age & Gender Distribution</h2>
              <GroupedBarCard
                data={demographicsByAge.byAge}
                xKey="age"
                series={demographicsByAge.sexKeys.map((k, idx) => ({
                  key: k,
                  name: k,
                  color: ["#2563eb", "#f97316", "#16a34a", "#a855f7"][idx % 4],
                }))}
              />
            </GlassPanel>
            <GlassPanel>
              <h2 className="mb-4 text-lg font-semibold">Top 10 Victim-Offender Relationships</h2>
              <HorizontalStackedBarCard
                data={relationRows}
                yKey="relationship"
                series={[{ key: "count", name: "Count", color: "#0ea5e9" }]}
              />
            </GlassPanel>
          </div>

          <GlassPanel>
            <h2 className="mb-4 text-lg font-semibold">Victim Activity vs Offense Category</h2>
            <HeatmapGridCard data={heatRows} xKey="offense" yKey="activity" valueKey="count" />
          </GlassPanel>

          <EvidencePanel
            title="Victim Risk Evidence"
            summary="Raw demographic/relationship rows and optional raw sample for parity check."
          >
            <div className="space-y-4">
              <DataTable rows={dashboard?.demographics ?? []} />
              <DataTable rows={dashboard?.relationships ?? []} />
              {includeRaw ? <DataTable rows={dashboard?.raw_sample ?? []} /> : null}
            </div>
          </EvidencePanel>
        </>
      )}

      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Use age, relationship, and activity-pattern evidence together for victim-centric protection and social-service coordination.
        </p>
      </GlassPanel>
    </div>
  );
}

export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { BarCard, HeatmapGridCard, LineCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";
import { RiskMap } from "@/components/risk-map";

export default async function CommandCenterPage() {
  const bundle = await apiGet<Record<string, any>>("/dashboard/command-center");
  const data = bundle.data[0] ?? {
    predicted_risk_map: [],
    yearly_trend: [],
    hour_region_heatmap: [],
    crime_type_distribution: [],
    alerts: [],
  };

  const cityTrend = Object.values(
    (data.yearly_trend ?? []).reduce((acc: Record<string, { year: string; count_total: number }>, row: any) => {
      const y = String(row.year);
      const v = Number(row.count_total ?? 0);
      acc[y] = { year: y, count_total: (acc[y]?.count_total ?? 0) + v };
      return acc;
    }, {} as Record<string, { year: string; count_total: number }>),
  ) as Array<{ year: string; count_total: number }>;
  cityTrend.sort((a, b) => Number(a.year) - Number(b.year));

  const heatRows = (data.hour_region_heatmap ?? [])
    .map((r: any) => ({ hour: String(r.hour_of_day), community_area: String(r.community_area), count_total: Number(r.count_total ?? 0) }))
    .slice(0, 700);
  const typeBars = (data.crime_type_distribution ?? [])
    .map((r: any) => ({ primary_type: String(r.primary_type), type_count: Number(r.type_count ?? 0) }))
    .sort((a: any, b: any) => b.type_count - a.type_count)
    .slice(0, 15);
  const alertBars = (data.alerts ?? []).map((r: any) => ({ community_area: String(r.community_area), mom_change: Number(r.mom_change ?? 0) }));

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Deployment Dashboard"
        title="Command Center"
        description="A high-value operational cockpit that combines forecast map, trend shifts, offense mix and alert priorities for rapid deployment planning."
        conclusion="Command signal: one operational surface for next-month risk, structural trend, and immediate anomaly escalation."
      />

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Map: Predicted Next-Month Risk by Region</h2>
        <RiskMap points={data.predicted_risk_map ?? []} />
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Trend: Crime Count vs Year by Region</h2>
          <LineCard data={cityTrend} xKey="year" yKey="count_total" color="#0ea5e9" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Heatmap: Hour of Day vs Region</h2>
          <HeatmapGridCard data={heatRows} xKey="hour" yKey="community_area" valueKey="count_total" />
        </GlassPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Crime Type Distribution (Top)</h2>
          <BarCard data={typeBars} xKey="primary_type" yKey="type_count" color="#2563eb" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Alert Panel: Largest Month-over-Month Increase</h2>
          <BarCard data={alertBars} xKey="community_area" yKey="mom_change" color="#f97316" />
        </GlassPanel>
      </div>

      <EvidencePanel title="Evidence Tables (Command Center)" summary="All raw aggregated slices remain available for appendix-level Q&A.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DataTable rows={data.yearly_trend ?? []} />
          <DataTable rows={data.crime_type_distribution ?? []} />
          <DataTable rows={data.hour_region_heatmap ?? []} />
          <DataTable rows={data.alerts ?? []} />
        </div>
      </EvidencePanel>

      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Activate rapid-response review where alert spikes coincide with high baseline risk and dense hour-region concentration.
        </p>
      </GlassPanel>
    </div>
  );
}


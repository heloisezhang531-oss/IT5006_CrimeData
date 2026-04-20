export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { HeatmapGridCard } from "@/components/charts";
import { DataTable } from "@/components/table";
import { GeoDistribution } from "@/components/geo-distribution";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function OperationsPage() {
  const heat = await apiGet<Record<string, number | string>>("/eda/temporal/hour-day-heatmap");
  const pointsPreview = await apiGet<Record<string, number | string>>("/eda/geography/points?year=2024&limit=300");
  const years = Array.from({ length: 10 }, (_, i) => 2015 + i);

  const heatRows = heat.data.map((r) => ({
    hour: String(r.hour ?? ""),
    day: String(r.day ?? ""),
    crime_count: Number(r.crime_count ?? 0),
  }));

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Geographical Distribution"
        title="Point Map + Community Choropleth Comparison"
        description="Streamlit parity geo module with year-based incident point visualization and two side-by-side community choropleths with detailed top-type context."
        conclusion="Geo signal: compare community burden between years while preserving point-level spatial intuition."
      />

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Story | Phase1 §3</p>
        <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr] xl:items-center">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">EDA Story: Spatial Burden Is Clustered and Policy-Relevant</h2>
            <p className="mt-2 text-sm text-slate-600">
              This map-first page carries the report's spatial story into operations: community-level differences are persistent and should
              be compared year-over-year, not read as isolated snapshots.
            </p>
          </div>
          <img
            src="/report-figures/operations-geo.png"
            alt="Operations geographic snapshot"
            className="h-56 w-full rounded-2xl border border-slate-200 object-cover"
          />
        </div>
      </GlassPanel>

      <GlassPanel>
        <GeoDistribution years={years} />
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Crime Heatmap: Hour vs Day</h2>
        <HeatmapGridCard data={heatRows} xKey="hour" yKey="day" valueKey="crime_count" />
      </GlassPanel>

      <EvidencePanel title="Evidence Tables (Geography)" summary="Raw point samples and hour-day heatmap rows for audit.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DataTable rows={pointsPreview.data} />
          <DataTable rows={heat.data} />
        </div>
      </EvidencePanel>

    </div>
  );
}


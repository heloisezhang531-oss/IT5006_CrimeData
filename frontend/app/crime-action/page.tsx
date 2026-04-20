export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { HeatmapGridCard, HorizontalStackedBarCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function CrimeActionPage() {
  const topCrime = await apiGet<Record<string, number | string>>("/eda/categorical/top-crime-types?limit=10");
  const topLocations = await apiGet<Record<string, number | string>>("/eda/categorical/top-locations?limit=10");
  const heat = await apiGet<Record<string, number | string>>("/eda/categorical/crime-location-heatmap?limit=10");

  const typeWide = Object.values(
    topCrime.data.reduce((acc, row) => {
      const name = String(row.primary_type ?? "UNKNOWN");
      if (!acc[name]) acc[name] = { primary_type: name, arrested: 0, not_arrested: 0 };
      const isArrested = String(row.arrest ?? "False") === "True";
      if (isArrested) {
        acc[name].arrested += Number(row.count ?? 0);
      } else {
        acc[name].not_arrested += Number(row.count ?? 0);
      }
      return acc;
    }, {} as Record<string, { primary_type: string; arrested: number; not_arrested: number }>),
  ).sort((a, b) => b.arrested + b.not_arrested - (a.arrested + a.not_arrested));

  const locationWide = Object.values(
    topLocations.data.reduce((acc, row) => {
      const name = String(row.location_description ?? "UNKNOWN");
      if (!acc[name]) acc[name] = { location_description: name, arrested: 0, not_arrested: 0 };
      const isArrested = String(row.arrest ?? "False") === "True";
      if (isArrested) {
        acc[name].arrested += Number(row.count ?? 0);
      } else {
        acc[name].not_arrested += Number(row.count ?? 0);
      }
      return acc;
    }, {} as Record<string, { location_description: string; arrested: number; not_arrested: number }>),
  ).sort((a, b) => b.arrested + b.not_arrested - (a.arrested + a.not_arrested));

  const heatRows = heat.data.map((r) => ({
    crime_type: String(r.primary_type ?? ""),
    location: String(r.location_description ?? ""),
    count: Number(r.count ?? 0),
  }));

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Categorical Analysis"
        title="Top Crimes, Top Locations, and Their Intersection"
        description="Streamlit parity module for top-10 crime types and locations with arrest breakdown, plus crime-location interaction heatmap."
        conclusion="Category signal: Theft/Battery and Street/Residence concentration should drive focused intervention playbooks."
      />

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Story | Phase1 §4-§6</p>
        <div className="grid gap-5 xl:grid-cols-[1.35fr_0.85fr] xl:items-center">
          <div className="xl:pr-3">
            <h2 className="text-2xl font-semibold text-slate-900">EDA Story II: Crime Mix and Domestic Burden Need Stratified Actions</h2>
            <p className="mt-2 text-sm text-slate-600">
              The report-level narrative is mapped here as offense-type and location-type intersections, so interventions can be matched to
              specific crime-context combinations rather than one uniform response.
            </p>
          </div>
          <img
            src="/pics/crime_action.jpg"
            alt="Crime action categorical snapshot"
            className="h-72 w-full rounded-2xl border border-slate-200 object-cover object-center xl:h-80"
          />
        </div>
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Top 10 Crime Types (Arrest Breakdown)</h2>
          <HorizontalStackedBarCard
            data={typeWide}
            yKey="primary_type"
            series={[
              { key: "arrested", name: "Arrested", color: "#FF6B6B" },
              { key: "not_arrested", name: "Not Arrested", color: "#4ECDC4" },
            ]}
          />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Top 10 Locations (Arrest Breakdown)</h2>
          <HorizontalStackedBarCard
            data={locationWide}
            yKey="location_description"
            series={[
              { key: "arrested", name: "Arrested", color: "#FF6B6B" },
              { key: "not_arrested", name: "Not Arrested", color: "#4ECDC4" },
            ]}
          />
        </GlassPanel>
      </div>

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Interactive Heatmap: Top Crimes vs Locations</h2>
        <HeatmapGridCard data={heatRows} xKey="location" yKey="crime_type" valueKey="count" />
      </GlassPanel>

      <EvidencePanel title="Evidence Tables (Categorical)" summary="Raw categorical rows for parity audit and drill-down.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DataTable rows={topCrime.data} />
          <DataTable rows={topLocations.data} />
        </div>
      </EvidencePanel>

    </div>
  );
}


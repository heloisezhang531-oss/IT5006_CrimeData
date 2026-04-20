export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { BarCard, LineCard, ScatterQuadrantCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function PerformancePage() {
  const hit = await apiGet<Record<string, number | string>>("/performance/hotspot-hit");
  const byRegion = await apiGet<Record<string, number | string>>("/performance/by-region");
  const byType = await apiGet<Record<string, number | string>>("/performance/by-crime-type");

  const regionScatter = byRegion.data.map((r) => ({
    accuracy: Number(r.accuracy ?? 0),
    recall: Number(r.recall ?? 0),
  }));

  const typeBars = byType.data
    .map((r) => ({ dominant_type: String(r.dominant_type), precision: Number(r.precision ?? 0) }))
    .sort((a, b) => b.precision - a.precision);

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Performance & Accountability"
        title="Where the Model Helps, Where It Fails"
        description="Quantify hotspot hit quality and reliability by region/type so operations do not overtrust weak segments."
        conclusion="Accountability signal: reliability is uneven, so deployment confidence should vary by region and offense profile."
      />

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Predicted Hotspot vs Actual Hotspot</h2>
        <LineCard data={hit.data} xKey="pred_month" yKey="hotspot_precision" color="#22c55e" />
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Region Reliability Quadrant (Accuracy vs Recall)</h2>
          <ScatterQuadrantCard data={regionScatter} xKey="accuracy" yKey="recall" xThreshold={0.8} yThreshold={0.6} color="#0ea5e9" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Performance by Dominant Crime Type (Precision)</h2>
          <BarCard data={typeBars} xKey="dominant_type" yKey="precision" color="#2563eb" />
        </GlassPanel>
      </div>

      <EvidencePanel title="Evidence Tables (Performance)" summary="Detailed metrics kept for audit, not primary presentation flow.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DataTable rows={byRegion.data} />
          <DataTable rows={byType.data} />
        </div>
      </EvidencePanel>

    </div>
  );
}


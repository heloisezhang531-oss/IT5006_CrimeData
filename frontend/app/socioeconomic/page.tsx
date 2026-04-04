export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { LineCard, ScatterQuadrantCard } from "@/components/charts";
import { RiskMap } from "@/components/risk-map";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function SocioeconomicPage() {
  const rvh = await apiGet<Record<string, number | string>>("/socio/risk-vs-hardship");
  const map = await apiGet<Record<string, number | string>>("/socio/predicted-risk-hardship-map");
  const trend = await apiGet<Record<string, number | string>>("/socio/region-risk-hardship-trend");

  const avgTrend = Object.values(
    trend.data.reduce((acc, row) => {
      const m = String(row.pred_month);
      const p = Number(row.pred_prob ?? 0);
      const h = Number(row.hardship_index ?? 0);
      if (!acc[m]) acc[m] = { pred_month: m, pred_prob: 0, hardship_index: 0, n: 0 };
      acc[m].pred_prob += p;
      acc[m].hardship_index += h;
      acc[m].n += 1;
      return acc;
    }, {} as Record<string, { pred_month: string; pred_prob: number; hardship_index: number; n: number }>),
  ).map((r) => ({ pred_month: r.pred_month, pred_prob: r.pred_prob / r.n, hardship_index: r.hardship_index / r.n }));

  const hardshipScatter = rvh.data.map((r) => ({
    hardship_index: Number(r.hardship_index ?? 0),
    pred_prob: Number(r.pred_prob ?? 0),
  }));

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Socioeconomic Context Monitoring"
        title="Risk Through the Hardship Lens"
        description="Use hardship-aware intelligence to distinguish structural vulnerability from short-term spikes and support balanced enforcement plus prevention."
        conclusion="Context signal: structurally vulnerable communities tend to carry persistently higher modeled risk, supporting prevention-oriented planning."
      />

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Predicted Risk Map with Hardship Overlay</h2>
        <RiskMap points={map.data as any} />
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Crime Risk vs Hardship Index</h2>
          <ScatterQuadrantCard data={hardshipScatter} xKey="hardship_index" yKey="pred_prob" xThreshold={50} yThreshold={0.5} color="#2563eb" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Region Risk Trend + Hardship Trend</h2>
          <LineCard data={avgTrend} xKey="pred_month" yKey="pred_prob" color="#0ea5e9" />
        </GlassPanel>
      </div>

      <EvidencePanel title="Evidence Tables (Socioeconomic)" summary="Community-level hardship-risk rows for policy review and export.">
        <DataTable rows={rvh.data} />
      </EvidencePanel>

      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Combine hotspot deployment with longer-horizon support planning in high-hardship communities to avoid purely reactive allocation.
        </p>
      </GlassPanel>
    </div>
  );
}


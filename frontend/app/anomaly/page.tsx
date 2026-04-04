export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { BarCard, HeatmapGridCard, LineCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function AnomalyPage() {
  const momCount = await apiGet<Record<string, number | string>>("/anomaly/mom-count-change");
  const momComp = await apiGet<Record<string, number | string>>("/anomaly/mom-composition-change");
  const obsPred = await apiGet<Record<string, number | string>>("/anomaly/observed-vs-predicted");

  const diffSeries = obsPred.data.map((r) => ({
    pred_month: String(r.pred_month),
    error_proxy: Math.abs(Number(r.actual_count ?? 0) - Number(r.pred_prob ?? 0) * 100),
  })).slice(-40);

  const momByMonth = Object.values(
    momCount.data.reduce((acc, row) => {
      const month = String(row.month);
      const v = Math.abs(Number(row.mom_change ?? 0));
      acc[month] = { month, mom_change_abs: (acc[month]?.mom_change_abs ?? 0) + v };
      return acc;
    }, {} as Record<string, { month: string; mom_change_abs: number }>),
  )
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-18);

  const compHeat = momComp.data
    .map((r) => ({
      month: String(r.month),
      primary_type: String(r.primary_type),
      mom_share_change: Math.abs(Number(r.mom_share_change ?? 0)),
    }))
    .slice(-300);

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Early Warning / Anomaly Detection"
        title="Detect Unexpected Change Before It Spreads"
        description="Monitor month-to-month deltas and observed-vs-predicted divergence to spot potential abnormal events and model failure zones."
        conclusion="Early-warning signal: monitor both absolute count shocks and composition drift to capture emerging threats sooner."
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Observed Crime vs Predicted Crime (Error Proxy)</h2>
          <LineCard data={diffSeries} xKey="pred_month" yKey="error_proxy" color="#f59e0b" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Absolute Month-to-Month Count Change</h2>
          <BarCard data={momByMonth} xKey="month" yKey="mom_change_abs" color="#3b82f6" />
        </GlassPanel>
      </div>

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Crime Composition Shift Heatmap</h2>
        <HeatmapGridCard data={compHeat} xKey="month" yKey="primary_type" valueKey="mom_share_change" />
      </GlassPanel>

      <EvidencePanel title="Evidence Tables (Anomaly)" summary="Detailed anomaly rows for incident review and briefing exports.">
        <div className="grid gap-4 xl:grid-cols-2">
          <DataTable rows={momCount.data} />
          <DataTable rows={momComp.data} />
        </div>
      </EvidencePanel>

      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Trigger review when forecast divergence and composition changes spike together, not when only one indicator moves.
        </p>
      </GlassPanel>
    </div>
  );
}


export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { HeatmapGridCard, MultiLineCard } from "@/components/charts";
import { GlassPanel, PageHero } from "@/components/ui";

export default async function AnomalyPage() {
  const momComp = await apiGet<Record<string, number | string>>("/anomaly/mom-composition-change");
  const obsPred = await apiGet<Record<string, number | string>>("/anomaly/observed-vs-predicted");

  const monthlyRiskCompare = Object.values(
    obsPred.data
      .filter((r) => String(r.pred_month).startsWith("2025-"))
      .reduce((acc, row) => {
        const month = String(row.pred_month);
        const actual = Number(row.actual_label ?? 0);
        const predicted = Number(row.pred_label ?? 0);
        acc[month] = {
          month,
          actual_high_risk_areas: (acc[month]?.actual_high_risk_areas ?? 0) + (Number.isFinite(actual) ? actual : 0),
          predicted_high_risk_areas: (acc[month]?.predicted_high_risk_areas ?? 0) + (Number.isFinite(predicted) ? predicted : 0),
        };
        return acc;
      }, {} as Record<string, { month: string; actual_high_risk_areas: number; predicted_high_risk_areas: number }>),
  )
    .sort((a, b) => a.month.localeCompare(b.month));

  const compHeat = momComp.data
    .map((r) => ({
      month: String(r.month),
      primary_type: String(r.primary_type),
      mom_share_change: Number(r.mom_share_change ?? 0),
    }));

  const compositionInsight = (() => {
    if (!compHeat.length) {
      return "Insight: no composition-shift data is available for the selected period.";
    }
    const strongest = compHeat.reduce((best, row) =>
      Math.abs(row.mom_share_change) > Math.abs(best.mom_share_change) ? row : best,
    );
    const direction =
      strongest.mom_share_change > 0
        ? "increase"
        : strongest.mom_share_change < 0
          ? "decrease"
          : "flat change";
    return `Insight: ${strongest.primary_type} shows the strongest month-over-month composition movement in ${strongest.month}, with a ${direction} of about ${(Math.abs(strongest.mom_share_change) * 100).toFixed(2)} percentage points, indicating where the crime mix is structurally rotating.`;
  })();

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Early Warning / Anomaly Detection"
        title="Monitor 2025 Prediction Consistency and Composition Drift"
        description="Focus on 2025 monthly model-vs-actual high-risk area counts and top-10 crime-type composition shifts."
        conclusion="Use both model consistency and composition drift signals before triggering operations changes."
      />

      <div className="space-y-6">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Actual vs Predicted High-Risk Area Counts</h2>
          <MultiLineCard
            data={monthlyRiskCompare}
            xKey="month"
            heightClass="h-[460px]"
            series={[
              { key: "actual_high_risk_areas", color: "#facc15", name: "Actual (High-risk areas)" },
              { key: "predicted_high_risk_areas", color: "#38bdf8", name: "Predicted (High-risk areas)" },
            ]}
          />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Top-10 Crime Type Composition Shift</h2>
          <HeatmapGridCard
            data={compHeat}
            xKey="month"
            yKey="primary_type"
            valueKey="mom_share_change"
            maxHeightClass="max-h-[620px]"
          />
          <p className="mt-3 text-xs text-zinc-400">{compositionInsight}</p>
        </GlassPanel>
      </div>
    </div>
  );
}


export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { BridgeCard, DumbbellCard, ScatterQuadrantCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function ModelLabPage() {
  const ablation = await apiGet<Record<string, number | string>>("/model-lab/ablation");
  const generalization = await apiGet<Record<string, unknown>>("/model-lab/generalization");
  const reliability = await apiGet<Record<string, number | string>>("/model-lab/reliability");

  const ablationRows = ablation.data.map((r) => ({
    model: String(r.model),
    without: Number(r.without_hardship_roc_auc ?? 0),
    with: Number(r.with_hardship_roc_auc ?? 0),
    delta_roc_auc: Number(r.delta_roc_auc ?? 0),
  }));
  const reliabilityPoints = reliability.data.map((r) => ({
    avg_accuracy: Number(r.avg_accuracy ?? 0),
    avg_recall: Number(r.avg_recall ?? 0),
  }));

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Model Lab"
        title="Ablation, Generalization, Reliability"
        description="Compare hardship inclusion impact, inspect FBI transfer artifacts, and review reliability bands before operational adoption."
        conclusion="Scientific signal: hardship context improves nonlinear models, but cross-system generalization still needs explicit adaptation."
      />

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Story | Phase2 §4.6-§4.7</p>
        <h2 className="text-2xl font-semibold text-slate-900">Model Story: Why Hardship Helps and Where Transfer Breaks</h2>
        <p className="text-sm text-slate-600">
          We place the report's modeling storyline directly in this page: hardship feature lift is visible in feature importance and global SHAP
          patterns, while external transfer still needs dedicated calibration.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <img
            src="/report-figures/model-shap-bar.png"
            alt="SHAP feature importance summary bar"
            className="h-52 w-full rounded-2xl border border-slate-200 bg-white object-contain p-2"
          />
          <img
            src="/report-figures/model-shap-beeswarm.png"
            alt="SHAP beeswarm summary"
            className="h-52 w-full rounded-2xl border border-slate-200 bg-white object-contain p-2"
          />
        </div>
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Hardship Ablation (With vs Without)</h2>
        <DumbbellCard
          data={ablationRows}
          labelKey="model"
          leftKey="without"
          rightKey="with"
          leftLabel="Without Hardship"
          rightLabel="With Hardship"
        />
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Ablation Delta (ROC-AUC)</h2>
          <BridgeCard data={ablationRows} labelKey="model" valueKey="delta_roc_auc" positiveColor="#22c55e" negativeColor="#f97316" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Reliability Bands (Accuracy vs Recall)</h2>
          <ScatterQuadrantCard data={reliabilityPoints} xKey="avg_accuracy" yKey="avg_recall" xThreshold={0.8} yThreshold={0.5} color="#2563eb" />
        </GlassPanel>
      </div>

      <EvidencePanel title="Evidence Tables (Model Lab)" summary="Full ablation/reliability rows and NIBRS artifact index are kept for verification.">
        <div className="space-y-4">
          <DataTable rows={ablation.data} />
          <DataTable rows={reliability.data} />
          <DataTable rows={generalization.data.map((r) => ({ file: String(r.file ?? ""), content_type: typeof r.content }))} />
        </div>
      </EvidencePanel>

      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Promote hardship-aware tree models for Chicago operations, while treating NIBRS transfer as an active R&D track rather than production-ready parity.
        </p>
      </GlassPanel>
    </div>
  );
}


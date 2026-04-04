export const dynamic = "force-dynamic";

import { apiGet } from "@/lib/api";
import { BridgeCard, DumbbellCard, HeatmapGridCard, LineCard, ScatterQuadrantCard, StackedAreaCard } from "@/components/charts";
import { EvidencePanel, GlassPanel, InsightPill } from "@/components/ui";
import { FloatingBackdrop, KpiCounter, Reveal, StorySectionShell } from "@/components/motion";
import { launchSections, openingKpis } from "@/lib/story";
import Link from "next/link";

type Row = Record<string, number | string>;

const metricsChicago2025 = [
  { model: "XGBoost", roc_auc: 0.9941, f1: 0.8262, precision: 0.7093, recall: 0.9892, accuracy: 0.9167 },
  { model: "Random Forest", roc_auc: 0.9911, f1: 0.8918, precision: 0.8711, recall: 0.9135, accuracy: 0.9556 },
  { model: "Logistic Regression", roc_auc: 0.8376, f1: 0.5491, precision: 0.4137, recall: 0.8162, accuracy: 0.7316 },
];

const metricsNibrs = [
  { model: "XGBoost", roc_auc: 0.4281, f1: 0.2872, precision: 0.2273, recall: 0.3901, accuracy: 0.5160 },
  { model: "Random Forest", roc_auc: 0.3556, f1: 0.1512, precision: 0.1467, recall: 0.1560, accuracy: 0.5621 },
  { model: "Logistic Regression", roc_auc: 0.5239, f1: 0.3921, precision: 0.2495, recall: 0.9149, accuracy: 0.2908 },
];

export default async function LaunchPage() {
  const health = await apiGet<{ status: string }>("/health");
  const countYearRegion = await apiGet<Row>("/strategic/crime-count-year");
  const countYearType = await apiGet<Row>("/strategic/crime-count-year-by-type");
  const hourType = await apiGet<Row>("/operations/hourly-count-by-type");
  const domestic = await apiGet<Row>("/crime-action/domestic-trend");
  const byRegion = await apiGet<Row>("/performance/by-region");
  const ablation = await apiGet<Row>("/model-lab/ablation");
  const riskHardship = await apiGet<Row>("/socio/risk-vs-hardship");

  const cityYear = Object.values(
    countYearRegion.data.reduce((acc, row) => {
      const year = String(row.year);
      const value = Number(row.count_total ?? 0);
      acc[year] = { year, count_total: (acc[year]?.count_total ?? 0) + value };
      return acc;
    }, {} as Record<string, { year: string; count_total: number }>),
  ).sort((a, b) => Number(a.year) - Number(b.year));

  const domesticMonthly = Object.values(
    domestic.data.reduce((acc, row) => {
      const month = String(row.month);
      const v = Number(row.count_domestic ?? 0);
      acc[month] = { month, count_domestic: (acc[month]?.count_domestic ?? 0) + v };
      return acc;
    }, {} as Record<string, { month: string; count_domestic: number }>),
  )
    .sort((a, b) => a.month.localeCompare(b.month))
    .slice(-36);

  const keyTypes = ["STALKING", "WEAPONS VIOLATION", "MOTOR VEHICLE THEFT", "BATTERY"];
  const typeByYearMap = new Map<string, Record<string, string | number>>();
  countYearType.data.forEach((row) => {
    const t = String(row.primary_type ?? "");
    if (!keyTypes.includes(t)) return;
    const y = String(row.year);
    if (!typeByYearMap.has(y)) typeByYearMap.set(y, { year: y });
    const cur = typeByYearMap.get(y)!;
    cur[t] = Number(row.type_count ?? 0);
  });
  const typeTrends = Array.from(typeByYearMap.values()).sort((a, b) => Number(a.year) - Number(b.year));

  const byHourTypeForHeat = hourType.data
    .map((r) => ({
      hour: String(r.hour_of_day),
      type: String(r.primary_type ?? "UNKNOWN"),
      count_total: Number(r.type_count ?? r.count_total ?? 0),
    }))
    .filter((r) => keyTypes.includes(r.type));

  const reliabilityPoints = byRegion.data.map((r) => ({
    accuracy: Number(r.accuracy ?? 0),
    recall: Number(r.recall ?? 0),
  }));

  const ablationRows = ablation.data.map((r) => ({
    model: String(r.model),
    without: Number(r.without_hardship_roc_auc ?? 0),
    with: Number(r.with_hardship_roc_auc ?? 0),
    delta: Number(r.delta_roc_auc ?? 0),
  }));

  const generalizationBridge = metricsChicago2025.map((c) => {
    const n = metricsNibrs.find((m) => m.model === c.model);
    return {
      model: c.model,
      roc_delta: Number((c.roc_auc - Number(n?.roc_auc ?? 0)).toFixed(4)),
      f1_delta: Number((c.f1 - Number(n?.f1 ?? 0)).toFixed(4)),
    };
  });

  const hardshipQuadrant = riskHardship.data.map((r) => ({
    pred_prob: Number(r.pred_prob ?? 0),
    hardship_index: Number(r.hardship_index ?? 0),
  }));

  return (
    <div className="relative ambient-gradient">
      <FloatingBackdrop />

      <div className="relative mx-auto grid max-w-7xl gap-10 lg:grid-cols-[240px_1fr]">
        <aside className="hidden lg:block">
          <div className="sticky top-24 glass p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">60-Min Flow</p>
            <div className="mt-4 space-y-2">
              {launchSections.map((s) => (
                <a key={s.id} href={`#${s.id}`} className="block rounded-xl px-3 py-2 text-xs text-slate-600 transition hover:bg-white hover:text-sky-700">
                  <p className="font-semibold">{s.chapter}</p>
                  <p>{s.title}</p>
                </a>
              ))}
            </div>
          </div>
        </aside>

        <main className="space-y-2">
          <StorySectionShell id="opening" className="pt-10 md:pt-14">
            <Reveal>
              <div className="glass-strong timeline-glow relative overflow-hidden p-8 md:p-12">
                <InsightPill label="Launch Keynote Mode" />
                <h1 className="story-headline mt-4 max-w-4xl">
                  Predictive Public Safety: From Spatial Evidence to Actionable Next-Month Risk Decisions
                </h1>
                <p className="story-copy mt-4 max-w-3xl">
                  We operationalize a community-month forecasting framework aligned with Phase1 EDA evidence and Phase2 model validation,
                  emphasizing interpretable risk allocation instead of reactive policing.
                </p>
                <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  {openingKpis.map((kpi) => (
                    <div key={kpi.label} className="rounded-2xl border border-white/70 bg-white/80 p-4">
                      <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{kpi.label}</p>
                      <p className="mt-1 text-3xl font-semibold text-slate-900">
                        <KpiCounter value={kpi.value} precision={kpi.precision ?? 0} suffix={kpi.unit ? ` ${kpi.unit}` : ""} />
                      </p>
                    </div>
                  ))}
                </div>
                <p className="mt-4 text-sm text-slate-500">
                  Backend: {health.data[0]?.status ?? "unknown"} | Data source mode: {String(health.meta?.data_source_mode ?? "n/a")}
                </p>
              </div>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="data-foundation">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">05:00-15:00 · Data Foundation</p>
                  <h2 className="story-headline mt-2">Trustworthy Pipeline Before Any Forecast Claim</h2>
                  <p className="story-copy mt-3 max-w-3xl">
                    Chicago event records and FBI NIBRS are harmonized into a consistent community-month representation with aligned offense semantics
                    and normalized spatial context.
                  </p>
                </div>
                <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr_auto_1fr] md:items-center">
                  <div className="float-slow rounded-2xl border border-slate-200 bg-white p-5">
                    <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Source A</p>
                    <p className="mt-2 text-lg font-semibold">Chicago Crimes</p>
                    <p className="mt-1 text-sm text-slate-500">2015-2024 event-level incidents</p>
                  </div>
                  <div className="text-center text-2xl text-slate-400">→</div>
                  <div className="float-slow rounded-2xl border border-slate-200 bg-white p-5">
                    <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Standardization</p>
                    <p className="mt-2 text-lg font-semibold">Feature Harmonization</p>
                    <p className="mt-1 text-sm text-slate-500">Temporal, spatial, and hardship context aligned</p>
                  </div>
                  <div className="text-center text-2xl text-slate-400">→</div>
                  <div className="float-slow rounded-2xl border border-slate-200 bg-white p-5">
                    <p className="text-xs uppercase tracking-[0.12em] text-slate-500">Source B</p>
                    <p className="mt-2 text-lg font-semibold">FBI NIBRS</p>
                    <p className="mt-1 text-sm text-slate-500">External robustness testbed</p>
                  </div>
                </div>
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="eda-space-time">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">15:00-27:00 · EDA Story I</p>
                  <h2 className="story-headline mt-2">Space-Time Concentration Is Systematic, Not Random</h2>
                  <p className="story-copy mt-3">
                    The 2020 structural dip and rebound, combined with stable hourly concentration patterns, support monthly forward-risk modeling.
                  </p>
                </div>
                <LineCard data={cityYear} xKey="year" yKey="count_total" />
                <HeatmapGridCard data={byHourTypeForHeat} xKey="hour" yKey="type" valueKey="count_total" />
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="eda-crime-domestic">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">27:00-35:00 · EDA Story II</p>
                  <h2 className="story-headline mt-2">Crime-Type Shift and Domestic Burden Need Stratified Response</h2>
                  <p className="story-copy mt-3">
                    Longitudinal offense composition and domestic incidence show why offense-specific and community-specific intervention is necessary.
                  </p>
                </div>
                <StackedAreaCard
                  data={typeTrends}
                  xKey="year"
                  series={[
                    { key: "STALKING", color: "#0ea5e9", name: "Stalking" },
                    { key: "WEAPONS VIOLATION", color: "#f97316", name: "Weapons Violation" },
                    { key: "MOTOR VEHICLE THEFT", color: "#6366f1", name: "Motor Vehicle Theft" },
                    { key: "BATTERY", color: "#22c55e", name: "Battery" },
                  ]}
                />
                <LineCard data={domesticMonthly} xKey="month" yKey="count_domestic" color="#ef4444" />
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-2xl border border-red-100 bg-red-50 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-red-500">Domestic Signal</p>
                    <p className="mt-2 text-3xl font-semibold text-red-700">19.3%</p>
                    <p className="mt-1 text-sm text-red-700/80">Share of all crimes identified as domestic in Phase1.</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 md:col-span-2">
                    <p className="text-sm text-slate-600">
                      Decision implication: combine offense trajectory monitoring with domestic-specific prevention and victim-support coordination,
                      instead of relying on one-size-fits-all patrol allocation.
                    </p>
                  </div>
                </div>
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="modeling-core">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">35:00-47:00 · Modeling Core</p>
                  <h2 className="story-headline mt-2">Tree Models Lead on Practical Predictive Utility</h2>
                  <p className="story-copy mt-3">
                    XGBoost dominates discrimination while Random Forest offers stronger precision-F1 balance for operational decision scenarios.
                  </p>
                </div>
                <BridgeCard
                  data={metricsChicago2025}
                  labelKey="model"
                  valueKey="roc_auc"
                  positiveColor="#2563eb"
                  negativeColor="#ef4444"
                />
                <ScatterQuadrantCard
                  data={metricsChicago2025}
                  xKey="precision"
                  yKey="recall"
                  xThreshold={0.7}
                  yThreshold={0.85}
                  color="#0ea5e9"
                />
                <EvidencePanel title="Evidence snapshot" summary="Chicago 2025 confusion-style performance proxies from Phase2 table metrics">
                  <BridgeCard
                    data={metricsChicago2025}
                    labelKey="model"
                    valueKey="f1"
                    positiveColor="#22c55e"
                    negativeColor="#ef4444"
                  />
                </EvidencePanel>
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="hardship-ablation">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">47:00-54:00 · Hardship Ablation</p>
                  <h2 className="story-headline mt-2">Hardship Complements Crime Signals in Nonlinear Models</h2>
                  <p className="story-copy mt-3">
                    Ablation confirms measurable gains when hardship context is included, especially for tree-based methods.
                  </p>
                </div>
                <DumbbellCard
                  data={ablationRows}
                  labelKey="model"
                  leftKey="without"
                  rightKey="with"
                  leftLabel="Without Hardship"
                  rightLabel="With Hardship"
                />
                <BridgeCard data={ablationRows} labelKey="model" valueKey="delta" positiveColor="#22c55e" negativeColor="#f97316" />
                <ScatterQuadrantCard
                  data={hardshipQuadrant}
                  xKey="hardship_index"
                  yKey="pred_prob"
                  xThreshold={50}
                  yThreshold={0.5}
                  color="#2563eb"
                />
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="generalization">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">54:00-58:00 · Generalization</p>
                  <h2 className="story-headline mt-2">Robust Across Time in Chicago, Partial Across Systems</h2>
                  <p className="story-copy mt-3">
                    External NIBRS transfer remains challenging, reinforcing the need for domain adaptation and schema-aware calibration.
                  </p>
                </div>
                <BridgeCard data={generalizationBridge} labelKey="model" valueKey="roc_delta" positiveColor="#0ea5e9" negativeColor="#f59e0b" />
                <ScatterQuadrantCard
                  data={metricsNibrs}
                  xKey="precision"
                  yKey="recall"
                  xThreshold={0.25}
                  yThreshold={0.45}
                  color="#f97316"
                />
              </GlassPanel>
            </Reveal>
          </StorySectionShell>

          <StorySectionShell id="roadmap">
            <Reveal>
              <GlassPanel className="space-y-6">
                <div>
                  <p className="story-subtitle">58:00-60:00 · Closing</p>
                  <h2 className="story-headline mt-2">From Prediction to Responsible Operational Intelligence</h2>
                  <p className="story-copy mt-3">
                    Next iteration focuses on richer labels, dynamic context, stronger external transfer, and fairness-by-design auditing.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    "Move from binary top-25% labels to multi-tier risk levels.",
                    "Add dynamic external features: weather, events, mobility context.",
                    "Strengthen NIBRS transfer with domain adaptation and calibration.",
                    "Introduce fairness and bias monitoring as first-class metrics.",
                  ].map((line, i) => (
                    <div key={line} className="rounded-2xl border border-slate-200 bg-white/80 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.13em] text-slate-500">Roadmap {i + 1}</p>
                      <p className="mt-2 text-sm text-slate-700">{line}</p>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-3">
                  <Link href="/command-center" className="rounded-full bg-slate-900 px-5 py-2 text-sm font-semibold text-white transition hover:bg-slate-700">
                    Open Command Center Appendix
                  </Link>
                  <Link href="/model-lab" className="rounded-full border border-slate-300 bg-white px-5 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
                    Open Model Lab Appendix
                  </Link>
                </div>
              </GlassPanel>
            </Reveal>
          </StorySectionShell>
        </main>
      </div>
    </div>
  );
}

export const dynamic = 'force-dynamic';
import Link from "next/link";
import { apiGet } from "@/lib/api";
import { FloatingBackdrop, KpiCounter } from "@/components/motion";
import { GlassPanel, InsightPill } from "@/components/ui";
import { openingKpis } from "@/lib/story";

const cards = [
  ["Strategic Monitoring", "/strategic", "Long-term regional and category trend intelligence."],
  ["Geographical Distribution", "/operations", "Year-based incident map and dual community choropleth comparison."],
  ["Categorical Analysis", "/crime-action", "Top crime/location arrest breakdown and intersection heatmap."],
  ["Raw Data", "/raw-data", "Recent 1,000 records with search and pagination."],
  ["Victim Risk Analysis", "/victim-risk", "Victim profiling, relationship risk, and activity-offense heatmap."],
  ["Early Warning", "/anomaly", "Month-over-month anomalies and predicted-vs-observed gaps."],
  ["Socioeconomic Context", "/socioeconomic", "Hardship-linked risk insights for preventive planning."],
  ["Performance", "/performance", "Hotspot hit rate and reliability slices by region/type."],
  ["Command Center", "/command-center", "Unified deployment dashboard with top alerts."],
  ["Model Lab", "/model-lab", "Ablation and FBI generalization evidence."],
] as const;

const storyline = [
  {
    chapter: "Phase1 §2-§3",
    title: "EDA Story I: Space-Time Concentration",
    description: "Use yearly, monthly, weekday, and hour-day concentration to define stable patrol windows.",
    href: "/strategic",
    image: "/report-figures/strategic-eda.png",
  },
  {
    chapter: "Phase1 §4-§6",
    title: "EDA Story II: Crime Mix and Domestic Burden",
    description: "Track offense- and location-specific burden instead of single global totals.",
    href: "/crime-action",
    image: "/report-figures/crime-action-categorical.png",
  },
  {
    chapter: "Phase2 §4.6-§4.7",
    title: "Model Story: Hardship Lift and Transfer Risk",
    description: "Ablation and external transfer diagnostics guide where model confidence is production-safe.",
    href: "/model-lab",
    image: "/report-figures/model-shap-beeswarm.png",
  },
] as const;

export default async function HomePage() {
  const health = await apiGet<{ status: string }>("/health");

  return (
    <div className="relative space-y-10 ambient-gradient rounded-[2rem] border border-white/60 p-4 md:p-8">
      <FloatingBackdrop />

      <section className="relative overflow-hidden glass-strong timeline-glow p-8 md:p-12">
        <InsightPill label="Launch Keynote Mode" />
        <h1 className="story-headline mt-4 max-w-5xl">
          Predictive Public Safety: From Spatial Evidence to Actionable Next-Month Risk Decisions
        </h1>
        <p className="story-copy mt-4 max-w-4xl">
          We operationalize a community-month forecasting framework aligned with Phase1 EDA evidence and Phase2 model
          validation, emphasizing interpretable risk allocation instead of reactive policing.
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
          Backend health: {health.data[0]?.status ?? "unknown"} | Data source mode:{" "}
          {String(health.meta?.data_source_mode ?? "n/a")}
        </p>
      </section>

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Storyline Handoff</p>
        <h2 className="story-headline mt-2 text-2xl md:text-3xl">EDA and Modeling Story Has Been Split Into Functional Pages</h2>
        <div className="grid gap-4 lg:grid-cols-3">
          {storyline.map((item) => (
            <Link key={item.href} href={item.href} className="rounded-2xl border border-slate-200 bg-white/85 p-4 transition hover:-translate-y-1">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-sky-700">{item.chapter}</p>
              <h3 className="mt-2 text-lg font-semibold text-slate-900">{item.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{item.description}</p>
              <img src={item.image} alt={item.title} className="mt-3 h-36 w-full rounded-xl border border-slate-200 object-cover" />
            </Link>
          ))}
        </div>
      </GlassPanel>

      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {cards.map(([title, href, desc]) => (
          <Link key={href} href={href} className="glass p-6 transition hover:-translate-y-1 hover:shadow-2xl">
            <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
            <p className="mt-2 text-sm text-slate-600">{desc}</p>
          </Link>
        ))}
      </section>
    </div>
  );
}


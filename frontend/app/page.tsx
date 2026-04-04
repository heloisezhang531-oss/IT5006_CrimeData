export const dynamic = 'force-dynamic';
import Link from "next/link";
import { apiGet } from "@/lib/api";
import { GlassPanel, PageHero } from "@/components/ui";

const cards = [
  ["Launch Keynote", "/launch", "60-minute storytelling stage aligned to Phase1 + Phase2 reports."],
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

export default async function HomePage() {
  const health = await apiGet<{ status: string }>("/health");

  return (
    <div className="space-y-10">
      <PageHero
        eyebrow="Crime Intelligence Platform"
        title="Predictive Public Safety Intelligence"
        description="An Apple-style analytical launch surface for EDA, next-month risk forecasting, hardship-aware monitoring, and cross-domain generalization experiments."
        conclusion="Start with Launch Keynote for the 1-hour product presentation, then open appendix pages for deep evidence."
      />

      <GlassPanel>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">Backend health</p>
            <p className="text-2xl font-semibold text-slate-900">{health.data[0]?.status ?? "unknown"}</p>
          </div>
          <p className="text-sm text-slate-600">Source mode: {String(health.meta?.data_source_mode ?? "n/a")}</p>
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


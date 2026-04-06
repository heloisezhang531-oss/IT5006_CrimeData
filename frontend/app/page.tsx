export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { HomeHub } from "@/components/home-hub";
import { openingKpis } from "@/lib/story";

const cards = [
  { title: "Strategic Monitoring", href: "/strategic", desc: "Long-term regional and category trend intelligence." },
  { title: "Geographical Distribution", href: "/operations", desc: "Year-based incident map and dual community choropleth comparison." },
  { title: "Categorical Analysis", href: "/crime-action", desc: "Top crime/location arrest breakdown and intersection heatmap." },
  { title: "Early Warning", href: "/anomaly", desc: "Month-over-month anomalies and observed-vs-predicted divergence." },
  { title: "Socioeconomic Context", href: "/socioeconomic", desc: "Hardship-linked risk insights for preventive planning." },
  { title: "Performance", href: "/performance", desc: "Hotspot hit rate and reliability slices by region/type." },
  { title: "Command Center", href: "/command-center", desc: "Unified deployment dashboard with top alerts." },
] as const;

const storyline = [
  {
    chapter: "Phase1 搂2-搂3",
    title: "EDA Story I: Space-Time Concentration",
    description: "Use yearly, monthly, weekday, and hour-day concentration to define stable patrol windows.",
    href: "/strategic",
    image: "/report-figures/strategic-eda.png",
  },
  {
    chapter: "Phase1 搂4-搂6",
    title: "EDA Story II: Crime Mix and Domestic Burden",
    description: "Track offense- and location-specific burden instead of single global totals.",
    href: "/crime-action",
    image: "/report-figures/crime-action-categorical.png",
  },
] as const;

export default async function HomePage() {
  const health = await apiGet<{ status: string }>("/health");
  const healthStatus = String(health.data[0]?.status ?? "unknown");
  const dataSourceMode = String(health.meta?.data_source_mode ?? "n/a");

  return (
    <HomeHub kpis={openingKpis} healthStatus={healthStatus} dataSourceMode={dataSourceMode} storyline={storyline} cards={cards} />
  );
}



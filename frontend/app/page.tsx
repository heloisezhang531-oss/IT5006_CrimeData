export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { HomeHub } from "@/components/home-hub";
import { openingKpis } from "@/lib/story";

const cards = [
  { title: "Strategic Monitoring", href: "/strategic", desc: "Long-term regional and category trend intelligence." },
  { title: "Geographical Distribution", href: "/operations", desc: "Year-based incident map and dual community choropleth comparison." },
  { title: "Categorical Analysis", href: "/crime-action", desc: "Top crime/location arrest breakdown and intersection heatmap." },
  { title: "Early Warning", href: "/anomaly", desc: "Month-over-month anomalies and observed-vs-predicted divergence." },
  { title: "Prediction", href: "/prediction", desc: "Predicted risk mapping and hardship-linked context insights." },
  { title: "Performance", href: "/performance", desc: "Hotspot hit rate and reliability slices by region/type." },
] as const;

export default async function HomePage() {
  const health = await apiGet<{ status: string }>("/health");
  const healthStatus = String(health.data[0]?.status ?? "unknown");
  const dataSourceMode = String(health.meta?.data_source_mode ?? "n/a");

  return (
    <HomeHub kpis={openingKpis} healthStatus={healthStatus} dataSourceMode={dataSourceMode} cards={cards} />
  );
}



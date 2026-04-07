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

export default async function HomePage() {
  const health = await apiGet<{ status: string }>("/health");
  const keyStats = await apiGet<Record<string, unknown>>("/eda/key-stats/arrest-domestic");
  const healthStatus = String(health.data[0]?.status ?? "unknown");
  const dataSourceMode = String(health.meta?.data_source_mode ?? "n/a");
  const arrestRows = (keyStats.data[0]?.arrest as Array<Record<string, unknown>>) ?? [];
  const arrestedCount = Number(
    arrestRows.find((row) => String(row.raw_value ?? "").toLowerCase() === "true")?.count ?? 0,
  );
  const totalCount = arrestRows.reduce((sum, row) => sum + Number(row.count ?? 0), 0);
  const arrestRate = totalCount > 0 ? (arrestedCount / totalCount) * 100 : 0;
  const kpis = openingKpis.map((item) =>
    item.label === "Arrest Rate"
      ? {
          ...item,
          value: Number(arrestRate.toFixed(1)),
        }
      : item,
  );

  return (
    <HomeHub kpis={kpis} healthStatus={healthStatus} dataSourceMode={dataSourceMode} cards={cards} />
  );
}



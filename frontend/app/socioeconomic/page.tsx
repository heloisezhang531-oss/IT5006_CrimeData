export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { DataTable } from "@/components/table";
import { CommunityScatterCard } from "@/components/charts";
import { RiskMap } from "@/components/risk-map";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function SocioeconomicPage() {
  const mapTargetMonth = "2025-06";
  const map = await apiGet<Record<string, number | string>>(`/socio/predicted-risk-hardship-map?target_month=${mapTargetMonth}`);
  const communityGeo = await apiGet<Record<string, unknown>>("/eda/geography/community-geojson");

  const communityNameByArea = (() => {
    const features = (communityGeo.data?.[0]?.geojson as { features?: Array<{ properties?: Record<string, unknown> }> } | undefined)?.features ?? [];
    const lookup: Record<number, string> = {};
    features.forEach((feature) => {
      const areaRaw = feature?.properties?.area_numbe;
      const nameRaw = feature?.properties?.community;
      const area = Number(areaRaw);
      const name = typeof nameRaw === "string" ? nameRaw.trim() : "";
      if (Number.isFinite(area) && name.length > 0) {
        lookup[area] = name;
      }
    });
    return lookup;
  })();

  const hardshipScatter = map.data.map((r) => ({
    community_area: Number(r.community_area ?? 0),
    community_name: (() => {
      const area = Number(r.community_area ?? 0);
      const directName = typeof r.community_name === "string" ? r.community_name.trim() : "";
      if (directName.length > 0) return directName;
      return communityNameByArea[area] ?? "Unknown community";
    })(),
    pred_month: String(r.pred_month ?? mapTargetMonth),
    hardship_index: Number(r.hardship_index ?? 0),
    pred_prob: Number(r.pred_prob ?? 0),
    pred_label: Number(r.pred_label ?? 0),
  }));

  const predictedHighRiskCutoff = (() => {
    const highRiskValues = hardshipScatter
      .filter((row) => Number(row.pred_label) === 1)
      .map((row) => Number(row.pred_prob))
      .filter((value) => Number.isFinite(value));
    if (highRiskValues.length > 0) {
      return Math.min(...highRiskValues);
    }
    const all = hardshipScatter.map((row) => Number(row.pred_prob)).filter((value) => Number.isFinite(value));
    if (all.length === 0) return undefined;
    const sorted = [...all].sort((a, b) => a - b);
    const idx = Math.max(0, Math.ceil(sorted.length * 0.75) - 1);
    return sorted[idx];
  })();

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Socioeconomic Context Monitoring"
        title="Risk Through the Hardship Lens"
        description="Data used in this page is from June 2025. Use hardship-aware intelligence to distinguish structural vulnerability from short-term spikes and support balanced enforcement plus prevention."
        conclusion="Context signal: structurally vulnerable communities tend to carry persistently higher modeled risk, supporting prevention-oriented planning."
      />

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Story | Phase2 §4.6</p>
        <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr] xl:items-center">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">Hardship Story: Context Features Add Operational Meaning</h2>
            <p className="mt-2 text-sm text-slate-600">
              This panel mirrors the report's hardship argument: predicted risk should be read together with structural deprivation context
              so resources can blend enforcement and prevention.
            </p>
          </div>
          <img
            src="/pics/socioeconomic.jpg"
            alt="Socioeconomic risk map snapshot"
            className="h-56 w-full rounded-2xl border border-slate-200 object-cover"
          />
        </div>
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-4 text-lg font-semibold">Predicted Risk Map with Hardship Overlay</h2>
        <RiskMap points={map.data as any} />
      </GlassPanel>

      <div className="grid gap-6">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Crime Risk vs Hardship Index</h2>
          <CommunityScatterCard
            data={hardshipScatter}
            xKey="hardship_index"
            yKey="pred_prob"
            labelKey="community_name"
            idKey="community_area"
            monthKey="pred_month"
            yThreshold={predictedHighRiskCutoff}
            yThresholdLabel={"High-risk\ncutoff"}
          />
        </GlassPanel>
      </div>

      <EvidencePanel title="Evidence Tables (Socioeconomic)" summary="Community-level hardship-risk rows for policy review and export.">
        <DataTable rows={hardshipScatter as Record<string, unknown>[]} />
      </EvidencePanel>

    </div>
  );
}


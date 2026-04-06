export const dynamic = 'force-dynamic';
import { apiGet } from "@/lib/api";
import { BarCard, GroupedBarCard, HeatmapGridCard, LineCard, PieCard } from "@/components/charts";
import { DataTable } from "@/components/table";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

export default async function StrategicPage() {
  const total = await apiGet<Record<string, number | string>>("/eda/overview/total-records");
  const missing = await apiGet<Record<string, number | string>>("/eda/overview/missing-values");
  const keyStats = await apiGet<Record<string, unknown>>("/eda/key-stats/arrest-domestic");
  const yearly = await apiGet<Record<string, number | string>>("/eda/temporal/yearly");
  const monthly = await apiGet<Record<string, number | string>>("/eda/temporal/monthly");
  const dayOfWeek = await apiGet<Record<string, number | string>>("/eda/temporal/day-of-week");
  const heat = await apiGet<Record<string, number | string>>("/eda/temporal/hour-day-heatmap");
  const typeYearly = await apiGet<Record<string, number | string>>("/eda/temporal/crime-types-yearly?limit=all");

  const totalRecords = Number(total.data[0]?.total_records ?? 0);
  const arrestRows = (keyStats.data[0]?.arrest as Array<Record<string, number | string>>) ?? [];
  const domesticRows = (keyStats.data[0]?.domestic as Array<Record<string, number | string>>) ?? [];

  const monthlyNamed = monthly.data.map((r) => ({
    month_name: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][
      Math.max(0, Number(r.month ?? 1) - 1)
    ],
    count: Number(r.count ?? 0),
  }));

  const daySeries = dayOfWeek.data
    .map((r) => ({
      Day: String(r.Day ?? r.day ?? ""),
      count: Number(r.count ?? 0),
      day_index: Number(r.day_index ?? 0),
    }))
    .sort((a, b) => a.day_index - b.day_index);

  const heatRows = heat.data.map((r) => ({
    hour: String(r.hour ?? ""),
    day: String(r.day ?? ""),
    crime_count: Number(r.crime_count ?? 0),
  }));

  const typeRows = typeYearly.data.map((r) => ({
    year: String(r.year),
    primary_type: String(r.primary_type),
    count: Number(r.count ?? 0),
  }));
  const totalByType = typeRows.reduce((acc, row) => {
    acc[row.primary_type] = (acc[row.primary_type] ?? 0) + row.count;
    return acc;
  }, {} as Record<string, number>);

  const withPct = typeRows.map((r) => {
    const totalType = totalByType[r.primary_type] || 1;
    const percentage = (r.count / totalType) * 100;
    const y_visual = percentage <= 30 ? percentage : 30 + (percentage - 30) * (10 / 70);
    return { ...r, percentage, y_visual };
  });

  const typeOrder = Object.entries(totalByType)
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => name);
  const years = Array.from(new Set(withPct.map((r) => r.year))).sort();
  const groupedData = typeOrder.map((crime) => {
    const row: Record<string, number | string> = { primary_type: crime };
    years.forEach((year) => {
      const found = withPct.find((r) => r.primary_type === crime && r.year === year);
      row[year] = found ? Number(found.y_visual.toFixed(2)) : 0;
    });
    return row;
  });

  const palette = ["#1d4ed8", "#0ea5e9", "#06b6d4", "#14b8a6", "#22c55e", "#84cc16", "#f59e0b", "#f97316", "#ef4444", "#ec4899"];

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Overview + Key Statistics + Temporal Trends"
        title="Chicago Crime EDA Alignment (2015-2024)"
        description="Streamlit parity view for dataset overview, arrest/domestic split, and temporal signatures across year, month, weekday, and hour-day patterns."
        conclusion="Baseline EDA signal: long-run burden is persistent with clear seasonality and time-window concentration."
      />

      <GlassPanel className="space-y-4">
        <p className="story-subtitle">Report Story | Phase1 §2-§3</p>
        <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr] xl:items-center">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">EDA Story I: Space-Time Concentration Is Stable Enough for Forecasting</h2>
            <p className="mt-2 text-sm text-slate-600">
              This section keeps the same evidence chain used in the report: annual burden persistence, seasonal monthly structure, and
              hour-day concentration windows.
            </p>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              <li>Yearly trend anchors long-run baseline pressure.</li>
              <li>Monthly and weekday splits expose recurring operational windows.</li>
              <li>Hour-day heatmap supports shift-level deployment planning.</li>
            </ul>
          </div>
          <img
            src="/report-figures/strategic-eda.png"
            alt="Strategic EDA snapshot"
            className="h-56 w-full rounded-2xl border border-slate-200 object-cover"
          />
        </div>
      </GlassPanel>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Dataset Overview</h2>
          <p className="text-sm text-slate-600">Total Crime Records (2015-2024)</p>
          <p className="mt-2 text-4xl font-semibold text-slate-900">{totalRecords.toLocaleString()}</p>
          <p className="mt-4 text-sm text-slate-500">Time range fixed to Jan 2015 - Dec 2024.</p>
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Missing Values Percentage by Column</h2>
          <BarCard data={missing.data} xKey="Column" yKey="Missing Rate (%)" color="#f97316" />
        </GlassPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Arrest Distribution</h2>
          <PieCard data={arrestRows} nameKey="status" valueKey="count" colors={["#FF6B6B", "#4ECDC4"]} />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Domestic Violence Distribution</h2>
          <PieCard data={domesticRows} nameKey="type" valueKey="count" colors={["#FF6B6B", "#4ECDC4"]} />
        </GlassPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Annual Crime Trend (2015-2024)</h2>
          <LineCard data={yearly.data} xKey="year" yKey="count" color="#4682B4" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Monthly Distribution</h2>
          <BarCard data={monthlyNamed} xKey="month_name" yKey="count" color="#ff7f50" />
        </GlassPanel>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Day of Week Distribution</h2>
          <BarCard data={daySeries} xKey="Day" yKey="count" color="#ef4444" />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-4 text-lg font-semibold">Crime Heatmap: Hour vs Day</h2>
          <HeatmapGridCard data={heatRows} xKey="hour" yKey="day" valueKey="crime_count" />
        </GlassPanel>
      </div>

      <GlassPanel>
        <h2 className="mb-2 text-lg font-semibold">All Crime Types Temporal Trends (Scaled 30%-100%)</h2>
        <p className="mb-4 text-xs text-slate-500">
          Y-axis follows Streamlit compressed display: 0-30% linear, 30-100% compressed.
        </p>
        <GroupedBarCard
          data={groupedData}
          xKey="primary_type"
          series={years.map((year, idx) => ({
            key: year,
            name: year,
            color: palette[idx % palette.length],
          }))}
        />
      </GlassPanel>

      <EvidencePanel
        title="Evidence Tables (Overview/Temporal)"
        summary="Expanded rows for parity audit and cross-checking with Streamlit output."
      >
        <div className="grid gap-4 xl:grid-cols-3">
          <DataTable rows={missing.data} />
          <DataTable rows={yearly.data} />
          <DataTable rows={typeYearly.data} />
        </div>
      </EvidencePanel>
      <GlassPanel>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-[0.12em] text-slate-500">One-line decision</h3>
        <p className="text-sm text-slate-700">
          Use annual trend persistence and hourly-weekday concentration jointly when planning baseline patrol and prevention priorities.
        </p>
      </GlassPanel>
    </div>
  );
}


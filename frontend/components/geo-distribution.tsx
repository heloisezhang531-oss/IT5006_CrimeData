"use client";

import dynamic from "next/dynamic";

const GeoDistributionClient = dynamic(
  () => import("./geo-distribution-client").then((m) => m.GeoDistributionClient),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-6">
        <div className="h-[420px] rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
          Loading point map...
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="h-[460px] rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            Loading choropleth...
          </div>
          <div className="h-[460px] rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            Loading choropleth...
          </div>
        </div>
      </div>
    ),
  },
);

export function GeoDistribution({ years }: { years: number[] }) {
  return <GeoDistributionClient years={years} />;
}

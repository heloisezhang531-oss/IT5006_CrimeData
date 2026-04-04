"use client";

import dynamic from "next/dynamic";

export type RiskPoint = {
  community_area: number;
  pred_prob: number;
  risk_level: string;
};

const RiskMapClient = dynamic(
  () => import("./risk-map-client").then((m) => m.RiskMapClient),
  {
    ssr: false,
    loading: () => (
      <div className="h-[420px] w-full rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
        Loading map tiles...
      </div>
    ),
  },
);

export function RiskMap({ points }: { points: RiskPoint[] }) {
  return <RiskMapClient points={points} />;
}

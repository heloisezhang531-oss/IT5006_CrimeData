"use client";

import dynamic from "next/dynamic";

export type RiskPoint = {
  community_area: number;
  community_name?: string;
  pred_prob: number;
  risk_level: string;
  hardship_index?: number;
  pred_month?: string;
};

const RiskMapClient = dynamic(
  () => import("./risk-map-client").then((m) => m.RiskMapClient),
  {
    ssr: false,
    loading: () => (
      <div className="h-[420px] w-full border border-machine-yellow/20 bg-void/55 p-4 text-xs uppercase tracking-[0.14em] text-zinc-500">
        Loading map tiles...
      </div>
    ),
  },
);

export function RiskMap({ points }: { points: RiskPoint[] }) {
  return <RiskMapClient points={points} />;
}

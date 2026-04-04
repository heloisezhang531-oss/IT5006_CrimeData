"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Row = Record<string, string | number | null>;

const GRID_STROKE = "#d9e4f0";

export function LineCard({
  data,
  xKey,
  yKey,
  color = "#0ea5e9",
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line type="monotone" dataKey={yKey} stroke={color} strokeWidth={2.8} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BarCard({
  data,
  xKey,
  yKey,
  color = "#2563eb",
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={yKey} fill={color} radius={[10, 10, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function StackedAreaCard({
  data,
  xKey,
  series,
}: {
  data: Row[];
  xKey: string;
  series: Array<{ key: string; color: string; name?: string }>;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 18, left: 0, bottom: 18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {series.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stackId="1"
              stroke={s.color}
              fill={s.color}
              fillOpacity={0.75}
              name={s.name ?? s.key}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function normalize01(v: number, min: number, max: number) {
  if (!Number.isFinite(v)) return 0;
  if (max - min <= 1e-12) return 0.5;
  return (v - min) / (max - min);
}

export function HeatmapGridCard({
  data,
  xKey,
  yKey,
  valueKey,
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  valueKey: string;
}) {
  const xLabels = Array.from(new Set(data.map((d) => String(d[xKey]))));
  const yLabels = Array.from(new Set(data.map((d) => String(d[yKey]))));
  const valueMap = new Map<string, number>();
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  data.forEach((d) => {
    const x = String(d[xKey]);
    const y = String(d[yKey]);
    const v = Number(d[valueKey] ?? 0);
    valueMap.set(`${x}|${y}`, v);
    min = Math.min(min, v);
    max = Math.max(max, v);
  });
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    min = 0;
    max = 1;
  }

  return (
    <div className="space-y-3">
      <div className="grid max-h-80 overflow-auto rounded-2xl border border-slate-200 bg-white/80 p-3 text-[11px]">
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `70px repeat(${Math.max(xLabels.length, 1)}, minmax(20px,1fr))` }}
        >
          <div />
          {xLabels.map((x) => (
            <div key={x} className="truncate text-center text-[10px] font-semibold text-slate-500">
              {x}
            </div>
          ))}
          {yLabels.map((y) => (
            <div key={`row-${y}`} className="contents">
              <div className="truncate pr-2 text-right text-[10px] font-semibold text-slate-500">
                {y}
              </div>
              {xLabels.map((x) => {
                const v = valueMap.get(`${x}|${y}`) ?? 0;
                const p = normalize01(v, min, max);
                const bg = `rgba(29, 78, 216, ${0.12 + 0.78 * p})`;
                return <div key={`${x}-${y}`} title={`${x}, ${y}: ${v}`} className="h-6 rounded" style={{ background: bg }} />;
              })}
            </div>
          ))}
        </div>
      </div>
      <p className="text-xs text-slate-500">
        Intensity scale: {min.toFixed(0)} to {max.toFixed(0)}
      </p>
    </div>
  );
}

export function DumbbellCard({
  data,
  labelKey,
  leftKey,
  rightKey,
  leftLabel = "Without",
  rightLabel = "With",
}: {
  data: Row[];
  labelKey: string;
  leftKey: string;
  rightKey: string;
  leftLabel?: string;
  rightLabel?: string;
}) {
  const min = Math.min(...data.map((d) => Math.min(Number(d[leftKey] ?? 0), Number(d[rightKey] ?? 0))), 0);
  const max = Math.max(...data.map((d) => Math.max(Number(d[leftKey] ?? 0), Number(d[rightKey] ?? 0))), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-slate-400" />{leftLabel}</span>
        <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 rounded-full bg-sky-500" />{rightLabel}</span>
      </div>
      <div className="space-y-3">
        {data.map((r, idx) => {
          const label = String(r[labelKey]);
          const left = Number(r[leftKey] ?? 0);
          const right = Number(r[rightKey] ?? 0);
          const leftPos = normalize01(left, min, max);
          const rightPos = normalize01(right, min, max);
          const lo = Math.min(leftPos, rightPos);
          const width = Math.max(Math.abs(rightPos - leftPos), 0.008);
          return (
            <div key={`${label}-${idx}`} className="grid grid-cols-[160px_1fr] items-center gap-3">
              <p className="truncate text-xs font-semibold text-slate-600">{label}</p>
              <div className="relative h-8 rounded-xl bg-slate-100">
                <div className="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-slate-300" style={{ left: `${lo * 100}%`, width: `${width * 100}%` }} />
                <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-slate-500 shadow-sm" style={{ left: `calc(${leftPos * 100}% - 6px)` }} />
                <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-sky-500 shadow-sm" style={{ left: `calc(${rightPos * 100}% - 6px)` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ScatterQuadrantCard({
  data,
  xKey,
  yKey,
  color = "#2563eb",
  xThreshold = 0.5,
  yThreshold = 0.5,
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  color?: string;
  xThreshold?: number;
  yThreshold?: number;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 16, left: 0, bottom: 12 }}>
          <CartesianGrid stroke={GRID_STROKE} />
          <XAxis dataKey={xKey} type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey={yKey} type="number" tick={{ fontSize: 12 }} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <ReferenceLine x={xThreshold} stroke="#64748b" strokeDasharray="4 4" />
          <ReferenceLine y={yThreshold} stroke="#64748b" strokeDasharray="4 4" />
          <Scatter data={data} fill={color} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BridgeCard({
  data,
  labelKey,
  valueKey,
  positiveColor = "#16a34a",
  negativeColor = "#ef4444",
}: {
  data: Row[];
  labelKey: string;
  valueKey: string;
  positiveColor?: string;
  negativeColor?: string;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 18 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey={labelKey} tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={valueKey} radius={[8, 8, 0, 0]}>
            {data.map((r, i) => {
              const v = Number(r[valueKey] ?? 0);
              return <Cell key={i} fill={v >= 0 ? positiveColor : negativeColor} />;
            })}
          </Bar>
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PieCard({
  data,
  nameKey,
  valueKey,
  colors,
}: {
  data: Row[];
  nameKey: string;
  valueKey: string;
  colors?: string[];
}) {
  const palette = colors ?? ["#FF6B6B", "#4ECDC4", "#0ea5e9", "#f59e0b", "#6366f1"];
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip />
          <Legend />
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            cx="50%"
            cy="50%"
            outerRadius={108}
            label
          >
            {data.map((entry, idx) => (
              <Cell key={`${nameKey}-${idx}`} fill={palette[idx % palette.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HorizontalStackedBarCard({
  data,
  yKey,
  series,
}: {
  data: Row[];
  yKey: string;
  series: Array<{ key: string; color: string; name?: string }>;
}) {
  return (
    <div className="h-[460px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 12, right: 20, left: 20, bottom: 12 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis type="number" tick={{ fontSize: 12 }} />
          <YAxis dataKey={yKey} type="category" tick={{ fontSize: 12 }} width={170} />
          <Tooltip />
          <Legend />
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} stackId="stack" fill={s.color} name={s.name ?? s.key} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function GroupedBarCard({
  data,
  xKey,
  series,
}: {
  data: Row[];
  xKey: string;
  series: Array<{ key: string; color: string; name?: string }>;
}) {
  return (
    <div className="h-[620px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 24, left: 0, bottom: 80 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey={xKey} interval={0} angle={-30} textAnchor="end" height={90} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={s.color} name={s.name ?? s.key} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

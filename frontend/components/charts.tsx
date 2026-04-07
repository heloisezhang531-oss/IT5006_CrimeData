"use client";

import type { ReactNode } from "react";
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

const GRID_STROKE = "rgba(250, 204, 21, 0.12)";
const AXIS_TICK = { fill: "#71717a", fontSize: 11, fontFamily: "JetBrains Mono" };
const TOOLTIP_STYLE = {
  backgroundColor: "#050505",
  border: "1px solid rgba(250, 204, 21, 0.35)",
  borderRadius: "0px",
  color: "#f8fafc",
  fontFamily: "JetBrains Mono",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};
const TOOLTIP_LABEL_STYLE = { color: "#facc15", fontSize: "11px" };
const LEGEND_STYLE = { color: "#a1a1aa", fontSize: "11px", textTransform: "uppercase" };

function hasRows(data: Row[]): boolean {
  return Array.isArray(data) && data.length > 0;
}

function ChartEmpty({ label }: { label: string }) {
  return <div className="chart-empty">{label}</div>;
}

function ChartFrame({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`chart-frame ${className ?? ""}`}>{children}</div>;
}

export function LineCard({
  data,
  xKey,
  yKey,
  color = "#facc15",
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO TREND DATA" />;
  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Line type="monotone" dataKey={yKey} stroke={color} strokeWidth={2.2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function MultiLineCard({
  data,
  xKey,
  series,
  heightClass = "h-[620px]",
}: {
  data: Row[];
  xKey: string;
  series: Array<{ key: string; color: string; name?: string }>;
  heightClass?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO TREND DATA" />;
  return (
    <div className={`${heightClass} w-full`}>
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={2.2}
                dot={false}
                name={s.name ?? s.key}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function BarCard({
  data,
  xKey,
  yKey,
  color = "#facc15",
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO BAR DATA" />;
  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Bar dataKey={yKey} fill={color} radius={[0, 0, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
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
  if (!hasRows(data)) return <ChartEmpty label="NO STACKED DATA" />;
  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 12, right: 18, left: 0, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            {series.map((s) => (
              <Area
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stackId="1"
                stroke={s.color}
                fill={s.color}
                fillOpacity={0.6}
                name={s.name ?? s.key}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

function normalize01(v: number, min: number, max: number) {
  if (!Number.isFinite(v)) return 0;
  if (max - min <= 1e-12) return 0.5;
  return (v - min) / (max - min);
}

function formatIntensityScaleValue(v: number): string {
  if (!Number.isFinite(v)) return "N/A";
  const abs = Math.abs(v);
  if (abs >= 100) return v.toFixed(0);
  if (abs >= 10) return v.toFixed(1);
  if (abs >= 1) return v.toFixed(2);
  return `${(v * 100).toFixed(2)}%`;
}

function heatmapCellBackground(v: number, min: number, max: number): string {
  const p = normalize01(v, min, max);
  return `rgba(250, 204, 21, ${0.12 + 0.78 * p})`;
}

export function HeatmapGridCard({
  data,
  xKey,
  yKey,
  valueKey,
  maxHeightClass = "max-h-80",
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  valueKey: string;
  maxHeightClass?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO HEATMAP DATA" />;

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
      <div className={`${maxHeightClass} overflow-auto border border-machine-yellow/20 bg-void/50 p-3`}>
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `70px repeat(${Math.max(xLabels.length, 1)}, minmax(20px,1fr))` }}
        >
          <div />
          {xLabels.map((x) => (
            <div key={x} className="truncate text-center text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
              {x}
            </div>
          ))}
          {yLabels.map((y) => (
            <div key={`row-${y}`} className="contents">
              <div className="truncate pr-2 text-right text-[10px] font-semibold uppercase tracking-[0.1em] text-zinc-500">
                {y}
              </div>
              {xLabels.map((x) => {
                const v = valueMap.get(`${x}|${y}`) ?? 0;
                const bg = heatmapCellBackground(v, min, max);
                return <div key={`${x}-${y}`} title={`${x}, ${y}: ${v}`} className="h-6" style={{ background: bg }} />;
              })}
            </div>
          ))}
        </div>
      </div>
      <p className="text-[10px] uppercase tracking-[0.14em] text-zinc-500">
        INTENSITY SCALE: {formatIntensityScaleValue(min)} TO {formatIntensityScaleValue(max)}
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
  if (!hasRows(data)) return <ChartEmpty label="NO DUMBBELL DATA" />;
  const min = Math.min(...data.map((d) => Math.min(Number(d[leftKey] ?? 0), Number(d[rightKey] ?? 0))), 0);
  const max = Math.max(...data.map((d) => Math.max(Number(d[leftKey] ?? 0), Number(d[rightKey] ?? 0))), 1);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 text-[10px] uppercase tracking-[0.14em] text-zinc-500">
        <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 bg-zinc-500" />{leftLabel}</span>
        <span className="inline-flex items-center gap-1"><span className="h-2.5 w-2.5 bg-machine-yellow" />{rightLabel}</span>
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
              <p className="truncate text-xs font-semibold uppercase tracking-[0.08em] text-zinc-400">{label}</p>
              <div className="relative h-8 border border-machine-yellow/20 bg-void/55">
                <div className="absolute top-1/2 h-0.5 -translate-y-1/2 bg-zinc-700" style={{ left: `${lo * 100}%`, width: `${width * 100}%` }} />
                <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 bg-zinc-500" style={{ left: `calc(${leftPos * 100}% - 6px)` }} />
                <div className="absolute top-1/2 h-3 w-3 -translate-y-1/2 bg-machine-yellow" style={{ left: `calc(${rightPos * 100}% - 6px)` }} />
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
  color = "#facc15",
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
  if (!hasRows(data)) return <ChartEmpty label="NO SCATTER DATA" />;
  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 16, left: 0, bottom: 12 }}>
            <CartesianGrid stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis dataKey={yKey} type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <ReferenceLine x={xThreshold} stroke="#71717a" strokeDasharray="4 4" />
            <ReferenceLine y={yThreshold} stroke="#71717a" strokeDasharray="4 4" />
            <Scatter data={data} fill={color} />
          </ScatterChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function CommunityScatterCard({
  data,
  xKey,
  yKey,
  labelKey,
  idKey,
  monthKey,
  color = "#facc15",
  xThreshold,
  yThreshold,
  yThresholdLabel,
}: {
  data: Row[];
  xKey: string;
  yKey: string;
  labelKey: string;
  idKey: string;
  monthKey: string;
  color?: string;
  xThreshold?: number;
  yThreshold?: number;
  yThresholdLabel?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO SCATTER DATA" />;
  const cutoffLines = (yThresholdLabel ?? "")
    .split("\n")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  const tooltipContent = ({ active, payload }: { active?: boolean; payload?: Array<{ payload?: Row }> }) => {
    if (!active || !payload || payload.length === 0) return null;
    const point = payload[0]?.payload ?? {};
    const communityName = String(point[labelKey] ?? "Unknown community");
    const month = String(point[monthKey] ?? "N/A");
    const hardship = Number(point[xKey] ?? 0);
    const risk = Number(point[yKey] ?? 0);
    return (
      <div style={TOOLTIP_STYLE}>
        <div style={{ ...TOOLTIP_LABEL_STYLE, marginBottom: "4px" }}>{communityName}</div>
        <div>Month: {month}</div>
        <div>Hardship Index: {hardship.toFixed(2)}</div>
        <div>Predicted Risk: {(risk * 100).toFixed(1)}%</div>
      </div>
    );
  };

  return (
    <div className="h-[560px] w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 16, left: 0, bottom: 12 }}>
            <CartesianGrid stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis dataKey={yKey} type="number" domain={[0, 1]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={tooltipContent} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            {Number.isFinite(xThreshold) && <ReferenceLine x={xThreshold} stroke="#71717a" strokeDasharray="4 4" />}
            {Number.isFinite(yThreshold) && (
              <ReferenceLine
                y={yThreshold}
                stroke="#71717a"
                strokeDasharray="4 4"
                label={
                  cutoffLines.length > 0
                    ? (props: { viewBox?: { x?: number; y?: number } }) => {
                        const x = Number(props.viewBox?.x ?? 0) + 8;
                        const y = Number(props.viewBox?.y ?? 0) - Math.max((cutoffLines.length - 1) * 6, 0);
                        return (
                          <text x={x} y={y} fill="#a1a1aa" fontSize={11} fontFamily="JetBrains Mono" textAnchor="start">
                            {cutoffLines.map((line, idx) => (
                              <tspan key={`${line}-${idx}`} x={x} dy={idx === 0 ? 0 : 12}>
                                {line}
                              </tspan>
                            ))}
                          </text>
                        );
                      }
                    : undefined
                }
              />
            )}
            <Scatter name="Predicted Risk" data={data} fill={color} />
          </ScatterChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function DualScatterCompareCard({
  data,
  xKey,
  predKey,
  actualKey,
  labelKey,
  idKey,
  predColor = "#facc15",
  actualColor = "#38bdf8",
  xThreshold = 50,
  yThreshold = 0.75,
}: {
  data: Row[];
  xKey: string;
  predKey: string;
  actualKey: string;
  labelKey: string;
  idKey: string;
  predColor?: string;
  actualColor?: string;
  xThreshold?: number;
  yThreshold?: number;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO SCATTER DATA" />;

  const predictedData = data.map((row) => ({
    ...row,
    __series: "Predicted Risk",
    __y: Number(row[predKey] ?? 0),
  }));
  const actualData = data.map((row) => ({
    ...row,
    __series: "Actual Risk (Count Rank)",
    __y: Number(row[actualKey] ?? 0),
  }));

  const tooltipContent = ({ active, payload }: { active?: boolean; payload?: Array<{ value?: unknown; name?: unknown; payload?: Row }> }) => {
    if (!active || !payload || payload.length === 0) return null;
    const point = payload[0]?.payload ?? {};
    const seriesName = String(payload[0]?.name ?? payload[0]?.payload?.["__series"] ?? "Risk");
    const communityArea = Number(point[idKey] ?? 0);
    const communityName = String(point[labelKey] ?? `Community ${communityArea}`);
    const hardship = Number(point[xKey] ?? 0);
    const pred = Number(point[predKey] ?? 0);
    const actual = Number(point[actualKey] ?? 0);
    const actualCount = Number(point["actual_count"] ?? 0);
    const month = String(point["pred_month"] ?? "");
    return (
      <div style={TOOLTIP_STYLE}>
        <div style={{ ...TOOLTIP_LABEL_STYLE, marginBottom: "4px" }}>{communityName}</div>
        <div>CA: {communityArea}</div>
        <div>Month: {month || "N/A"}</div>
        <div>Series: {seriesName}</div>
        <div>Hardship Index: {hardship.toFixed(2)}</div>
        <div>Predicted Risk: {(pred * 100).toFixed(1)}%</div>
        <div>Actual Risk (Rank): {(actual * 100).toFixed(1)}%</div>
        <div>Actual Count: {Number.isFinite(actualCount) ? actualCount.toFixed(0) : "N/A"}</div>
      </div>
    );
  };

  return (
    <div className="h-[560px] w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 16, right: 16, left: 0, bottom: 12 }}>
            <CartesianGrid stroke={GRID_STROKE} />
            <XAxis dataKey={xKey} type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis dataKey="__y" type="number" domain={[0, 1]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={tooltipContent} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            <ReferenceLine x={xThreshold} stroke="#71717a" strokeDasharray="4 4" />
            <ReferenceLine y={yThreshold} stroke="#71717a" strokeDasharray="4 4" />
            <Scatter name="Predicted Risk" data={predictedData} fill={predColor} />
            <Scatter name="Actual Risk (Count Rank)" data={actualData} fill={actualColor} />
          </ScatterChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

export function BridgeCard({
  data,
  labelKey,
  valueKey,
  positiveColor = "#facc15",
  negativeColor = "#ef4444",
}: {
  data: Row[];
  labelKey: string;
  valueKey: string;
  positiveColor?: string;
  negativeColor?: string;
}) {
  if (!hasRows(data)) return <ChartEmpty label="NO BRIDGE DATA" />;
  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis dataKey={labelKey} tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Bar dataKey={valueKey} radius={[0, 0, 0, 0]}>
              {data.map((r, i) => {
                const v = Number(r[valueKey] ?? 0);
                return <Cell key={i} fill={v >= 0 ? positiveColor : negativeColor} />;
              })}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </ChartFrame>
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
  if (!hasRows(data)) return <ChartEmpty label="NO PIE DATA" />;
  const palette = colors ?? ["#facc15", "#ef4444", "#f8fafc", "#52525b", "#27272a"];
  const total = data.reduce((sum, row) => sum + Number(row[valueKey] ?? 0), 0);

  const pieTooltipContent = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ name?: unknown; value?: unknown; payload?: Row }>;
  }) => {
    if (!active || !payload || payload.length === 0) return null;
    const item = payload[0];
    const row = item?.payload ?? {};
    const name = String(row[nameKey] ?? item?.name ?? "N/A");
    const value = Number(row[valueKey] ?? item?.value ?? 0);
    const pct = total > 0 ? (value / total) * 100 : 0;
    return (
      <div style={TOOLTIP_STYLE}>
        <div style={{ ...TOOLTIP_LABEL_STYLE, marginBottom: "4px" }}>{name.toUpperCase()}</div>
        <div style={{ color: "#f8fafc", fontSize: "12px" }}>{value.toLocaleString()}</div>
        <div style={{ color: "#a1a1aa", fontSize: "11px" }}>{pct.toFixed(1)}%</div>
      </div>
    );
  };

  return (
    <div className="h-80 w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Tooltip content={pieTooltipContent} />
            <Legend wrapperStyle={{ ...LEGEND_STYLE, fontSize: "10px" }} iconSize={10} iconType="circle" />
            <Pie data={data} dataKey={valueKey} nameKey={nameKey} cx="50%" cy="50%" outerRadius={108} label>
              {data.map((_, idx) => (
                <Cell key={`${nameKey}-${idx}`} fill={palette[idx % palette.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </ChartFrame>
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
  if (!hasRows(data)) return <ChartEmpty label="NO STACK DATA" />;
  return (
    <div className="h-[460px] w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 12, right: 20, left: 20, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <YAxis dataKey={yKey} type="category" tick={AXIS_TICK} axisLine={false} tickLine={false} width={170} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} stackId="stack" fill={s.color} name={s.name ?? s.key} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
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
  if (!hasRows(data)) return <ChartEmpty label="NO GROUPED DATA" />;
  return (
    <div className="h-[620px] w-full">
      <ChartFrame className="h-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 24, left: 0, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
            <XAxis
              dataKey={xKey}
              interval={0}
              angle={-30}
              textAnchor="end"
              height={90}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
            />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} />
            <Legend wrapperStyle={LEGEND_STYLE} />
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} fill={s.color} name={s.name ?? s.key} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </ChartFrame>
    </div>
  );
}

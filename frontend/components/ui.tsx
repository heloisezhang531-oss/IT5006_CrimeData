import { ReactNode } from "react";

export function PageHero({
  eyebrow,
  title,
  description,
  conclusion,
}: {
  eyebrow: string;
  title: string;
  description: string;
  conclusion?: string;
}) {
  return (
    <section className="mb-10 space-y-3">
      <p className="section-subtitle">{eyebrow}</p>
      <h1 className="section-title">{title}</h1>
      <p className="max-w-3xl text-base text-slate-600 md:text-lg">{description}</p>
      {conclusion ? (
        <p className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-medium text-sky-700">
          {conclusion}
        </p>
      ) : null}
    </section>
  );
}

export function GlassPanel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`glass p-6 ${className ?? ""}`}>{children}</div>;
}

export function InsightPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-slate-200 bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
      {label}
    </span>
  );
}

export function EvidencePanel({
  title,
  summary,
  children,
}: {
  title: string;
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="group rounded-2xl border border-slate-200/80 bg-white/70">
      <summary className="cursor-pointer list-none px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-800">{title}</p>
            <p className="text-xs text-slate-500">{summary}</p>
          </div>
          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-sky-700 group-open:hidden">
            Expand Evidence
          </span>
          <span className="hidden text-xs font-semibold uppercase tracking-[0.12em] text-sky-700 group-open:inline">
            Hide Evidence
          </span>
        </div>
      </summary>
      <div className="px-4 pb-4">{children}</div>
    </details>
  );
}

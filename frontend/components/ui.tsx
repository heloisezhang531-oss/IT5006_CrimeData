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
    <section className="glass-card mb-8 space-y-4 p-6 md:mb-10 md:p-8">
      <span className="inline-flex border border-machine-yellow/35 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-machine-yellow">
        {eyebrow}
      </span>
      <h1 className="section-title">{title}</h1>
      <p className="max-w-4xl text-sm text-zinc-400 md:text-base">{description}</p>
      {conclusion ? (
        <p className="inline-flex border border-machine-yellow/35 bg-machine-yellow/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-machine-yellow">
          {conclusion}
        </p>
      ) : null}
    </section>
  );
}

export function GlassPanel({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={`glass-card p-6 md:p-7 ${className ?? ""}`}>{children}</div>;
}

export function InsightPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center border border-machine-yellow/35 bg-machine-yellow/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-machine-yellow">
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
    <details className="group border border-machine-yellow/20 bg-void/55">
      <summary className="cursor-pointer list-none px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-system-white">{title}</p>
            <p className="text-xs text-zinc-500">{summary}</p>
          </div>
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-machine-yellow group-open:hidden">
            Expand Evidence
          </span>
          <span className="hidden text-[10px] font-semibold uppercase tracking-[0.16em] text-machine-yellow group-open:inline">
            Hide Evidence
          </span>
        </div>
      </summary>
      <div className="border-t border-machine-yellow/20 px-4 pb-4 pt-4">{children}</div>
    </details>
  );
}

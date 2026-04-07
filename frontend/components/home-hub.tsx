"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Crosshair, Eye } from "lucide-react";
import { KpiCounter } from "@/components/motion";

type KpiItem = {
  label: string;
  value: number;
  unit?: string;
  precision?: number;
};

type StoryItem = {
  chapter: string;
  title: string;
  description: string;
  href: string;
  image: string;
};

type ModuleCard = {
  title: string;
  href: string;
  desc: string;
};

const ACCESS_SESSION_KEY = "crime-intel-access-granted";

function PoiCorners() {
  return (
    <>
      <span className="poi-corner poi-tl" />
      <span className="poi-corner poi-tr" />
      <span className="poi-corner poi-bl" />
      <span className="poi-corner poi-br" />
    </>
  );
}

function AccessLanding({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="flex min-h-[calc(100vh-180px)] items-center justify-center p-2 md:p-8">
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="liquid-glass relative w-full max-w-4xl p-8 text-center md:p-12"
      >
        <PoiCorners />
        <div className="absolute left-4 top-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-machine-yellow/75">
          <Crosshair className="h-3 w-3" />
          <span>SYS.OP.01</span>
        </div>
        <div className="absolute right-4 top-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-zinc-500">
          <span>REC</span>
          <span className="h-2 w-2 animate-pulse bg-threat-red" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
        >
          <Eye className="mx-auto mb-6 h-16 w-16 text-machine-yellow/85" />
          <h1 className="text-3xl font-bold uppercase tracking-[0.16em] text-system-white md:text-6xl">
            Administrative
          </h1>
          <h2 className="mt-2 text-2xl font-bold uppercase tracking-[0.28em] text-machine-yellow md:text-5xl">
            Access
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9 }}
          className="mb-10 mt-8 space-y-2 text-xs uppercase tracking-[0.16em] text-zinc-500"
        >
          <p>
            <span className="text-machine-yellow">[</span> IDENTIFYING THREATS...
            <span className="text-machine-yellow">]</span>
          </p>
          <p>
            MACHINE STATUS: <span className="text-system-white">ONLINE</span>
          </p>
          <p>
            CONNECTION: <span className="text-system-white">SECURE</span>
          </p>
        </motion.div>

        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4 }}
          onClick={onEnter}
          className="group relative border border-machine-yellow px-8 py-4 text-xs font-bold uppercase tracking-[0.22em] text-machine-yellow transition hover:bg-machine-yellow hover:text-void"
        >
          <PoiCorners />
          <span className="relative z-10">Enter System <span className="blink-cursor">_</span></span>
        </motion.button>
      </motion.div>
    </div>
  );
}

export function HomeHub({
  kpis,
  healthStatus,
  dataSourceMode,
  storyline,
  cards,
}: {
  kpis: readonly KpiItem[];
  healthStatus: string;
  dataSourceMode: string;
  storyline: readonly StoryItem[];
  cards: readonly ModuleCard[];
}) {
  const [entered, setEntered] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const granted = window.sessionStorage.getItem(ACCESS_SESSION_KEY) === "1";
    setEntered(granted);
    setHydrated(true);
  }, []);

  const enterDashboard = () => {
    window.sessionStorage.setItem(ACCESS_SESSION_KEY, "1");
    setEntered(true);
  };

  if (!hydrated) {
    return <div className="chart-empty">INITIALIZING INTERFACE...</div>;
  }

  return (
    <AnimatePresence mode="wait">
      {!entered ? (
        <motion.div key="landing" exit={{ opacity: 0, scale: 1.04, filter: "blur(10px)" }} transition={{ duration: 0.45 }}>
          <AccessLanding onEnter={enterDashboard} />
        </motion.div>
      ) : (
        <motion.div
          key="dashboard"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
          className="space-y-8"
        >
          <section className="glass-strong home-hero-gold timeline-glow relative overflow-hidden p-6 md:p-10">
            <img
              src="/pics/top_secret.png"
              alt="Top secret crime tracking board"
              className="pointer-events-none absolute right-3 top-3 z-10 hidden w-52 rotate-[7deg] drop-shadow-[0_12px_26px_rgba(0,0,0,0.45)] md:block lg:w-64"
            />
            <span className="inline-flex border border-machine-yellow/35 bg-machine-yellow/10 px-3 py-1 text-[10px] uppercase tracking-[0.18em] text-machine-yellow">
              Launch Keynote Mode
            </span>
            <h1 className="story-headline mt-4 max-w-5xl">
              Predictive Public Safety: From Spatial Evidence to Actionable Next-Month Risk Decisions
            </h1>
            <p className="story-copy mt-4 max-w-4xl">
              We operationalize a community-month forecasting framework aligned with Phase1 EDA evidence and Phase2 model validation,
              emphasizing interpretable risk allocation instead of reactive policing.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {kpis.map((kpi) => (
                <div key={kpi.label} className="glass-card p-4">
                  <p className="kpi-label">{kpi.label}</p>
                  <p className="mt-2 text-3xl font-bold text-system-white">
                    <KpiCounter value={kpi.value} precision={kpi.precision ?? 0} suffix={kpi.unit ? ` ${kpi.unit}` : ""} />
                  </p>
                </div>
              ))}
            </div>
            <p className="mt-5 text-[11px] font-normal uppercase tracking-[0.1em] text-white/60">
              Backend: <span className="font-normal text-black/85">{healthStatus}</span> | Data source mode:{" "}
              <span className="font-normal text-machine-yellow">{dataSourceMode}</span>
            </p>
          </section>

          <section className="glass-card space-y-4 p-6">
            <p className="story-subtitle">Report Storyline Handoff</p>
            <h2 className="text-2xl font-bold uppercase tracking-[0.08em] text-system-white md:text-3xl">
              EDA and Modeling Story Has Been Split Into Functional Pages
            </h2>
            <div className="grid gap-4 lg:grid-cols-3">
              {storyline.map((item) => (
                <Link key={item.href} href={item.href} className="glass-card p-4 transition hover:-translate-y-1">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-machine-yellow">{item.chapter}</p>
                  <h3 className="mt-2 text-base font-bold uppercase tracking-[0.08em] text-system-white">{item.title}</h3>
                  <p className="mt-2 text-xs text-zinc-400">{item.description}</p>
                  <img src={item.image} alt={item.title} className="mt-3 h-36 w-full border border-machine-yellow/25 object-cover" />
                </Link>
              ))}
            </div>
          </section>

          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <Link key={card.href} href={card.href} className="glass-card group p-5 transition hover:-translate-y-1">
                <h3 className="text-base font-bold uppercase tracking-[0.08em] text-system-white">{card.title}</h3>
                <p className="mt-2 text-xs text-zinc-400">{card.desc}</p>
                <span className="mt-4 inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-machine-yellow">
                  Open Module <ChevronRight className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
                </span>
              </Link>
            ))}
          </section>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

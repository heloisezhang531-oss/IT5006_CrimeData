"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";

export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 22 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function StorySectionShell({
  id,
  children,
  className,
}: {
  id: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section id={id} className={`scroll-mt-28 py-14 md:py-20 ${className ?? ""}`}>
      {children}
    </section>
  );
}

export function KpiCounter({
  value,
  suffix = "",
  precision = 0,
}: {
  value: number;
  suffix?: string;
  precision?: number;
}) {
  const [display, setDisplay] = useState(0);
  const safeTarget = Number.isFinite(value) ? value : 0;
  const duration = 1200;

  useEffect(() => {
    let raf = 0;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setDisplay(safeTarget * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [safeTarget]);

  const text = useMemo(() => display.toFixed(precision), [display, precision]);
  return <span>{text}{suffix}</span>;
}

export function FloatingBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <motion.div
        aria-hidden
        className="absolute -left-16 top-24 h-56 w-56 rounded-full bg-sky-300/30 blur-3xl"
        animate={{ y: [0, -18, 0], x: [0, 8, 0] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="absolute right-0 top-8 h-72 w-72 rounded-full bg-blue-300/25 blur-3xl"
        animate={{ y: [0, 16, 0], x: [0, -12, 0] }}
        transition={{ duration: 11, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="absolute bottom-12 left-1/3 h-52 w-52 rounded-full bg-emerald-300/20 blur-3xl"
        animate={{ y: [0, -14, 0], x: [0, -6, 0] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

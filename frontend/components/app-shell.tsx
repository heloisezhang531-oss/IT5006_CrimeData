"use client";

import Link from "next/link";
import { useMemo, useState, type ComponentType } from "react";
import { usePathname } from "next/navigation";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Eye,
  LayoutDashboard,
  Map as MapIcon,
  Menu,
  Search,
  Shield,
  Terminal,
  X,
} from "lucide-react";

type NavItem = {
  id: string;
  label: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
  description: string;
};

const NAV_ITEMS: NavItem[] = [
  {
    id: "home",
    label: "Home",
    href: "/",
    icon: Eye,
    description: "Landing and module overview",
  },
  {
    id: "strategic",
    label: "Strategic",
    href: "/strategic",
    icon: LayoutDashboard,
    description: "Long-term planning and trend evidence",
  },
  {
    id: "operations",
    label: "Operations",
    href: "/operations",
    icon: Shield,
    description: "Map-based distribution and patrol windows",
  },
  {
    id: "crime-action",
    label: "Crime Action",
    href: "/crime-action",
    icon: MapIcon,
    description: "Category and location intersection analysis",
  },
  {
    id: "anomaly",
    label: "Anomaly",
    href: "/anomaly",
    icon: AlertTriangle,
    description: "Early warning and observed/predicted drift",
  },
  {
    id: "socioeconomic",
    label: "Socioeconomic",
    href: "/socioeconomic",
    icon: Activity,
    description: "Hardship-linked public safety context",
  },
  {
    id: "performance",
    label: "Performance",
    href: "/performance",
    icon: BarChart3,
    description: "Model quality and reliability slices",
  },
  {
    id: "command-center",
    label: "Command Center",
    href: "/command-center",
    icon: Terminal,
    description: "Unified operational intelligence board",
  },
];

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

function DataStreamBackdrop() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden opacity-60">
      {Array.from({ length: 24 }).map((_, idx) => (
        <div
          key={idx}
          className="code-stream absolute top-0"
          style={{
            left: `${(idx * 100) / 24}%`,
            animationDuration: `${10 + ((idx * 7) % 8)}s`,
            animationDelay: `-${idx * 1.3}s`,
          }}
        >
          {Array.from({ length: 28 })
            .map((__, i) => ((i + idx) % 3 === 0 ? "1" : "0"))
            .join("")}
        </div>
      ))}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_10%,rgba(5,5,5,0.92)_100%)]" />
    </div>
  );
}

function normalizePath(pathname: string | null): string {
  if (!pathname) return "/";
  if (pathname === "/") return "/";
  return pathname.replace(/\/+$/, "");
}

function isItemActive(itemHref: string, pathname: string): boolean {
  if (itemHref === "/") return pathname === "/";
  return pathname === itemHref || pathname.startsWith(`${itemHref}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = normalizePath(usePathname());
  const [mobileOpen, setMobileOpen] = useState(false);

  const current = useMemo(
    () => NAV_ITEMS.find((item) => isItemActive(item.href, pathname)) ?? NAV_ITEMS[0],
    [pathname],
  );

  return (
    <div className="relative h-screen w-full overflow-hidden bg-void text-system-white">
      <DataStreamBackdrop />

      <div className="relative z-10 flex h-full w-full">
        <aside
          className={`machine-sidebar custom-scrollbar ${mobileOpen ? "translate-x-0" : "-translate-x-full"} fixed inset-y-0 left-0 z-40 w-72 lg:translate-x-0 lg:static lg:w-72`}
        >
          <div className="border-b border-machine-yellow/20 px-5 py-5">
            <Link href="/" className="relative flex items-center gap-3 border border-machine-yellow/30 px-3 py-3">
              <PoiCorners />
              <span className="relative z-10 flex h-8 w-8 items-center justify-center bg-machine-yellow text-void">
                <Eye className="h-5 w-5" />
              </span>
              <span className="relative z-10 text-sm font-bold uppercase tracking-[0.24em] text-system-white">
                Crime Intelligence
              </span>
            </Link>
          </div>

          <div className="border-b border-machine-yellow/20 px-5 py-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-machine-yellow/80">[ Modules ]</p>
          </div>

          <nav className="flex-1 overflow-y-auto px-3 py-4">
            {NAV_ITEMS.map((item) => {
              const active = isItemActive(item.href, pathname);
              const Icon = item.icon;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                  className={`nav-item ${active ? "nav-item-active" : "nav-item-inactive"}`}
                  title={item.description}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <div className="border-t border-machine-yellow/20 px-5 py-4">
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">SYS: ONLINE</div>
            <div className="mt-2 text-xs text-zinc-400">{current.description}</div>
          </div>
        </aside>

        {mobileOpen ? (
          <button
            aria-label="Close navigation"
            className="fixed inset-0 z-30 bg-black/60 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        ) : null}

        <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
          <header className="machine-header">
            <div className="flex items-center gap-3">
              <button
                aria-label="Open navigation"
                className="inline-flex h-9 w-9 items-center justify-center border border-machine-yellow/40 text-machine-yellow lg:hidden"
                onClick={() => setMobileOpen(true)}
              >
                <Menu className="h-4 w-4" />
              </button>
              <div>
                <p className="text-[10px] uppercase tracking-[0.24em] text-machine-yellow/80">Module</p>
                <h1 className="text-sm font-bold uppercase tracking-[0.2em] text-system-white md:text-base">
                  {current.label}
                </h1>
              </div>
            </div>

            <div className="hidden items-center gap-3 md:flex">
              <label className="relative block w-64">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />
                <input
                  type="text"
                  placeholder="SEARCH RECORDS..."
                  className="w-full border border-machine-yellow/30 bg-void/80 py-2 pl-9 pr-3 text-xs uppercase tracking-[0.1em] text-system-white outline-none transition focus:border-machine-yellow"
                />
              </label>
              <button className="inline-flex h-9 w-9 items-center justify-center border border-machine-yellow/30 text-machine-yellow">
                <Terminal className="h-4 w-4" />
              </button>
            </div>

            <button
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              className="inline-flex h-9 w-9 items-center justify-center border border-machine-yellow/30 text-machine-yellow md:hidden"
              onClick={() => setMobileOpen((open) => !open)}
            >
              {mobileOpen ? <X className="h-4 w-4" /> : <Terminal className="h-4 w-4" />}
            </button>
          </header>

          <main className="machine-content custom-scrollbar">
            <div className="flex min-h-full flex-col">
              <div className="flex-1">{children}</div>
              <footer className="machine-footer mt-6">
                <div className="flex items-center gap-3">
                  <span>© 2026 CRIME INTEL</span>
                  <span className="h-3 w-px bg-machine-yellow/30" />
                  <span>LAT 41.8781 N | LNG 87.6298 W</span>
                </div>
                <div className="flex items-center gap-3 text-machine-yellow">
                  <span className="h-1.5 w-1.5 bg-machine-yellow" />
                  <span>PIPELINE LIVE</span>
                </div>
              </footer>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

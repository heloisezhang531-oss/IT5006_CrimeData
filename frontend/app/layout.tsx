import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Crime Intelligence Platform",
  description: "FastAPI + React crime intelligence dashboard",
};

const nav = [
  ["Launch", "/launch"],
  ["Strategic", "/strategic"],
  ["Operations", "/operations"],
  ["Crime Action", "/crime-action"],
  ["Raw Data", "/raw-data"],
  ["Victim Risk", "/victim-risk"],
  ["Anomaly", "/anomaly"],
  ["Socioeconomic", "/socioeconomic"],
  ["Performance", "/performance"],
  ["Command Center", "/command-center"],
  ["Model Lab", "/model-lab"],
] as const;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-40 border-b border-white/40 bg-white/65 backdrop-blur-xl">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-lg font-semibold tracking-tight text-slate-900">
              Crime Intelligence
            </Link>
            <nav className="hidden gap-5 text-sm text-slate-700 lg:flex">
              {nav.map(([label, href]) => (
                <Link key={href} href={href} className="transition hover:text-sky-700">
                  {label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-10 md:px-8">{children}</main>
      </body>
    </html>
  );
}

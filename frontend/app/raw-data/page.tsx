"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet } from "@/lib/api";
import { EvidencePanel, GlassPanel, PageHero } from "@/components/ui";

const PAGE_SIZE = 25;

export default function RawDataPage() {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const payload = await apiGet<Record<string, unknown>>("/eda/raw/recent?limit=1000", {
          clientTtlMs: 5000,
          forceRefresh: reloadToken > 0,
        });
        if (cancelled) return;
        if (payload.meta?.error) {
          setRows([]);
          setError(`Failed to load raw data: ${String(payload.meta.error)}`);
        } else {
          setRows(payload.data ?? []);
          if (!payload.data?.length) {
            setError("Raw data endpoint returned no rows.");
          }
        }
      } catch {
        if (cancelled) return;
        setRows([]);
        setError("Failed to load raw rows. Please check backend availability and try again.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((row) =>
      Object.values(row).some((value) => String(value ?? "").toLowerCase().includes(needle)),
    );
  }, [rows, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageRows = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const cols = pageRows[0] ? Object.keys(pageRows[0]).slice(0, 12) : [];
  const from = filtered.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1;
  const to = filtered.length === 0 ? 0 : Math.min(safePage * PAGE_SIZE, filtered.length);

  return (
    <div className="space-y-8">
      <PageHero
        eyebrow="Raw Data"
        title="Raw Data Sample (2015-2024)"
        description="Streamlit parity raw-data module. Shows the latest 1,000 rows with quick search and paging for audit and drill-down."
        conclusion="Raw-data signal: preserve row-level traceability for every narrative chart."
      />

      <GlassPanel>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-slate-500">Rows loaded</p>
            <p className="text-2xl font-semibold text-slate-900">{rows.length.toLocaleString()}</p>
          </div>
          <div className="flex w-full max-w-2xl flex-wrap items-center gap-2">
            <input
              className="min-w-[240px] flex-1 rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm"
              placeholder="Search any field..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
            />
            <button
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={() => setReloadToken((v) => v + 1)}
            >
              Reload
            </button>
          </div>
        </div>
        {error ? <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">{error}</p> : null}
      </GlassPanel>

      <GlassPanel>
        {loading && rows.length === 0 ? (
          <p className="text-sm text-slate-500">Loading raw rows...</p>
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600">
            No rows match the current query. Try clearing the search keyword or reloading data.
          </div>
        ) : (
          <div className="space-y-3">
            {loading ? <p className="text-xs text-slate-500">Refreshing rows...</p> : null}
            <div className="overflow-auto rounded-2xl border border-slate-200 bg-white/80">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-slate-100 text-slate-600">
                  <tr>
                    {cols.map((c) => (
                      <th key={c} className="px-3 py-2 font-semibold">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pageRows.map((row, idx) => (
                    <tr key={idx} className="border-t border-slate-200">
                      {cols.map((c) => (
                        <td key={c} className="max-w-[220px] truncate px-3 py-2 text-slate-700">
                          {String(row[c] ?? "-")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between text-sm text-slate-600">
              <p>
                Showing {from}-{to} of {filtered.length}
              </p>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-40"
                  disabled={safePage <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Prev
                </button>
                <span>
                  {safePage}/{totalPages}
                </span>
                <button
                  className="rounded-lg border border-slate-300 px-3 py-1 disabled:opacity-40"
                  disabled={safePage >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        )}
      </GlassPanel>

      <EvidencePanel
        title="Raw Data Notes"
        summary="Data is sourced from /api/eda/raw/recent with fallback-safe synthetic rows when TiDB is unavailable."
      >
        <p className="text-sm text-slate-600">
          Columns are capped in-table for readability. Full row payload remains available via backend endpoint.
        </p>
      </EvidencePanel>
    </div>
  );
}

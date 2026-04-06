export function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) {
    return (
      <p className="border border-machine-yellow/20 bg-void/55 px-4 py-3 text-xs uppercase tracking-[0.14em] text-zinc-500">
        No data returned from backend.
      </p>
    );
  }
  const cols = Object.keys(rows[0]).slice(0, 6);
  return (
    <div className="overflow-auto border border-machine-yellow/20 bg-void/55">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-machine-yellow/10 text-zinc-400">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-4 py-2 font-semibold uppercase tracking-[0.12em]">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 12).map((r, i) => (
            <tr key={i} className="border-t border-machine-yellow/15 text-zinc-300">
              {cols.map((c) => (
                <td key={c} className="px-4 py-2">
                  {String(r[c] ?? "-")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

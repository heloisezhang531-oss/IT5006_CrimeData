export function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">No data available.</p>;
  }
  const cols = Object.keys(rows[0]).slice(0, 6);
  return (
    <div className="overflow-auto rounded-2xl border border-slate-200 bg-white/70">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-slate-100/80 text-slate-600">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-4 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 12).map((r, i) => (
            <tr key={i} className="border-t border-slate-200/70 text-slate-700">
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

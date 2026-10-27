import React from "react";

export const inputCls =
  "w-full bg-paper-card border border-edge-light rounded-xl px-3 py-2.5 text-sm text-ink outline-none focus:border-brand transition-colors disabled:opacity-60";

export function Field({ label, children, className = "" }) {
  return (
    <label className={`block ${className}`}>
      <span className="text-[11px] font-semibold text-ink-2 uppercase tracking-widest block mb-1.5">{label}</span>
      {children}
    </label>
  );
}

export function Select({ value, onChange, options, placeholder, disabled, testid }) {
  return (
    <select data-testid={testid} disabled={disabled} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      {placeholder !== undefined && <option value="">{placeholder}</option>}
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

export function Btn({ children, variant = "primary", className = "", ...rest }) {
  const base = "px-4 py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-[0.98] disabled:opacity-50 ";
  const v = variant === "primary"
    ? "bg-brand hover:bg-brand-hover text-paper shadow-clay"
    : "border border-edge-light bg-paper-card text-ink-2 hover:text-ink hover:bg-paper-sidebar";
  return <button {...rest} className={base + v + " " + className}>{children}</button>;
}

/** columns: [{key, label, render?}] */
export function DataTable({ columns, rows, empty = "No rows match these parameters.", testid }) {
  if (!rows.length) return <div className="text-sm text-ink-3 py-6 text-center" data-testid={testid && `${testid}-empty`}>{empty}</div>;
  return (
    <div className="overflow-x-auto" data-testid={testid}>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-widest text-ink-3 border-b border-edge-light">
            {columns.map((c) => <th key={c.key} className="py-2 pr-4 font-semibold whitespace-nowrap">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-edge-light/60 hover:bg-paper-sidebar/60">
              {columns.map((c) => (
                <td key={c.key} className="py-2 pr-4 text-ink">{c.render ? c.render(r) : (r[c.key] ?? "—")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function downloadCsv(filename, columns, rows) {
  const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const csv = [columns.map((c) => esc(c.label)).join(",")]
    .concat(rows.map((r) => columns.map((c) => esc(r[c.key])).join(",")))
    .join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const errMsg = (e, fallback = "Something went wrong") => {
  const d = e?.response?.data?.detail;
  return typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join(", ") : fallback;
};

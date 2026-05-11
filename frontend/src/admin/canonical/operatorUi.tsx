import { ReactNode } from "react";

import type { TimeRangePreset } from "./operatorFilters.tsx";

export type HealthTone = "ok" | "warn" | "bad";

export function toneChipCls(tone: HealthTone): string {
  if (tone === "ok") return "border-emerald-200 bg-emerald-50 text-emerald-950";
  if (tone === "warn") return "border-amber-200 bg-amber-50 text-amber-950";
  return "border-red-200 bg-red-50 text-red-950";
}

export function pillLabel(tone: HealthTone): string {
  if (tone === "ok") return "PASS";
  if (tone === "warn") return "WARN";
  return "FAIL";
}

export function OperatorDrawer({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <>
      <button
        type="button"
        className="fixed inset-0 z-40 cursor-default bg-black/35"
        aria-label="Close panel"
        onClick={onClose}
      />
      <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col border-l border-stone-200 bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-3 border-b border-stone-100 px-5 py-4">
          <h3 className="text-base font-semibold text-stone-900">{title}</h3>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-sm text-stone-600 hover:bg-stone-100"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </aside>
    </>
  );
}

export function AccordionSection({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <details className="rounded-xl border border-stone-200 bg-white shadow-sm open:ring-1 open:ring-stone-100">
      <summary className="cursor-pointer list-none px-5 py-4 [&::-webkit-details-marker]:hidden">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-stone-900">{title}</p>
            {subtitle ? <p className="mt-0.5 text-xs text-stone-600">{subtitle}</p> : null}
          </div>
          <span className="text-xs font-medium text-indigo-700">Toggle</span>
        </div>
      </summary>
      <div className="border-t border-stone-100 px-5 py-4">{children}</div>
    </details>
  );
}

export function CanonicalFilterToolbar({
  filters,
  onChange,
}: {
  filters: import("./operatorFilters").CanonicalOperatorFilters;
  onChange: (patch: Partial<import("./operatorFilters").CanonicalOperatorFilters>) => void;
}) {
  const selCls =
    "rounded-md border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-900 shadow-sm";
  const inpCls = "rounded-md border border-stone-200 bg-white px-2 py-1.5 text-xs text-stone-900 shadow-sm";
  return (
    <div className="flex flex-wrap items-end gap-3 rounded-xl border border-stone-200 bg-stone-50/80 p-4">
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Connector
        <input
          className={inpCls}
          placeholder="any"
          value={filters.connector}
          onChange={(e) => onChange({ connector: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Bundle
        <input
          className={inpCls}
          placeholder="any"
          value={filters.bundle}
          onChange={(e) => onChange({ bundle: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Object kind
        <input
          className={inpCls}
          placeholder="any"
          value={filters.objectKind}
          onChange={(e) => onChange({ objectKind: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Status
        <input
          className={inpCls}
          placeholder="any"
          value={filters.status}
          onChange={(e) => onChange({ status: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Confidence class
        <input
          className={inpCls}
          placeholder="any"
          value={filters.confidenceClass}
          onChange={(e) => onChange({ confidenceClass: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Replay class (receipt)
        <input
          className={inpCls}
          placeholder="C0–C5"
          value={filters.replayClass}
          onChange={(e) => onChange({ replayClass: e.target.value })}
        />
      </label>
      <label className="flex flex-col gap-1 text-[11px] font-medium uppercase tracking-wide text-stone-500">
        Time range
        <select
          className={selCls}
          value={filters.timeRange}
          onChange={(e) => onChange({ timeRange: e.target.value as TimeRangePreset })}
        >
          <option value="all">All loaded</option>
          <option value="1h">1h</option>
          <option value="24h">24h</option>
          <option value="7d">7d</option>
        </select>
      </label>
      <button
        type="button"
        className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-50"
        onClick={() =>
          onChange({
            connector: "",
            bundle: "",
            objectKind: "",
            status: "",
            confidenceClass: "",
            replayClass: "",
            timeRange: "all",
          })
        }
      >
        Reset filters
      </button>
    </div>
  );
}

export function CompactTable({
  columns,
  rows,
  empty,
}: {
  columns: { key: string; label: string; className?: string }[];
  rows: Record<string, ReactNode>[];
  empty?: ReactNode;
}) {
  if (rows.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-stone-200 bg-stone-50 px-4 py-6 text-center text-sm text-stone-600">
        {empty ?? "No rows match filters."}
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-stone-200">
      <table className="min-w-full text-left text-xs">
        <thead className="bg-stone-50 text-stone-700">
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={`whitespace-nowrap px-3 py-2 font-semibold ${c.className ?? ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-stone-100">
              {columns.map((c) => (
                <td key={c.key} className={`max-w-[22rem] truncate px-3 py-2 align-top ${c.className ?? ""}`}>
                  {row[c.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { titleConnector } from "../cortexAdminTypes";
import type { CanonCoverage, CanonCoverageConnector } from "../cortexAdminTypes";
import { SectionSkeleton } from "./SectionSkeleton";

function gapBadge(gap: string | null | undefined) {
  if (!gap) return null;
  const styles: Record<string, string> = {
    unmaterialized: "bg-amber-100 text-amber-900",
    no_raw: "bg-stone-100 text-stone-600",
    unknown_type: "bg-red-100 text-red-800",
    deferred: "bg-sky-100 text-sky-900",
    skipped: "bg-stone-100 text-stone-500",
  };
  return (
    <span
      className={`ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${styles[gap] ?? "bg-stone-100"}`}
    >
      {gap.replace("_", " ")}
    </span>
  );
}

function ConnectorBlock({ row }: { row: CanonCoverageConnector }) {
  const [open, setOpen] = useState(false);
  const types = row.resource_types ?? [];
  const withGap = types.filter((t) => t.gap === "unmaterialized" || t.gap === "unknown_type");

  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50/50">
      <button
        type="button"
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3 text-left hover:bg-stone-100/80"
        onClick={() => setOpen(!open)}
      >
        <span className="text-xs text-indigo-700">{open ? "▼" : "▶"}</span>
        <span className="font-medium text-stone-900">{titleConnector(row.connector)}</span>
        <span className="text-xs text-stone-600">
          {row.raw_row_count.toLocaleString()} raw · {row.canon_entity_count.toLocaleString()}{" "}
          canon entities
        </span>
        {row.unmaterialized_raw_rows > 0 ? (
          <span className="text-xs font-medium text-amber-800">
            {row.unmaterialized_raw_rows.toLocaleString()} unmaterialized
          </span>
        ) : null}
        {withGap.length > 0 ? (
          <span className="text-xs text-stone-500">
            {withGap.length} type(s) with gaps
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="border-t border-stone-200 bg-white px-4 py-3">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="py-1 pr-3 font-medium">Resource type</th>
                <th className="py-1 pr-3 font-medium">Disposition</th>
                <th className="py-1 pr-3 font-medium">Canon entity type</th>
                <th className="py-1 pr-3 font-medium text-right">Raw rows</th>
                <th className="py-1 pr-3 font-medium text-right">Canon entities</th>
                <th className="py-1 font-medium">Gap</th>
              </tr>
            </thead>
            <tbody>
              {types.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-2 text-stone-500">
                    No resource types in registry for this connector yet.
                  </td>
                </tr>
              ) : (
                types.map((t) => (
                  <tr key={t.resource_type} className="border-b border-stone-50">
                    <td className="py-1.5 pr-3 font-mono text-stone-800">{t.resource_type}</td>
                    <td className="py-1.5 pr-3 text-stone-600">{t.disposition}</td>
                    <td className="py-1.5 pr-3 text-stone-600">{t.entity_type ?? "—"}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{t.raw_row_count}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">{t.canon_entity_count}</td>
                    <td className="py-1.5">{gapBadge(t.gap)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

export function CanonConnectorsCoverageTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const coverageQ = useQuery({
    queryKey: ["admin-cortex-canon-coverage", tenantId],
    queryFn: () => adminJson<CanonCoverage>(`/admin/tenants/${tenantId}/cortex/canon/coverage`),
    enabled: Boolean(tenantId),
  });

  if (coverageQ.isPending) {
    return <SectionSkeleton variant="table" />;
  }
  if (coverageQ.isError) {
    return <p className="text-sm text-red-700">{(coverageQ.error as Error).message}</p>;
  }

  const data = coverageQ.data;
  if (!data) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Canonization per connector</h2>
      <p className="mt-1 text-sm text-stone-600">
        Compare raw ingestion rows to materialized canon entities by resource type.{" "}
        <span className="text-amber-800">Unmaterialized</span> means raw exists but no canon
        entity yet (mapper backlog or pending pass).
      </p>
      <div className="mt-4 space-y-3">
        {data.connectors.map((c) => (
          <ConnectorBlock key={c.connector} row={c} />
        ))}
      </div>
    </section>
  );
}

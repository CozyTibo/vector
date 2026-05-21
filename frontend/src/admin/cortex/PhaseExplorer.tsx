import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { OperatorPhase } from "./pipelineTypes";

export type PhaseExplorerPayload = {
  columns: string[];
  items: Array<Record<string, unknown>>;
  truncated: boolean;
  total: number;
  limit: number;
  offset: number;
};

type Props = {
  phase: OperatorPhase;
  connector?: string;
  resourceType?: string;
  searchQuery?: string;
};

function cellValue(row: Record<string, unknown>, col: string): string {
  const v = row[col];
  if (v == null) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

export function PhaseExplorer({ phase, connector, resourceType, searchQuery }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [offset, setOffset] = useState(0);
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const limit = 50;

  const explorerQ = useQuery({
    queryKey: [
      "admin-cortex-phase-explorer",
      tenantId,
      phase,
      offset,
      connector,
      resourceType,
      searchQuery,
    ],
    queryFn: () => {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (connector) params.set("connector", connector);
      if (resourceType?.trim()) params.set("resource_type", resourceType.trim());
      if (searchQuery?.trim()) params.set("search_query", searchQuery.trim());
      return adminJson<PhaseExplorerPayload>(
        `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/explorer?${params}`,
      );
    },
    enabled: Boolean(tenantId),
  });

  const data = explorerQ.data;
  const columns = data?.columns ?? [];

  return (
    <section className="space-y-3 rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Explorer</h2>
      {explorerQ.isPending ? <p className="text-sm text-stone-500">Loading rows…</p> : null}
      {explorerQ.isError ? (
        <p className="text-sm text-red-700">{(explorerQ.error as Error).message}</p>
      ) : null}
      {data ? (
        <>
          <p className="text-xs text-stone-500">
            Showing {data.items.length} of {data.total.toLocaleString()} rows
          </p>
          <div className="overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-1 w-14" />
                  {columns.map((col) => (
                    <th key={col} className="px-2 py-1">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.items.map((row, idx) => {
                  const rowKey = String(
                    row.job_id ?? row.entity_id ?? row.materialization_id ?? row.raw_record_id ?? row.link_id ?? row.artifact_id ?? idx,
                  );
                  const expanded = expandedKey === rowKey;
                  const detailPath =
                    typeof row.detail_path === "string" ? row.detail_path : null;
                  return (
                    <Fragment key={rowKey}>
                      <tr className="border-t border-stone-100">
                        <td className="px-2 py-1 align-top">
                          <button
                            type="button"
                            className="rounded border border-stone-300 px-1.5 py-0.5 text-[10px]"
                            onClick={() => setExpandedKey(expanded ? null : rowKey)}
                          >
                            {expanded ? "hide" : "show"}
                          </button>
                        </td>
                        {columns.map((col) => (
                          <td key={col} className="px-2 py-1 align-top">
                            {col === "job_id" && detailPath ? (
                              <Link className="font-mono text-indigo-700 underline" to={detailPath}>
                                {cellValue(row, col).slice(0, 12)}…
                              </Link>
                            ) : (
                              cellValue(row, col)
                            )}
                          </td>
                        ))}
                      </tr>
                      {expanded ? (
                        <tr className="border-t border-stone-100 bg-stone-50/80">
                          <td colSpan={columns.length + 1} className="px-2 py-2">
                            <pre className="max-h-96 overflow-auto rounded border border-stone-200 bg-white p-2 text-[10px]">
                              {JSON.stringify(row.evidence ?? row.evidence_detail ?? row, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
              disabled={offset === 0}
              onClick={() => setOffset((o) => Math.max(0, o - limit))}
            >
              Previous
            </button>
            <button
              type="button"
              className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
              disabled={!data.truncated}
              onClick={() => setOffset((o) => o + limit)}
            >
              Next
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

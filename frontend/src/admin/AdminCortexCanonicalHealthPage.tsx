import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { formatRelativeAge, titleConnector } from "./cortexAdminTypes";
import type { ConnectorRollup } from "./canonical/coverageMatrixTypes";
import { StatusBadge } from "./ui/StatusBadge.tsx";

type CanonicalSummary = PhaseSummaryPayload & {
  health?: {
    materialization_row_count?: number;
    active_canonical_failure_count?: number;
    last_verification_passed?: boolean | null;
    verification_freshness_label?: string;
  };
  forward_progress?: { untreated_estimate?: number; metrics?: Record<string, unknown> };
  connector_rollups?: ConnectorRollup[];
  failure_count?: number;
};

function CanonicalSummaryBody({ summary }: { summary: CanonicalSummary }) {
  const h = summary.health ?? {};
  const untreated = Number(summary.forward_progress?.untreated_estimate ?? summary.backlog_count ?? 0);
  const failures = Number(h.active_canonical_failure_count ?? summary.failure_count ?? 0);

  return (
    <>
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase text-stone-500">Materialized rows</p>
          <p className="mt-1 text-lg font-semibold">{Number(h.materialization_row_count ?? 0).toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
          <p className="text-xs uppercase text-amber-800">Untreated backlog</p>
          <p className="mt-1 text-lg font-semibold text-amber-950">{untreated.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-red-100 bg-red-50 p-4 shadow-sm">
          <p className="text-xs uppercase text-red-800">Active failures</p>
          <p className="mt-1 text-lg font-semibold text-red-950">{failures.toLocaleString()}</p>
        </div>
        <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs uppercase text-stone-500">Verification</p>
          <p className="mt-1 text-sm font-medium">
            {h.last_verification_passed === false ? "Failed" : h.last_verification_passed ? "Passed" : "—"}
            {h.verification_freshness_label ? ` (${h.verification_freshness_label})` : ""}
          </p>
        </div>
      </section>

      {(summary.connector_rollups ?? []).length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-stone-900">Per-connector coverage</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead className="bg-stone-50 text-left text-stone-700">
                <tr>
                  <th className="px-2 py-2">Connector</th>
                  <th className="px-2 py-2">Raw</th>
                  <th className="px-2 py-2">Canonical</th>
                  <th className="px-2 py-2">Untreated</th>
                  <th className="px-2 py-2">Last materialized</th>
                  <th className="px-2 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {(summary.connector_rollups ?? []).map((r) => {
                  const bad = r.replayFailures > 0 || r.hasDeadRoute;
                  const warn = !bad && (r.untreatedRoutable > 0 || r.hasDormant);
                  const tone = bad ? "bad" : warn ? "warn" : "ok";
                  return (
                    <tr key={r.connector} className="border-t border-stone-100">
                      <td className="px-2 py-2 font-medium">{titleConnector(r.connector)}</td>
                      <td className="px-2 py-2 tabular-nums">{r.rawRows.toLocaleString()}</td>
                      <td className="px-2 py-2 tabular-nums">{r.canonicalRows.toLocaleString()}</td>
                      <td className="px-2 py-2 tabular-nums">{r.untreatedRoutable.toLocaleString()}</td>
                      <td className="px-2 py-2 text-xs">
                        {r.lastMaterialized ? formatRelativeAge(r.lastMaterialized) : "—"}
                      </td>
                      <td className="px-2 py-2">
                        <StatusBadge tone={tone === "bad" ? "bad" : tone === "warn" ? "warn" : "ok"}>
                          {bad ? "action" : warn ? "watch" : "ok"}
                        </StatusBadge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}
    </>
  );
}

function CanonicalExplorer() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [offset, setOffset] = useState(0);

  const explorerQ = useQuery({
    queryKey: ["admin-cortex-phase-explorer", tenantId, "canonical", offset],
    queryFn: () =>
      adminJson<{
        items: Array<{
          canonical_type: string;
          source: string;
          entity: string;
          updated_at: string;
          status: string;
          evidence: Record<string, unknown>;
        }>;
        truncated: boolean;
      }>(`/admin/tenants/${tenantId}/cortex/pipeline/phases/canonical/explorer?limit=50&offset=${offset}`),
    enabled: Boolean(tenantId),
  });

  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-base font-semibold text-stone-900">Canonical explorer</h2>
      <div className="mt-3 overflow-x-auto rounded border border-stone-200">
        <table className="min-w-full text-xs">
          <thead className="bg-stone-50 text-left">
            <tr>
              <th className="px-2 py-1 w-16" />
              <th className="px-2 py-1">canonical_type</th>
              <th className="px-2 py-1">source</th>
              <th className="px-2 py-1">entity</th>
              <th className="px-2 py-1">updated_at</th>
              <th className="px-2 py-1">status</th>
            </tr>
          </thead>
          <tbody>
            {(explorerQ.data?.items ?? []).map((row) => {
              const id = String(row.entity ?? row.source);
              const open = expanded === id;
              return (
                <tr key={id} className="border-t border-stone-100">
                  <td className="px-2 py-1">
                    <button
                      type="button"
                      className="rounded border border-stone-300 px-1.5 py-0.5 text-[10px]"
                      onClick={() => setExpanded(open ? null : id)}
                    >
                      {open ? "hide" : "show"}
                    </button>
                  </td>
                  <td className="px-2 py-1 font-mono">{row.canonical_type}</td>
                  <td className="px-2 py-1 font-mono">{row.source}</td>
                  <td className="px-2 py-1 font-mono">{row.entity}</td>
                  <td className="px-2 py-1">{row.updated_at ? new Date(row.updated_at).toLocaleString() : "—"}</td>
                  <td className="px-2 py-1">{row.status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {expanded ? (
        <pre className="mt-3 max-h-96 overflow-auto rounded border border-stone-200 bg-stone-50 p-3 text-[10px]">
          {JSON.stringify(
            explorerQ.data?.items.find((x) => String(x.entity ?? x.source) === expanded)?.evidence ?? {},
            null,
            2,
          )}
        </pre>
      ) : null}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - 50))}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-xs disabled:opacity-40"
          disabled={!explorerQ.data?.truncated}
          onClick={() => setOffset((o) => o + 50)}
        >
          Next
        </button>
      </div>
    </section>
  );
}

export default function AdminCortexCanonicalHealthPage() {
  return (
    <PhasePageShell
      phase="canonical"
      title="Canonical"
      description="Raw → deterministic canonical rows. Materialization runs on the execution engine only."
      summaryContent={(summary) => <CanonicalSummaryBody summary={summary as CanonicalSummary} />}
      explorerContent={<CanonicalExplorer />}
    />
  );
}

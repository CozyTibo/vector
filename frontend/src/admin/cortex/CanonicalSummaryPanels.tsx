import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { adminApiPath } from "../../lib/adminApiUrl";
import { formatRelativeAge, titleConnector } from "../cortexAdminTypes";
import type { ConnectorRollup } from "../canonical/coverageMatrixTypes";
import type { CoveragePayload } from "../canonical/coverageMatrixTypes";
import { StatusBadge } from "../ui/StatusBadge";
import { SectionSkeleton } from "./SectionSkeleton";
import type { PhaseSummaryPayload } from "./PhasePageShell";
import { usePhaseSummaryDetail } from "./usePhaseSummaryDetail";

type CanonicalMetrics = PhaseSummaryPayload & {
  health?: {
    materialization_row_count?: number;
    active_canonical_failure_count?: number;
    last_verification_passed?: boolean | null;
    verification_freshness_label?: string;
  };
  forward_progress?: { untreated_estimate?: number };
  failure_count?: number;
};

export function CanonicalSummaryPanels() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const metricsQ = usePhaseSummaryDetail("canonical", true);
  const coverageQ = useQuery({
    queryKey: ["admin-cortex-canonical-coverage-rollups", tenantId],
    queryFn: () =>
      adminJson<CoveragePayload>(
        adminApiPath(tenantId, "/cortex/canonical/coverage-matrix"),
        undefined,
        { timeoutMs: 45_000 },
      ),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    select: (data) => (data.connector_rollups ?? []) as ConnectorRollup[],
  });

  const m = metricsQ.data as CanonicalMetrics | undefined;
  const h = m?.health ?? {};
  const untreated = Number(m?.forward_progress?.untreated_estimate ?? m?.backlog_count ?? 0);
  const failures = Number(h.active_canonical_failure_count ?? m?.failure_count ?? 0);
  const rollups = coverageQ.data ?? [];

  return (
    <div className="space-y-4">
      {metricsQ.isError ? (
        <p className="text-sm text-red-700">{(metricsQ.error as Error).message}</p>
      ) : null}
      {metricsQ.isPending && !m ? (
        <SectionSkeleton variant="cards" />
      ) : (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase text-stone-500">Materialized rows</p>
            <p className="mt-1 text-lg font-semibold">
              {Number(h.materialization_row_count ?? 0).toLocaleString()}
            </p>
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
              {h.last_verification_passed === false
                ? "Failed"
                : h.last_verification_passed
                  ? "Passed"
                  : "—"}
              {h.verification_freshness_label ? ` (${h.verification_freshness_label})` : ""}
            </p>
          </div>
        </section>
      )}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Per-connector coverage</h2>
        {coverageQ.isPending && rollups.length === 0 ? (
          <div className="mt-3">
            <SectionSkeleton variant="table" />
          </div>
        ) : coverageQ.isError ? (
          <p className="mt-3 text-sm text-red-700">{(coverageQ.error as Error).message}</p>
        ) : rollups.length === 0 ? (
          <p className="mt-3 text-sm text-stone-500">No connector rollups yet.</p>
        ) : (
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
                {rollups.map((r) => {
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
        )}
      </section>
    </div>
  );
}

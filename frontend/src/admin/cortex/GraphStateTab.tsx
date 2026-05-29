import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { GraphReadiness, GraphStats } from "../cortexAdminTypes";
import { GraphSchedulerPanel } from "./GraphSchedulerPanel";
import { useGraphReadiness } from "./useGraphReadiness";

function CheckRow({
  ok,
  label,
  detail,
}: {
  ok: boolean;
  label: string;
  detail?: string;
}) {
  return (
    <li className="flex gap-2 text-sm">
      <span className={ok ? "text-emerald-700" : "text-amber-800"} aria-hidden>
        {ok ? "✓" : "○"}
      </span>
      <span>
        <span className="font-medium text-stone-900">{label}</span>
        {detail ? <span className="text-stone-600"> — {detail}</span> : null}
      </span>
    </li>
  );
}

function ReadinessChecks({ data }: { data: GraphReadiness }) {
  const last = data.latest_pass_run;
  const lastStats = last?.stats ?? {};
  const lastProcessed = typeof lastStats.processed === "number" ? lastStats.processed : 0;
  const lastUpserted = typeof lastStats.edges_upserted === "number" ? lastStats.edges_upserted : 0;
  const enrichOnlyDrain =
    lastProcessed > 0 &&
    lastUpserted === 0 &&
    data.dirty_queue_extract_pending === 0 &&
    data.active_relationship_count === 0;

  return (
    <ul className="mt-3 space-y-2">
      <CheckRow
        ok={!data.canon_backlog}
        label="Canon caught up"
        detail={
          data.canon_backlog
            ? "Graph extract is blocked until canonical materialization finishes"
            : "No pending canon dirty rows or raw cursor lag"
        }
      />
      <CheckRow
        ok={data.dirty_queue_pending === 0}
        label="Graph dirty queue empty"
        detail={
          data.dirty_queue_pending > 0
            ? `${data.dirty_queue_pending.toLocaleString()} pending (${data.dirty_queue_extract_pending} extract · ${data.dirty_queue_enrich_pending} enrich)`
            : "No pending extract or enrich work"
        }
      />
      <CheckRow
        ok={data.graph_caught_up}
        label="Graph lane idle"
        detail={
          data.scheduler.tenant_needs_work
            ? "Scheduler still has work for this tenant"
            : data.scheduler.lane_stale
              ? "Lane may be stale — check orchestrator"
              : "Caught up for current extractor version"
        }
      />
      <CheckRow
        ok={data.active_relationship_count > 0 || data.scoped_entity_count === 0}
        label="Active execution links"
        detail={`${data.active_relationship_count.toLocaleString()} active · ${data.scoped_entity_count.toLocaleString()} scoped canon entities`}
      />
      <CheckRow
        ok
        label="Unlinked scoped entities"
        detail={
          data.scoped_entity_count === 0
            ? "No scoped canon entities yet"
            : `${data.unlinked_scoped_entity_count.toLocaleString()} with no active links · ${(data.scoped_entity_count - data.unlinked_scoped_entity_count).toLocaleString()} linked`
        }
      />
      {enrichOnlyDrain ? (
        <li className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Recent passes processed entities but upserted no edges (likely actor enrich-only).
          Use <strong>Rebuild graph projections</strong> below after canon is caught up to extract
          links from messages, PRs, and work items.
        </li>
      ) : null}
    </ul>
  );
}

function kindBrowseHref(kind: string): string {
  const params = new URLSearchParams({ tab: "data", kind });
  return `?${params}`;
}

export function GraphStateTab() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const readinessQ = useGraphReadiness();
  const statsQ = useQuery({
    queryKey: ["admin-cortex-graph-stats", tenantId],
    queryFn: () => adminJson<GraphStats>(`/admin/tenants/${tenantId}/cortex/graph/stats`),
    enabled: Boolean(tenantId),
  });

  const data = readinessQ.data;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <GraphSchedulerPanel />

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Overall state</h2>
        <p className="mt-1 text-sm text-stone-600">
          Extractor v{data.extractor_version} (code v{data.extractor_version_code}) ·{" "}
          {data.unresolved_reference_count.toLocaleString()} unresolved refs
        </p>
        <ReadinessChecks data={data} />
        {Object.keys(data.dirty_queue_by_reason).length > 0 ? (
          <div className="mt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
              Dirty queue by reason
            </p>
            <table className="mt-2 w-full max-w-md text-sm">
              <tbody>
                {Object.entries(data.dirty_queue_by_reason).map(([reason, count]) => (
                  <tr key={reason} className="border-b border-stone-50">
                    <td className="py-1 font-mono text-xs text-stone-700">{reason}</td>
                    <td className="py-1 text-right tabular-nums">{count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-stone-900">Links by kind</h2>
        <p className="mt-1 text-sm text-stone-600">
          Open a kind to browse every active link and verify extraction accuracy.
        </p>
        {statsQ.isPending ? (
          <p className="mt-2 text-sm text-stone-500">Loading…</p>
        ) : (
          <table className="mt-3 w-full max-w-lg text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="py-2 pr-4 font-medium">Kind</th>
                <th className="py-2 font-medium text-right">Count</th>
              </tr>
            </thead>
            <tbody>
              {(statsQ.data?.by_kind ?? []).map((row) => {
                const browseTo = kindBrowseHref(row.relationship_kind);
                return (
                  <tr key={row.relationship_kind} className="border-b border-stone-50">
                    <td className="py-2 pr-4">
                      <Link
                        className={[
                          row.count === 0
                            ? "text-stone-500 hover:text-stone-700"
                            : "font-medium text-indigo-700",
                          "hover:underline",
                        ].join(" ")}
                        to={browseTo}
                      >
                        {row.relationship_kind_label}
                      </Link>
                      <span className="ml-2 font-mono text-xs text-stone-400">
                        {row.relationship_kind}
                      </span>
                    </td>
                    <td
                      className={[
                        "py-2 text-right tabular-nums",
                        row.count === 0 ? "text-stone-400" : "",
                      ].join(" ")}
                    >
                      <Link
                        className={[
                          row.count === 0
                            ? "text-stone-400 hover:text-stone-600"
                            : "text-indigo-700",
                          "hover:underline",
                        ].join(" ")}
                        to={browseTo}
                      >
                        {row.count.toLocaleString()}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../cortex/SectionSkeleton";
import { DeployInfoFooter } from "./DeployInfoFooter";
import { OperatorActionPanel } from "./OperatorActionPanel";
import { useOperatorOverview } from "./useOperatorOverview";
import { useOperatorRuntime } from "./useOperatorRuntime";
import type { OperatorDualLane, OperatorRuntimeLease, OperatorRuntimeTransition } from "./operatorTypes";

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

function LeaseTruthSection({ lease }: { lease: OperatorRuntimeLease | null }) {
  if (!lease) {
    return (
      <section className="rounded-xl border border-stone-200 bg-white p-5 text-sm text-stone-700 shadow-sm">
        No execution lease row — worker has not started for this tenant.
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-stone-300 bg-stone-900 px-5 py-4 text-stone-100 shadow-sm">
      <p className="text-sm font-semibold tracking-wide">
        {lease.status?.toUpperCase() ?? "UNKNOWN"}
        {lease.phase_cursor ? ` · ${lease.phase_cursor.replace(/_/g, " ")}` : ""}
        {lease.block_reason_code ? ` · blocked: ${lease.block_reason_code}` : ""}
      </p>
      <p className="mt-2 text-xs text-stone-300">
        FSM {lease.fsm_state ?? "—"}
        {lease.obligation_epoch != null ? ` · obligation ${lease.obligation_epoch}` : ""}
        {lease.target_epoch != null ? ` → target ${lease.target_epoch}` : ""}
      </p>
      <p className="mt-1 text-xs text-stone-400">
        Canonical lane {lease.canonical_lane_status ?? "—"} · Execution lane{" "}
        {lease.execution_lane_status ?? "—"}
      </p>
      {lease.pipeline_run_id ? (
        <p className="mt-1 text-xs text-stone-400">Pipeline run {lease.pipeline_run_id}</p>
      ) : null}
      {lease.last_error ? <p className="mt-2 text-xs text-red-300">Last error: {lease.last_error}</p> : null}
      {lease.block_detail ? (
        <details className="mt-3 text-xs text-stone-300">
          <summary className="cursor-pointer text-indigo-300">Block detail</summary>
          <pre className="mt-2 overflow-x-auto rounded bg-stone-950 p-2 text-[11px]">
            {typeof lease.block_detail === "string"
              ? lease.block_detail
              : JSON.stringify(lease.block_detail, null, 2)}
          </pre>
        </details>
      ) : null}
    </section>
  );
}

function laneFact(lane: Record<string, unknown> | null | undefined, label: string): string {
  if (!lane || typeof lane !== "object") return `${label}: no snapshot.`;
  const status = String(lane.lane_status ?? "UNKNOWN");
  const outcome = lane.outcome != null ? String(lane.outcome) : null;
  const phase = lane.phase_cursor != null ? String(lane.phase_cursor) : null;
  const bits = [status];
  if (outcome) bits.push(`outcome ${outcome}`);
  if (phase) bits.push(`cursor ${phase}`);
  return `${label}: ${bits.join(" · ")}`;
}

function IdentitySubstrateSection({
  health,
  repair,
}: {
  health: Record<string, unknown> | null | undefined;
  repair: Record<string, unknown> | null | undefined;
}) {
  if (!health && !repair) return null;
  const metrics = (health?.metrics as Record<string, unknown> | undefined) ?? {};
  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/40 p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Identity substrate</p>
      <p className="mt-1 text-xs text-stone-600">
        Same repair path as phase 03 — pagination state lives on the convergence lease.
      </p>
      <ul className="mt-3 space-y-1 text-sm text-stone-800">
        <li>
          Health: <span className="font-medium">{String(health?.status ?? "—")}</span>
        </li>
        <li>
          Anchor offset: {String(repair?.anchor_offset ?? 0)} / {String(repair?.anchors_total ?? "—")}
          {repair?.anchor_backfill_exhausted ? " (exhausted)" : ""}
        </li>
        <li>Human actors: {String(metrics.active_human_actors ?? "—")}</li>
        <li>Anchors: {String(metrics.identity_anchors ?? "—")}</li>
        <li>Auth links: {String(metrics.authoritative_links ?? "—")}</li>
        <li>Promotion rules: {String(metrics.distinct_authoritative_promotion_rules ?? "—")}</li>
      </ul>
    </section>
  );
}

function DualLaneSection({ dualLane }: { dualLane: OperatorDualLane }) {
  const canonical = dualLane.canonical_lane;
  const execution = dualLane.execution_lane;
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Dual-lane inspect</p>
      <p className="mt-1 text-xs text-stone-600">Canonical vs execution lane facts (no health badges).</p>
      <ul className="mt-3 space-y-2 text-sm text-stone-800">
        <li>{laneFact(canonical, "Canonical")}</li>
        <li>{laneFact(execution, "Execution")}</li>
      </ul>
    </section>
  );
}

function TransitionTimeline({
  transitions,
  total,
  onLoadMore,
  loadingMore,
}: {
  transitions: OperatorRuntimeTransition[];
  total: number;
  onLoadMore: () => void;
  loadingMore: boolean;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const expandedRow = transitions.find(
    (t) => `${t.created_at}-${t.trigger}-${t.from_state}` === expanded,
  );

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Transition timeline</p>
      <p className="mt-1 text-xs text-stone-600">
        Showing {transitions.length} of {total} transitions.
      </p>
      {transitions.length === 0 ? (
        <p className="mt-3 text-sm text-stone-600">No transitions recorded yet.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full text-left text-xs text-stone-800">
            <thead>
              <tr className="border-b border-stone-200 text-stone-500">
                <th className="py-2 pr-4 font-medium">Time</th>
                <th className="py-2 pr-4 font-medium">Trigger</th>
                <th className="py-2 pr-4 font-medium">From → To</th>
                <th className="py-2 pr-4 font-medium">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {transitions.map((tr) => {
                const key = `${tr.created_at}-${tr.trigger}-${tr.from_state}`;
                return (
                  <tr
                    key={key}
                    className="cursor-pointer border-b border-stone-100 hover:bg-stone-50"
                    onClick={() => setExpanded(expanded === key ? null : key)}
                  >
                    <td className="py-2 pr-4 whitespace-nowrap">{fmtTime(tr.created_at)}</td>
                    <td className="py-2 pr-4">{tr.trigger}</td>
                    <td className="py-2 pr-4">
                      {tr.from_state} → {tr.to_state}
                    </td>
                    <td className="py-2 pr-4">{tr.gate_result ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      {expandedRow && Object.keys(expandedRow.detail_json).length > 0 ? (
        <pre className="mt-3 overflow-x-auto rounded-md border border-stone-200 bg-stone-50 p-3 text-[11px] text-stone-800">
          {JSON.stringify(expandedRow.detail_json, null, 2)}
        </pre>
      ) : null}
      {transitions.length < total ? (
        <button
          type="button"
          className="mt-4 rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-40"
          disabled={loadingMore}
          onClick={onLoadMore}
        >
          {loadingMore ? "Loading…" : "Load more"}
        </button>
      ) : null}
    </section>
  );
}

function QueueHintsSection({
  counts,
  tenantId,
}: {
  counts: { deferral_retry_ready: number; synthesis_failed: number; tcre_queued: number };
  tenantId: string;
}) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-stone-900">Queue hints</p>
      <p className="mt-1 text-xs text-stone-600">Counts with links to the Queues tab for full lists.</p>
      <ul className="mt-3 space-y-2 text-sm">
        <li>
          Retry-ready deferrals: {counts.deferral_retry_ready}{" "}
          <Link to={`/admin/tenants/${tenantId}/cortex/queues?tab=deferrals`} className="text-indigo-700">
            queues →
          </Link>
        </li>
        <li>
          TCRE queued: {counts.tcre_queued}{" "}
          <Link to={`/admin/tenants/${tenantId}/cortex/queues?tab=tcre_queued`} className="text-indigo-700">
            queues →
          </Link>
        </li>
        <li>
          Synthesis failed: {counts.synthesis_failed}{" "}
          <Link to={`/admin/tenants/${tenantId}/cortex/queues?tab=synthesis_failed`} className="text-indigo-700">
            queues →
          </Link>
        </li>
      </ul>
    </section>
  );
}

export default function OperatorRuntimePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [transitionLimit, setTransitionLimit] = useState(50);
  const overviewQ = useOperatorOverview();
  const runtimeQ = useOperatorRuntime(transitionLimit);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  if (runtimeQ.isError) {
    return <p className="text-sm text-red-700">{(runtimeQ.error as Error).message}</p>;
  }

  const data = runtimeQ.data;
  const loading = runtimeQ.isPending && !data;
  const runnable = overviewQ.data?.runnable_connectors ?? [];

  return (
    <div className="space-y-6">
      {loading ? <SectionSkeleton variant="strip" /> : data ? <LeaseTruthSection lease={data.lease} /> : null}

      {loading ? (
        <SectionSkeleton variant="attention" />
      ) : data ? (
        <DualLaneSection dualLane={data.dual_lane} />
      ) : null}

      {loading ? null : data ? (
        <IdentitySubstrateSection
          health={data.identity_substrate_health}
          repair={data.identity_substrate_repair}
        />
      ) : null}

      {loading ? (
        <SectionSkeleton variant="table" />
      ) : data ? (
        <TransitionTimeline
          transitions={data.transitions}
          total={data.transition_total}
          loadingMore={runtimeQ.isFetching && transitionLimit > 50}
          onLoadMore={() => setTransitionLimit((n) => Math.min(n + 50, 200))}
        />
      ) : null}

      {loading ? (
        <SectionSkeleton variant="table" />
      ) : data ? (
        <QueueHintsSection counts={data.queue_counts} tenantId={tenantId} />
      ) : null}

      <OperatorActionPanel variant="full" runnableConnectors={runnable} />

      <p className="text-xs text-stone-500">
        Island registry scans live under Inspect → Islands (not loaded on every runtime fetch).
      </p>

      <DeployInfoFooter />
    </div>
  );
}

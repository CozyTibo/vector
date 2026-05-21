import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { PipelineActions } from "./cortex/PipelineActions";
import { collectAttention, buildPhaseOverviews } from "./cortex/pipelinePhaseStatus";
import { PipelineStrip } from "./cortex/PipelineStrip";
import type { ExecutionInspect } from "./cortex/pipelineTypes";
import { CortexOverview, titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const executionQ = useQuery({
    queryKey: ["admin-cortex-execution", tenantId],
    queryFn: () => adminJson<ExecutionInspect>(`/admin/tenants/${tenantId}/cortex/execution/state`),
    enabled: Boolean(tenantId),
  });

  const ingestionQ = useQuery({
    queryKey: ["admin-cortex-ingestion", tenantId],
    queryFn: () => adminJson<CortexOverview>(`/admin/tenants/${tenantId}/cortex/ingestion`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (executionQ.isPending || ingestionQ.isPending) {
    return <p className="text-sm text-stone-600">Loading pipeline overview…</p>;
  }
  if (executionQ.isError) {
    return <p className="text-sm text-red-700">{(executionQ.error as Error).message}</p>;
  }

  const inspect = executionQ.data ?? null;
  const phases = buildPhaseOverviews(inspect);
  const attention = collectAttention(phases);
  const ingestion = ingestionQ.data;
  const runnableConnectors =
    ingestion?.connectors
      .filter((c) => c.cortex_routed && c.connection_status === "active")
      .map((c) => c.connector) ?? [];

  const sched = ingestion?.global_scheduler;
  const schedulerLabel = !sched?.env_scheduler_enabled
    ? "Scheduled polling: OFF (env)"
    : sched.paused_via_redis
      ? "Scheduled polling: PAUSED (operator)"
      : "Scheduled polling: ON";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Pipeline</h2>
            <p className="text-sm text-stone-600">
              Execution lease is authoritative · FSM {inspect?.lease?.fsm_state ?? "—"} · cursor{" "}
              {inspect?.lease?.phase_cursor ?? "—"}
            </p>
          </div>
          {inspect?.lease?.block_reason_code ? (
            <StatusBadge tone="bad">{inspect.lease.block_reason_code}</StatusBadge>
          ) : (
            <StatusBadge tone="ok">{inspect?.lease?.status ?? "idle"}</StatusBadge>
          )}
        </div>
        <div className="mt-4">
          <PipelineStrip phases={phases} />
        </div>
      </section>

      {attention.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">Attention</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {attention.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <PipelineActions runnableConnectors={runnableConnectors} />

      <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-stone-700">
            <span className="font-medium">{schedulerLabel}</span>
            {sched ? (
              <span className="text-stone-500">
                {" "}
                · beat {sched.beat_interval_seconds}s · gap {sched.min_gap_seconds}s
              </span>
            ) : null}
          </p>
          <Link
            to={`/admin/tenants/${tenantId}/cortex/settings`}
            className="text-sm font-medium text-indigo-700 no-underline hover:underline"
          >
            Settings
          </Link>
        </div>
        {ingestion && runnableConnectors.length > 0 ? (
          <p className="mt-2 text-xs text-stone-500">
            Active connectors: {runnableConnectors.map(titleConnector).join(", ")}
          </p>
        ) : null}
      </section>
    </div>
  );
}

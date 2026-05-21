import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { PipelineActions } from "./cortex/PipelineActions";
import { RecentIngestionRuns } from "./cortex/RecentIngestionRuns";
import { PipelineStrip } from "./cortex/PipelineStrip";
import type { PhaseOverview, PipelineOverview } from "./cortex/pipelineTypes";
import { OPERATOR_PHASES } from "./cortex/pipelineTypes";
import { titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

function phasesForStrip(overview: PipelineOverview): PhaseOverview[] {
  return OPERATOR_PHASES.map((meta) => {
    const row = overview.phases.find((p) => p.phase === meta.phase);
    const status = row?.status ?? "waiting";
    const detail =
      row?.blockers?.[0] ??
      (row?.backlog_count != null && row.backlog_count > 0
        ? `${row.backlog_count.toLocaleString()} backlog`
        : null);
    return { ...meta, status, detail };
  });
}

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const overviewQ = useQuery({
    queryKey: ["admin-cortex-pipeline-overview", tenantId],
    queryFn: () => adminJson<PipelineOverview>(`/admin/tenants/${tenantId}/cortex/pipeline/overview`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (overviewQ.isPending) return <p className="text-sm text-stone-600">Loading pipeline overview…</p>;
  if (overviewQ.isError) return <p className="text-sm text-red-700">{(overviewQ.error as Error).message}</p>;

  const overview = overviewQ.data;
  const phases = phasesForStrip(overview);
  const exec = overview.execution;
  const sched = overview.scheduler;
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
              Execution lease is authoritative · FSM {exec.fsm_state ?? "—"} · cursor {exec.phase_cursor ?? "—"}
            </p>
          </div>
          {exec.block_reason_code ? (
            <StatusBadge tone="bad">{exec.block_reason_code}</StatusBadge>
          ) : (
            <StatusBadge tone="ok">{exec.lease_status ?? "idle"}</StatusBadge>
          )}
        </div>
        <div className="mt-4">
          <PipelineStrip phases={phases} />
        </div>
      </section>

      {overview.attention.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">Attention</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-900">
            {overview.attention.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <PipelineActions runnableConnectors={overview.runnable_connectors} />

      <RecentIngestionRuns
        runs={overview.recent_ingestion_runs ?? []}
        tenantId={tenantId}
        nextScheduled={overview.next_scheduled_ingestion}
      />

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
        {overview.runnable_connectors.length > 0 ? (
          <p className="mt-2 text-xs text-stone-500">
            Active connectors: {overview.runnable_connectors.map(titleConnector).join(", ")}
          </p>
        ) : null}
      </section>
    </div>
  );
}

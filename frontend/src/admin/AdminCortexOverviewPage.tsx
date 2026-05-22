import { Link, useParams } from "react-router-dom";

import { PipelineActions } from "./cortex/PipelineActions";
import { RecentIngestionRuns } from "./cortex/RecentIngestionRuns";
import { PipelineStrip } from "./cortex/PipelineStrip";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import type { PhaseOverview, PipelineOverview } from "./cortex/pipelineTypes";
import { OPERATOR_PHASES } from "./cortex/pipelineTypes";
import {
  usePipelineOverviewExecution,
  usePipelineOverviewIngestion,
  usePipelineOverviewPhases,
} from "./cortex/usePipelineOverview";
import { titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

function phasesForStrip(phases: PipelineOverview["phases"] | undefined): PhaseOverview[] {
  return OPERATOR_PHASES.map((meta) => {
    const row = phases?.find((p) => p.phase === meta.phase);
    const status = row?.status ?? "waiting";
    const statusLabel =
      row?.status_label?.trim() ||
      (status === "healthy"
        ? "Healthy"
        : status === "running"
          ? "Running"
          : status === "blocked"
            ? "Blocked"
            : status === "degraded"
              ? "Has gaps"
              : "Waiting");
    return {
      ...meta,
      status,
      statusLabel,
      objectCountLabel: row?.object_count_label ?? null,
    };
  });
}

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const executionQ = usePipelineOverviewExecution();
  const phasesQ = usePipelineOverviewPhases();
  const ingestionQ = usePipelineOverviewIngestion();

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  const exec = executionQ.data;
  const phases = phasesForStrip(phasesQ.data?.phases);
  const attention = phasesQ.data?.attention ?? [];
  const sched = ingestionQ.data?.scheduler;
  const runnableConnectors = ingestionQ.data?.runnable_connectors ?? [];

  const schedulerLabel = !sched?.env_scheduler_enabled
    ? "Scheduled polling: OFF (env)"
    : sched.paused_via_redis
      ? "Scheduled polling: PAUSED (operator)"
      : "Scheduled polling: ON";

  const phasesError = phasesQ.isError ? (phasesQ.error as Error).message : null;
  const ingestionError = ingestionQ.isError ? (ingestionQ.error as Error).message : null;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Pipeline</h2>
            <p className="text-sm text-stone-600">
              Execution lease is authoritative
              {executionQ.isPending && !exec ? (
                <span className="text-stone-400"> · loading FSM…</span>
              ) : exec ? (
                <>
                  {" "}
                  · FSM {exec.fsm_state ?? "—"} · cursor {exec.phase_cursor ?? "—"}
                </>
              ) : executionQ.isError ? (
                <span className="text-red-700"> · execution unavailable</span>
              ) : null}
            </p>
          </div>
          {executionQ.isPending && !exec ? (
            <div className="h-6 w-20 animate-pulse rounded bg-stone-200" aria-hidden />
          ) : exec?.block_reason_code ? (
            <StatusBadge tone="bad">{exec.block_reason_code}</StatusBadge>
          ) : exec ? (
            <StatusBadge tone="ok">{exec.lease_status ?? "idle"}</StatusBadge>
          ) : null}
        </div>
        <div className="mt-4">
          {phasesQ.isPending && !phasesQ.data ? (
            <SectionSkeleton variant="strip" />
          ) : phasesError ? (
            <p className="text-sm text-red-700">{phasesError}</p>
          ) : (
            <PipelineStrip phases={phases} />
          )}
        </div>
      </section>

      {phasesQ.isPending && !phasesQ.data ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">What needs attention</h3>
          <div className="mt-3">
            <SectionSkeleton variant="attention" />
          </div>
        </section>
      ) : attention.length > 0 ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">What needs attention</h3>
          <p className="mt-1 text-xs text-amber-800/90">
            Plain-language reasons a step is waiting, blocked, or has gaps. Open the phase tab for detail.
          </p>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-amber-900">
            {attention.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {ingestionQ.isPending && !ingestionQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-stone-900">Pipeline actions</p>
          <div className="mt-4">
            <SectionSkeleton variant="actions" />
          </div>
        </section>
      ) : ingestionError ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-red-700">{ingestionError}</p>
        </section>
      ) : (
        <PipelineActions runnableConnectors={runnableConnectors} />
      )}

      <RecentIngestionRuns
        runs={ingestionQ.data?.recent_ingestion_runs ?? []}
        tenantId={tenantId}
        nextScheduled={ingestionQ.data?.next_scheduled_ingestion}
        loading={ingestionQ.isPending && !ingestionQ.data}
        error={ingestionError}
      />

      <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        {ingestionQ.isPending && !ingestionQ.data ? (
          <SectionSkeleton variant="footer" />
        ) : ingestionError ? (
          <p className="text-sm text-red-700">{ingestionError}</p>
        ) : (
          <>
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
            {runnableConnectors.length > 0 ? (
              <p className="mt-2 text-xs text-stone-500">
                Active connectors: {runnableConnectors.map(titleConnector).join(", ")}
              </p>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}

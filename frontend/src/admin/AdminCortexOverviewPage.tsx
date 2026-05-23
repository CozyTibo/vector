import { Link, useParams } from "react-router-dom";

import { ContinuityAttentionList } from "./cortex/ContinuityAttentionList";
import { ContinuityStatusCard } from "./cortex/ContinuityStatusCard";
import { OperatorPrimaryKpiCard } from "./cortex/OperatorPrimaryKpiCard";
import { PipelineActions } from "./cortex/PipelineActions";
import { RecentIngestionRuns } from "./cortex/RecentIngestionRuns";
import {
  OperationalPhaseStrip,
  phasesForOperationalStrip,
} from "./cortex/OperationalPhaseStrip";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import {
  usePipelineOverviewIngestion,
  usePipelineOverviewPhases,
} from "./cortex/usePipelineOverview";
import { titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const phasesQ = usePipelineOverviewPhases();
  const ingestionQ = usePipelineOverviewIngestion();

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  const exec = phasesQ.data?.execution ?? null;
  const continuity = phasesQ.data?.continuity_status ?? undefined;
  const operatorKpi = phasesQ.data?.operator_primary_kpi ?? undefined;
  const operationalPhases = phasesForOperationalStrip(phasesQ.data?.phases);
  const attentionItems = phasesQ.data?.attention_items ?? [];
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
      <ContinuityStatusCard
        status={continuity}
        loading={phasesQ.isPending && !phasesQ.data}
      />

      <OperatorPrimaryKpiCard
        kpi={operatorKpi}
        loading={phasesQ.isPending && !phasesQ.data}
      />

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Pipeline continuity</h2>
            <p className="text-sm text-stone-600">
              Lease FSM is authoritative
              {phasesQ.isPending && !exec ? (
                <span className="text-stone-400"> · loading…</span>
              ) : exec ? (
                <>
                  {" "}
                  · FSM {exec.fsm_state ?? "—"} · cursor {exec.phase_cursor ?? "—"}
                </>
              ) : phasesQ.isError ? (
                <span className="text-red-700"> · pipeline status unavailable</span>
              ) : null}
            </p>
          </div>
          {phasesQ.isPending && !exec ? (
            <div className="h-6 w-20 animate-pulse rounded bg-stone-200" aria-hidden />
          ) : exec?.block_reason_code ? (
            <StatusBadge tone="bad">{exec.block_reason_code}</StatusBadge>
          ) : exec ? (
            <StatusBadge tone={exec.lease_status === "running" ? "ok" : "warn"}>
              {exec.lease_status ?? "idle"}
            </StatusBadge>
          ) : null}
        </div>
        <div className="mt-4">
          {phasesQ.isPending && !phasesQ.data ? (
            <SectionSkeleton variant="strip" />
          ) : phasesError ? (
            <p className="text-sm text-red-700">{phasesError}</p>
          ) : (
            <OperationalPhaseStrip phases={operationalPhases} />
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
      ) : (
        <ContinuityAttentionList items={attentionItems} />
      )}

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

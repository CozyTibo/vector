import { Link, useParams } from "react-router-dom";

import { ContinuityAttentionList } from "./cortex/ContinuityAttentionList";
import { ContinuityStatusCard } from "./cortex/ContinuityStatusCard";
import { DeferralOmissionCard } from "./cortex/DeferralOmissionCard";
import { OperatorPrimaryKpiCard } from "./cortex/OperatorPrimaryKpiCard";
import { SemanticReadinessCard } from "./cortex/SemanticReadinessCard";
import { PipelineActions } from "./cortex/PipelineActions";
import { RecentIngestionRuns } from "./cortex/RecentIngestionRuns";
import {
  OperationalPhaseStrip,
  phasesForOperationalStrip,
} from "./cortex/OperationalPhaseStrip";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import {
  usePipelineOverviewBootstrap,
  usePipelineSemanticReadiness,
} from "./cortex/usePipelineOverview";
import { titleConnector } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const bootstrapQ = usePipelineOverviewBootstrap();
  const semanticQ = usePipelineSemanticReadiness();

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  const bootstrap = bootstrapQ.data;
  const exec = bootstrap?.execution ?? null;
  const continuity = bootstrap?.continuity_status ?? undefined;
  const operatorKpi = bootstrap?.operator_primary_kpi ?? undefined;
  const hideLegacyPrimaryKpi = operatorKpi?.hide_from_overview === true;
  const semanticReadiness = semanticQ.data ?? undefined;
  const operationalPhases = phasesForOperationalStrip(bootstrap?.phases);
  const attentionItems = bootstrap?.attention_items ?? [];
  const sched = bootstrap?.scheduler;
  const runnableConnectors = bootstrap?.runnable_connectors ?? [];

  const schedulerLabel = !sched?.env_scheduler_enabled
    ? "Scheduled polling: OFF (env)"
    : sched.paused_via_redis
      ? "Scheduled polling: PAUSED (operator)"
      : "Scheduled polling: ON";

  const bootstrapError = bootstrapQ.isError ? (bootstrapQ.error as Error).message : null;

  return (
    <div className="space-y-6">
      <SemanticReadinessCard
        data={semanticReadiness}
        loading={semanticQ.isPending && !semanticReadiness}
      />

      <ContinuityStatusCard
        status={continuity}
        loading={bootstrapQ.isPending && !continuity}
      />

      {!hideLegacyPrimaryKpi ? (
        <OperatorPrimaryKpiCard
          kpi={operatorKpi}
          loading={bootstrapQ.isPending && !operatorKpi}
        />
      ) : null}

      <DeferralOmissionCard
        omission={operatorKpi?.deferral_omission ?? undefined}
        loading={bootstrapQ.isPending && !bootstrap}
      />

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Pipeline continuity</h2>
            <p className="text-sm text-stone-600">
              Lease FSM is authoritative
              {bootstrapQ.isPending && !exec ? (
                <span className="text-stone-400"> · loading…</span>
              ) : exec ? (
                <>
                  {" "}
                  · FSM {exec.fsm_state ?? "—"} · cursor {exec.phase_cursor ?? "—"}
                </>
              ) : bootstrapError ? (
                <span className="text-red-700"> · pipeline status unavailable</span>
              ) : null}
            </p>
          </div>
          {bootstrapQ.isPending && !exec ? (
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
          {bootstrapQ.isPending && !bootstrap ? (
            <SectionSkeleton variant="strip" />
          ) : bootstrapError ? (
            <p className="text-sm text-red-700">{bootstrapError}</p>
          ) : (
            <OperationalPhaseStrip phases={operationalPhases} />
          )}
        </div>
      </section>

      {bootstrapQ.isPending && !bootstrap ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">What needs attention</h3>
          <div className="mt-3">
            <SectionSkeleton variant="attention" />
          </div>
        </section>
      ) : (
        <ContinuityAttentionList items={attentionItems} />
      )}

      {bootstrapQ.isPending && !bootstrap ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-stone-900">Pipeline actions</p>
          <div className="mt-4">
            <SectionSkeleton variant="actions" />
          </div>
        </section>
      ) : bootstrapError ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-red-700">{bootstrapError}</p>
        </section>
      ) : (
        <PipelineActions runnableConnectors={runnableConnectors} />
      )}

      <RecentIngestionRuns
        runs={bootstrap?.recent_ingestion_runs ?? []}
        tenantId={tenantId}
        nextScheduled={bootstrap?.next_scheduled_ingestion}
        loading={bootstrapQ.isPending && !bootstrap}
        error={bootstrapError}
      />

      <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        {bootstrapQ.isPending && !bootstrap ? (
          <SectionSkeleton variant="footer" />
        ) : bootstrapError ? (
          <p className="text-sm text-red-700">{bootstrapError}</p>
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

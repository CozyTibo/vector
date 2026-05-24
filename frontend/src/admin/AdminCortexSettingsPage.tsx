import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import {
  CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE,
  CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
} from "./adminConstants";
import { SectionSkeleton } from "./cortex/SectionSkeleton";
import {
  pipelineOverviewIngestionQueryKey,
  pipelineOverviewSliceQueryKeys,
  usePipelineOverviewIngestion,
} from "./cortex/usePipelineOverview";
import { DeployInfoFooter } from "./operator/DeployInfoFooter";
import { isCortexAdminV2Enabled } from "./operator/featureFlags";
import { invalidateOperatorOverviewCaches, useOperatorOverviewScheduler } from "./operator/useOperatorOverview";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexSettingsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const v2 = isCortexAdminV2Enabled();
  const legacyIngestionQ = usePipelineOverviewIngestion();
  const operatorSchedQ = useOperatorOverviewScheduler();

  const sched = v2 ? operatorSchedQ.scheduler : legacyIngestionQ.data?.scheduler;
  const schedPending = v2 ? operatorSchedQ.isPending && !sched : legacyIngestionQ.isPending && !sched;
  const schedError = v2 ? operatorSchedQ.error : legacyIngestionQ.error;

  const pauseMut = useMutation({
    mutationFn: async (paused: boolean) => {
      const res = await adminFetch("/admin/cortex/ingestion/scheduler-pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paused,
          confirmation: paused ? CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE : CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      if (v2) {
        invalidateOperatorOverviewCaches(qc, tenantId);
      } else {
        for (const key of pipelineOverviewSliceQueryKeys(tenantId)) {
          void qc.invalidateQueries({ queryKey: key });
        }
        void qc.invalidateQueries({ queryKey: pipelineOverviewIngestionQueryKey(tenantId) });
      }
      void qc.invalidateQueries({ queryKey: ["admin-cortex-ingestion", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-semibold text-stone-900">Cortex settings</h1>
        <p className="mt-1 text-sm text-stone-600">Scheduler and operator controls. Pipeline actions live on Overview.</p>
      </header>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-900">Scheduled ingestion</h2>
        {schedPending ? (
          <div className="mt-4">
            <SectionSkeleton variant="actions" />
          </div>
        ) : schedError ? (
          <p className="mt-3 text-sm text-red-700">{(schedError as Error).message}</p>
        ) : sched ? (
          <>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <StatusBadge tone={sched.env_scheduler_enabled ? "ok" : "warn"}>
                {sched.env_scheduler_enabled ? "env enabled" : "env disabled"}
              </StatusBadge>
              <StatusBadge tone={sched.paused_via_redis ? "warn" : "ok"}>
                {sched.paused_via_redis ? "operator paused" : "not paused"}
              </StatusBadge>
            </div>
            <p className="mt-2 text-xs text-stone-600">
              {sched.operator_mode_label ?? "Scheduler"}
              {" · "}
              beat {(sched as { beat_interval_seconds?: number }).beat_interval_seconds ?? "—"}s · gap{" "}
              {(sched as { min_gap_seconds?: number }).min_gap_seconds ?? "—"}s
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-40"
                disabled={pauseMut.isPending || sched.paused_via_redis}
                onClick={() => pauseMut.mutate(true)}
              >
                Pause scheduled ingestion
              </button>
              <button
                type="button"
                className="rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-100 disabled:opacity-40"
                disabled={pauseMut.isPending || !sched.paused_via_redis}
                onClick={() => pauseMut.mutate(false)}
              >
                Resume scheduled ingestion
              </button>
            </div>
            {pauseMut.isError ? (
              <p className="mt-2 text-xs text-red-700">{(pauseMut.error as Error).message}</p>
            ) : null}
          </>
        ) : null}
      </section>

      <section className="rounded-xl border border-dashed border-stone-300 bg-stone-50 p-4 text-xs text-stone-600">
        Debug surfaces (replay, doctrine, certification) are not linked from operator nav. Use API or Cursor with
        read-only inspect endpoints.
      </section>

      <DeployInfoFooter />
    </div>
  );
}

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { readErrorDetail } from "../../lib/canonicalApi";
import {
  CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE,
  CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
} from "../adminConstants";
import type { CortexIngestionOverview } from "../cortexAdminTypes";
import { invalidateCortexIngestionOverview } from "./useCortexIngestionOverview";

type Props = {
  overview: CortexIngestionOverview | undefined;
};

export function IngestionSchedulerPanel({ overview }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const sched = overview?.global_scheduler;

  const pauseMut = useMutation({
    mutationFn: async (paused: boolean) => {
      const res = await adminFetch("/admin/cortex/ingestion/scheduler-pause", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paused,
          confirmation: paused
            ? CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE
            : CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => invalidateCortexIngestionOverview(qc, tenantId),
  });

  if (!sched) return null;

  const paused = sched.paused_via_redis;
  const label = sched.operator_mode_label ?? (sched.env_scheduler_enabled ? "Active" : "Off (env)");

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Scheduler</h2>
      <p className="mt-1 text-sm text-stone-600">
        Beat interval {sched.beat_interval_seconds}s · min gap {sched.min_gap_seconds}s · mode{" "}
        <span className="font-medium text-stone-800">{label}</span>
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
          disabled={pauseMut.isPending || paused}
          onClick={() => pauseMut.mutate(true)}
        >
          Pause all tenants
        </button>
        <button
          type="button"
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          disabled={pauseMut.isPending || !paused}
          onClick={() => pauseMut.mutate(false)}
        >
          Resume
        </button>
      </div>
      {pauseMut.isError ? (
        <p className="mt-2 text-sm text-red-700">{(pauseMut.error as Error).message}</p>
      ) : null}
    </section>
  );
}

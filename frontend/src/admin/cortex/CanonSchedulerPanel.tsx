import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { useCanonReadiness } from "./useCanonReadiness";

const TRIGGER_PHRASE = "RUN CANON MATERIALIZATION PASS";

export function CanonSchedulerPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const readinessQ = useCanonReadiness();
  const [confirm, setConfirm] = useState("");

  const triggerM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/canon/actions/trigger-pass`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation: confirm }),
        },
      );
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canon"] });
      setConfirm("");
    },
  });

  const sched = readinessQ.data?.scheduler;
  if (!sched) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Scheduler</h2>
      <p className="mt-1 text-sm text-stone-600">
        Canon Beat every {sched.interval_seconds}s (default 300s) · mode{" "}
        <span className="font-medium text-stone-800">
          {sched.enabled ? "Active" : "Off (env)"}
        </span>
        {readinessQ.data ? (
          <>
            {" "}
            · pending raw ~{readinessQ.data.materialization_lag.pending_raw_rows_estimate}
          </>
        ) : null}
      </p>
      <div className="mt-3 rounded border border-amber-100 bg-amber-50/80 p-3">
        <p className="text-xs text-amber-950">
          Manual pass — type exactly: <code className="font-mono">{TRIGGER_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[240px] flex-1 rounded border border-amber-200 px-2 py-1.5 text-sm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          <button
            type="button"
            disabled={confirm !== TRIGGER_PHRASE || triggerM.isPending}
            onClick={() => triggerM.mutate()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {triggerM.isPending ? "Enqueueing…" : "Run canon pass"}
          </button>
        </div>
        {triggerM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(triggerM.error as Error).message}</p>
        ) : null}
      </div>
    </section>
  );
}

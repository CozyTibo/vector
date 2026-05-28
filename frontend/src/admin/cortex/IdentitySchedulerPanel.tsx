import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch } from "../../lib/adminFetch";
import { useIdentityReadiness } from "./useIdentityReadiness";

const TRIGGER_PHRASE = "RUN IDENTITY RECONCILIATION PASS";
const REBUILD_PHRASE = "REBUILD IDENTITIES FROM CANON ACTORS";

export function IdentitySchedulerPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const readinessQ = useIdentityReadiness();
  const [triggerConfirm, setTriggerConfirm] = useState("");
  const [rebuildConfirm, setRebuildConfirm] = useState("");

  const triggerM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/identities/actions/trigger-pass`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: triggerConfirm }),
      });
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-identity-readiness"] });
      setTriggerConfirm("");
    },
  });

  const rebuildM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/identities/actions/rebuild`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: rebuildConfirm }),
      });
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-identity-readiness"] });
      setRebuildConfirm("");
    },
  });

  const sched = readinessQ.data?.scheduler;
  if (!sched) return null;

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-stone-900">Scheduler</h2>
      <p className="mt-1 text-sm text-stone-600">
        Identity Beat every {sched.interval_seconds}s · mode{" "}
        <span className="font-medium text-stone-800">{sched.enabled ? "Active" : "Off (env)"}</span>
      </p>
      <div className="mt-3 rounded border border-amber-100 bg-amber-50/80 p-3">
        <p className="text-xs text-amber-950">
          Manual pass — type exactly: <code className="font-mono">{TRIGGER_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[260px] flex-1 rounded border border-amber-200 px-2 py-1.5 text-sm"
            value={triggerConfirm}
            onChange={(e) => setTriggerConfirm(e.target.value)}
          />
          <button
            type="button"
            disabled={triggerConfirm !== TRIGGER_PHRASE || triggerM.isPending}
            onClick={() => triggerM.mutate()}
            className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {triggerM.isPending ? "Enqueueing…" : "Run identity pass"}
          </button>
        </div>
        {triggerM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(triggerM.error as Error).message}</p>
        ) : null}
      </div>
      <div className="mt-3 rounded border border-rose-100 bg-rose-50/80 p-3">
        <p className="text-xs text-rose-950">
          Full rebuild — type exactly: <code className="font-mono">{REBUILD_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[260px] flex-1 rounded border border-rose-200 px-2 py-1.5 text-sm"
            value={rebuildConfirm}
            onChange={(e) => setRebuildConfirm(e.target.value)}
          />
          <button
            type="button"
            disabled={rebuildConfirm !== REBUILD_PHRASE || rebuildM.isPending}
            onClick={() => rebuildM.mutate()}
            className="rounded-md bg-rose-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-800 disabled:opacity-50"
          >
            {rebuildM.isPending ? "Rebuilding…" : "Rebuild identities"}
          </button>
        </div>
        {rebuildM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(rebuildM.error as Error).message}</p>
        ) : null}
      </div>
    </section>
  );
}


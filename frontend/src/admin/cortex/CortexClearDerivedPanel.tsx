import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE } from "../adminConstants";
import { adminFetch } from "../../lib/adminFetch";

type ClearDerivedResponse = {
  accepted: boolean;
  tenant_id: string;
  task_id: string;
  queue: string;
};

export function CortexClearDerivedPanel() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState("");
  const [lastResult, setLastResult] = useState<ClearDerivedResponse | null>(null);

  const clearM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/actions/clear-derived`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: confirm }),
      });
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return (await res.json()) as ClearDerivedResponse;
    },
    onSuccess: (data) => {
      setLastResult(data);
      setConfirm("");
      void qc.invalidateQueries({ queryKey: ["admin-cortex"] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canon"] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-graph"] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-identities"] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-declared-domains"] });
      void qc.invalidateQueries({ queryKey: ["admin-execution-surfaces"] });
    },
  });

  return (
    <section className="rounded-xl border border-rose-200 bg-rose-50/40 p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-rose-950">Clear derived Cortex state</h2>
      <p className="mt-1 text-sm text-rose-900/90">
        Deletes canonical entities, identities, graph links, declared domains, pass queues, and raw-memory
        indexes for this tenant.{" "}
        <span className="font-medium">Raw ingestion records are kept.</span> Work runs in the background; a
        canon pass is enqueued when the wipe finishes, then the scheduler continues identity, graph, and
        declared-domain lanes.
      </p>
      <div className="mt-3 rounded border border-rose-200 bg-white/80 p-3">
        <p className="text-xs text-rose-950">
          Type exactly:{" "}
          <code className="font-mono text-[11px]">{CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE}</code>
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          <input
            className="min-w-[280px] flex-1 rounded border border-rose-200 px-2 py-1.5 text-sm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Confirmation phrase"
          />
          <button
            type="button"
            disabled={confirm !== CORTEX_CLEAR_DERIVED_CONFIRM_PHRASE || clearM.isPending}
            onClick={() => clearM.mutate()}
            className="rounded-md bg-rose-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-800 disabled:opacity-50"
          >
            {clearM.isPending ? "Enqueueing…" : "Clear derived & rematerialize"}
          </button>
        </div>
        {clearM.isError ? (
          <p className="mt-2 text-xs text-red-700">{(clearM.error as Error).message}</p>
        ) : null}
        {lastResult ? (
          <p className="mt-2 text-xs text-rose-900">
            Background job enqueued on queue <code className="font-mono">{lastResult.queue}</code> (task{" "}
            <code className="font-mono">{lastResult.task_id}</code>). Derived counts will drop as the worker
            runs; refresh substrate tabs after a few minutes.
          </p>
        ) : null}
      </div>
    </section>
  );
}

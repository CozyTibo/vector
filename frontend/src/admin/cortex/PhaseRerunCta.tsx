import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import { phaseSummaryDetailQueryKey } from "./usePhaseSummaryDetail";
import {
  invalidatePipelineOverviewCaches,
  pipelineOverviewSliceQueryKeys,
} from "./usePipelineOverview";
import type { OperatorPhase } from "./pipelineTypes";

const PHASE_TO_START: Partial<Record<OperatorPhase, string>> = {
  identity: "identity",
  graph: "graph",
  retrieval: "retrieval",
};

type Props = {
  phase: OperatorPhase;
  label: string;
  description: string;
};

export function PhaseRerunCta({ phase, label, description }: Props) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const startPhase = PHASE_TO_START[phase];

  const runMut = useMutation({
    mutationFn: async () => {
      if (!startPhase) throw new Error("phase_not_rerunnable");
      return adminJson<{ mode: string }>(`/admin/tenants/${tenantId}/cortex/pipeline/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "from_phase", start_phase: startPhase }),
      });
    },
    onSuccess: () => {
      invalidatePipelineOverviewCaches(tenantId);
      for (const key of pipelineOverviewSliceQueryKeys(tenantId)) {
        void qc.invalidateQueries({ queryKey: key });
      }
      void qc.invalidateQueries({ queryKey: phaseSummaryDetailQueryKey(tenantId, phase) });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-phase-summary", tenantId, phase] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-pipeline-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-phase-explorer", tenantId, phase] });
    },
  });

  if (!startPhase) return null;

  return (
    <section className="rounded-lg border border-indigo-100 bg-indigo-50/60 p-4">
      <p className="text-sm font-medium text-indigo-950">{label}</p>
      <p className="mt-1 text-xs text-indigo-900/90">{description}</p>
      <button
        type="button"
        disabled={!tenantId || runMut.isPending}
        onClick={() => runMut.mutate()}
        className="mt-3 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
      >
        {runMut.isPending ? "Starting…" : label}
      </button>
      {runMut.isError ? (
        <p className="mt-2 text-xs text-red-700">{(runMut.error as Error).message}</p>
      ) : runMut.isSuccess ? (
        <p className="mt-2 text-xs text-green-800">Execution rerun enqueued.</p>
      ) : null}
    </section>
  );
}

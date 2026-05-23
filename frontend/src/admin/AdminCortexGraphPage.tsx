import { Link, useParams, useSearchParams } from "react-router-dom";

import { PhaseRerunCta } from "./cortex/PhaseRerunCta";
import { usePipelineOverviewPhases } from "./cortex/usePipelineOverview";
import { StatusBadge } from "./ui/StatusBadge";
import { ExecutionThreadInspector } from "./cortex/graph/ExecutionThreadInspector";
import { GraphInspectorDescription, GraphInspectorNav } from "./cortex/graph/GraphInspectorNav";
import { GraphTruthInspector } from "./cortex/graph/GraphTruthInspector";
import {
  defaultGraphInspector,
  type GraphInspectorId,
} from "./cortex/graph/graphInspectorTypes";
import { IdentityContinuityInspector } from "./cortex/graph/IdentityContinuityInspector";
import { IslandInspector } from "./cortex/graph/IslandInspector";
import { RetrievalRealityInspector } from "./cortex/graph/RetrievalRealityInspector";
import { useGraphTruthInspector } from "./cortex/graph/useGraphTruthInspector";

const VALID_INSPECTORS = new Set<GraphInspectorId>([
  "graph-truth",
  "identity",
  "execution-thread",
  "island",
  "retrieval",
]);

function resolveInspector(param: string | null): GraphInspectorId {
  if (param && VALID_INSPECTORS.has(param as GraphInspectorId)) {
    return param as GraphInspectorId;
  }
  return defaultGraphInspector();
}

function statusTone(status: string): "ok" | "warn" | "bad" | "neutral" {
  if (status === "healthy") return "ok";
  if (status === "running") return "neutral";
  if (status === "waiting") return "warn";
  if (status === "blocked") return "bad";
  return "warn";
}

export default function AdminCortexGraphPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const inspector = resolveInspector(searchParams.get("inspector"));

  const phasesQ = usePipelineOverviewPhases();
  const inspectorQ = useGraphTruthInspector();
  const graphPhase = phasesQ.data?.phases?.find((p) => p.phase === "graph");

  const setInspector = (next: GraphInspectorId) => {
    setSearchParams((prev) => {
      const copy = new URLSearchParams(prev);
      copy.set("inspector", next);
      copy.delete("tab");
      return copy;
    });
  };

  const inspectorError = inspectorQ.isError ? (inspectorQ.error as Error).message : null;
  const inspectorData = inspectorQ.data;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-stone-900">Execution reality</h1>
          {graphPhase ? (
            <StatusBadge tone={statusTone(graphPhase.status)}>
              {graphPhase.status_label ?? graphPhase.status}
            </StatusBadge>
          ) : phasesQ.isPending ? (
            <span className="text-sm text-stone-400">loading phase status…</span>
          ) : null}
        </div>
        <p className="max-w-3xl text-sm text-stone-600">
          Inspect whether Cortex reconstructed execution reality truthfully — identity continuity,
          retrieval composition, islands, and promotion lineage. Not graph vanity metrics.
        </p>
        <Link
          to={`/admin/tenants/${tenantId}/cortex`}
          className="inline-block text-sm font-medium text-indigo-700 no-underline hover:underline"
        >
          ← Pipeline overview
        </Link>
      </header>

      <GraphInspectorNav active={inspector} onChange={setInspector} />
      <GraphInspectorDescription active={inspector} />

      <PhaseRerunCta
        phase="graph"
        label="Rebuild graph phase"
        description="Enqueues execution from the graph phase when promotion or topology needs refresh."
      />

      {inspector === "graph-truth" ? (
        <GraphTruthInspector data={inspectorData} loading={inspectorQ.isPending} error={inspectorError} />
      ) : null}
      {inspector === "identity" ? <IdentityContinuityInspector data={inspectorData} /> : null}
      {inspector === "retrieval" ? <RetrievalRealityInspector data={inspectorData} /> : null}
      {inspector === "island" ? <IslandInspector data={inspectorData} /> : null}
      {inspector === "execution-thread" ? <ExecutionThreadInspector /> : null}
    </div>
  );
}

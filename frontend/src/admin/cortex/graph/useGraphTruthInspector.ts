import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../../lib/adminFetch";
import type { GraphInspectorId } from "./graphInspectorTypes";
import type { GraphTruthInspectorPayload } from "./graphInspectorTypes";

export const graphTruthInspectorQueryKey = (
  tenantId: string,
  includeConnectedComponents: boolean,
) => ["admin-cortex-graph-truth-inspector", tenantId, includeConnectedComponents] as const;

const INSPECTORS_NEEDING_GRAPH_TRUTH = new Set<GraphInspectorId>([
  "graph-truth",
  "retrieval",
  "island",
]);

export function inspectorNeedsGraphTruth(inspector: GraphInspectorId): boolean {
  return INSPECTORS_NEEDING_GRAPH_TRUTH.has(inspector);
}

export function useGraphTruthInspector(
  inspector: GraphInspectorId,
  options?: { enabled?: boolean },
) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const includeConnectedComponents = inspector === "island";
  const enabled =
    Boolean(tenantId) &&
    inspectorNeedsGraphTruth(inspector) &&
    (options?.enabled ?? true);

  return useQuery({
    queryKey: graphTruthInspectorQueryKey(tenantId, includeConnectedComponents),
    queryFn: () => {
      const qs = includeConnectedComponents ? "?include_connected_components=true" : "";
      return adminJson<GraphTruthInspectorPayload>(
        `/admin/tenants/${tenantId}/cortex/pipeline/graph-truth-inspector${qs}`,
        undefined,
        { timeoutMs: 60_000 },
      );
    },
    enabled,
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 0,
  });
}

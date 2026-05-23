import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../../lib/adminFetch";
import type { GraphTruthInspectorPayload } from "./graphInspectorTypes";

export const graphTruthInspectorQueryKey = (tenantId: string) =>
  ["admin-cortex-graph-truth-inspector", tenantId] as const;

export function useGraphTruthInspector() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: graphTruthInspectorQueryKey(tenantId),
    queryFn: () =>
      adminJson<GraphTruthInspectorPayload>(
        `/admin/tenants/${tenantId}/cortex/pipeline/graph-truth-inspector`,
      ),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 1,
  });
}

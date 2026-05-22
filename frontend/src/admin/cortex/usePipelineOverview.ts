import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { PipelineOverview } from "./pipelineTypes";

export const pipelineOverviewQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview", tenantId] as const;

export function usePipelineOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewQueryKey(tenantId),
    queryFn: () =>
      adminJson<PipelineOverview>(`/admin/tenants/${tenantId}/cortex/pipeline/overview`),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

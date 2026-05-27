import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CortexIngestionOverview } from "../cortexAdminTypes";

const overviewQueryOpts = {
  staleTime: 30_000,
  gcTime: 5 * 60_000,
  retry: 0,
} as const;

export function cortexIngestionOverviewKey(tenantId: string) {
  return ["admin-cortex-ingestion-overview", tenantId] as const;
}

export function useCortexIngestionOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: cortexIngestionOverviewKey(tenantId),
    queryFn: () =>
      adminJson<CortexIngestionOverview>(`/admin/tenants/${tenantId}/cortex/ingestion`),
    enabled: Boolean(tenantId),
    ...overviewQueryOpts,
  });
}

export function invalidateCortexIngestionOverview(
  queryClient: ReturnType<typeof useQueryClient>,
  tenantId: string,
) {
  void queryClient.invalidateQueries({ queryKey: cortexIngestionOverviewKey(tenantId) });
}

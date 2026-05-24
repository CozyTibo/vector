import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchOperatorOverview } from "./fetchOperator";
import { invalidateOperatorOverviewKey, operatorKeys } from "./operatorKeys";
import type { OperatorOverview } from "./operatorTypes";

const overviewQueryOpts = {
  staleTime: 30_000,
  gcTime: 5 * 60_000,
  retry: 0,
} as const;

export function useOperatorOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const enabled = Boolean(tenantId);
  return useQuery({
    queryKey: operatorKeys.overview(tenantId),
    queryFn: () => fetchOperatorOverview(tenantId),
    enabled,
    ...overviewQueryOpts,
  });
}

export function useOperatorOverviewScheduler() {
  const q = useOperatorOverview();
  return {
    ...q,
    scheduler: q.data?.scheduler,
  };
}

export function invalidateOperatorOverviewCaches(queryClient: ReturnType<typeof useQueryClient>, tenantId: string) {
  void queryClient.invalidateQueries({ queryKey: invalidateOperatorOverviewKey(tenantId) });
}

export type { OperatorOverview };

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { fetchOperatorRuntime } from "./fetchOperator";
import { isCortexAdminV2Enabled } from "./featureFlags";
import { invalidateOperatorOverviewKey, invalidateOperatorRuntimePrefix, operatorKeys } from "./operatorKeys";
import type { OperatorRuntime } from "./operatorTypes";

const runtimeQueryOpts = {
  staleTime: 15_000,
  gcTime: 5 * 60_000,
  retry: 0,
} as const;

export function useOperatorRuntime(transitionLimit = 50) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const enabled = Boolean(tenantId) && isCortexAdminV2Enabled();
  return useQuery({
    queryKey: operatorKeys.runtime(tenantId, transitionLimit),
    queryFn: () =>
      fetchOperatorRuntime(tenantId, { transitionLimit, transitionOffset: 0 }),
    enabled,
    ...runtimeQueryOpts,
  });
}

export function invalidateOperatorCaches(
  queryClient: ReturnType<typeof useQueryClient>,
  tenantId: string,
) {
  void queryClient.invalidateQueries({ queryKey: invalidateOperatorOverviewKey(tenantId) });
  void queryClient.invalidateQueries({ queryKey: invalidateOperatorRuntimePrefix(tenantId) });
}

export type { OperatorRuntime };

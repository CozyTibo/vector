import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { GraphReadiness } from "../cortexAdminTypes";

export function useGraphReadiness() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: ["admin-cortex-graph-readiness", tenantId],
    queryFn: () =>
      adminJson<GraphReadiness>(`/admin/tenants/${tenantId}/cortex/graph/readiness`),
    enabled: Boolean(tenantId),
  });
}

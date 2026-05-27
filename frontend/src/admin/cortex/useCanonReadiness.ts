import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { CanonReadiness } from "../cortexAdminTypes";

export function useCanonReadiness() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: ["admin-cortex-canon-readiness", tenantId],
    queryFn: () => adminJson<CanonReadiness>(`/admin/tenants/${tenantId}/cortex/canon`),
    enabled: Boolean(tenantId),
    staleTime: 30_000,
  });
}

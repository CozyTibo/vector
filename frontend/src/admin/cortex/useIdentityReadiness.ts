import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { IdentityReadiness } from "../cortexAdminTypes";

export function useIdentityReadiness() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: ["admin-cortex-identity-readiness", tenantId],
    queryFn: () => adminJson<IdentityReadiness>(`/admin/tenants/${tenantId}/cortex/identities/readiness`),
    enabled: Boolean(tenantId),
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}


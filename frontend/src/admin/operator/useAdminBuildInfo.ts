import { useQuery } from "@tanstack/react-query";

import { adminFetch } from "../../lib/adminFetch";
import { isCortexAdminV2Enabled } from "./featureFlags";

export type AdminBuildInfo = {
  surface_kind: "admin_build_info";
  git_sha: string | null;
  git_sha_short: string | null;
  cortex_admin_v2_enabled: boolean;
  env: string;
};

export function adminBuildInfoQueryKey() {
  return ["admin-build-info"] as const;
}

export function useAdminBuildInfo() {
  return useQuery({
    queryKey: adminBuildInfoQueryKey(),
    queryFn: async (): Promise<AdminBuildInfo> => {
      const res = await adminFetch("/admin/build-info");
      if (!res.ok) {
        throw new Error(`build-info ${res.status}`);
      }
      return res.json();
    },
    staleTime: 60_000,
    retry: 1,
  });
}

export function useOperatorOverviewProbe(tenantId: string) {
  const enabled = Boolean(tenantId) && isCortexAdminV2Enabled();
  return useQuery({
    queryKey: ["cortex-operator-overview-probe", tenantId],
    enabled,
    queryFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/operator/overview`);
      if (!res.ok) {
        throw new Error(`operator overview ${res.status}`);
      }
      return res.json();
    },
    staleTime: 30_000,
    retry: 0,
  });
}

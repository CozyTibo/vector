import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";

export type DeclaredDomainReadiness = {
  tenant_id: string;
  extractor_version: number;
  declared_domain_count: number;
  active_membership_count: number;
  dirty_queue_pending: number;
  graph_behind: boolean;
  level1_advisory: boolean;
  batch_entity_limit: number;
  latest_pass_run: {
    id: string;
    status: string;
    stats: Record<string, unknown>;
  } | null;
  scheduler: {
    lane_stale?: boolean;
    tenant_needs_work?: boolean;
  };
};

export function useDeclaredDomainReadiness() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: ["admin-cortex-declared-domains-readiness", tenantId],
    queryFn: () =>
      adminJson<DeclaredDomainReadiness>(
        `/admin/tenants/${tenantId}/cortex/declared-domains/readiness`,
      ),
    enabled: Boolean(tenantId),
  });
}

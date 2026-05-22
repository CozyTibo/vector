import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { OperatorPhase } from "./pipelineTypes";

export const phaseSummaryDetailQueryKey = (tenantId: string, phase: OperatorPhase) =>
  ["admin-cortex-phase-summary-detail", tenantId, phase] as const;

export type PhaseSummaryDetail = Record<string, unknown> & {
  surface_kind: string;
  phase: string;
  tenant_id: string;
};

export function usePhaseSummaryDetail(phase: OperatorPhase, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: phaseSummaryDetailQueryKey(tenantId, phase),
    queryFn: () =>
      adminJson<PhaseSummaryDetail>(
        `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/summary/detail`,
      ),
    enabled: Boolean(tenantId) && enabled,
    staleTime: 45_000,
    gcTime: 5 * 60_000,
  });
}

import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../../lib/adminFetch";
import { readErrorDetail } from "../../lib/canonicalApi";
import type { OperatorPhase } from "./pipelineTypes";

export const phaseSummaryDetailQueryKey = (tenantId: string, phase: OperatorPhase) =>
  ["admin-cortex-phase-summary-detail", tenantId, phase] as const;

export type PhaseSummaryDetail = Record<string, unknown> & {
  surface_kind: string;
  phase: string;
  tenant_id: string;
};

const CORE_SUMMARY_KEYS = new Set([
  "surface_kind",
  "phase",
  "tenant_id",
  "status",
  "processed_count",
  "backlog_count",
  "last_success_at",
  "blockers",
]);

function detailPath(tenantId: string, phase: OperatorPhase, suffix: "summary-detail" | "summary/detail") {
  return `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/${suffix}`;
}

function stripCoreFields(full: Record<string, unknown>): Record<string, unknown> {
  const extra: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(full)) {
    if (!CORE_SUMMARY_KEYS.has(key)) {
      extra[key] = value;
    }
  }
  return extra;
}

async function fetchPhaseSummaryDetail(
  tenantId: string,
  phase: OperatorPhase,
): Promise<PhaseSummaryDetail> {
  const candidates: Array<"summary-detail" | "summary/detail"> = [
    "summary-detail",
    "summary/detail",
  ];

  for (const suffix of candidates) {
    const path = detailPath(tenantId, phase, suffix);
    const res = await adminFetch(path);
    if (res.ok) {
      return (await res.json()) as PhaseSummaryDetail;
    }
    if (res.status !== 404) {
      throw new Error(await readErrorDetail(res));
    }
  }

  const full = await adminJson<Record<string, unknown>>(
    `/admin/tenants/${tenantId}/cortex/pipeline/phases/${phase}/summary`,
  );
  return {
    surface_kind: "phase_summary_detail",
    phase: String(full.phase ?? phase),
    tenant_id: String(full.tenant_id ?? tenantId),
    ...stripCoreFields(full),
  };
}

export function usePhaseSummaryDetail(phase: OperatorPhase, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: phaseSummaryDetailQueryKey(tenantId, phase),
    queryFn: () => {
      if (!tenantId) {
        throw new Error("Missing tenant id for phase summary detail");
      }
      return fetchPhaseSummaryDetail(tenantId, phase);
    },
    enabled: Boolean(tenantId) && enabled,
    staleTime: 45_000,
    gcTime: 5 * 60_000,
  });
}

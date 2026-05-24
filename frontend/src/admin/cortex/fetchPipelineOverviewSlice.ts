import { adminFetch, adminJson } from "../../lib/adminFetch";
import { adminApiPath } from "../../lib/adminApiUrl";
import { readErrorDetail } from "../../lib/canonicalApi";
import type {
  AttentionItem,
  ContinuityStatus,
  OperatorPrimaryKpi,
  PipelineOverview,
  SemanticReadiness,
} from "./pipelineTypes";

let monolithInflight: Promise<PipelineOverview> | null = null;
let monolithTenantId: string | null = null;

export function invalidateMonolithOverviewCache() {
  monolithInflight = null;
  monolithTenantId = null;
}

async function fetchMonolithOverview(tenantId: string): Promise<PipelineOverview> {
  if (monolithInflight && monolithTenantId === tenantId) {
    return monolithInflight;
  }
  monolithTenantId = tenantId;
  monolithInflight = adminJson<PipelineOverview>(
    adminApiPath(tenantId, "/cortex/pipeline/overview"),
  ).finally(() => {
    monolithInflight = null;
    monolithTenantId = null;
  });
  return monolithInflight;
}

async function trySlice<T>(
  tenantId: string,
  path: string,
  timeoutMs?: number,
): Promise<T | null> {
  try {
    const res = await adminFetch(adminApiPath(tenantId, path), undefined, { timeoutMs });
    if (res.ok) {
      return (await res.json()) as T;
    }
    // Only fall back to monolith when slice routes are missing — not on server errors/timeouts.
    if (res.status === 404 || res.status === 405) {
      return null;
    }
    throw new Error(await readErrorDetail(res));
  } catch (err) {
    if (err instanceof Error && err.message) {
      throw err;
    }
    return null;
  }
}

export type PipelineExecutionSlice = {
  execution: PipelineOverview["execution"];
  continuity_status?: ContinuityStatus | null;
  operator_primary_kpi?: OperatorPrimaryKpi | null;
  semantic_readiness?: SemanticReadiness | null;
};

export async function fetchSemanticReadinessSlice(tenantId: string): Promise<SemanticReadiness | null> {
  return trySlice<SemanticReadiness>(tenantId, "/cortex/pipeline/semantic-readiness", 25_000);
}

export async function fetchPipelineExecutionSlice(tenantId: string): Promise<PipelineExecutionSlice> {
  const body = await trySlice<{
    execution: PipelineOverview["execution"];
    continuity_status?: ContinuityStatus | null;
    operator_primary_kpi?: OperatorPrimaryKpi | null;
    semantic_readiness?: SemanticReadiness | null;
  }>(tenantId, "/cortex/pipeline/overview/execution", 20_000);
  if (body) {
    return {
      execution: body.execution,
      continuity_status: body.continuity_status ?? null,
      operator_primary_kpi: body.operator_primary_kpi ?? null,
      semantic_readiness: body.semantic_readiness ?? null,
    };
  }
  const full = await fetchMonolithOverview(tenantId);
  const monolith = full as PipelineOverview & {
    continuity_status?: ContinuityStatus;
    semantic_readiness?: SemanticReadiness | null;
  };
  return {
    execution: full.execution,
    continuity_status: monolith.continuity_status ?? null,
    operator_primary_kpi: full.operator_primary_kpi ?? null,
    semantic_readiness: monolith.semantic_readiness ?? null,
  };
}

export async function fetchPipelinePhasesSlice(tenantId: string) {
  const body = await trySlice<{
    phases: PipelineOverview["phases"];
    attention: string[];
    attention_items?: AttentionItem[];
    continuity_status?: ContinuityStatus | null;
    execution?: PipelineOverview["execution"] | null;
    operator_primary_kpi?: OperatorPrimaryKpi | null;
  }>(tenantId, "/cortex/pipeline/overview/phases", 25_000);
  if (body) {
    return {
      phases: body.phases,
      attention: body.attention,
      attention_items: body.attention_items ?? [],
      continuity_status: body.continuity_status ?? null,
      execution: body.execution ?? null,
      operator_primary_kpi: body.operator_primary_kpi ?? null,
    };
  }
  const full = await fetchMonolithOverview(tenantId);
  const extended = full as PipelineOverview & {
    attention_items?: AttentionItem[];
    continuity_status?: ContinuityStatus | null;
  };
  return {
    phases: full.phases,
    attention: full.attention,
    attention_items: extended.attention_items ?? [],
    continuity_status: extended.continuity_status ?? null,
    execution: full.execution ?? null,
    operator_primary_kpi: full.operator_primary_kpi ?? null,
  };
}

export async function fetchPipelineIngestionSlice(tenantId: string) {
  const body = await trySlice<{
    scheduler?: PipelineOverview["scheduler"];
    runnable_connectors: string[];
    recent_ingestion_runs: PipelineOverview["recent_ingestion_runs"];
    next_scheduled_ingestion?: PipelineOverview["next_scheduled_ingestion"];
  }>(tenantId, "/cortex/pipeline/overview/ingestion", 15_000);
  if (body) return body;
  const full = await fetchMonolithOverview(tenantId);
  return {
    scheduler: full.scheduler,
    runnable_connectors: full.runnable_connectors,
    recent_ingestion_runs: full.recent_ingestion_runs,
    next_scheduled_ingestion: full.next_scheduled_ingestion,
  };
}

import { adminFetch, adminJson } from "../../lib/adminFetch";
import { adminApiPath } from "../../lib/adminApiUrl";
import { readErrorDetail } from "../../lib/canonicalApi";
import type { PipelineOverview } from "./pipelineTypes";

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
    if (res.status === 404 || res.status === 405 || res.status === 503) {
      return null;
    }
    throw new Error(await readErrorDetail(res));
  } catch {
    return null;
  }
}

export async function fetchPipelineExecutionSlice(tenantId: string) {
  const body = await trySlice<{ execution: PipelineOverview["execution"] }>(
    tenantId,
    "/cortex/pipeline/overview/execution",
    20_000,
  );
  if (body) return body.execution;
  const full = await fetchMonolithOverview(tenantId);
  return full.execution;
}

export async function fetchPipelinePhasesSlice(tenantId: string) {
  const body = await trySlice<{
    phases: PipelineOverview["phases"];
    attention: string[];
  }>(tenantId, "/cortex/pipeline/overview/phases", 30_000);
  if (body) return body;
  const full = await fetchMonolithOverview(tenantId);
  return { phases: full.phases, attention: full.attention };
}

export async function fetchPipelineIngestionSlice(tenantId: string) {
  const body = await trySlice<{
    scheduler?: PipelineOverview["scheduler"];
    runnable_connectors: string[];
    recent_ingestion_runs: PipelineOverview["recent_ingestion_runs"];
    next_scheduled_ingestion?: PipelineOverview["next_scheduled_ingestion"];
  }>(tenantId, "/cortex/pipeline/overview/ingestion", 30_000);
  if (body) return body;
  const full = await fetchMonolithOverview(tenantId);
  return {
    scheduler: full.scheduler,
    runnable_connectors: full.runnable_connectors,
    recent_ingestion_runs: full.recent_ingestion_runs,
    next_scheduled_ingestion: full.next_scheduled_ingestion,
  };
}

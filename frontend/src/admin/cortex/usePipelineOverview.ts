import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../lib/adminFetch";
import type { PipelineOverview } from "./pipelineTypes";

export const pipelineOverviewQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview", tenantId] as const;

export const pipelineOverviewExecutionQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-execution", tenantId] as const;

export const pipelineOverviewPhasesQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-phases", tenantId] as const;

export const pipelineOverviewIngestionQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-ingestion", tenantId] as const;

export const pipelineOverviewSliceQueryKeys = (tenantId: string) => [
  pipelineOverviewExecutionQueryKey(tenantId),
  pipelineOverviewPhasesQueryKey(tenantId),
  pipelineOverviewIngestionQueryKey(tenantId),
];

export type PipelineOverviewPhases = {
  tenant_id: string;
  phases: PipelineOverview["phases"];
  attention: string[];
};

export type PipelineOverviewIngestion = {
  tenant_id: string;
  scheduler?: PipelineOverview["scheduler"];
  runnable_connectors: string[];
  recent_ingestion_runs: PipelineOverview["recent_ingestion_runs"];
  next_scheduled_ingestion?: PipelineOverview["next_scheduled_ingestion"];
};

const sliceQueryOpts = {
  staleTime: 60_000,
  gcTime: 5 * 60_000,
} as const;

export function usePipelineOverviewExecution() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewExecutionQueryKey(tenantId),
    queryFn: async () => {
      const res = await adminJson<{ execution: PipelineOverview["execution"] }>(
        `/admin/tenants/${tenantId}/cortex/pipeline/overview/execution`,
      );
      return res.execution;
    },
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

export function usePipelineOverviewPhases() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewPhasesQueryKey(tenantId),
    queryFn: () =>
      adminJson<PipelineOverviewPhases>(
        `/admin/tenants/${tenantId}/cortex/pipeline/overview/phases`,
      ),
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

export function usePipelineOverviewIngestion() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewIngestionQueryKey(tenantId),
    queryFn: () =>
      adminJson<PipelineOverviewIngestion>(
        `/admin/tenants/${tenantId}/cortex/pipeline/overview/ingestion`,
      ),
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

/** Prefetch all overview slices in parallel (layout warm-up). */
export function usePrefetchPipelineOverviewSlices() {
  usePipelineOverviewExecution();
  usePipelineOverviewPhases();
  usePipelineOverviewIngestion();
}

/** Legacy monolithic overview — prefer slice hooks for the overview page. */
export function usePipelineOverview() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewQueryKey(tenantId),
    queryFn: () =>
      adminJson<PipelineOverview>(`/admin/tenants/${tenantId}/cortex/pipeline/overview`),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
  });
}

import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import type {
  AttentionItem,
  ContinuityStatus,
  OperatorPrimaryKpi,
  PipelineOverview,
} from "./pipelineTypes";
import type { PipelineExecutionSlice } from "./fetchPipelineOverviewSlice";
import {
  fetchPipelineExecutionSlice,
  fetchPipelineIngestionSlice,
  fetchPipelinePhasesSlice,
  invalidateMonolithOverviewCache,
} from "./fetchPipelineOverviewSlice";

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
  attention_items: AttentionItem[];
  continuity_status: ContinuityStatus | null;
  execution: PipelineOverview["execution"] | null;
  operator_primary_kpi: OperatorPrimaryKpi | null;
};

export type PipelineOverviewExecution = PipelineExecutionSlice & {
  tenant_id: string;
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
  retry: 1,
} as const;

export function usePipelineOverviewExecution() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewExecutionQueryKey(tenantId),
    queryFn: async () => {
      const data = await fetchPipelineExecutionSlice(tenantId);
      return { tenant_id: tenantId, ...data };
    },
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

export function usePipelineOverviewPhases() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewPhasesQueryKey(tenantId),
    queryFn: async () => {
      const data = await fetchPipelinePhasesSlice(tenantId);
      return {
        tenant_id: tenantId,
        phases: data.phases,
        attention: data.attention,
        attention_items: data.attention_items,
        continuity_status: data.continuity_status ?? null,
        execution: data.execution ?? null,
        operator_primary_kpi: data.operator_primary_kpi ?? null,
      };
    },
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

export function usePipelineOverviewIngestion() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewIngestionQueryKey(tenantId),
    queryFn: async () => {
      const data = await fetchPipelineIngestionSlice(tenantId);
      return { tenant_id: tenantId, ...data };
    },
    enabled: Boolean(tenantId),
    ...sliceQueryOpts,
  });
}

/** Prefetch all overview slices in parallel (layout warm-up). */
export function usePrefetchPipelineOverviewSlices() {
  usePipelineOverviewPhases();
  usePipelineOverviewIngestion();
}

/** Invalidate slice caches after pipeline mutations. */
export function invalidatePipelineOverviewCaches(tenantId: string) {
  invalidateMonolithOverviewCache();
  return pipelineOverviewSliceQueryKeys(tenantId);
}

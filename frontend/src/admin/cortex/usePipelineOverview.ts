import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import type {
  AttentionItem,
  ContinuityStatus,
  OperatorPrimaryKpi,
  PipelineOverview,
} from "./pipelineTypes";
import type { PipelineExecutionSlice, PipelineOverviewBootstrap } from "./fetchPipelineOverviewSlice";
import {
  fetchPipelineExecutionSlice,
  fetchPipelineIngestionSlice,
  fetchPipelineOverviewBootstrap,
  fetchPipelinePhasesSlice,
  fetchSemanticReadinessSlice,
  invalidateMonolithOverviewCache,
} from "./fetchPipelineOverviewSlice";

export const pipelineOverviewQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview", tenantId] as const;

export const pipelineOverviewBootstrapQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-bootstrap", tenantId] as const;

export const pipelineOverviewExecutionQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-execution", tenantId] as const;

export const pipelineOverviewPhasesQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-phases", tenantId] as const;

export const pipelineOverviewIngestionQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-overview-ingestion", tenantId] as const;

export const pipelineSemanticReadinessQueryKey = (tenantId: string) =>
  ["admin-cortex-pipeline-semantic-readiness", tenantId] as const;

export const pipelineOverviewSliceQueryKeys = (tenantId: string) => [
  pipelineOverviewBootstrapQueryKey(tenantId),
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
  retry: 0,
} as const;

/** Primary overview load — one request, one DB context build on the backend. */
export function usePipelineOverviewBootstrap() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineOverviewBootstrapQueryKey(tenantId),
    queryFn: () => fetchPipelineOverviewBootstrap(tenantId),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 0,
  });
}

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

/** Deferred load — semantic panel is expensive; do not block lease/phases paint. */
export function usePipelineSemanticReadiness() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: pipelineSemanticReadinessQueryKey(tenantId),
    queryFn: () => fetchSemanticReadinessSlice(tenantId),
    enabled: Boolean(tenantId),
    staleTime: 60_000,
    gcTime: 5 * 60_000,
    retry: 0,
  });
}

/** Warm overview bootstrap once per cortex layout mount. */
export function usePrefetchPipelineOverviewBootstrap() {
  usePipelineOverviewBootstrap();
}

/** Invalidate overview caches after pipeline mutations. */
export function invalidatePipelineOverviewCaches(tenantId: string) {
  invalidateMonolithOverviewCache();
  return pipelineOverviewSliceQueryKeys(tenantId);
}

export type { PipelineOverviewBootstrap };

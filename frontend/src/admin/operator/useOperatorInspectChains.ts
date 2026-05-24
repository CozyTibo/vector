import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import {
  fetchOperatorExecutionThread,
  fetchOperatorRetrievalEntries,
  fetchOperatorRetrievalEpochs,
  fetchOperatorRetrievalLineage,
  fetchOperatorSynthesisJobs,
} from "./fetchOperator";
import { isCortexAdminV2Enabled } from "./featureFlags";
import { operatorKeys } from "./operatorKeys";

const inspectQueryOpts = {
  staleTime: 60_000,
  gcTime: 5 * 60_000,
  retry: 0,
} as const;

export function useOperatorRetrievalEpochs(limit = 5) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.retrievalEpochs(tenantId),
    queryFn: () => fetchOperatorRetrievalEpochs(tenantId, limit),
    enabled: Boolean(tenantId) && isCortexAdminV2Enabled(),
    ...inspectQueryOpts,
  });
}

export function useOperatorRetrievalEntries(query: Record<string, string>, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const hasQuery = Object.values(query).some((v) => Boolean(v?.trim()));
  return useQuery({
    queryKey: operatorKeys.retrievalEntries(tenantId, query),
    queryFn: () => fetchOperatorRetrievalEntries(tenantId, query),
    enabled: Boolean(tenantId) && isCortexAdminV2Enabled() && enabled && hasQuery,
    ...inspectQueryOpts,
  });
}

export function useOperatorRetrievalLineage(kind: string, ref: string, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.retrievalLineage(tenantId, kind, ref),
    queryFn: () => fetchOperatorRetrievalLineage(tenantId, kind, ref),
    enabled: Boolean(tenantId) && isCortexAdminV2Enabled() && enabled && Boolean(kind && ref),
    ...inspectQueryOpts,
  });
}

export function useOperatorSynthesisJobs(query: Record<string, string>, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.synthesisJobs(tenantId, query),
    queryFn: () => fetchOperatorSynthesisJobs(tenantId, query),
    enabled: Boolean(tenantId) && isCortexAdminV2Enabled() && enabled,
    ...inspectQueryOpts,
  });
}

export function useOperatorExecutionThread(query: Record<string, string>, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const hasQuery = Object.values(query).some((v) => Boolean(v?.trim()));
  return useQuery({
    queryKey: operatorKeys.executionThread(tenantId, query),
    queryFn: () => fetchOperatorExecutionThread(tenantId, query),
    enabled: Boolean(tenantId) && isCortexAdminV2Enabled() && enabled && hasQuery,
    ...inspectQueryOpts,
  });
}

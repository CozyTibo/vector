import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import {
  fetchOperatorEdgeProvenance,
  fetchOperatorGraphSnapshot,
  fetchOperatorIslandsList,
} from "./fetchOperator";
import { operatorKeys } from "./operatorKeys";

const inspectQueryOpts = {
  staleTime: 60_000,
  gcTime: 5 * 60_000,
  retry: 0,
} as const;

function graphSnapshotPollInterval(data: Awaited<ReturnType<typeof fetchOperatorGraphSnapshot>> | undefined) {
  const status = data?.component_snapshot?.job_status;
  if (status === "pending" || status === "running") return 2_000;
  return false;
}

export function useOperatorGraphSnapshot() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.graphSnapshot(tenantId),
    queryFn: () => fetchOperatorGraphSnapshot(tenantId),
    enabled: Boolean(tenantId),
    ...inspectQueryOpts,
  });
}

/** Graph snapshot with polling while async component scan is in flight (R4). */
export function useOperatorGraphSnapshotPolling() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.graphSnapshot(tenantId),
    queryFn: () => fetchOperatorGraphSnapshot(tenantId),
    enabled: Boolean(tenantId),
    refetchInterval: (query) => graphSnapshotPollInterval(query.state.data),
    ...inspectQueryOpts,
  });
}

export function useOperatorEdgeProvenance(query: Record<string, string>, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const hasQuery = Object.values(query).some((v) => Boolean(v?.trim()));
  return useQuery({
    queryKey: operatorKeys.edgeProvenance(tenantId, query),
    queryFn: () => fetchOperatorEdgeProvenance(tenantId, query),
    enabled: Boolean(tenantId) && enabled && hasQuery,
    ...inspectQueryOpts,
  });
}

export function useOperatorIslandsList() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: operatorKeys.islands(tenantId),
    queryFn: () => fetchOperatorIslandsList(tenantId),
    enabled: Boolean(tenantId),
    ...inspectQueryOpts,
  });
}

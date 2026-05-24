import { useQuery } from "@tanstack/react-query";
import { useParams, useSearchParams } from "react-router-dom";

import { fetchOperatorQueues } from "./fetchOperator";
import { operatorKeys } from "./operatorKeys";
import type { OperatorQueueTab } from "./operatorTypes";

const QUEUE_TABS: Array<{ key: OperatorQueueTab; label: string }> = [
  { key: "synthesis_failed", label: "Synthesis failed" },
  { key: "tcre_queued", label: "TCRE queued" },
  { key: "deferrals", label: "Deferrals" },
  { key: "ingestion_failed", label: "Ingestion failed" },
];

export function operatorQueueTabs() {
  return QUEUE_TABS;
}

export function useOperatorQueues(limit = 50) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = (searchParams.get("tab") as OperatorQueueTab | null) ?? "synthesis_failed";
  const offset = Math.max(0, Number(searchParams.get("offset") ?? "0") || 0);

  const query = useQuery({
    queryKey: [...operatorKeys.queues(tenantId, tab), offset, limit],
    queryFn: () => fetchOperatorQueues(tenantId, { tab, limit, offset }),
    enabled: Boolean(tenantId),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
    retry: 0,
  });

  function setTab(next: OperatorQueueTab) {
    setSearchParams({ tab: next, offset: "0" });
  }

  function setOffset(next: number) {
    setSearchParams({ tab, offset: String(Math.max(0, next)) });
  }

  return { ...query, tab, offset, limit, setTab, setOffset };
}

export const operatorKeys = {
  overview: (tenantId: string) => ["cortex-operator-overview", tenantId] as const,
  runtime: (tenantId: string, transitionLimit: number) =>
    ["cortex-operator-runtime", tenantId, transitionLimit] as const,
  graphSnapshot: (tenantId: string) => ["cortex-operator-inspect", tenantId, "graph-snapshot"] as const,
  edgeProvenance: (tenantId: string, query: Record<string, string>) =>
    ["cortex-operator-inspect", tenantId, "edges", query] as const,
  islands: (tenantId: string) => ["cortex-operator-inspect", tenantId, "islands"] as const,
  queues: (tenantId: string, tab: string) => ["cortex-operator-queues", tenantId, tab] as const,
};

export function invalidateOperatorOverviewKey(tenantId: string) {
  return operatorKeys.overview(tenantId);
}

export function invalidateOperatorRuntimePrefix(tenantId: string) {
  return ["cortex-operator-runtime", tenantId] as const;
}

export function invalidateOperatorInspectPrefix(tenantId: string) {
  return ["cortex-operator-inspect", tenantId] as const;
}

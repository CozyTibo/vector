export const operatorKeys = {
  overview: (tenantId: string) => ["cortex-operator-overview", tenantId] as const,
  runtime: (tenantId: string, transitionLimit: number) =>
    ["cortex-operator-runtime", tenantId, transitionLimit] as const,
  queues: (tenantId: string, tab: string) => ["cortex-operator-queues", tenantId, tab] as const,
};

export function invalidateOperatorOverviewKey(tenantId: string) {
  return operatorKeys.overview(tenantId);
}

export function invalidateOperatorRuntimePrefix(tenantId: string) {
  return ["cortex-operator-runtime", tenantId] as const;
}

export const operatorKeys = {
  overview: (tenantId: string) => ["cortex-operator-overview", tenantId] as const,
  runtime: (tenantId: string, offset: number) => ["cortex-operator-runtime", tenantId, offset] as const,
  queues: (tenantId: string, tab: string) => ["cortex-operator-queues", tenantId, tab] as const,
};

export function invalidateOperatorOverviewKey(tenantId: string) {
  return operatorKeys.overview(tenantId);
}

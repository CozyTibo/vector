import { useQuery } from "@tanstack/react-query";

import { fetchOperatorPeopleDirectory, fetchOperatorPersonProfile } from "./fetchOperator";

export function operatorPeopleDirectoryKey(tenantId: string, limit: number, offset: number) {
  return ["operator-people-directory", tenantId, limit, offset] as const;
}

export function operatorPersonProfileKey(tenantId: string, personId: string) {
  return ["operator-person-profile", tenantId, personId] as const;
}

export function useOperatorPeopleDirectory(
  tenantId: string,
  params: { limit?: number; offset?: number } = {},
) {
  const limit = params.limit ?? 100;
  const offset = params.offset ?? 0;
  return useQuery({
    queryKey: operatorPeopleDirectoryKey(tenantId, limit, offset),
    queryFn: () => fetchOperatorPeopleDirectory(tenantId, { limit, offset }),
    enabled: Boolean(tenantId),
  });
}

export function useOperatorPersonProfile(tenantId: string, personId: string | null) {
  return useQuery({
    queryKey: operatorPersonProfileKey(tenantId, personId ?? ""),
    queryFn: () => fetchOperatorPersonProfile(tenantId, personId!),
    enabled: Boolean(tenantId && personId),
  });
}

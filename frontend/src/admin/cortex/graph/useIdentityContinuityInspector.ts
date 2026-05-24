import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../../../lib/adminFetch";
import type {
  IdentityContinuityEntityInspector,
  IdentityContinuityInspectorTenant,
  IdentityContinuitySearchResult,
  IdentitySearchParams,
} from "./identityContinuityTypes";

export const identityContinuityInspectorQueryKey = (tenantId: string) =>
  ["admin-cortex-identity-continuity-inspector", tenantId] as const;

export const identityContinuitySearchQueryKey = (tenantId: string, params: IdentitySearchParams) =>
  ["admin-cortex-identity-continuity-search", tenantId, params] as const;

export const identityContinuityEntityQueryKey = (tenantId: string, entityId: string) =>
  ["admin-cortex-identity-continuity-entity", tenantId, entityId] as const;

export function useIdentityContinuityInspectorTenant(enabled = true) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: identityContinuityInspectorQueryKey(tenantId),
    queryFn: () =>
      adminJson<IdentityContinuityInspectorTenant>(
        `/admin/tenants/${tenantId}/cortex/pipeline/identity-continuity-inspector`,
      ),
    enabled: Boolean(tenantId) && enabled,
    staleTime: 60_000,
  });
}

export function useIdentityContinuitySearch(params: IdentitySearchParams, enabled: boolean) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const hasParam = Object.values(params).some((v) => Boolean(v?.trim()));
  return useQuery({
    queryKey: identityContinuitySearchQueryKey(tenantId, params),
    queryFn: () => {
      const qs = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value?.trim()) qs.set(key, value.trim());
      }
      return adminJson<IdentityContinuitySearchResult>(
        `/admin/tenants/${tenantId}/cortex/identity/continuity-inspector/search?${qs}`,
      );
    },
    enabled: Boolean(tenantId) && enabled && hasParam,
    retry: false,
  });
}

export function useIdentityContinuityEntity(entityId: string | null) {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  return useQuery({
    queryKey: identityContinuityEntityQueryKey(tenantId, entityId ?? ""),
    queryFn: () =>
      adminJson<IdentityContinuityEntityInspector>(
        `/admin/tenants/${tenantId}/cortex/identity/continuity-inspector/entities/${entityId}`,
      ),
    enabled: Boolean(tenantId && entityId),
    staleTime: 30_000,
  });
}

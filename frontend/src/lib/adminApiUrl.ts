import { getApiBase } from "./canonicalApi";

const TENANT_SCOPED_BASE_RE =
  /\/admin\/tenants\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** API origin only — strips accidental per-tenant suffixes from VITE_API_BASE_URL. */
export function normalizeApiBase(): string {
  return getApiBase().replace(/\/$/, "").replace(TENANT_SCOPED_BASE_RE, "");
}

/**
 * Build an admin API path. Accepts full `/admin/tenants/...` paths or tenant-relative
 * cortex paths such as `/cortex/pipeline/overview/execution`.
 */
export function adminApiPath(tenantId: string, path: string): string {
  let p = path.startsWith("/") ? path : `/${path}`;

  if (p.startsWith("/cortex/")) {
    return `/admin/tenants/${tenantId}${p}`;
  }
  if (p.startsWith("/overview")) {
    return `/admin/tenants/${tenantId}/cortex/pipeline${p}`;
  }
  if (!p.startsWith("/admin/")) {
    return `/admin/tenants/${tenantId}/cortex/pipeline/${p.replace(/^\//, "")}`;
  }
  return p;
}

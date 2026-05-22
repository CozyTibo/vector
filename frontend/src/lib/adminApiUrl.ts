import { getApiBase } from "./canonicalApi";

const TENANT_UUID =
  "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

const TENANT_SCOPED_BASE_RE = new RegExp(
  `/admin/tenants/${TENANT_UUID}(?:/overview)?$`,
  "i",
);

const TENANT_SCOPED_EXTRACT_RE = new RegExp(
  `/admin/tenants/(${TENANT_UUID})(?:/overview)?$`,
  "i",
);

const LEGACY_TENANT_OVERVIEW_RE = new RegExp(
  `^/admin/tenants/${TENANT_UUID}/overview$`,
  "i",
);

const TENANT_IN_PATH_RE = new RegExp(`^/admin/tenants/(${TENANT_UUID})`, "i");

/** API origin only — strips accidental per-tenant suffixes from VITE_API_BASE_URL. */
export function normalizeApiBase(): string {
  return getApiBase().replace(/\/$/, "").replace(TENANT_SCOPED_BASE_RE, "");
}

/** Tenant id embedded in a misconfigured ``VITE_API_BASE_URL`` (per-tenant base). */
export function tenantIdFromApiBase(): string | null {
  const m = getApiBase().replace(/\/$/, "").match(TENANT_SCOPED_EXTRACT_RE);
  return m ? m[1] : null;
}

function _tenantIdFromPath(path: string): string | null {
  const m = path.match(TENANT_IN_PATH_RE);
  return m ? m[1] : null;
}

/**
 * Resolve a final admin URL path (no origin). Fixes legacy ``/overview`` when the build
 * baked in a per-tenant API base (``…/admin/tenants/{id}`` + ``/overview``).
 */
export function resolveAdminRequestPath(path: string, tenantIdHint?: string): string {
  let p = path.startsWith("/") ? path : `/${path}`;
  const tid = tenantIdHint ?? _tenantIdFromPath(p) ?? tenantIdFromApiBase();

  if (tid && (p === "/overview" || LEGACY_TENANT_OVERVIEW_RE.test(p))) {
    return `/admin/tenants/${tid}/cortex/pipeline/overview`;
  }
  if (tid && p.startsWith("/overview")) {
    return `/admin/tenants/${tid}/cortex/pipeline${p}`;
  }
  return p;
}

/**
 * Build an admin API path. Accepts full `/admin/tenants/...` paths or tenant-relative
 * cortex paths such as `/cortex/pipeline/overview/execution`.
 */
export function adminApiPath(tenantId: string, path: string): string {
  let p = path.startsWith("/") ? path : `/${path}`;

  if (LEGACY_TENANT_OVERVIEW_RE.test(p)) {
    return `/admin/tenants/${tenantId}/cortex/pipeline/overview`;
  }
  if (p === "/overview") {
    return `/admin/tenants/${tenantId}/cortex/pipeline/overview`;
  }
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

/** Full URL for an admin request (origin + normalized path). */
export function resolveAdminRequestUrl(path: string, tenantIdHint?: string): string {
  const resolved = resolveAdminRequestPath(path, tenantIdHint);
  return `${normalizeApiBase()}${resolved}`;
}

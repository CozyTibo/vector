import { getApiBase } from "./canonicalApi";

const TENANT_UUID =
  "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";

/** Strip any path after ``/admin/tenants/{id}`` from a misconfigured API base. */
const TENANT_SCOPED_TAIL_RE = new RegExp(`/admin/tenants/${TENANT_UUID}.*$`, "i");

const TENANT_ID_IN_BASE_RE = new RegExp(`/admin/tenants/(${TENANT_UUID})`, "i");

const LEGACY_TENANT_OVERVIEW_RE = new RegExp(
  `^/admin/tenants/${TENANT_UUID}/overview$`,
  "i",
);

const LEGACY_CORTEX_OVERVIEW_RE = new RegExp(
  `^/admin/tenants/${TENANT_UUID}/cortex/overview`,
  "i",
);

const TENANT_IN_PATH_RE = new RegExp(`^/admin/tenants/(${TENANT_UUID})`, "i");

/** Legacy pipeline overview slices only — must not match ``/execution-surfaces/...``. */
const OVERVIEW_SLICE_SUFFIX_RE =
  /^\/(?:phases|ingestion)(?:\/|$)|^\/execution\/(?!surfaces)(?:\/|$)/;

function rewriteCortexOverviewPath(path: string): string {
  if (path === "/cortex/overview" || path.startsWith("/cortex/overview/")) {
    return path.replace("/cortex/overview", "/cortex/pipeline/overview");
  }
  if (LEGACY_CORTEX_OVERVIEW_RE.test(path)) {
    return path.replace("/cortex/overview", "/cortex/pipeline/overview");
  }
  return path;
}

/** API origin only — strips accidental per-tenant suffixes from VITE_API_BASE_URL. */
export function normalizeApiBase(): string {
  return getApiBase().replace(/\/$/, "").replace(TENANT_SCOPED_TAIL_RE, "");
}

/** Tenant id embedded in a misconfigured ``VITE_API_BASE_URL`` (per-tenant base). */
export function tenantIdFromApiBase(): string | null {
  const m = getApiBase().replace(/\/$/, "").match(TENANT_ID_IN_BASE_RE);
  return m ? m[1] : null;
}

function _tenantIdFromPath(path: string): string | null {
  const m = path.match(TENANT_IN_PATH_RE);
  return m ? m[1] : null;
}

/**
 * Resolve a final admin URL path (no origin). Fixes legacy ``/overview`` when the build
 * baked in a per-tenant API base (``…/admin/tenants/{id}/cortex/overview`` + ``/phases``).
 */
export function resolveAdminRequestPath(path: string, tenantIdHint?: string): string {
  let p = path.startsWith("/") ? path : `/${path}`;
  p = rewriteCortexOverviewPath(p);
  const tid = tenantIdHint ?? _tenantIdFromPath(p) ?? tenantIdFromApiBase();

  if (tid && OVERVIEW_SLICE_SUFFIX_RE.test(p)) {
    return `/admin/tenants/${tid}/cortex/pipeline/overview${p}`;
  }
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
  p = rewriteCortexOverviewPath(p);

  if (LEGACY_TENANT_OVERVIEW_RE.test(p)) {
    return `/admin/tenants/${tenantId}/cortex/pipeline/overview`;
  }
  if (p === "/overview") {
    return `/admin/tenants/${tenantId}/cortex/pipeline/overview`;
  }
  if (OVERVIEW_SLICE_SUFFIX_RE.test(p)) {
    return `/admin/tenants/${tenantId}/cortex/pipeline/overview${p}`;
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

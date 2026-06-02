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

/** API resource present (``…/execution-surfaces/overview``, not SPA ``…/execution-surfaces?tab=``). */
const EXECUTION_SURFACES_PATH_RE = /\/cortex\/execution-surfaces\/[a-z]+/i;

/** SPA route mistaken for an API path when ``?tab=`` is used without a resource segment. */
const EXECUTION_SURFACES_SPA_ROUTE_RE = new RegExp(
  `^/admin/tenants/(${TENANT_UUID})/cortex/execution-surfaces/?$`,
  "i",
);

/** Broken URL produced when a misconfigured API base strips ``/tenants/{id}/cortex/execution-``. */
const MALFORMED_ADMIN_SURFACES_RE = /^\/admin\/surfaces\/(.*)$/i;

const BARE_SURFACES_SUFFIX_RE = /^\/surfaces(?:\/|$)/;

function resolveExecutionSurfacesSpaPath(path: string, tenantIdHint?: string): string {
  const qIndex = path.indexOf("?");
  const pathOnly = qIndex >= 0 ? path.slice(0, qIndex) : path;
  if (!EXECUTION_SURFACES_SPA_ROUTE_RE.test(pathOnly)) {
    return path;
  }
  const tid = tenantIdHint ?? _tenantIdFromPath(pathOnly) ?? tenantIdFromApiBase();
  if (!tid) {
    return path;
  }
  const qs = new URLSearchParams(qIndex >= 0 ? path.slice(qIndex + 1) : "");
  const tab = qs.get("tab") ?? "overview";
  qs.delete("tab");
  qs.delete("domain_id");
  qs.delete("person_id");
  qs.delete("artifact_id");

  const resource =
    tab === "domains" || tab === "people" || tab === "work" || tab === "activity"
      ? tab
      : "overview";
  const apiQs = new URLSearchParams();
  if (resource === "domains") {
    for (const key of ["sort", "lifecycle", "limit"] as const) {
      const value = qs.get(key);
      if (value) apiQs.set(key, value);
    }
  } else if (resource === "activity") {
    for (const key of ["hours", "entity_type", "entity_id", "limit"] as const) {
      const value = qs.get(key);
      if (value) apiQs.set(key, value);
    }
  } else if (resource === "people") {
    const limit = qs.get("limit");
    if (limit) apiQs.set("limit", limit);
  } else if (resource === "work") {
    for (const key of ["entity_type", "q", "limit"] as const) {
      const value = qs.get(key);
      if (value) apiQs.set(key, value);
    }
  }
  const query = apiQs.toString();
  return `/admin/tenants/${tid}/cortex/execution-surfaces/${resource}${query ? `?${query}` : ""}`;
}

function repairMalformedExecutionSurfacesPath(path: string, tenantIdHint?: string): string {
  const malformed = path.match(MALFORMED_ADMIN_SURFACES_RE);
  const bare = BARE_SURFACES_SUFFIX_RE.test(path);
  if (!malformed && !bare) {
    return path;
  }
  const tid = tenantIdHint ?? _tenantIdFromPath(path) ?? tenantIdFromApiBase();
  if (!tid) {
    return path;
  }
  const suffix = malformed
    ? malformed[1]
    : path.replace(/^\//, "").replace(/^surfaces\//, "");
  return `/admin/tenants/${tid}/cortex/execution-surfaces/${suffix}`;
}

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
  let base = getApiBase().replace(/\/$/, "").replace(TENANT_SCOPED_TAIL_RE, "");
  // Misconfigured bases sometimes end at ``/admin`` without a tenant id.
  if (base.endsWith("/admin") && !TENANT_ID_IN_BASE_RE.test(base)) {
    base = base.slice(0, -"/admin".length);
  }
  return base;
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
  p = repairMalformedExecutionSurfacesPath(p, tenantIdHint);
  p = resolveExecutionSurfacesSpaPath(p, tenantIdHint);
  if (EXECUTION_SURFACES_PATH_RE.test(p)) {
    return p;
  }
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
export function executionSurfacesAdminPath(
  tenantId: string,
  resource: string,
  query?: URLSearchParams | string,
): string {
  const qs =
    query === undefined ? "" : typeof query === "string" ? query.replace(/^\?/, "") : query.toString();
  return `/admin/tenants/${tenantId}/cortex/execution-surfaces/${resource}${qs ? `?${qs}` : ""}`;
}

export function adminApiPath(tenantId: string, path: string): string {
  let p = path.startsWith("/") ? path : `/${path}`;
  p = rewriteCortexOverviewPath(p);

  if (p.startsWith("/execution-surfaces/") || p === "/execution-surfaces") {
    return `/admin/tenants/${tenantId}/cortex${p.startsWith("/") ? p : `/${p}`}`;
  }

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

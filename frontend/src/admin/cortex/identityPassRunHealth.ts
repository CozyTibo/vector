import type { IdentityReadiness } from "../cortexAdminTypes";

/** Alert when scheduled identity passes have not started within this window. */
export const IDENTITY_PASS_STALE_MS = 10 * 60 * 1000;

export function isIdentityPassRunStale(readiness: IdentityReadiness | undefined): boolean {
  if (!readiness?.scheduler?.enabled) {
    return false;
  }
  const startedAt = readiness.latest_pass_run?.started_at;
  if (!startedAt) {
    return true;
  }
  const startedMs = new Date(startedAt).getTime();
  if (Number.isNaN(startedMs)) {
    return true;
  }
  return Date.now() - startedMs > IDENTITY_PASS_STALE_MS;
}

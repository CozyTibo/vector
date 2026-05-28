import type { CanonReadiness, CortexIngestionOverview, IdentityReadiness } from "../cortexAdminTypes";

/** Alert when scheduled passes have not started within this window. */
export const PASS_RUN_STALE_MS = 10 * 60 * 1000;

export type LatestPassRunLike = {
  started_at: string;
} | null;

export function isPassRunStale(
  latestRun: LatestPassRunLike | undefined,
  schedulerEnabled: boolean,
  staleMs: number = PASS_RUN_STALE_MS,
): boolean {
  if (!schedulerEnabled) {
    return false;
  }
  const startedAt = latestRun?.started_at;
  if (!startedAt) {
    return true;
  }
  const startedMs = new Date(startedAt).getTime();
  if (Number.isNaN(startedMs)) {
    return true;
  }
  return Date.now() - startedMs > staleMs;
}

/** Tab STALE badge: no pass started in 10m, or backend lane/orchestrator unhealthy. */
export function isIdentityPassRunStale(readiness: IdentityReadiness | undefined): boolean {
  const passRunStale = isPassRunStale(
    readiness?.latest_pass_run ?? null,
    readiness?.scheduler?.enabled ?? false,
  );
  const laneStale = readiness?.scheduler?.lane_stale === true;
  return passRunStale || laneStale;
}

export function isCanonPassRunStale(readiness: CanonReadiness | undefined): boolean {
  const latest = readiness?.latest_pass_run;
  const typed =
    latest && typeof latest === "object" && typeof latest.started_at === "string"
      ? { started_at: latest.started_at }
      : null;
  const passRunStale = isPassRunStale(typed, readiness?.scheduler?.enabled ?? false);
  const laneStale = readiness?.scheduler?.lane_stale === true;
  return passRunStale || laneStale;
}

export function isIngestionSchedulerActive(overview: CortexIngestionOverview | undefined): boolean {
  const sched = overview?.global_scheduler;
  if (!sched) {
    return false;
  }
  return sched.env_scheduler_enabled && !sched.paused_via_redis;
}

export function latestIngestionRunStartedAt(overview: CortexIngestionOverview | undefined): string | null {
  let best: string | null = null;
  let bestMs = 0;
  for (const row of overview?.connectors ?? []) {
    const started = row.latest_run?.started_at;
    if (!started) {
      continue;
    }
    const ms = new Date(started).getTime();
    if (Number.isNaN(ms) || ms <= bestMs) {
      continue;
    }
    bestMs = ms;
    best = started;
  }
  return best;
}

export function isIngestionPassRunStale(overview: CortexIngestionOverview | undefined): boolean {
  const latest = latestIngestionRunStartedAt(overview);
  return isPassRunStale(latest ? { started_at: latest } : null, isIngestionSchedulerActive(overview));
}

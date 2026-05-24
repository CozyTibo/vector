/** Feature flags for cortex operator admin v2 rollout (R0 dark launch). */

export function isCortexAdminV2Enabled(): boolean {
  return import.meta.env.VITE_CORTEX_ADMIN_V2 === "true";
}

export function frontendGitSha(): string | null {
  const sha = import.meta.env.VITE_GIT_SHA?.trim();
  return sha || null;
}

export function frontendGitShaShort(): string | null {
  const sha = frontendGitSha();
  return sha ? sha.slice(0, 7) : null;
}

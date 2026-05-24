/** Frontend build identity for deploy footer. */

export function frontendGitSha(): string | null {
  const sha = import.meta.env.VITE_GIT_SHA?.trim();
  return sha || null;
}

export function frontendGitShaShort(): string | null {
  const sha = frontendGitSha();
  return sha ? sha.slice(0, 7) : null;
}

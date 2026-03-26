/**
 * Decode GitHub v1 external_key strings for debug display (no API calls).
 * Format: `{connection_uuid}:repo:{id}` | `:pr:` | `:issue:` | `:commit:` | `:user:`
 */

export type DecodedExternalKey = {
  headline: string;
  lines: string[];
};

export function decodeGithubExternalKey(externalKey: string): DecodedExternalKey | null {
  const parts = externalKey.split(":");
  if (parts.length < 3) {
    return null;
  }
  const kind = parts[1];
  if (kind === "repo") {
    const repoId = parts[2] ?? "";
    return {
      headline: "GitHub repository",
      lines: [`Repo (GitHub ID): ${repoId}`],
    };
  }
  if (kind === "pr") {
    const repoId = parts[2] ?? "";
    const num = parts[3] ?? "";
    return {
      headline: "GitHub pull request",
      lines: [`Repo (GitHub ID): ${repoId}`, `#${num}`],
    };
  }
  if (kind === "issue") {
    const repoId = parts[2] ?? "";
    const num = parts[3] ?? "";
    return {
      headline: "GitHub issue",
      lines: [`Repo (GitHub ID): ${repoId}`, `#${num}`],
    };
  }
  if (kind === "commit") {
    const repoId = parts[2] ?? "";
    const sha = parts[3] ?? "";
    const short = sha.length >= 7 ? sha.slice(0, 7) : sha;
    return {
      headline: "GitHub commit",
      lines: [`Repo (GitHub ID): ${repoId}`, `SHA: ${short}`],
    };
  }
  if (kind === "user") {
    const gh = parts[2] ?? "";
    return {
      headline: "GitHub user",
      lines: [`GitHub user ID: ${gh}`],
    };
  }
  return {
    headline: "External key",
    lines: ["Unrecognized pattern — see raw key below."],
  };
}

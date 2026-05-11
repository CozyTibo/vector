import type { SlackCollaboratorMember } from "./onboardingApi";

/** Product workspace route for manager / Vector user access (formerly “Teams”). */
export const WORKSPACE_ACCESS_LIST_PATH = "/app/access";

export function workspaceAccessGroupPath(teamId: string): string {
  return `${WORKSPACE_ACCESS_LIST_PATH}/${teamId}`;
}

export type VectorManagerAccessMode = "company_wide" | "dedicated_users";

export function managerAccessModeFromAnswers(answers: Record<string, unknown>): VectorManagerAccessMode {
  const raw = answers.vector_manager_access_mode;
  if (raw === "company_wide" || raw === "dedicated_users") {
    return raw;
  }
  return "dedicated_users";
}

/** Slack people with full-workspace access when answers.vector_manager_access_mode is company_wide. */
export function companyWideFullAccessMembersFromAnswers(
  answers: Record<string, unknown>,
): SlackCollaboratorMember[] {
  const raw = answers.vector_company_wide_users;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return [];
  }
  const members = (raw as { members?: unknown }).members;
  if (!Array.isArray(members)) {
    return [];
  }
  const out: SlackCollaboratorMember[] = [];
  const seen = new Set<string>();
  for (const m of members) {
    if (!m || typeof m !== "object" || Array.isArray(m)) {
      continue;
    }
    const row = m as Record<string, unknown>;
    const uid = row.slack_user_id;
    if (typeof uid !== "string" || !uid.trim()) {
      continue;
    }
    const id = uid.trim();
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    const un = row.username;
    const username = typeof un === "string" && un.trim() ? un.trim().replace(/^@/, "") : id;
    const lab = row.label;
    const label = typeof lab === "string" && lab.trim() ? lab.trim() : username;
    out.push({ slack_user_id: id, username, label });
  }
  return out;
}

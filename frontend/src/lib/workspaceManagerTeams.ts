import type { SlackCollaboratorMember } from "./onboardingApi";
import { companyWideFullAccessMembersFromAnswers, managerAccessModeFromAnswers } from "./workspaceAccess";

export type ManagerAccessScope = "all" | "scoped";

export type ManagerTeam = {
  id: string;
  name: string;
  members: SlackCollaboratorMember[];
  /** Slack user id; must be one of `members` when set. */
  manager_slack_user_id: string | null;
  /** `all` = full workspace context for this manager only; `scoped` = manager plus explicit people in scope. */
  access_scope: ManagerAccessScope;
};

function parseAccessScope(raw: unknown): ManagerAccessScope {
  return raw === "all" ? "all" : "scoped";
}

/** Renders manager first when set, then the rest in their existing order. */
export function membersOrderedWithManagerFirst(team: ManagerTeam): SlackCollaboratorMember[] {
  const mgrId = team.manager_slack_user_id;
  if (!mgrId) {
    return team.members;
  }
  const manager = team.members.find((m) => m.slack_user_id === mgrId);
  if (!manager) {
    return team.members;
  }
  const others = team.members.filter((m) => m.slack_user_id !== mgrId);
  return [manager, ...others];
}

function mapPersistedTeam(t: Record<string, unknown>): ManagerTeam {
  const members = Array.isArray(t.members) ? (t.members as SlackCollaboratorMember[]) : [];
  const ids = new Set(members.map((m) => m.slack_user_id));
  const rawMgr = t.manager_slack_user_id;
  const mgr =
    typeof rawMgr === "string" && rawMgr.trim() && ids.has(rawMgr.trim()) ? rawMgr.trim() : null;
  return {
    id: String(t.id),
    name: String(t.name || "Team"),
    members,
    manager_slack_user_id: mgr,
    access_scope: parseAccessScope(t.access_scope),
  };
}

function companyWideMembersAsManagerRows(members: SlackCollaboratorMember[]): ManagerTeam[] {
  return members.map((m) => ({
    id: crypto.randomUUID(),
    name: m.label.trim() || m.username || "Manager",
    members: [m],
    manager_slack_user_id: m.slack_user_id,
    access_scope: "all" as const,
  }));
}

/** Teams from onboarding answers: persisted `workspace_manager_teams`, else legacy company-wide roster, else Slack-derived default. */
export function defaultTeamsFromOnboarding(answers: Record<string, unknown>): ManagerTeam[] {
  const existing = answers.workspace_manager_teams as { teams?: unknown[] } | undefined;
  if (existing?.teams && Array.isArray(existing.teams)) {
    if (existing.teams.length > 0) {
      return existing.teams
        .filter((t): t is Record<string, unknown> => Boolean(t) && typeof t === "object" && !Array.isArray(t))
        .map(mapPersistedTeam);
    }
    const cw = companyWideFullAccessMembersFromAnswers(answers);
    if (cw.length > 0 && managerAccessModeFromAnswers(answers) === "company_wide") {
      return companyWideMembersAsManagerRows(cw);
    }
    return [];
  }

  const members: SlackCollaboratorMember[] = [];
  const seen = new Set<string>();

  const ss = answers.slack_stakeholders as
    | { slack_user_ids?: string[]; mention_labels?: string[] }
    | undefined;
  const ids = ss?.slack_user_ids;
  const labels = ss?.mention_labels;
  if (Array.isArray(ids)) {
    ids.forEach((uid, i) => {
      if (typeof uid !== "string" || !uid.trim() || seen.has(uid)) {
        return;
      }
      seen.add(uid);
      const lab = Array.isArray(labels) && typeof labels[i] === "string" ? labels[i]!.trim() : uid;
      const handle = lab.replace(/^@/, "").split(/\s+/)[0] ?? uid;
      members.push({
        slack_user_id: uid,
        username: handle,
        label: lab,
      });
    });
  }

  const collab = answers.slack_collaborators as { members?: SlackCollaboratorMember[] } | undefined;
  if (collab?.members && Array.isArray(collab.members)) {
    for (const m of collab.members) {
      if (!m?.slack_user_id || seen.has(m.slack_user_id)) {
        continue;
      }
      seen.add(m.slack_user_id);
      members.push({
        slack_user_id: m.slack_user_id,
        username: (m.username || m.slack_user_id).replace(/^@/, ""),
        label: m.label || m.username || m.slack_user_id,
      });
    }
  }

  if (members.length === 0) {
    return [];
  }
  return [
    {
      id: crypto.randomUUID(),
      name: "Access group",
      members,
      manager_slack_user_id: null,
      access_scope: "scoped",
    },
  ];
}

/** Shapes persisted in ``workspace_manager_teams.teams[]`` (includes ``access_scope`` for the Access UI). */
export function teamsForOnboardingApi(teams: ManagerTeam[]): Array<{
  id: string;
  name: string;
  members: SlackCollaboratorMember[];
  manager_slack_user_id: string | null;
  access_scope: ManagerAccessScope;
}> {
  return teams.map((t) => {
    const mgr = t.manager_slack_user_id;
    let members = t.members;
    if (t.access_scope === "all" && mgr) {
      const row = t.members.find((m) => m.slack_user_id === mgr);
      members = row ? [row] : [];
    }
    const mgrRow = mgr ? members.find((m) => m.slack_user_id === mgr) : undefined;
    const name =
      t.name.trim() ||
      (mgrRow ? `${mgrRow.label.trim() || mgrRow.username} — access` : "Manager");
    return {
      id: t.id,
      name,
      members,
      manager_slack_user_id: mgr,
      access_scope: t.access_scope,
    };
  });
}

/** Legacy ``vector_manager_access_mode``: company-wide only when every row is full-workspace access. */
export function legacyVectorManagerAccessModeFromTeams(teams: ManagerTeam[]): "company_wide" | "dedicated_users" {
  if (teams.length === 0) {
    return "dedicated_users";
  }
  return teams.every((t) => t.access_scope === "all") ? "company_wide" : "dedicated_users";
}

/** Legacy ``vector_company_wide_users`` — union of managers on all-access rows; empty when any row is scoped. */
export function legacyVectorCompanyWideUsersFromTeams(teams: ManagerTeam[]): { members: SlackCollaboratorMember[] } {
  if (!teams.length || !teams.every((t) => t.access_scope === "all")) {
    return { members: [] };
  }
  const byId = new Map<string, SlackCollaboratorMember>();
  for (const t of teams) {
    const mgr = t.manager_slack_user_id;
    const row = mgr ? t.members.find((m) => m.slack_user_id === mgr) : undefined;
    if (row) {
      byId.set(row.slack_user_id, row);
    }
  }
  return { members: [...byId.values()] };
}

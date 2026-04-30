import type { SlackCollaboratorMember } from "./onboardingApi";

export type ManagerTeam = {
  id: string;
  name: string;
  members: SlackCollaboratorMember[];
  /** Slack user id; must be one of `members` when set. */
  manager_slack_user_id: string | null;
};

/** Teams from onboarding answers: persisted `workspace_manager_teams`, else Slack-derived default. */
export function defaultTeamsFromOnboarding(answers: Record<string, unknown>): ManagerTeam[] {
  const existing = answers.workspace_manager_teams as { teams?: ManagerTeam[] } | undefined;
  /** Persisted workspace teams (including `[]` after removing every team). Must not fall through to Slack-derived default. */
  if (existing?.teams && Array.isArray(existing.teams)) {
    return existing.teams.map((t) => {
      const members = Array.isArray(t.members) ? (t.members as SlackCollaboratorMember[]) : [];
      const ids = new Set(members.map((m) => m.slack_user_id));
      const rawMgr = (t as { manager_slack_user_id?: unknown }).manager_slack_user_id;
      const mgr =
        typeof rawMgr === "string" && rawMgr.trim() && ids.has(rawMgr.trim()) ? rawMgr.trim() : null;
      return {
        id: String(t.id),
        name: String(t.name || "Team"),
        members,
        manager_slack_user_id: mgr,
      };
    });
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
      name: "Managers",
      members,
      manager_slack_user_id: null,
    },
  ];
}

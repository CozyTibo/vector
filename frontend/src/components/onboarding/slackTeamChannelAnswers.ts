import type { SlackCollaboratorMember } from "../../lib/onboardingApi";

function isCollaboratorRow(x: unknown): x is SlackCollaboratorMember {
  if (!x || typeof x !== "object" || Array.isArray(x)) {
    return false;
  }
  const o = x as Record<string, unknown>;
  return (
    typeof o.slack_user_id === "string" &&
    o.slack_user_id.trim().length > 0 &&
    typeof o.username === "string" &&
    typeof o.label === "string"
  );
}

/** Parsed ``answers.slack_team_members.members``. */
export function slackTeamMembersFromAnswers(answers: Record<string, unknown>): SlackCollaboratorMember[] {
  const raw = answers.slack_team_members;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return [];
  }
  const members = (raw as { members?: unknown }).members;
  if (!Array.isArray(members)) {
    return [];
  }
  const seen = new Set<string>();
  const out: SlackCollaboratorMember[] = [];
  for (const m of members) {
    if (!isCollaboratorRow(m)) {
      continue;
    }
    const id = m.slack_user_id.trim();
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    out.push({
      slack_user_id: id,
      username: m.username.trim().replace(/^@/, ""),
      label: m.label.trim() || m.username.trim().replace(/^@/, ""),
    });
  }
  return out;
}

export type SlackWatchChannelRow = {
  channel_id: string;
  name: string;
};

function isChannelRow(x: unknown): x is SlackWatchChannelRow {
  if (!x || typeof x !== "object" || Array.isArray(x)) {
    return false;
  }
  const o = x as Record<string, unknown>;
  return typeof o.channel_id === "string" && o.channel_id.trim().length > 0 && typeof o.name === "string";
}

/** Parsed ``answers.slack_watch_channels.channels``. */
export function slackWatchChannelsFromAnswers(answers: Record<string, unknown>): SlackWatchChannelRow[] {
  const raw = answers.slack_watch_channels;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return [];
  }
  const channels = (raw as { channels?: unknown }).channels;
  if (!Array.isArray(channels)) {
    return [];
  }
  const seen = new Set<string>();
  const out: SlackWatchChannelRow[] = [];
  for (const c of channels) {
    if (!isChannelRow(c)) {
      continue;
    }
    const id = c.channel_id.trim();
    if (seen.has(id)) {
      continue;
    }
    seen.add(id);
    out.push({
      channel_id: id,
      name: c.name.trim().replace(/^#/, "") || id,
    });
  }
  return out;
}

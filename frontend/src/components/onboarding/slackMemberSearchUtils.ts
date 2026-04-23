import type { SlackWorkspaceMember } from "../../lib/onboardingApi";

const SLACKBOT_USER_ID = "USLACKBOT";

export function rosterWithoutSlackbot(members: SlackWorkspaceMember[]): SlackWorkspaceMember[] {
  return members.filter((m) => m.id !== SLACKBOT_USER_ID);
}

export function filterSlackMembersByQuery(
  roster: SlackWorkspaceMember[],
  query: string,
): SlackWorkspaceMember[] {
  const q = query.trim().toLowerCase();
  const base = q
    ? roster.filter(
        (m) =>
          m.username.toLowerCase().includes(q) ||
          m.label.toLowerCase().includes(q) ||
          m.id.toLowerCase().includes(q),
      )
    : roster;
  return base.slice(0, 12);
}

/** Display name (fallback: @login) for list rows and chips. */
export function slackMemberPickerPrimary(m: SlackWorkspaceMember): string {
  const t = m.label.trim();
  if (t) {
    return t;
  }
  return `@${m.username}`;
}

/** Slack @login when it adds context beyond the primary line. */
export function slackMemberPickerSecondary(m: SlackWorkspaceMember): string | null {
  const t = m.label.trim();
  if (!t || t.toLowerCase() === m.username.toLowerCase()) {
    return null;
  }
  return `@${m.username}`;
}

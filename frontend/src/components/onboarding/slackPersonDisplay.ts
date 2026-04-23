import type { SlackCollaboratorMember } from "../../lib/onboardingApi";

/** Slack login without a leading @. */
export function slackLoginNoAt(username: string): string {
  return username.trim().replace(/^@/, "");
}

/**
 * One-line Slack person text for chips and summaries: ``@login`` when the label is empty or matches
 * the login; otherwise ``Display name · @login`` (same pattern everywhere).
 */
export function slackPersonChipText(member: Pick<SlackCollaboratorMember, "username" | "label">): string {
  const login = slackLoginNoAt(member.username);
  const display = member.label.trim().replace(/^@/, "") || login;
  if (!display || display.toLowerCase() === login.toLowerCase()) {
    return `@${login}`;
  }
  return `${display} · @${login}`;
}

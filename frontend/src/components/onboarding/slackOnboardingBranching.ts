import type { SlackCollaboratorMember } from "../../lib/onboardingApi";
import { slackCollaboratorsFromAnswers } from "./slackCollaboratorsAnswers";

/** Slack user id chosen at stakeholder self-identify (``slack_stakeholders``). */
export function stakeholderSlackUserId(answers: Record<string, unknown>): string | null {
  const ss = answers.slack_stakeholders;
  if (!ss || typeof ss !== "object" || Array.isArray(ss)) {
    return null;
  }
  const ids = (ss as { slack_user_ids?: unknown }).slack_user_ids;
  if (!Array.isArray(ids) || typeof ids[0] !== "string" || !ids[0]!.trim()) {
    return null;
  }
  return ids[0]!.trim();
}

/** True when the onboardee included their own Slack account in the collaborators list. */
export function collaboratorsIncludesStakeholderSelf(answers: Record<string, unknown>): boolean {
  const self = stakeholderSlackUserId(answers);
  if (!self) {
    return false;
  }
  return slackCollaboratorsFromAnswers(answers).some((m) => m.slack_user_id === self);
}

/** Collaborators excluding the stakeholder Slack user (``other managers`` for wrap-up consent). */
export function otherSlackCollaboratorsExcludingStakeholder(
  answers: Record<string, unknown>,
): SlackCollaboratorMember[] {
  const self = stakeholderSlackUserId(answers);
  const all = slackCollaboratorsFromAnswers(answers);
  if (!self) {
    return all;
  }
  return all.filter((m) => m.slack_user_id !== self);
}

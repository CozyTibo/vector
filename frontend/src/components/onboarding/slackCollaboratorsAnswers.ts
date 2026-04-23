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

/** Parsed ``answers.slack_collaborators.members`` (deduped by ``slack_user_id``). */
export function slackCollaboratorsFromAnswers(answers: Record<string, unknown>): SlackCollaboratorMember[] {
  const raw = answers.slack_collaborators;
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

/** Seed one row from ``slack_stakeholders`` when collaborators are not stored yet. */
export function seedCollaboratorsFromStakeholders(answers: Record<string, unknown>): SlackCollaboratorMember[] {
  const ss = answers.slack_stakeholders;
  if (!ss || typeof ss !== "object" || Array.isArray(ss)) {
    return [];
  }
  const ids = (ss as { slack_user_ids?: unknown }).slack_user_ids;
  if (!Array.isArray(ids) || ids.length === 0 || typeof ids[0] !== "string") {
    return [];
  }
  const uid = ids[0]!.trim();
  const labels = (ss as { mention_labels?: unknown }).mention_labels;
  const rawText = (ss as { raw_text?: unknown }).raw_text;
  let username = uid;
  if (typeof rawText === "string") {
    const rt = rawText.trim();
    if (rt.startsWith("@")) {
      username = rt.slice(1);
    } else if (rt.length > 0) {
      username = rt;
    }
  }
  const label0 =
    Array.isArray(labels) && typeof labels[0] === "string" && labels[0]!.trim()
      ? labels[0]!.trim()
      : username;
  return [{ slack_user_id: uid, username, label: label0 }];
}

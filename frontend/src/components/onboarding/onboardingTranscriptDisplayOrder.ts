import { ONBOARDING_WRAP_UP_THANKS } from "./onboardingWrapUpCopy";
import { ONB_SLACK_HANDOFF_EVENT_ID } from "./slackHandoffCopy";
import type { ChatMessage } from "./types";

/** Parse ``type`` from a user message that stores structured JSON in ``content``. */
export function tryParseUserStructuredJsonType(content: string): string | null {
  const t = content.trim();
  if (!t.startsWith("{")) {
    return null;
  }
  try {
    const o = JSON.parse(t) as { type?: unknown };
    return typeof o.type === "string" ? o.type : null;
  } catch {
    return null;
  }
}

/** Same display line as product PATCH stakeholder user row (``raw_text`` preferred; else @labels). */
export function stakeholderAnswerDisplayLineFromAnswers(answers: Record<string, unknown>): string | null {
  const ss = answers.slack_stakeholders;
  if (!ss || typeof ss !== "object" || Array.isArray(ss)) {
    return null;
  }
  const o = ss as Record<string, unknown>;
  const raw = o.raw_text;
  if (typeof raw === "string" && raw.trim()) {
    return raw.trim();
  }
  const labels = o.mention_labels;
  if (Array.isArray(labels) && labels.length > 0) {
    const parts = labels
      .filter((x): x is string => typeof x === "string" && x.trim().length > 0)
      .map((l) => {
        const s = l.trim();
        return s.startsWith("@") ? s : `@${s}`;
      });
    return parts.length > 0 ? parts.join(" ") : null;
  }
  return null;
}

const B_STAKEHOLDER = 100;
const B_COLLAB = 200;
const B_TEAM = 300;
const B_CHANNELS = 350;
const B_WRAP = 400;
const B_CONSENT = 450;

function displayBucket(msg: ChatMessage, answers: Record<string, unknown>): number {
  if (msg.role === "event" && msg.id === ONB_SLACK_HANDOFF_EVENT_ID) {
    return B_STAKEHOLDER;
  }
  if (msg.role === "user") {
    const t = tryParseUserStructuredJsonType(msg.content);
    if (t === "slack_collaborators_selected") {
      return B_COLLAB;
    }
    if (t === "slack_team_members_selected") {
      return B_TEAM;
    }
    if (t === "slack_watch_channels_selected") {
      return B_CHANNELS;
    }
    if (t === "slack_manager_intro_consent") {
      return B_CONSENT;
    }
    const line = stakeholderAnswerDisplayLineFromAnswers(answers);
    if (line !== null && msg.content.trim() === line.trim()) {
      return B_STAKEHOLDER;
    }
    return 0;
  }
  if (msg.role === "vector") {
    const id = msg.id ?? "";
    if (id === "onb-handoff-intro-a" || id === "onb-handoff-intro-b") {
      return B_STAKEHOLDER;
    }
    if (id === "onb-collab-intro-1" || id === "onb-collab-confirm-1") {
      return B_COLLAB;
    }
    if (id === "onb-team-pick-1" || id === "onb-team-confirm-1") {
      return B_TEAM;
    }
    if (id === "onb-ch-pick-1" || id === "onb-ch-confirm-1") {
      return B_CHANNELS;
    }
    if (
      id === "onb-wrap-up-thanks" ||
      id === "admin-synth-wrap-thanks" ||
      msg.content.trim() === ONBOARDING_WRAP_UP_THANKS
    ) {
      return B_WRAP;
    }
    if (
      id === "onb-wrap-up-manager-ask" ||
      id === "admin-synth-wrap-manager-ask" ||
      msg.content.includes("introduce myself in Slack to the managers")
    ) {
      return B_WRAP;
    }
    return 0;
  }
  return 0;
}

function displaySubOrder(msg: ChatMessage, bucket: number, answers: Record<string, unknown>): number {
  const id = msg.id ?? "";
  switch (bucket) {
    case B_STAKEHOLDER: {
      if (msg.role === "event" && id === ONB_SLACK_HANDOFF_EVENT_ID) {
        return 0;
      }
      if (id === "onb-handoff-intro-a") {
        return 1;
      }
      if (id === "onb-handoff-intro-b") {
        return 2;
      }
      if (msg.role === "user") {
        const line = stakeholderAnswerDisplayLineFromAnswers(answers);
        if (line !== null && msg.content.trim() === line.trim()) {
          return 10;
        }
      }
      return 50;
    }
    case B_COLLAB: {
      if (id === "onb-collab-intro-1") {
        return 0;
      }
      if (id === "onb-collab-confirm-1") {
        return 1;
      }
      if (msg.role === "user") {
        return 10;
      }
      return 50;
    }
    case B_TEAM: {
      if (id === "onb-team-pick-1") {
        return 0;
      }
      if (id === "onb-team-confirm-1") {
        return 1;
      }
      if (msg.role === "user") {
        return 10;
      }
      return 50;
    }
    case B_CHANNELS: {
      if (id === "onb-ch-pick-1") {
        return 0;
      }
      if (id === "onb-ch-confirm-1") {
        return 1;
      }
      if (msg.role === "user") {
        return 10;
      }
      return 50;
    }
    case B_WRAP: {
      if (
        id === "onb-wrap-up-thanks" ||
        id === "admin-synth-wrap-thanks" ||
        msg.content.trim() === ONBOARDING_WRAP_UP_THANKS
      ) {
        return 0;
      }
      if (
        id === "onb-wrap-up-manager-ask" ||
        id === "admin-synth-wrap-manager-ask" ||
        msg.content.includes("introduce myself in Slack to the managers")
      ) {
        return 1;
      }
      return 50;
    }
    case B_CONSENT: {
      return 0;
    }
    default:
      return 0;
  }
}

/**
 * Reorder merged onboarding transcript rows for display so Slack tail matches the intended narrative:
 * stakeholder (Slack handoff + self line) → collaborators → team → channels → wrap-up → consent.
 * Uses stable ids / JSON ``type`` / stakeholder display line; tie-breaks with original index (not timestamps).
 *
 * Only the suffix from the first Slack-narrative row (bucket ≥ stakeholder) is reordered so earlier
 * profile and connector chat stays at the top.
 */
export function reorderOnboardingTranscriptForDisplay(
  messages: ChatMessage[],
  answers: Record<string, unknown>,
): ChatMessage[] {
  const buckets = messages.map((m) => displayBucket(m, answers));
  const tailMin = buckets.findIndex((b) => b >= B_STAKEHOLDER);
  if (tailMin < 0) {
    return messages;
  }
  const prefix = messages.slice(0, tailMin);
  const suffix = messages.slice(tailMin);
  const annotated = suffix.map((m, offset) => {
    const originalIndex = tailMin + offset;
    const bucket = displayBucket(m, answers);
    return {
      m,
      originalIndex,
      bucket,
      sub: displaySubOrder(m, bucket, answers),
    };
  });
  annotated.sort((a, b) => {
    if (a.bucket !== b.bucket) {
      return a.bucket - b.bucket;
    }
    if (a.sub !== b.sub) {
      return a.sub - b.sub;
    }
    return a.originalIndex - b.originalIndex;
  });
  return [...prefix, ...annotated.map((x) => x.m)];
}

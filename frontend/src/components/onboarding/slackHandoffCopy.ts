import type { ChatMessage } from "./types";

/** Same id as historical stakeholder step so ADMIN_ACCESS transcript merge still recognizes synthetic rows. */
export const ONB_SLACK_HANDOFF_EVENT_ID = "onb-stakeholders-conn";

function transcriptAlreadyShowsCommunicationConnectLine(
  prior: ChatMessage[],
  communicationToolLabel: string,
): boolean {
  const label = communicationToolLabel.trim();
  if (!label) {
    return false;
  }
  const asEvent = `connected to ${label}`.toLowerCase();
  const asUser = `${label} connected`.toLowerCase();
  return prior.some((m) => {
    const c = (m.content ?? "").trim().toLowerCase();
    if (!c) {
      return false;
    }
    if (m.role === "event" && c === asEvent) {
      return true;
    }
    if (m.role === "user" && c === asUser) {
      return true;
    }
    return false;
  });
}

export function slackHandoffSyntheticMessages(communicationToolLabel: string, startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: ONB_SLACK_HANDOFF_EVENT_ID,
      role: "event",
      content: `Connected to ${communicationToolLabel}`,
      timestamp: t++,
    },
    {
      id: "onb-handoff-intro-a",
      role: "vector",
      content:
        "We're almost done here! I just need to identify you on Slack so we can finish the onboarding.",
      timestamp: t++,
    },
    {
      id: "onb-handoff-intro-b",
      role: "vector",
      content:
        "If we found a Slack account that matches your Vector email, confirm it below. Otherwise search for your name or @username in the list.",
      timestamp: t++,
    },
  ];
}

/**
 * Same as ``slackHandoffSyntheticMessages`` but omits the synthetic ``Connected to …`` event when the
 * transcript already has an equivalent line (persisted OAuth user line or a prior event).
 */
export function slackHandoffSyntheticMessagesDeduped(
  communicationToolLabel: string,
  startTs: number,
  priorTranscript: ChatMessage[],
): ChatMessage[] {
  const full = slackHandoffSyntheticMessages(communicationToolLabel, startTs);
  if (transcriptAlreadyShowsCommunicationConnectLine(priorTranscript, communicationToolLabel)) {
    return full.slice(1);
  }
  return full;
}

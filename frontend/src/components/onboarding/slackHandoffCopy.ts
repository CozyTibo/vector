import type { ChatMessage } from "./types";

/** Same id as historical stakeholder step so ADMIN_ACCESS transcript merge still recognizes synthetic rows. */
export const ONB_SLACK_HANDOFF_EVENT_ID = "onb-stakeholders-conn";

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
        "If we found a Slack account that matches your Vector email, confirm it below. Otherwise pick your @username from the list.",
      timestamp: t++,
    },
  ];
}

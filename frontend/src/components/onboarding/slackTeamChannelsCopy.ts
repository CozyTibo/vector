import type { ChatMessage } from "./types";

/** ``solo_manager``: only the stakeholder in the manager list; ``with_other_managers``: at least one other manager. */
export type SlackTeamMembersPickIntroVariant = "solo_manager" | "with_other_managers";

export function slackTeamMembersPickIntroMessages(
  startTs: number,
  variant: SlackTeamMembersPickIntroVariant = "with_other_managers",
): ChatMessage[] {
  let t = startTs;
  if (variant === "solo_manager") {
    return [
      {
        id: "onb-team-pick-1",
        role: "vector",
        content:
          "I'd like to know who's on your team so we can start tracking how work moves. " +
          "Right now you're the only manager listed—add teammates' Slack @handles below, or tap Continue if there's no one else to add yet.",
        timestamp: t++,
      },
    ];
  }
  return [
    {
      id: "onb-team-pick-1",
      role: "vector",
      content:
        "Since you're one of the people I'll coordinate with, I'd like to know who's on your team so we can start tracking how work moves. " +
        "Add their Slack handles below (other managers you listed are already set aside). Skip this if there's no one else to add yet.",
      timestamp: t++,
    },
  ];
}

export function slackTeamMembersConfirmIntroMessages(startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: "onb-team-confirm-1",
      role: "vector",
      content:
        "Here's the team you listed. Edit if something's off, or continue when it looks right.",
      timestamp: t++,
    },
  ];
}

export function slackWatchChannelsPickIntroMessages(startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: "onb-ch-pick-1",
      role: "vector",
      content:
        "Which Slack channels should I keep an eye on for your team? Search by name, add channels as chips, remove with ×, then tap Continue.",
      timestamp: t++,
    },
  ];
}

export function slackWatchChannelsConfirmIntroMessages(startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: "onb-ch-confirm-1",
      role: "vector",
      content:
        "Here are the channels you picked. Go back to edit, or continue when you are ready.",
      timestamp: t++,
    },
  ];
}

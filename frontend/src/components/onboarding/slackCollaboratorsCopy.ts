import type { ChatMessage } from "./types";

export function slackCollaboratorsPickIntroMessages(startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: "onb-collab-intro-1",
      role: "vector",
      content:
        "I need to know who I'll be working with in Slack. Will you work with me directly, and should I " +
        "also coordinate with other managers? Add their @handles below. You're already on the list; " +
        "remove anyone who shouldn't be listed, then tap Continue.",
      timestamp: t++,
    },
  ];
}

export function slackCollaboratorsConfirmIntroMessages(startTs: number): ChatMessage[] {
  let t = startTs;
  return [
    {
      id: "onb-collab-confirm-1",
      role: "vector",
      content:
        "Here's who you listed. Go back to edit the list, or continue when it looks right to you.",
      timestamp: t++,
    },
  ];
}

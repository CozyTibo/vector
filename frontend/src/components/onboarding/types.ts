export type ChatMessage = {
  id: string;
  /** `event` = compact timeline marker (e.g. connector connected), client-only UI. */
  role: "user" | "vector" | "event";
  content: string;
  timestamp: number;
};

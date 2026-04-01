export type ChatMessage = {
  id: string;
  role: "user" | "vector";
  content: string;
  timestamp: number;
};

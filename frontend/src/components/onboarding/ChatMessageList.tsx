import { useEffect, useRef } from "react";

import type { ChatMessage } from "./types";
import ChatMessageBubble from "./ChatMessageBubble";
import TypingIndicator from "./TypingIndicator";

type ChatMessageListProps = {
  messages: ChatMessage[];
  userDisplayName: string;
  isTyping?: boolean;
  /**
   * When true (default), scroll to the latest message when the list grows or typing starts.
   * Set false for read-only admin previews so the page does not jump on load.
   */
  autoScrollToBottom?: boolean;
};

export default function ChatMessageList({
  messages,
  userDisplayName,
  isTyping = false,
  autoScrollToBottom = true,
}: ChatMessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  /** Only auto-scroll when the thread grows or typing starts; avoid re-running on `messages` reference changes (fights trackpad scroll). */
  const prevLenRef = useRef(0);

  useEffect(() => {
    const len = messages.length;
    const grew = len > prevLenRef.current;
    prevLenRef.current = len;
    if (!autoScrollToBottom) {
      return;
    }
    if (grew || isTyping) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages.length, isTyping, autoScrollToBottom]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-contain px-1 pb-2 pt-3 sm:px-2">
        <div className="mx-auto flex w-full max-w-full flex-col">
          {messages.map((m, i) => {
            const prev = i > 0 ? messages[i - 1] : undefined;
            const isContinuation = Boolean(prev && prev.role === m.role);
            return (
              <ChatMessageBubble
                key={m.id}
                message={m}
                userDisplayName={userDisplayName}
                isContinuation={isContinuation}
              />
            );
          })}
          {isTyping ? <TypingIndicator /> : null}
          <div ref={endRef} className="h-2 w-full shrink-0" aria-hidden />
        </div>
      </div>
    </div>
  );
}

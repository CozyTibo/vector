import type { ChatMessage } from "./types";
import ChatAvatar from "./ChatAvatar";
import { landingAccentText, landingSubtleLineV } from "../landing/landingBrandPalette";
import { labelsForToolsPayload } from "./onboardingToolGroups";

type ChatMessageBubbleProps = {
  message: ChatMessage;
  userDisplayName: string;
  /** Same role as the previous message: one avatar/header group for the run. */
  isContinuation?: boolean;
};

function tryParseToolsSelectedContent(content: string): Record<string, string[]> | null {
  const t = content.trim();
  if (!t.startsWith("{")) {
    return null;
  }
  try {
    const o = JSON.parse(t) as unknown;
    if (!o || typeof o !== "object" || Array.isArray(o)) {
      return null;
    }
    const rec = o as Record<string, unknown>;
    if (rec.type !== "tools_selected") {
      return null;
    }
    const raw = rec.tools;
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
      return null;
    }
    const out: Record<string, string[]> = {};
    for (const [k, v] of Object.entries(raw)) {
      if (Array.isArray(v)) {
        out[k] = v.filter((x): x is string => typeof x === "string");
      }
    }
    return out;
  } catch {
    return null;
  }
}

function formatTime(ts: number): string {
  try {
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(ts));
  } catch {
    return "";
  }
}

export default function ChatMessageBubble({
  message,
  userDisplayName,
  isContinuation = false,
}: ChatMessageBubbleProps) {
  const isUser = message.role === "user";
  const toolsPick = isUser ? tryParseToolsSelectedContent(message.content) : null;

  if (isUser) {
    return (
      <div
        className={`onboarding-message-enter flex justify-end px-3 ${isContinuation ? "py-1" : "py-2.5"}`}
      >
        <div className="flex min-w-0 max-w-[min(100%,32rem)] flex-col items-end gap-1.5">
          {!isContinuation ? (
            <div className="flex items-baseline gap-2 text-[11px] text-zinc-500">
              <span className={`font-semibold ${landingAccentText}`}>{userDisplayName}</span>
              <time className="tabular-nums text-zinc-400" dateTime={new Date(message.timestamp).toISOString()}>
                {formatTime(message.timestamp)}
              </time>
            </div>
          ) : null}
          <div
            className={
              (isContinuation ? "rounded-2xl rounded-tr-sm " : "rounded-2xl rounded-tr-md ") +
              "border border-[#E878BE]/25 bg-gradient-to-br from-[#FDE8F4] via-[#FCE8F2] " +
              "to-[#F8D4E8] px-4 py-2.5 text-[15px] leading-relaxed text-zinc-900 shadow-[0_10px_28px_-18px_rgba(232,120,190,0.55)]"
            }
          >
            {toolsPick ? (
              <div className="flex flex-wrap justify-end gap-1.5">
                {labelsForToolsPayload(toolsPick).map((label, i) => (
                  <span
                    key={`${label}-${i}`}
                    className="inline-flex max-w-full items-center rounded-full border border-[#E878BE]/35 bg-white/90 px-2.5 py-1 text-xs font-medium text-zinc-800 shadow-sm"
                  >
                    {label}
                  </span>
                ))}
              </div>
            ) : (
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`onboarding-message-enter flex gap-3 px-3 sm:gap-3.5 ${isContinuation ? "py-1" : "py-2.5"}`}
    >
      {isContinuation ? (
        <div className="h-10 w-10 shrink-0" aria-hidden />
      ) : (
        <ChatAvatar variant="vector" />
      )}
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        {!isContinuation ? (
          <div className="flex items-baseline gap-2 text-[11px] text-zinc-500">
            <span className={`font-semibold ${landingAccentText}`}>Vector</span>
            <time className="tabular-nums text-zinc-400" dateTime={new Date(message.timestamp).toISOString()}>
              {formatTime(message.timestamp)}
            </time>
          </div>
        ) : null}
        <div className="relative inline-block max-w-[min(100%,32rem)] pl-[11px]">
          <div className={`pointer-events-none absolute bottom-1 left-0 top-1 w-[3px] rounded-full ${landingSubtleLineV}`} />
          <div
            className={
              (isContinuation
                ? "rounded-2xl rounded-tl-sm "
                : "rounded-2xl rounded-tl-md ") +
              "border border-zinc-200/85 bg-white/95 px-4 py-2.5 text-[15px] leading-relaxed " +
              "text-zinc-800 shadow-[0_12px_32px_-22px_rgba(15,23,42,0.35)] ring-1 ring-zinc-950/[0.04]"
            }
          >
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

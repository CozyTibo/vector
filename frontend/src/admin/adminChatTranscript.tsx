import ChatMessageList from "../components/onboarding/ChatMessageList";
import type { ChatMessage } from "../components/onboarding/types";

type AdminChatRow = {
  id?: string;
  role: string;
  content: string;
  created_at: string;
};

type AdminSlackDmRow = {
  id: string;
  direction: string;
  text: string;
  created_at: string | null;
  /** Slack message ``ts`` (seconds since epoch, string); preferred for ordering and display. */
  slack_ts?: string | null;
};

function normalizeOnboardingRole(role: string): "user" | "vector" | "event" {
  const x = role.trim().toLowerCase();
  if (x === "user") return "user";
  if (x === "event") return "event";
  if (x === "assistant" || x === "model" || x === "system") return "vector";
  return "vector";
}

/** Map persisted website onboarding chat rows to product chat bubbles. */
export function adminOnboardingRowsToChatMessages(rows: AdminChatRow[]): ChatMessage[] {
  // Preserve API order. The admin API sorts by (created_at, id); re-sorting here with string
  // compare on UUIDs breaks tie order vs the backend and scrambles same-second messages.
  return rows.map((r, i) => ({
    id: r.id ?? `ob-${i}-${r.created_at}`,
    role: normalizeOnboardingRole(r.role),
    content: r.content,
    timestamp: Date.parse(r.created_at) || 0,
  }));
}

function parseCreatedAtMs(created_at: string | null | undefined): number {
  if (created_at == null || !String(created_at).trim()) {
    return 0;
  }
  const t = Date.parse(created_at);
  return Number.isFinite(t) ? t : 0;
}

/** Slack ``ts`` is Unix seconds (often with a fractional part); UI expects ms. */
function slackTsToDisplayMs(slack_ts: string | null | undefined, fallbackMs: number): number {
  const raw = (slack_ts ?? "").trim();
  if (!raw) {
    return fallbackMs;
  }
  const sec = Number(raw);
  if (!Number.isFinite(sec)) {
    return fallbackMs;
  }
  return Math.round(sec * 1000);
}

/** Slack DM rows: outbound = Vector, inbound = User. */
export function adminSlackRowsToChatMessages(rows: AdminSlackDmRow[]): ChatMessage[] {
  // Preserve API order (chronological from server); client sort can scramble same-second messages.
  return rows.map((m) => {
    const fallback = parseCreatedAtMs(m.created_at);
    return {
      id: m.id,
      role: m.direction === "outbound" ? "vector" : "user",
      content: m.text,
      timestamp: slackTsToDisplayMs(m.slack_ts, fallback),
    };
  });
}

/** Renders the same chat chrome as product onboarding (Vector vs user). */
export function AdminOnboardingStyleThread({
  messages,
  userDisplayName,
  maxHeightClass = "max-h-[min(28rem,70vh)]",
}: {
  messages: ChatMessage[];
  userDisplayName: string;
  maxHeightClass?: string;
}) {
  if (messages.length === 0) {
    return (
      <p className="rounded-2xl border border-zinc-200/80 bg-zinc-50/80 px-4 py-8 text-center text-sm text-zinc-500">
        No messages yet.
      </p>
    );
  }

  return (
    <div
      className={`flex min-h-[12rem] flex-col overflow-hidden rounded-2xl border border-zinc-200/85 bg-white shadow-[0_12px_40px_-28px_rgba(15,23,42,0.25)] ring-1 ring-zinc-950/[0.04] ${maxHeightClass}`}
    >
      <ChatMessageList
        messages={messages}
        userDisplayName={userDisplayName}
        autoScrollToBottom={false}
      />
    </div>
  );
}

/** Slack-like DM chrome: neutral rail, header strip, taller default for admin. */
export function AdminSlackStyleThread({
  messages,
  managerLabel,
  maxHeightClass = "max-h-[min(44rem,85vh)]",
}: {
  messages: ChatMessage[];
  managerLabel: string;
  maxHeightClass?: string;
}) {
  if (messages.length === 0) {
    return (
      <p className="rounded-lg border border-stone-300/90 bg-[#f5f5f5] px-4 py-8 text-center text-sm text-stone-500">
        No messages in this thread yet.
      </p>
    );
  }

  return (
    <div
      className={`flex min-h-[14rem] flex-col overflow-hidden rounded-lg border border-stone-300/90 bg-[#f5f5f5] shadow-sm ${maxHeightClass}`}
    >
      <div className="shrink-0 border-b border-stone-300/80 bg-white px-4 py-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-stone-500">Direct message</p>
        <p className="text-sm font-medium text-stone-900">
          Vector <span className="text-stone-400">·</span> {managerLabel}
        </p>
      </div>
      <div className="flex min-h-0 flex-1 flex-col bg-[#f5f5f5] px-1 pt-1">
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-b-md bg-white">
          <ChatMessageList
            messages={messages}
            userDisplayName={managerLabel}
            autoScrollToBottom={false}
          />
        </div>
      </div>
    </div>
  );
}

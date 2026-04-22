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

/** Legacy rows may store JSON for structured-only user turns; map to display copy. */
function structuredOnlyUserDisplayLabel(content: string): string | null {
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
    if (rec.type === "connectors_intro_ready") {
      return "I'm ready to choose tools";
    }
    return null;
  } catch {
    return null;
  }
}

type SlackCollaboratorChip = {
  slack_user_id: string;
  username: string;
  label: string;
};

function tryParseSlackCollaboratorsSelectedContent(content: string): SlackCollaboratorChip[] | null {
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
    if (rec.type !== "slack_collaborators_selected" && rec.type !== "slack_team_members_selected") {
      return null;
    }
    const raw = rec.members;
    if (!Array.isArray(raw)) {
      return null;
    }
    const out: SlackCollaboratorChip[] = [];
    for (const m of raw) {
      if (!m || typeof m !== "object" || Array.isArray(m)) {
        continue;
      }
      const row = m as Record<string, unknown>;
      const id = row.slack_user_id;
      const un = row.username;
      const lab = row.label;
      if (typeof id !== "string" || !id.trim()) {
        continue;
      }
      const username =
        typeof un === "string" && un.trim() ? un.trim().replace(/^@/, "") : id.trim();
      const label =
        typeof lab === "string" && lab.trim() ? lab.trim() : username;
      out.push({ slack_user_id: id.trim(), username, label });
    }
    return out.length > 0 ? out : null;
  } catch {
    return null;
  }
}

type SlackWatchChannelChip = {
  channel_id: string;
  name: string;
};

function tryParseSlackWatchChannelsSelectedContent(content: string): SlackWatchChannelChip[] | null {
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
    if (rec.type !== "slack_watch_channels_selected") {
      return null;
    }
    const raw = rec.channels;
    if (!Array.isArray(raw)) {
      return null;
    }
    const out: SlackWatchChannelChip[] = [];
    for (const ch of raw) {
      if (!ch || typeof ch !== "object" || Array.isArray(ch)) {
        continue;
      }
      const row = ch as Record<string, unknown>;
      const id = row.channel_id;
      const nm = row.name;
      if (typeof id !== "string" || !id.trim()) {
        continue;
      }
      const name =
        typeof nm === "string" && nm.trim() ? nm.trim().replace(/^#/, "") : id.trim();
      out.push({ channel_id: id.trim(), name });
    }
    return out.length > 0 ? out : null;
  } catch {
    return null;
  }
}

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
    if (!Number.isFinite(ts)) {
      return "";
    }
    return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(new Date(ts));
  } catch {
    return "";
  }
}

function safeDateTimeIso(ts: number): string | undefined {
  if (!Number.isFinite(ts)) {
    return undefined;
  }
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) {
      return undefined;
    }
    return d.toISOString();
  } catch {
    return undefined;
  }
}

/** Persisted OAuth log lines use ``Linear connected``; timeline UI matches synthetic ``Connected to …`` events. */
function connectorConnectedDisplayLabel(content: string): string | null {
  const t = content.trim().toLowerCase();
  if (t === "linear connected") {
    return "Connected to Linear";
  }
  if (t === "github connected") {
    return "Connected to GitHub";
  }
  if (t === "slack connected") {
    return "Connected to Slack";
  }
  return null;
}

function OnboardingConnectorConnectedPill({ label }: { label: string }) {
  return (
    <div className="onboarding-message-enter flex justify-center px-3 py-3" role="status">
      <div
        className={
          "inline-flex max-w-[min(100%,24rem)] items-center gap-2 rounded-full border border-emerald-200/90 " +
          "bg-gradient-to-r from-emerald-50/95 to-teal-50/90 px-4 py-2 text-[13px] font-medium " +
          "leading-snug text-emerald-950 shadow-[0_8px_24px_-16px_rgba(5,150,105,0.35)]"
        }
      >
        <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.25)]" />
        <span>{label}</span>
      </div>
    </div>
  );
}

export default function ChatMessageBubble({
  message,
  userDisplayName,
  isContinuation = false,
}: ChatMessageBubbleProps) {
  if (message.role === "event") {
    return <OnboardingConnectorConnectedPill label={message.content} />;
  }

  const isUser = message.role === "user";
  const toolsPick = isUser ? tryParseToolsSelectedContent(message.content) : null;
  const collaboratorsPick = isUser ? tryParseSlackCollaboratorsSelectedContent(message.content) : null;
  const watchChannelsPick = isUser ? tryParseSlackWatchChannelsSelectedContent(message.content) : null;
  const structuredOnlyLabel =
    isUser && !toolsPick && !collaboratorsPick && !watchChannelsPick
      ? structuredOnlyUserDisplayLabel(message.content)
      : null;
  const persistedConnectorLabel =
    isUser && !toolsPick && !collaboratorsPick && !watchChannelsPick && !structuredOnlyLabel
      ? connectorConnectedDisplayLabel(message.content)
      : null;

  if (isUser) {
    if (persistedConnectorLabel) {
      return <OnboardingConnectorConnectedPill label={persistedConnectorLabel} />;
    }
    return (
      <div
        className={`onboarding-message-enter flex justify-end px-3 ${isContinuation ? "py-0.5" : "py-1.5"}`}
      >
        <div className="flex min-w-0 max-w-[min(100%,32rem)] flex-col items-end gap-1.5">
          {!isContinuation ? (
            <div className="flex items-baseline gap-2 text-[11px] text-zinc-500">
              <span className={`font-semibold ${landingAccentText}`}>{userDisplayName}</span>
              <time className="tabular-nums text-zinc-400" dateTime={safeDateTimeIso(message.timestamp)}>
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
            {collaboratorsPick ? (
              <div className="flex flex-wrap justify-end gap-1.5">
                {collaboratorsPick.map((m) => (
                  <span
                    key={m.slack_user_id}
                    className="inline-flex max-w-full items-center rounded-full border border-[#E878BE]/35 bg-white/90 px-2.5 py-1 text-xs font-medium text-zinc-800 shadow-sm"
                  >
                    @{m.username.replace(/^@/, "")}
                  </span>
                ))}
              </div>
            ) : watchChannelsPick ? (
              <div className="flex flex-wrap justify-end gap-1.5">
                {watchChannelsPick.map((c) => (
                  <span
                    key={c.channel_id}
                    className="inline-flex max-w-full items-center rounded-full border border-violet-300/60 bg-white/90 px-2.5 py-1 text-xs font-medium text-zinc-800 shadow-sm"
                  >
                    #{c.name.replace(/^#/, "")}
                  </span>
                ))}
              </div>
            ) : toolsPick ? (
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
            ) : structuredOnlyLabel ? (
              <p className="whitespace-pre-wrap break-words">{structuredOnlyLabel}</p>
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
      className={`onboarding-message-enter flex gap-3 px-3 sm:gap-3.5 ${isContinuation ? "py-0.5" : "py-1.5"}`}
    >
      {isContinuation ? (
        <div className="h-10 w-10 shrink-0" aria-hidden />
      ) : (
        <ChatAvatar variant="vector" />
      )}
      {/*
        items-start: avoid flex-col stretch making the bubble row full viewport width (broke accent
        bar height and left huge gaps). w-fit keeps the pink rail aligned to text block width.
      */}
      <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
        {!isContinuation ? (
          <div className="flex items-baseline gap-2 text-[11px] text-zinc-500">
            <span className={`font-semibold ${landingAccentText}`}>Vector</span>
              <time className="tabular-nums text-zinc-400" dateTime={safeDateTimeIso(message.timestamp)}>
              {formatTime(message.timestamp)}
            </time>
          </div>
        ) : null}
        <div className="relative w-fit max-w-[min(100%,32rem)] pl-[11px]">
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

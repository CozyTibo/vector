import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import type { ChatMessage } from "./types";
import ChatMessageList from "./ChatMessageList";
import { landingAccentText } from "../landing/landingBrandPalette";
import type { SlackWorkspaceChannel } from "../../lib/onboardingApi";
import type { SlackWatchChannelRow } from "./slackTeamChannelAnswers";

function channelToRow(ch: SlackWorkspaceChannel): SlackWatchChannelRow {
  const name = ch.name.trim().replace(/^#/, "") || ch.id;
  return { channel_id: ch.id, name };
}

function displayHashName(row: SlackWatchChannelRow): string {
  const n = row.name.trim().replace(/^#/, "") || row.channel_id;
  return `#${n}`;
}

function filterChannelsByQuery(channels: SlackWorkspaceChannel[], query: string): SlackWorkspaceChannel[] {
  const q = query.trim().toLowerCase().replace(/^#/, "");
  if (!q) {
    return channels;
  }
  return channels.filter((c) => {
    const n = c.name.trim().toLowerCase();
    return n.includes(q) || c.id.toLowerCase().includes(q);
  });
}

type SlackChannelsPickPanelProps = {
  priorChatMessages: ChatMessage[];
  introMessages: ChatMessage[];
  channels: SlackWorkspaceChannel[];
  channelsLoading: boolean;
  channelsError: string | null;
  initialChannels: SlackWatchChannelRow[];
  initialChannelsKey: string;
  submitError: string | null;
  submitting: boolean;
  onContinue: (rows: SlackWatchChannelRow[]) => void;
  userDisplayName: string;
  emptyHint: string;
};

export default function SlackChannelsPickPanel({
  priorChatMessages,
  introMessages,
  channels,
  channelsLoading,
  channelsError,
  initialChannels,
  initialChannelsKey,
  submitError,
  submitting,
  onContinue,
  userDisplayName,
  emptyHint,
}: SlackChannelsPickPanelProps) {
  const ids = useId();
  const inputId = `${ids}-ch-pick`;
  const listboxId = `${ids}-ch-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [picked, setPicked] = useState<SlackWatchChannelRow[]>(() => initialChannels);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    setPicked(initialChannels);
  }, [initialChannelsKey]);

  const listMessages = useMemo(() => {
    const t = Date.now();
    return [...priorChatMessages, ...introMessages.map((m, i) => ({ ...m, timestamp: t + i }))];
  }, [priorChatMessages, introMessages]);

  const roster = useMemo(() => channels.filter((c) => c.id.trim().length > 0), [channels]);

  const suggestions = useMemo(() => {
    const q = filterChannelsByQuery(roster, query);
    return q.filter((c) => !picked.some((p) => p.channel_id === c.id));
  }, [roster, query, picked]);

  useEffect(() => {
    setHighlight(0);
  }, [query, open]);

  const addChannel = useCallback((ch: SlackWorkspaceChannel) => {
    const row = channelToRow(ch);
    setPicked((prev) => {
      if (prev.some((p) => p.channel_id === row.channel_id)) {
        return prev;
      }
      return [...prev, row];
    });
    setQuery("");
    setOpen(false);
    window.requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
  }, []);

  const removeChannel = useCallback((channelId: string) => {
    setPicked((prev) => prev.filter((p) => p.channel_id !== channelId));
  }, []);

  const onInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (!open && (e.key === "ArrowDown" || e.key === "Enter")) {
        setOpen(true);
      }
      if (!open || suggestions.length === 0) {
        return;
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => (h + 1) % suggestions.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) => (h - 1 + suggestions.length) % suggestions.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        addChannel(suggestions[highlight]!);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    },
    [open, suggestions, highlight, addChannel],
  );

  const disabled = channelsLoading || Boolean(channelsError);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ChatMessageList messages={listMessages} userDisplayName={userDisplayName} isTyping={false} />
      <div className="shrink-0 border-t border-zinc-100/90 bg-white/90 px-4 pb-6 pt-3 backdrop-blur-sm sm:px-5">
        {channelsError ? (
          <p className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
            {channelsError}
          </p>
        ) : null}
        {submitError ? (
          <p className="mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
            {submitError}
          </p>
        ) : null}
        <div className="space-y-3">
          <p className="text-center text-[12px] leading-relaxed text-zinc-500">
            Search by channel name, tap a row to add. Remove with <span className="font-medium text-zinc-700">×</span> on a chip.
          </p>
          {picked.length > 0 ? (
            <div className="flex flex-wrap justify-center gap-2">
              {picked.map((row) => (
                <div
                  key={row.channel_id}
                  className="inline-flex max-w-full items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 py-1 pl-3 pr-1 shadow-sm"
                >
                  <span className="min-w-0 truncate text-[13px] font-semibold text-zinc-900">
                    {displayHashName(row)}
                  </span>
                  <button
                    type="button"
                    disabled={disabled || submitting}
                    onClick={() => removeChannel(row.channel_id)}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-zinc-500 transition hover:bg-zinc-200/90 hover:text-zinc-900 disabled:opacity-40"
                    aria-label={`Remove ${displayHashName(row)}`}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-[12px] text-zinc-600">{emptyHint}</p>
          )}
          <div className="relative">
            <div
              className={
                "flex min-h-[3rem] items-center rounded-2xl border border-zinc-200 bg-zinc-50/80 px-3 " +
                "outline-none transition focus-within:border-teal-400/80 focus-within:bg-white " +
                "focus-within:shadow-[0_0_0_3px_rgba(45,212,191,0.18)] " +
                (disabled ? "opacity-60" : "")
              }
            >
              <span className="select-none pr-0.5 text-[15px] font-medium text-zinc-500" aria-hidden>
                #
              </span>
              <input
                ref={inputRef}
                id={inputId}
                type="text"
                autoComplete="off"
                autoCorrect="off"
                spellCheck={false}
                disabled={disabled}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setOpen(true);
                }}
                onFocus={() => setOpen(true)}
                onBlur={() => {
                  window.setTimeout(() => setOpen(false), 180);
                }}
                onKeyDown={onInputKeyDown}
                aria-autocomplete="list"
                aria-expanded={open}
                aria-controls={listboxId}
                placeholder="channel name"
                className="min-w-0 flex-1 border-0 bg-transparent py-2 text-[15px] text-zinc-900 outline-none placeholder:text-zinc-400"
              />
            </div>
            {open && suggestions.length > 0 ? (
              <ul
                id={listboxId}
                role="listbox"
                aria-label="Slack channels to add"
                className="absolute bottom-full left-0 right-0 z-20 mb-1 max-h-52 overflow-y-auto rounded-xl border border-zinc-200/90 bg-white py-1 shadow-[0_12px_40px_-16px_rgba(15,23,42,0.25)]"
              >
                {suggestions.map((c, i) => {
                  const label = c.name.trim().replace(/^#/, "") || c.id;
                  return (
                    <li key={c.id}>
                      <button
                        type="button"
                        role="option"
                        aria-selected={i === highlight}
                        className={
                          "flex w-full items-center gap-2 px-3 py-2 text-left text-sm " +
                          (i === highlight ? "bg-zinc-100" : "hover:bg-zinc-50")
                        }
                        onMouseDown={(ev) => ev.preventDefault()}
                        onMouseEnter={() => setHighlight(i)}
                        onClick={() => addChannel(c)}
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-violet-100/90 text-[11px] font-bold text-violet-800">
                          #
                        </span>
                        <span className="min-w-0 flex-1 truncate font-semibold text-zinc-900">#{label}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : null}
          </div>
          <button
            type="button"
            disabled={submitting || disabled}
            onClick={() => onContinue(picked)}
            className={
              "w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white " +
              "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] " +
              "disabled:cursor-not-allowed disabled:opacity-50 " +
              landingAccentText
            }
          >
            {submitting ? "Saving…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}

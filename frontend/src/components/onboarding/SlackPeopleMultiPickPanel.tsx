import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import type { ChatMessage } from "./types";
import ChatMessageList from "./ChatMessageList";
import { landingAccentText } from "../landing/landingBrandPalette";
import type { SlackCollaboratorMember, SlackWorkspaceMember } from "../../lib/onboardingApi";
import {
  filterSlackMembersByQuery,
  rosterWithoutSlackbot,
  slackMemberPickerPrimary,
  slackMemberPickerSecondary,
} from "./slackMemberSearchUtils";

function workspaceMemberToCollaborator(m: SlackWorkspaceMember): SlackCollaboratorMember {
  return {
    slack_user_id: m.id,
    username: m.username.trim(),
    label: m.label.trim() || m.username.trim(),
  };
}

function slackHandleFromCollaborator(c: SlackCollaboratorMember): string {
  return `@${c.username.trim().replace(/^@/, "")}`;
}

type SlackPeopleMultiPickPanelProps = {
  priorChatMessages: ChatMessage[];
  introMessages: ChatMessage[];
  members: SlackWorkspaceMember[];
  membersLoading: boolean;
  membersError: string | null;
  /** Slack user ids excluded from roster (e.g. managers already chosen). */
  excludeSlackUserIds: string[];
  initialMembers: SlackCollaboratorMember[];
  initialMembersKey: string;
  submitError: string | null;
  submitting: boolean;
  onContinue: (members: SlackCollaboratorMember[]) => void;
  userDisplayName: string;
  /** When false, Continue is enabled even with zero picks (team step). */
  requireAtLeastOne: boolean;
  emptyHint: string;
};

export default function SlackPeopleMultiPickPanel({
  priorChatMessages,
  introMessages,
  members,
  membersLoading,
  membersError,
  excludeSlackUserIds,
  initialMembers,
  initialMembersKey,
  submitError,
  submitting,
  onContinue,
  userDisplayName,
  requireAtLeastOne,
  emptyHint,
}: SlackPeopleMultiPickPanelProps) {
  const ids = useId();
  const inputId = `${ids}-people-pick`;
  const listboxId = `${ids}-people-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [picked, setPicked] = useState<SlackCollaboratorMember[]>(() => initialMembers);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const excludeSet = useMemo(() => new Set(excludeSlackUserIds), [excludeSlackUserIds]);

  useEffect(() => {
    setPicked(initialMembers);
  }, [initialMembersKey]);

  const listMessages = useMemo(() => {
    const t = Date.now();
    return [...priorChatMessages, ...introMessages.map((m, i) => ({ ...m, timestamp: t + i }))];
  }, [priorChatMessages, introMessages]);

  const roster = useMemo(() => {
    const base = rosterWithoutSlackbot(members);
    return base.filter((m) => !excludeSet.has(m.id));
  }, [members, excludeSet]);

  const suggestions = useMemo(() => {
    const q = filterSlackMembersByQuery(roster, query);
    return q.filter((m) => !picked.some((p) => p.slack_user_id === m.id));
  }, [roster, query, picked]);

  useEffect(() => {
    setHighlight(0);
  }, [query, open]);

  const addMember = useCallback((m: SlackWorkspaceMember) => {
    const row = workspaceMemberToCollaborator(m);
    setPicked((prev) => {
      if (prev.some((p) => p.slack_user_id === row.slack_user_id)) {
        return prev;
      }
      return [...prev, row];
    });
    setQuery("");
    setOpen(false);
    window.requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
  }, []);

  const removeMember = useCallback((slackUserId: string) => {
    setPicked((prev) => prev.filter((p) => p.slack_user_id !== slackUserId));
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
        addMember(suggestions[highlight]!);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    },
    [open, suggestions, highlight, addMember],
  );

  const disabled = membersLoading || Boolean(membersError);
  const canContinue = requireAtLeastOne ? picked.length > 0 : true;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ChatMessageList messages={listMessages} userDisplayName={userDisplayName} isTyping={false} />
      <div className="shrink-0 border-t border-zinc-100/90 bg-white/90 px-4 pb-6 pt-3 backdrop-blur-sm sm:px-5">
        {membersError ? (
          <p className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
            {membersError}
          </p>
        ) : null}
        {submitError ? (
          <p className="mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
            {submitError}
          </p>
        ) : null}
        <div className="space-y-3">
          <p className="text-center text-[12px] leading-relaxed text-zinc-500">
            Search by{" "}
            <span className="font-medium text-zinc-700">Slack name</span> or{" "}
            <span className="font-medium text-zinc-700">@username</span>, tap a row to add. Remove with{" "}
            <span className="font-medium text-zinc-700">×</span> on a chip.
          </p>
          {picked.length > 0 ? (
            <div className="flex flex-wrap justify-center gap-2">
              {picked.map((m) => {
                const wm = members.find((x) => x.id === m.slack_user_id);
                const handle = slackHandleFromCollaborator(m);
                const initials = (m.label.trim() || m.username).slice(0, 2).toUpperCase();
                return (
                  <div
                    key={m.slack_user_id}
                    className="inline-flex max-w-full items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 py-1 pl-1.5 pr-1 shadow-sm"
                  >
                    {wm?.image_48 ? (
                      <img
                        src={wm.image_48}
                        alt=""
                        className="h-8 w-8 shrink-0 rounded-full object-cover ring-1 ring-zinc-200/80"
                      />
                    ) : (
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-zinc-200/90 text-[11px] font-semibold text-zinc-700 ring-1 ring-zinc-200/80">
                        {initials}
                      </span>
                    )}
                    <span className="min-w-0 truncate pr-0.5 text-[13px] font-semibold text-zinc-900">{handle}</span>
                    <button
                      type="button"
                      disabled={disabled || submitting}
                      onClick={() => removeMember(m.slack_user_id)}
                      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-zinc-500 transition hover:bg-zinc-200/90 hover:text-zinc-900 disabled:opacity-40"
                      aria-label={`Remove ${handle}`}
                    >
                      ×
                    </button>
                  </div>
                );
              })}
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
                @
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
                placeholder="name or username"
                className="min-w-0 flex-1 border-0 bg-transparent py-2 text-[15px] text-zinc-900 outline-none placeholder:text-zinc-400"
              />
            </div>
            {open && suggestions.length > 0 ? (
              <ul
                id={listboxId}
                role="listbox"
                aria-label="Slack members to add"
                className="absolute bottom-full left-0 right-0 z-20 mb-1 max-h-52 overflow-y-auto rounded-xl border border-zinc-200/90 bg-white py-1 shadow-[0_12px_40px_-16px_rgba(15,23,42,0.25)]"
              >
                {suggestions.map((m, i) => (
                  <li key={m.id}>
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
                      onClick={() => addMember(m)}
                    >
                      {m.image_48 ? (
                        <img src={m.image_48} alt="" className="h-7 w-7 shrink-0 rounded-md object-cover" />
                      ) : (
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-zinc-200/80 text-[11px] font-semibold text-zinc-600">
                          {(m.label.trim() || m.username).slice(0, 2).toUpperCase()}
                        </span>
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate font-semibold text-zinc-900">
                          {slackMemberPickerPrimary(m)}
                        </span>
                        {slackMemberPickerSecondary(m) ? (
                          <span className="block truncate text-[12px] text-zinc-500">
                            {slackMemberPickerSecondary(m)}
                          </span>
                        ) : null}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          <button
            type="button"
            disabled={submitting || disabled || !canContinue}
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

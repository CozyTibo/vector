import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import type { ChatMessage } from "./types";
import ChatMessageList from "./ChatMessageList";
import { landingAccentText } from "../landing/landingBrandPalette";
import type { SlackWorkspaceMember } from "../../lib/onboardingApi";
import { slackHandoffSyntheticMessagesDeduped } from "./slackHandoffCopy";

const SLACKBOT_USER_ID = "USLACKBOT";

function normalizeSignupEmail(email: string): string {
  return email.trim().toLowerCase();
}

function findSlackMemberBySignupEmail(
  members: SlackWorkspaceMember[],
  signupEmail: string,
): SlackWorkspaceMember | null {
  const n = normalizeSignupEmail(signupEmail);
  if (!n) {
    return null;
  }
  for (const m of members) {
    if (m.email && m.email === n) {
      return m;
    }
  }
  return null;
}

function filterMembers(roster: SlackWorkspaceMember[], query: string): SlackWorkspaceMember[] {
  const q = query.trim().toLowerCase();
  const base = q
    ? roster.filter(
        (m) =>
          m.username.toLowerCase().includes(q) ||
          m.label.toLowerCase().includes(q) ||
          m.id.toLowerCase().includes(q),
      )
    : roster;
  return base.slice(0, 12);
}

/** Display name (fallback: @login) for list rows and the selected chip. */
function slackMemberPickerPrimary(m: SlackWorkspaceMember): string {
  const t = m.label.trim();
  if (t) {
    return t;
  }
  return `@${m.username}`;
}

/** Slack @login when it adds context beyond the primary line. */
function slackMemberPickerSecondary(m: SlackWorkspaceMember): string | null {
  const t = m.label.trim();
  if (!t || t.toLowerCase() === m.username.toLowerCase()) {
    return null;
  }
  return `@${m.username}`;
}

type SlackStakeholdersPanelProps = {
  priorChatMessages: ChatMessage[];
  communicationToolLabel: string;
  signupEmail: string;
  members: SlackWorkspaceMember[];
  membersLoading: boolean;
  membersError: string | null;
  submitError: string | null;
  submitting: boolean;
  onSubmit: (payload: { text: string; slack_user_ids: string[]; mention_labels: string[] }) => void;
  userDisplayName: string;
};

export default function SlackStakeholdersPanel({
  priorChatMessages,
  communicationToolLabel,
  signupEmail,
  members,
  membersLoading,
  membersError,
  submitError,
  submitting,
  onSubmit,
  userDisplayName,
}: SlackStakeholdersPanelProps) {
  const ids = useId();
  const inputId = `${ids}-handle-input`;
  const listboxId = `${ids}-handle-list`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [emailMatchDismissed, setEmailMatchDismissed] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<SlackWorkspaceMember | null>(null);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  const listMessages = useMemo(() => {
    const t = Date.now();
    return [
      ...priorChatMessages,
      ...slackHandoffSyntheticMessagesDeduped(communicationToolLabel, t, priorChatMessages),
    ];
  }, [priorChatMessages, communicationToolLabel]);

  const roster = useMemo(
    () => members.filter((m) => m.id !== SLACKBOT_USER_ID),
    [members],
  );

  const emailMatchMember = useMemo(
    () => findSlackMemberBySignupEmail(members, signupEmail),
    [members, signupEmail],
  );

  const showEmailMatchPrompt =
    Boolean(emailMatchMember) && !emailMatchDismissed && !membersLoading && !membersError;

  /** Slack display name for the email-match headline (falls back to login). */
  const emailMatchPromptLead = useMemo(() => {
    if (!emailMatchMember) {
      return "";
    }
    const t = emailMatchMember.label.trim();
    return t || emailMatchMember.username;
  }, [emailMatchMember]);

  const emailMatchPromptShowSlackLogin = useMemo(() => {
    if (!emailMatchMember) {
      return false;
    }
    const t = emailMatchMember.label.trim();
    if (!t) {
      return false;
    }
    return t.toLowerCase() !== emailMatchMember.username.toLowerCase();
  }, [emailMatchMember]);

  const suggestions = useMemo(() => filterMembers(roster, query), [roster, query]);

  useEffect(() => {
    setHighlight(0);
  }, [query, open]);

  const submitMember = useCallback(
    (m: SlackWorkspaceMember) => {
      onSubmit({
        text: `@${m.username}`,
        slack_user_ids: [m.id],
        mention_labels: [m.label],
      });
    },
    [onSubmit],
  );

  const clearSelection = useCallback(() => {
    setSelected(null);
    setQuery("");
    setOpen(false);
    window.requestAnimationFrame(() => inputRef.current?.focus({ preventScroll: true }));
  }, []);

  const pickMember = useCallback((m: SlackWorkspaceMember) => {
    setSelected(m);
    setQuery(m.username);
    setOpen(false);
  }, []);

  const disabled = membersLoading || Boolean(membersError);
  const canContinue = selected !== null;

  const selectedSlackDisplay = useMemo(() => {
    if (!selected) {
      return { primary: "", secondary: null as string | null };
    }
    return {
      primary: slackMemberPickerPrimary(selected),
      secondary: slackMemberPickerSecondary(selected),
    };
  }, [selected]);

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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
      pickMember(suggestions[highlight]!);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

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
        {showEmailMatchPrompt && emailMatchMember ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-200/90 bg-zinc-50/80 px-4 py-4 text-center">
              <p className="text-[15px] font-medium leading-snug text-zinc-900">
                Is <span className="font-semibold text-zinc-950">@{emailMatchPromptLead}</span> you on
                Slack?
              </p>
              <p className="mt-1.5 text-[13px] leading-relaxed text-zinc-600">
                {emailMatchPromptShowSlackLogin ? (
                  <span className="block font-normal text-zinc-500">
                    Slack login @{emailMatchMember.username}
                  </span>
                ) : null}
                <span
                  className={
                    emailMatchPromptShowSlackLogin
                      ? "mt-1 block text-[12px] text-zinc-500"
                      : "block text-[12px] text-zinc-500"
                  }
                >
                  Same email as your Vector signup — confirm if this is you.
                </span>
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
              <button
                type="button"
                disabled={submitting || disabled}
                onClick={() => submitMember(emailMatchMember)}
                className={
                  "w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white " +
                  "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] " +
                  "disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[10rem] " +
                  landingAccentText
                }
              >
                {submitting ? "Saving…" : "Yes, that's me"}
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => setEmailMatchDismissed(true)}
                className="w-full rounded-full border border-zinc-200 bg-white px-6 py-3 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 disabled:opacity-50 sm:w-auto sm:min-w-[10rem]"
              >
                No, pick another
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-center text-[12px] leading-relaxed text-zinc-500">
              Tap the field, then type to filter by the{" "}
              <span className="font-medium text-zinc-700">name you use in Slack</span> or your{" "}
              <span className="font-medium text-zinc-700">@username</span>.
            </p>
            <div className="relative">
              {selected ? (
                <div className="flex min-h-[3rem] items-center justify-between gap-3 rounded-2xl border border-teal-400/50 bg-white px-3 py-2.5 shadow-[0_0_0_3px_rgba(45,212,191,0.12)]">
                  <div className="min-w-0">
                    <p className="truncate text-[15px] font-semibold text-zinc-900">
                      {selectedSlackDisplay.primary}
                    </p>
                    {selectedSlackDisplay.secondary ? (
                      <p className="truncate text-[13px] text-zinc-500">
                        {selectedSlackDisplay.secondary}
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={clearSelection}
                    className="shrink-0 text-[13px] font-medium text-zinc-600 underline decoration-zinc-300 underline-offset-2 hover:text-zinc-900 disabled:opacity-50"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <>
                  <div
                    className={
                      "flex min-h-[3rem] items-center rounded-2xl border border-zinc-200 bg-zinc-50/80 px-3 " +
                      "outline-none transition focus-within:border-teal-400/80 focus-within:bg-white " +
                      "focus-within:shadow-[0_0_0_3px_rgba(45,212,191,0.18)] " +
                      (disabled ? "opacity-60" : "")
                    }
                  >
                    <span
                      className="select-none pr-0.5 text-[15px] font-medium text-zinc-500"
                      aria-hidden
                    >
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
                      aria-label="Slack members"
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
                            onClick={() => pickMember(m)}
                          >
                            {m.image_48 ? (
                              <img
                                src={m.image_48}
                                alt=""
                                className="h-7 w-7 shrink-0 rounded-md object-cover"
                              />
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
                </>
              )}
            </div>
            <button
              type="button"
              disabled={submitting || disabled || !canContinue}
              onClick={() => {
                if (selected) {
                  submitMember(selected);
                }
              }}
              className={
                "w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white " +
                "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] " +
                "disabled:cursor-not-allowed disabled:opacity-50 " +
                landingAccentText
              }
            >
              {submitting ? "Saving…" : "Continue"}
            </button>
            {!canContinue && !disabled ? (
              <p className="text-center text-[12px] text-zinc-500">
                Pick your Slack profile from the list to continue.
              </p>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

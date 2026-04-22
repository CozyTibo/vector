import { useMemo } from "react";

import type { ChatMessage } from "./types";
import ChatMessageList from "./ChatMessageList";
import { landingAccentText } from "../landing/landingBrandPalette";
import type { SlackWatchChannelRow } from "./slackTeamChannelAnswers";

function displayHashName(row: SlackWatchChannelRow): string {
  const n = row.name.trim().replace(/^#/, "") || row.channel_id;
  return `#${n}`;
}

type SlackChannelsConfirmPanelProps = {
  priorChatMessages: ChatMessage[];
  confirmIntroMessages: ChatMessage[];
  listTitle: string;
  channels: SlackWatchChannelRow[];
  submitError: string | null;
  submitting: boolean;
  onEdit: () => void;
  onContinue: () => void;
  userDisplayName: string;
};

export default function SlackChannelsConfirmPanel({
  priorChatMessages,
  confirmIntroMessages,
  listTitle,
  channels,
  submitError,
  submitting,
  onEdit,
  onContinue,
  userDisplayName,
}: SlackChannelsConfirmPanelProps) {
  const listMessages = useMemo(() => {
    const t = Date.now();
    return [
      ...priorChatMessages,
      ...confirmIntroMessages.map((m, i) => ({ ...m, timestamp: t + i })),
    ];
  }, [priorChatMessages, confirmIntroMessages]);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <ChatMessageList messages={listMessages} userDisplayName={userDisplayName} isTyping={false} />
      <div className="shrink-0 border-t border-zinc-100/90 bg-white/90 px-4 pb-6 pt-3 backdrop-blur-sm sm:px-5">
        {submitError ? (
          <p className="mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
            {submitError}
          </p>
        ) : null}
        <div className="mb-4 rounded-2xl border border-zinc-200/90 bg-zinc-50/80 px-4 py-3">
          <p className="mb-2 text-center text-[12px] font-medium leading-snug text-zinc-600">{listTitle}</p>
          <ul className="space-y-2">
            {channels.map((row) => (
              <li
                key={row.channel_id}
                className="flex items-center gap-3 rounded-xl border border-zinc-200/80 bg-white px-3 py-2"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-100/90 text-[12px] font-bold text-violet-800 ring-1 ring-violet-200/80">
                  #
                </span>
                <p className="min-w-0 truncate text-[14px] font-semibold text-zinc-900">{displayHashName(row)}</p>
              </li>
            ))}
          </ul>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
          <button
            type="button"
            disabled={submitting}
            onClick={onEdit}
            className="w-full rounded-full border border-zinc-200 bg-white px-6 py-3 text-sm font-medium text-zinc-800 transition hover:bg-zinc-50 disabled:opacity-50 sm:w-auto sm:min-w-[10rem]"
          >
            Edit list
          </button>
          <button
            type="button"
            disabled={submitting}
            onClick={onContinue}
            className={
              "w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white " +
              "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] " +
              "disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[10rem] " +
              landingAccentText
            }
          >
            Looks good
          </button>
        </div>
      </div>
    </div>
  );
}

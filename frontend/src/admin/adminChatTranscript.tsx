import ChatMessageList from "../components/onboarding/ChatMessageList";
import { primaryCommunicationToolLabel } from "../components/onboarding/onboardingToolGroups";
import {
  slackCollaboratorsConfirmIntroMessages,
  slackCollaboratorsPickIntroMessages,
} from "../components/onboarding/slackCollaboratorsCopy";
import {
  ONB_SLACK_HANDOFF_EVENT_ID,
  slackHandoffSyntheticMessagesDeduped,
} from "../components/onboarding/slackHandoffCopy";
import {
  slackTeamMembersConfirmIntroMessages,
  slackTeamMembersPickIntroMessages,
  slackWatchChannelsConfirmIntroMessages,
  slackWatchChannelsPickIntroMessages,
} from "../components/onboarding/slackTeamChannelsCopy";
import {
  ONBOARDING_WRAP_UP_THANKS,
  wrapUpManagerIntroQuestion,
} from "../components/onboarding/onboardingWrapUpCopy";
import {
  reorderOnboardingTranscriptForDisplay,
  stakeholderAnswerDisplayLineFromAnswers,
  tryParseUserStructuredJsonType,
} from "../components/onboarding/onboardingTranscriptDisplayOrder";
import { slackPersonChipText } from "../components/onboarding/slackPersonDisplay";
import { otherSlackCollaboratorsExcludingStakeholder } from "../components/onboarding/slackOnboardingBranching";
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

/** Minimal onboarding snapshot fields needed to mirror product-only chat rows in the admin transcript. */
export type AdminOnboardingTranscriptSnapshot = {
  status: string;
  current_step: string;
  tools_engineering: string[];
  tools_pm: string[];
  tools_communication: string[];
  tools_calls?: string[];
  tools_calendars?: string[];
  tools_docs: string[];
  slack_stakeholders: { raw_text: string | null; slack_user_ids: string[] } | null;
  slack_collaborators?: { members: { slack_user_id: string; username: string; label: string }[] } | null;
  slack_team_members?: { members: { slack_user_id: string; username: string; label: string }[] } | null;
  slack_watch_channels?: { channels: { channel_id: string; name: string }[] } | null;
};

function adminSnapToAnswers(snap: AdminOnboardingTranscriptSnapshot): Record<string, unknown> {
  return {
    tools: {
      engineering: snap.tools_engineering,
      pm: snap.tools_pm,
      communication: snap.tools_communication,
      calls: snap.tools_calls ?? [],
      calendars: snap.tools_calendars ?? [],
      docs: snap.tools_docs,
    },
    slack_stakeholders: snap.slack_stakeholders,
    slack_collaborators: snap.slack_collaborators,
    slack_team_members: snap.slack_team_members,
    slack_watch_channels: snap.slack_watch_channels,
  };
}

function transcriptHasVectorContent(msgs: ChatMessage[], substring: string): boolean {
  return msgs.some((m) => m.role === "vector" && m.content.includes(substring));
}

function appendUniqueVectorIntros(
  out: ChatMessage[],
  intros: ChatMessage[],
  anchorTs: number,
  baseOffset: number,
): void {
  let i = 0;
  for (const row of intros) {
    if (out.some((x) => x.role === "vector" && x.content === row.content)) {
      continue;
    }
    out.push({
      ...row,
      timestamp: anchorTs - 120 + baseOffset + i,
    });
    i += 1;
  }
}

/**
 * Merge persisted onboarding_message rows with the same UI-only Vector copy the product shows
 * around Slack pick/confirm panels, so the admin transcript matches the member-facing thread.
 */
export function buildAdminWebsiteOnboardingTranscript(
  rows: AdminChatRow[],
  snap: AdminOnboardingTranscriptSnapshot,
): ChatMessage[] {
  const base = adminOnboardingRowsToChatMessages(rows);
  const answers = adminSnapToAnswers(snap);
  const stakeholderLine = stakeholderAnswerDisplayLineFromAnswers(answers);
  const handoffAlreadyInDb = base.some((m) => m.id === ONB_SLACK_HANDOFF_EVENT_ID);

  const out: ChatMessage[] = [];
  for (const m of base) {
    if (m.role === "user") {
      const jsonType = tryParseUserStructuredJsonType(m.content);
      if (jsonType === "slack_team_members_selected") {
        const teamPickVariant =
          otherSlackCollaboratorsExcludingStakeholder(answers).length === 0
            ? "solo_manager"
            : "with_other_managers";
        appendUniqueVectorIntros(
          out,
          slackTeamMembersPickIntroMessages(0, teamPickVariant),
          m.timestamp,
          0,
        );
        appendUniqueVectorIntros(out, slackTeamMembersConfirmIntroMessages(0), m.timestamp, 8);
      } else if (jsonType === "slack_collaborators_selected") {
        appendUniqueVectorIntros(out, slackCollaboratorsPickIntroMessages(0), m.timestamp, 0);
        appendUniqueVectorIntros(out, slackCollaboratorsConfirmIntroMessages(0), m.timestamp, 8);
      } else if (jsonType === "slack_watch_channels_selected") {
        appendUniqueVectorIntros(out, slackWatchChannelsPickIntroMessages(0), m.timestamp, 0);
        appendUniqueVectorIntros(out, slackWatchChannelsConfirmIntroMessages(0), m.timestamp, 8);
      } else if (
        jsonType === null &&
        stakeholderLine !== null &&
        m.content.trim() === stakeholderLine &&
        !handoffAlreadyInDb
      ) {
        const synth = slackHandoffSyntheticMessagesDeduped(
          primaryCommunicationToolLabel(answers),
          m.timestamp - 120,
          [...out],
        );
        synth.forEach((s, i) => {
          if (out.some((x) => x.id === s.id)) {
            return;
          }
          out.push({ ...s, timestamp: m.timestamp - 100 + i });
        });
      }
    }
    out.push(m);
  }

  const hasSlackHandoff =
    Boolean(snap.slack_stakeholders?.slack_user_ids && snap.slack_stakeholders.slack_user_ids.length > 0);
  const wrapUpContext =
    hasSlackHandoff &&
    (snap.current_step === "ADMIN_ACCESS" ||
      snap.current_step === "THANK_YOU" ||
      snap.status === "completed");
  if (wrapUpContext && !transcriptHasVectorContent(out, "We've got everything")) {
    const consentIdx = out.findIndex(
      (m) => m.role === "user" && tryParseUserStructuredJsonType(m.content) === "slack_manager_intro_consent",
    );
    const anchorTs =
      consentIdx >= 0
        ? out[consentIdx]!.timestamp
        : out.length > 0
          ? Math.max(...out.map((x) => x.timestamp))
          : Date.now();
    const thanksMsg: ChatMessage = {
      id: "admin-synth-wrap-thanks",
      role: "vector",
      content: ONBOARDING_WRAP_UP_THANKS,
      timestamp: anchorTs - 2,
    };
    const others = otherSlackCollaboratorsExcludingStakeholder(answers);
    const askMsg: ChatMessage | null =
      others.length > 0 && !transcriptHasVectorContent(out, "introduce myself in Slack to the managers")
        ? {
            id: "admin-synth-wrap-manager-ask",
            role: "vector",
            content: wrapUpManagerIntroQuestion(others.map((m) => slackPersonChipText(m)).join(", ")),
            timestamp: anchorTs - 1,
          }
        : null;
    const synthWrap = askMsg ? [thanksMsg, askMsg] : [thanksMsg];
    if (consentIdx >= 0) {
      out.splice(consentIdx, 0, ...synthWrap);
    } else {
      out.push(...synthWrap.map((row, i) => ({ ...row, timestamp: anchorTs + 1 + i })));
    }
  }

  return reorderOnboardingTranscriptForDisplay(out, answers);
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

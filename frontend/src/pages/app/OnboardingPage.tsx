import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import ChatInputBar from "../../components/onboarding/ChatInputBar";
import ChatMessageList from "../../components/onboarding/ChatMessageList";
import OnboardingChatLayout from "../../components/onboarding/OnboardingChatLayout";
import {
  CONNECTOR_STEP_FOOTER_LINK_CLASS,
  ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS,
  ONBOARDING_PRIMARY_CTA_GRADIENT_BUTTON_CLASS,
  ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS,
} from "../../components/onboarding/onboardingUiConstants";
import SlackCollaboratorsConfirmPanel from "../../components/onboarding/SlackCollaboratorsConfirmPanel";
import SlackCollaboratorsPickPanel from "../../components/onboarding/SlackCollaboratorsPickPanel";
import SlackChannelsConfirmPanel from "../../components/onboarding/SlackChannelsConfirmPanel";
import SlackChannelsPickPanel from "../../components/onboarding/SlackChannelsPickPanel";
import SlackPeopleMultiConfirmPanel from "../../components/onboarding/SlackPeopleMultiConfirmPanel";
import SlackPeopleMultiPickPanel from "../../components/onboarding/SlackPeopleMultiPickPanel";
import {
  seedCollaboratorsFromStakeholders,
  slackCollaboratorsFromAnswers,
} from "../../components/onboarding/slackCollaboratorsAnswers";
import {
  collaboratorsIncludesStakeholderSelf,
  otherSlackCollaboratorsExcludingStakeholder,
} from "../../components/onboarding/slackOnboardingBranching";
import { reorderOnboardingTranscriptForDisplay } from "../../components/onboarding/onboardingTranscriptDisplayOrder";
import {
  ONBOARDING_WRAP_UP_THANKS,
  wrapUpManagerIntroQuestion,
} from "../../components/onboarding/onboardingWrapUpCopy";
import { slackPersonChipText } from "../../components/onboarding/slackPersonDisplay";
import {
  slackTeamMembersConfirmIntroMessages,
  slackTeamMembersPickIntroMessages,
  slackWatchChannelsConfirmIntroMessages,
  slackWatchChannelsPickIntroMessages,
} from "../../components/onboarding/slackTeamChannelsCopy";
import {
  slackTeamMembersFromAnswers,
  slackWatchChannelsFromAnswers,
} from "../../components/onboarding/slackTeamChannelAnswers";
import SlackStakeholdersPanel from "../../components/onboarding/SlackStakeholdersPanel";
import {
  ONB_SLACK_HANDOFF_EVENT_ID,
  slackHandoffSyntheticMessagesDeduped,
} from "../../components/onboarding/slackHandoffCopy";
import ToolSelectorBlock from "../../components/onboarding/ToolSelectorBlock";
import {
  emptyToolPick,
  hydrateToolPickFromAnswers,
  ONBOARDING_TOOL_GROUPS,
  primaryCommunicationToolLabel,
  toolPickToBackendPayload,
  type ToolPickState,
} from "../../components/onboarding/onboardingToolGroups";
import { minTypingDelay } from "../../components/onboarding/chatDelay";
import type { ChatMessage } from "../../components/onboarding/types";
import { landingAccentText } from "../../components/landing/landingBrandPalette";
import {
  completeOnboarding,
  fetchOnboarding,
  fetchSlackWorkspaceChannels,
  fetchSlackWorkspaceMembers,
  patchOnboarding,
  postOnboardingChat,
  postRestartOnboarding,
  type OnboardingMessagePayload,
  type OnboardingStatePayload,
  type OnboardingStep,
  type SlackCollaboratorMember,
} from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";

/** Branded opening copy (display only; FSM still driven by the bootstrap chat response). */
const ONBOARDING_OPENING_MESSAGE = `Hey! I'm Vector, your execution manager.

I help teams see what's actually happening across execution: the real motion of work, not another dashboard.

I'm going to ask a few quick questions so I know who I'm talking to and how to connect this workspace to your world. Takes about a minute.

What should I call you?`;

/** Must match backend `onboarding_llm.BOOTSTRAP_OPENING_REPLY_TEXT` so refreshed chats keep the same opening UX. */
const SERVER_BOOTSTRAP_OPENING_REPLY_TEXT =
  "Hey! I'm Vector, your execution manager. I'll ask a few quick questions to set things up. What should I call you?";

function mapServerMessageToChatMessage(m: OnboardingMessagePayload): ChatMessage {
  const role: ChatMessage["role"] = m.role === "user" ? "user" : "vector";
  const content =
    role === "vector" && m.content === SERVER_BOOTSTRAP_OPENING_REPLY_TEXT
      ? ONBOARDING_OPENING_MESSAGE
      : m.content;
  return {
    id: m.id,
    role,
    content,
    timestamp: new Date(m.created_at).getTime(),
  };
}

type LiveConnectorId = "github" | "linear" | "slack";

type ConnectorQueueId = LiveConnectorId | "comm_placeholder";

function NextConnectStep(next: ConnectorQueueId): OnboardingStep {
  if (next === "linear") {
    return "CONNECT_PROJECT_MANAGEMENT";
  }
  if (next === "github") {
    return "CONNECT_ENGINEERING";
  }
  if (next === "slack" || next === "comm_placeholder") {
    return "CONNECT_COMMUNICATION";
  }
  return "SCANNING";
}

/** Order matches backend `onboarding_flow._connect_queue_full_from_tools`. */
function connectQueueFromTools(answers: Record<string, unknown>): ConnectorQueueId[] {
  const t = answers.tools as Record<string, string[]> | undefined;
  if (!t) {
    return [];
  }
  const order: ConnectorQueueId[] = [];
  const pm = t.pm ?? [];
  if (pm.includes("linear")) {
    order.push("linear");
  }
  const eng = t.engineering ?? [];
  if (eng.includes("github")) {
    order.push("github");
  }
  const comm = t.communication ?? [];
  if (comm.includes("slack")) {
    order.push("slack");
  } else if (comm.includes("ms_teams") || comm.includes("discord")) {
    order.push("comm_placeholder");
  }
  return order;
}

function liveProviderConnected(provider: LiveConnectorId, server: OnboardingStatePayload): boolean {
  if (provider === "slack") {
    return server.slack_connected;
  }
  if (provider === "linear") {
    return server.linear_connected;
  }
  return server.github_connected;
}

/** Display name for the communication tool when the queue is the Teams/Discord placeholder. */
function unsupportedCommunicationPickLabel(answers: Record<string, unknown>): string {
  const raw = answers.tools;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return "Microsoft Teams or Discord";
  }
  const comm = (raw as Record<string, unknown>).communication;
  if (!Array.isArray(comm)) {
    return "Microsoft Teams or Discord";
  }
  const hasTeams = comm.includes("ms_teams");
  const hasDiscord = comm.includes("discord");
  if (hasTeams && hasDiscord) {
    return "Microsoft Teams and Discord";
  }
  if (hasTeams) {
    return "Microsoft Teams";
  }
  if (hasDiscord) {
    return "Discord";
  }
  return "Microsoft Teams or Discord";
}

const UNSUPPORTED_MANDATORY_SECTION_KEYS = ["communication", "pm", "engineering"] as const;

function unsupportedMandatorySectionsFromAnswers(answers: Record<string, unknown>): string[] {
  const raw = answers.unsupported_mandatory_sections;
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter(
    (x): x is string =>
      typeof x === "string" && (UNSUPPORTED_MANDATORY_SECTION_KEYS as readonly string[]).includes(x),
  );
}

/** Readable scope for the unsupported-mandatory card (one, two, or three areas). */
function unsupportedMandatoryScopeDescription(sections: string[]): string {
  const labels: Record<string, string> = {
    communication: "communication tools such as Microsoft Teams or Discord",
    pm: "project management tools outside Linear (for example Jira, ClickUp, or Notion)",
    engineering: "engineering tools outside GitHub (for example GitLab or Bitbucket)",
  };
  const parts = sections.map((s) => labels[s] ?? s);
  if (parts.length === 1) {
    return parts[0]!;
  }
  if (parts.length === 2) {
    return `${parts[0]} and ${parts[1]}`;
  }
  return `${parts[0]}, ${parts[1]}, and ${parts[2]}`;
}

/** UI-only Slack handoff rows (not persisted); see ``slackHandoffSyntheticMessagesDeduped``. */
function syntheticStakeholderStepMessages(
  answers: Record<string, unknown>,
  startTs: number,
  priorForDedup: ChatMessage[],
): ChatMessage[] {
  return slackHandoffSyntheticMessagesDeduped(
    primaryCommunicationToolLabel(answers),
    startTs,
    priorForDedup,
  );
}

/** Matches persisted PATCH stakeholder user line (raw_text preferred; else @labels). */
function stakeholderAnswerDisplayLine(answers: Record<string, unknown>): string | null {
  const ss = answers.slack_stakeholders;
  if (!ss || typeof ss !== "object" || Array.isArray(ss)) {
    return null;
  }
  const o = ss as Record<string, unknown>;
  const raw = o.raw_text;
  if (typeof raw === "string" && raw.trim()) {
    return raw.trim();
  }
  const labels = o.mention_labels;
  if (Array.isArray(labels) && labels.length > 0) {
    const parts = labels
      .filter((x): x is string => typeof x === "string" && x.trim().length > 0)
      .map((l) => {
        const t = l.trim();
        return t.startsWith("@") ? t : `@${t}`;
      });
    return parts.length > 0 ? parts.join(" ") : null;
  }
  return null;
}

/** Merge API transcript with UI-only stakeholder intros; keep the user's @ reply after Vector's prompts. */
function buildAdminAccessStakeholderBase(
  msgs: ChatMessage[],
  answers: Record<string, unknown>,
): ChatMessage[] {
  if (msgs.some((m) => m.id === ONB_SLACK_HANDOFF_EVENT_ID)) {
    return msgs;
  }
  const stakeholderLine = stakeholderAnswerDisplayLine(answers);
  if (stakeholderLine === null) {
    return msgs;
  }
  const stakeTrim = stakeholderLine.trim();
  const idx = msgs.findIndex(
    (m) => m.role === "user" && m.content.trim() === stakeTrim,
  );
  if (idx < 0) {
    const lastTs = msgs.length > 0 ? Math.max(...msgs.map((m) => m.timestamp)) : Date.now();
    return [...msgs, ...syntheticStakeholderStepMessages(answers, lastTs + 1, msgs)];
  }

  const before = msgs.slice(0, idx);
  const stakeMsg = msgs[idx]!;
  const synth = syntheticStakeholderStepMessages(
    answers,
    stakeMsg.timestamp - 100,
    before,
  ).map((row, i) => ({
    ...row,
    timestamp: stakeMsg.timestamp - 20 + i,
  }));
  return [...before, ...synth, stakeMsg, ...msgs.slice(idx + 1)];
}

function effectiveConnectQueue(answers: Record<string, unknown>, currentStep: string): string[] {
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    return [...(q as string[])];
  }
  if (
    currentStep === "CONNECT_COMMUNICATION" ||
    currentStep === "CONNECT_PROJECT_MANAGEMENT" ||
    currentStep === "CONNECT_ENGINEERING"
  ) {
    const order = connectQueueFromTools(answers);
    return order.length ? [order[0]!] : [];
  }
  return [];
}

function normalizeQueueAfterOAuth(
  answers: Record<string, unknown>,
  currentStep: string,
  provider: LiveConnectorId,
): string[] {
  let queue: string[] = [];
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    queue = [...(q as string[])];
  }
  if (
    queue.length === 0 &&
    (currentStep === "CONNECT_COMMUNICATION" ||
      currentStep === "CONNECT_PROJECT_MANAGEMENT" ||
      currentStep === "CONNECT_ENGINEERING") &&
    (provider === "slack" || provider === "linear" || provider === "github")
  ) {
    queue = [provider];
  }
  if (queue[0] === provider) {
    return queue.slice(1);
  }
  return queue.filter((p) => p !== provider);
}

function onboardingQueryKey(apiBase: string, tenantId: string): [string, string, string] {
  return ["onboarding", apiBase, tenantId];
}

/** Optimistic step/answers + version after POST /onboarding/chat (messages unchanged until next GET). */
function mergeOnboardingFromChat(
  qc: QueryClient,
  apiBase: string,
  tenantId: string | undefined,
  data: { step: string; answers: Record<string, unknown> },
) {
  if (!tenantId) {
    return;
  }
  qc.setQueryData(onboardingQueryKey(apiBase, tenantId), (old: OnboardingStatePayload | undefined) => {
    if (!old) {
      return old;
    }
    return {
      ...old,
      current_step: data.step,
      answers: data.answers,
      version: old.version + 1,
      messages: old.messages,
    };
  });
}

export default function OnboardingPage() {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const me = useProductMeQuery(apiBase);
  const tenantId = me.data?.tenant_id;

  const ob = useQuery({
    queryKey: onboardingQueryKey(apiBase, tenantId ?? ""),
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });

  const slackMembersForStep = useQuery({
    queryKey: ["slack-onboarding-members", apiBase, tenantId ?? ""],
    queryFn: () => fetchSlackWorkspaceMembers(apiBase),
    enabled: Boolean(
      tenantId &&
        ob.data?.current_step &&
        [
          "SLACK_STAKEHOLDERS",
          "SLACK_COLLABORATORS",
          "SLACK_COLLABORATORS_CONFIRM",
          "SLACK_TEAM_MEMBERS",
          "SLACK_TEAM_MEMBERS_CONFIRM",
        ].includes(ob.data.current_step),
    ),
  });

  const slackChannelsForStep = useQuery({
    queryKey: ["slack-onboarding-channels", apiBase, tenantId ?? ""],
    queryFn: () => fetchSlackWorkspaceChannels(apiBase),
    enabled: Boolean(
      tenantId &&
        ob.data?.current_step &&
        ["SLACK_WATCH_CHANNELS", "SLACK_WATCH_CHANNELS_CONFIRM"].includes(ob.data.current_step),
    ),
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [toolPick, setToolPick] = useState<ToolPickState>(() => emptyToolPick());
  const [isTyping, setIsTyping] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  /** True while the chat pipeline or typing indicator is active; used to refocus input when idle. */
  const chatInputHadBusyRef = useRef(false);
  /** After hydrate-from-API or successful opening POST for this onboarding row; cleared on restart / tenant change. */
  const bootstrapCompletedForServerIdRef = useRef<string | null>(null);
  /** Bumped on opening-bootstrap effect cleanup (Strict Mode) and before restart / tenant switch so stale POST asyncs skip apply. */
  const openingBootstrapGenerationRef = useRef(0);

  const [finishOnboardingError, setFinishOnboardingError] = useState<string | null>(null);
  const [stakeholdersSubmitError, setStakeholdersSubmitError] = useState<string | null>(null);
  const [stakeholdersBusy, setStakeholdersBusy] = useState(false);
  const [collaboratorsSubmitError, setCollaboratorsSubmitError] = useState<string | null>(null);
  const [collaboratorsBusy, setCollaboratorsBusy] = useState(false);
  const [slackTeamSubmitError, setSlackTeamSubmitError] = useState<string | null>(null);
  const [slackTeamBusy, setSlackTeamBusy] = useState(false);
  const [slackWatchChannelsSubmitError, setSlackWatchChannelsSubmitError] = useState<string | null>(null);
  const [slackWatchChannelsBusy, setSlackWatchChannelsBusy] = useState(false);
  /** Shown when ?*_connected=1 is in the URL but GET /onboarding does not reflect the link yet, or PATCH fails. */
  const [oauthReturnError, setOauthReturnError] = useState<string | null>(null);
  const oauthAdvanceLockRef = useRef<string | null>(null);
  const completeOnboardingGoAppRef = useRef(false);
  const prevTenantForResetRef = useRef<string | undefined>(undefined);
  /** Connectors intro: both chips visible, or only "ready" after "Ask a question". */
  const [connectorsIntroChipMode, setConnectorsIntroChipMode] = useState<"both" | "ready_only">(
    "both",
  );
  const [restartDialogOpen, setRestartDialogOpen] = useState(false);
  const [restartError, setRestartError] = useState<string | null>(null);

  const server = ob.data;

  const resetLocalOnboardingUi = useCallback(() => {
    bootstrapCompletedForServerIdRef.current = null;
    setMessages([]);
    setChatInput("");
    setToolPick(emptyToolPick());
    setIsTyping(false);
    setChatBusy(false);
    chatInputHadBusyRef.current = false;
    setConnectorsIntroChipMode("both");
    setStakeholdersSubmitError(null);
    setCollaboratorsSubmitError(null);
    setSlackTeamSubmitError(null);
    setSlackWatchChannelsSubmitError(null);
    setFinishOnboardingError(null);
    oauthAdvanceLockRef.current = null;
  }, [tenantId]);

  /** Clear local chat state when switching accounts (React Query cache is tenant-scoped; refs/state are not). */
  useEffect(() => {
    if (!tenantId) {
      return;
    }
    if (prevTenantForResetRef.current === undefined) {
      prevTenantForResetRef.current = tenantId;
      return;
    }
    if (prevTenantForResetRef.current === tenantId) {
      return;
    }
    prevTenantForResetRef.current = tenantId;
    openingBootstrapGenerationRef.current += 1;
    bootstrapCompletedForServerIdRef.current = null;
    setMessages([]);
    setChatInput("");
    setToolPick(emptyToolPick());
    setIsTyping(false);
    setChatBusy(false);
    chatInputHadBusyRef.current = false;
    setFinishOnboardingError(null);
    setOauthReturnError(null);
    oauthAdvanceLockRef.current = null;
    setConnectorsIntroChipMode("both");
  }, [tenantId]);

  /**
   * Restore persisted chat from GET /onboarding before bootstrap. Same onboarding row id survives
   * restart; ``bootstrapCompletedForServerIdRef`` is cleared in ``resetLocalOnboardingUi`` so we
   * re-hydrate or bootstrap again after ``POST /onboarding/restart``.
   */
  useEffect(() => {
    if (!server) {
      return;
    }
    if (bootstrapCompletedForServerIdRef.current === server.id) {
      return;
    }
    const apiMsgs = server.messages ?? [];
    if (!apiMsgs.length) {
      return;
    }
    setMessages(apiMsgs.map(mapServerMessageToChatMessage));
    bootstrapCompletedForServerIdRef.current = server.id;
  }, [server]);

  /** Connector OAuth, Slack stakeholders, and admin CTA: hydrate chat from API (e.g. persisted \"… connected\" lines). */
  useEffect(() => {
    if (!server) {
      return;
    }
    const hydrateSteps: OnboardingStep[] = [
      "CONNECT_PROJECT_MANAGEMENT",
      "CONNECT_ENGINEERING",
      "CONNECT_COMMUNICATION",
      "SLACK_STAKEHOLDERS",
      "SLACK_COLLABORATORS",
      "SLACK_COLLABORATORS_CONFIRM",
      "SLACK_TEAM_MEMBERS",
      "SLACK_TEAM_MEMBERS_CONFIRM",
      "SLACK_WATCH_CHANNELS",
      "SLACK_WATCH_CHANNELS_CONFIRM",
      "ADMIN_ACCESS",
    ];
    if (!hydrateSteps.includes(server.current_step as OnboardingStep)) {
      return;
    }
    const apiMsgs = server.messages;
    if (!apiMsgs?.length) {
      return;
    }
    setMessages(apiMsgs.map(mapServerMessageToChatMessage));
  }, [server?.current_step, server?.id, server?.version]);

  const displayStep: OnboardingStep | null = useMemo(() => {
    if (!server) {
      return null;
    }
    if (server.status === "completed") {
      return "THANK_YOU";
    }
    return server.current_step as OnboardingStep;
  }, [server]);

  const otherManagersForWrapUp = useMemo(() => {
    if (!server) {
      return [];
    }
    return otherSlackCollaboratorsExcludingStakeholder(server.answers);
  }, [server?.answers, server?.version]);

  const wrapUpTailMessages = useMemo((): ChatMessage[] => {
    if (displayStep !== "ADMIN_ACCESS" || !server) {
      return [];
    }
    const lastTs = messages.length > 0 ? Math.max(...messages.map((m) => m.timestamp)) : Date.now();
    const t0 = lastTs + 15;
    const thanks: ChatMessage = {
      id: "onb-wrap-up-thanks",
      role: "vector",
      content: ONBOARDING_WRAP_UP_THANKS,
      timestamp: t0,
    };
    if (otherManagersForWrapUp.length === 0) {
      return [thanks];
    }
    const handles = otherManagersForWrapUp.map((m) => slackPersonChipText(m)).join(", ");
    return [
      thanks,
      {
        id: "onb-wrap-up-manager-ask",
        role: "vector",
        content: wrapUpManagerIntroQuestion(handles),
        timestamp: t0 + 1,
      },
    ];
  }, [displayStep, server, messages, otherManagersForWrapUp]);

  const adminAccessDisplayMessages = useMemo(() => {
    if (displayStep !== "ADMIN_ACCESS" || !server) {
      return [];
    }
    const base = buildAdminAccessStakeholderBase(messages, server.answers);
    return reorderOnboardingTranscriptForDisplay([...base, ...wrapUpTailMessages], server.answers);
  }, [displayStep, server, messages, wrapUpTailMessages]);

  const thankYou = Boolean(server && (server.status === "completed" || displayStep === "THANK_YOU"));

  const profilePhase = useMemo(() => {
    const p = server?.answers.profile_phase;
    return typeof p === "string" ? p : "name";
  }, [server?.answers.profile_phase]);

  useEffect(() => {
    if (profilePhase !== "connectors_intro") {
      setConnectorsIntroChipMode("both");
    }
  }, [profilePhase]);

  /** After Vector finishes typing or the chat request completes, keep focus in the message field. */
  useEffect(() => {
    const busy = chatBusy || isTyping;
    const onChatProfile = displayStep === "CHAT_PROFILE";
    const connectorsIntroInputLocked =
      profilePhase === "connectors_intro" && connectorsIntroChipMode === "both";
    if (
      chatInputHadBusyRef.current &&
      !busy &&
      onChatProfile &&
      !connectorsIntroInputLocked
    ) {
      const id = window.requestAnimationFrame(() => {
        chatInputRef.current?.focus({ preventScroll: true });
      });
      return () => window.cancelAnimationFrame(id);
    }
    chatInputHadBusyRef.current = busy;
  }, [chatBusy, isTyping, displayStep, profilePhase, connectorsIntroChipMode]);

  const userLabel = "You";

  /** Tool picker groups (mirrors ``ONBOARDING_TOOL_GROUPS`` / backend catalog). */
  const toolGroupsUi = ONBOARDING_TOOL_GROUPS;

  useEffect(() => {
    if (!server || profilePhase !== "tools") {
      return;
    }
    setToolPick(hydrateToolPickFromAnswers(server.answers));
  }, [server?.id, server?.version, profilePhase]);

  const patchMut = useMutation({
    mutationFn: (body: Parameters<typeof patchOnboarding>[1]) => patchOnboarding(apiBase, body),
    onSuccess: () => {
      if (tenantId) {
        void qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
      }
    },
  });

  const finishOnboardingMut = useMutation({
    mutationFn: () => completeOnboarding(apiBase),
    onMutate: () => setFinishOnboardingError(null),
    onSuccess: async () => {
      const goApp = completeOnboardingGoAppRef.current;
      completeOnboardingGoAppRef.current = false;
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
      }
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      if (goApp) {
        navigate("/app", { replace: true });
      }
    },
    onError: (e: unknown) => {
      setFinishOnboardingError(e instanceof Error ? e.message : "Could not finish onboarding.");
    },
  });

  const patchConsentThenComplete = useCallback(
    async (choice: "yes" | "later" | "not_applicable") => {
      setFinishOnboardingError(null);
      try {
        await patchOnboarding(apiBase, { answers: { slack_introduce_managers_consent: choice } });
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        }
        completeOnboardingGoAppRef.current = true;
        await finishOnboardingMut.mutateAsync();
      } catch (e) {
        setFinishOnboardingError(e instanceof Error ? e.message : "Could not finish setup.");
      }
    },
    [apiBase, qc, tenantId, finishOnboardingMut],
  );

  const restartOnboardingMut = useMutation({
    mutationFn: () => postRestartOnboarding(apiBase),
    onMutate: () => setRestartError(null),
    onSuccess: async (data: OnboardingStatePayload) => {
      // Drop any in-flight opening POST from *before* restart. Do not bump again in
      // resetLocalOnboardingUi — that ran after setQueryData and invalidated the *new* bootstrap.
      openingBootstrapGenerationRef.current += 1;
      if (tenantId) {
        qc.setQueryData(onboardingQueryKey(apiBase, tenantId), {
          ...data,
          messages: data.messages ?? [],
        });
      }
      resetLocalOnboardingUi();
      setRestartDialogOpen(false);
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
      }
    },
    onError: (e: unknown) => {
      setRestartError(e instanceof Error ? e.message : "Could not restart onboarding.");
    },
  });

  const restartTextLinkClass =
    "text-[13px] font-medium text-zinc-500 underline decoration-zinc-300/80 underline-offset-2 hover:text-zinc-800 disabled:cursor-not-allowed disabled:opacity-45";

  const onboardingHeaderTrailing = (
    <button
      type="button"
      className={restartTextLinkClass}
      disabled={restartOnboardingMut.isPending}
      onClick={() => setRestartDialogOpen(true)}
    >
      Clear &amp; restart
    </button>
  );

  const restartConfirmOverlay =
    restartDialogOpen ? (
      <div
        className="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/45 p-4 backdrop-blur-[1px]"
        role="presentation"
        onMouseDown={(e) => {
          if (e.target === e.currentTarget && !restartOnboardingMut.isPending) {
            setRestartDialogOpen(false);
          }
        }}
      >
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="restart-onboarding-title"
          className="w-full max-w-md rounded-2xl border border-zinc-200/90 bg-white p-6 shadow-2xl"
          onMouseDown={(e) => e.stopPropagation()}
        >
          <h2 id="restart-onboarding-title" className="text-lg font-semibold text-zinc-900">
            Start onboarding over?
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-zinc-600">
            Your chat history and saved answers will be cleared, and the display name saved from
            onboarding is removed so you can enter it again. Connected tools (Slack, GitHub, Linear,
            etc.) stay linked to this workspace. You cannot undo this.
          </p>
          {restartError ? <p className="mt-3 text-sm text-red-700">{restartError}</p> : null}
          <div className="mt-6 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              className="rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50 disabled:opacity-50"
              disabled={restartOnboardingMut.isPending}
              onClick={() => setRestartDialogOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="rounded-full bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-800 disabled:opacity-50"
              disabled={restartOnboardingMut.isPending}
              onClick={() => restartOnboardingMut.mutate()}
            >
              {restartOnboardingMut.isPending ? "Restarting…" : "Clear and restart"}
            </button>
          </div>
        </div>
      </div>
    ) : null;

  const goToStep = useCallback(
    (step: OnboardingStep, answers?: Record<string, unknown>) => {
      patchMut.mutate({ current_step: step, answers });
    },
    [patchMut],
  );

  const continueAfterManualConnect = useCallback(
    (provider: LiveConnectorId) => {
      if (!server) {
        return;
      }
      let queue = [...effectiveConnectQueue(server.answers, server.current_step)];
      if (liveProviderConnected(provider, server)) {
        if (queue[0] === provider) {
          queue = queue.slice(1);
        } else {
          queue = queue.filter((p) => p !== provider);
        }
        if (queue.length === 0) {
          const tools = server.answers.tools as Record<string, string[]> | undefined;
          const comm = tools?.communication ?? [];
          if (comm.includes("slack") && server.slack_connected) {
            patchMut.mutate({
              current_step: "SLACK_STAKEHOLDERS",
              answers: { ...server.answers, connect_queue: [], connect_plan: [] },
            });
          } else {
            finishOnboardingMut.mutate();
          }
        } else {
          const next = queue[0] as ConnectorQueueId;
          goToStep(NextConnectStep(next), {
            ...server.answers,
            connect_queue: queue,
            connect_plan: queue,
          });
        }
        return;
      }
      if (queue[0] !== provider) {
        return;
      }
      const rest = queue.slice(1);
      if (rest.length === 0) {
        finishOnboardingMut.mutate();
      } else {
        const next = rest[0] as ConnectorQueueId;
        goToStep(NextConnectStep(next), {
          ...server.answers,
          connect_queue: rest,
          connect_plan: rest,
        });
      }
    },
    [server, goToStep, finishOnboardingMut, patchMut],
  );

  const submitSlackStakeholders = useCallback(
    async (payload: { text: string; slack_user_ids: string[]; mention_labels: string[] }) => {
      if (payload.slack_user_ids.length === 0) {
        return;
      }
      setStakeholdersSubmitError(null);
      setStakeholdersBusy(true);
      try {
        const uid = payload.slack_user_ids[0]!;
        const username = payload.text.trim().replace(/^@/, "") || uid;
        const labelRaw = payload.mention_labels[0];
        const label =
          typeof labelRaw === "string" && labelRaw.trim() ? labelRaw.trim() : username;
        await patchOnboarding(apiBase, {
          current_step: "SLACK_COLLABORATORS",
          answers: {
            slack_stakeholders: {
              raw_text: payload.text,
              slack_user_ids: payload.slack_user_ids,
              mention_labels: payload.mention_labels,
            },
            slack_collaborators: {
              members: [{ slack_user_id: uid, username, label }],
            },
          },
        });
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        }
      } catch (e) {
        setStakeholdersSubmitError(e instanceof Error ? e.message : "Could not save stakeholders.");
      } finally {
        setStakeholdersBusy(false);
      }
    },
    [apiBase, qc, tenantId],
  );

  const collaboratorsPickInitial = useMemo((): SlackCollaboratorMember[] => {
    if (!server) {
      return [];
    }
    const fromAnswers = slackCollaboratorsFromAnswers(server.answers);
    if (fromAnswers.length > 0) {
      return fromAnswers;
    }
    return seedCollaboratorsFromStakeholders(server.answers);
  }, [server?.answers, server?.version]);

  const collaboratorsConfirmList = useMemo((): SlackCollaboratorMember[] => {
    if (!server) {
      return [];
    }
    return slackCollaboratorsFromAnswers(server.answers);
  }, [server?.answers, server?.version]);

  const collaboratorSlackUserIdsExcludeForTeam = useMemo(() => {
    if (!server) {
      return [];
    }
    return slackCollaboratorsFromAnswers(server.answers).map((m) => m.slack_user_id);
  }, [server?.answers, server?.version]);

  const teamMembersPickInitial = useMemo((): SlackCollaboratorMember[] => {
    if (!server) {
      return [];
    }
    return slackTeamMembersFromAnswers(server.answers);
  }, [server?.answers, server?.version]);

  const teamMembersConfirmList = useMemo((): SlackCollaboratorMember[] => {
    if (!server) {
      return [];
    }
    return slackTeamMembersFromAnswers(server.answers);
  }, [server?.answers, server?.version]);

  const slackTeamPickIntroVariant = useMemo(() => {
    if (!server) {
      return "with_other_managers" as const;
    }
    return otherSlackCollaboratorsExcludingStakeholder(server.answers).length === 0
      ? ("solo_manager" as const)
      : ("with_other_managers" as const);
  }, [server?.answers, server?.version]);

  const slackTeamPickIntroMessages = useMemo(
    () => slackTeamMembersPickIntroMessages(Date.now(), slackTeamPickIntroVariant),
    [server?.current_step, server?.version, slackTeamPickIntroVariant],
  );
  const slackTeamConfirmIntroMessages = useMemo(
    () => slackTeamMembersConfirmIntroMessages(Date.now()),
    [server?.current_step, server?.version],
  );
  const slackWatchPickIntroMessages = useMemo(
    () => slackWatchChannelsPickIntroMessages(Date.now()),
    [server?.current_step, server?.version],
  );
  const slackWatchConfirmIntroMessages = useMemo(
    () => slackWatchChannelsConfirmIntroMessages(Date.now()),
    [server?.current_step, server?.version],
  );

  const watchChannelsPickInitial = useMemo(() => {
    if (!server) {
      return [];
    }
    return slackWatchChannelsFromAnswers(server.answers);
  }, [server?.answers, server?.version]);

  const watchChannelsConfirmList = useMemo(() => {
    if (!server) {
      return [];
    }
    return slackWatchChannelsFromAnswers(server.answers);
  }, [server?.answers, server?.version]);

  const submitCollaboratorsPick = useCallback(
    async (members: SlackCollaboratorMember[]) => {
      setCollaboratorsSubmitError(null);
      setCollaboratorsBusy(true);
      try {
        await patchOnboarding(apiBase, {
          current_step: "SLACK_COLLABORATORS_CONFIRM",
          answers: { slack_collaborators: { members } },
        });
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        }
      } catch (e) {
        setCollaboratorsSubmitError(
          e instanceof Error ? e.message : "Could not save your collaborator list.",
        );
      } finally {
        setCollaboratorsBusy(false);
      }
    },
    [apiBase, qc, tenantId],
  );

  const submitCollaboratorsConfirmEdit = useCallback(async () => {
    setCollaboratorsSubmitError(null);
    setCollaboratorsBusy(true);
    try {
      await patchOnboarding(apiBase, { current_step: "SLACK_COLLABORATORS" });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setCollaboratorsSubmitError(e instanceof Error ? e.message : "Could not go back to edit.");
    } finally {
      setCollaboratorsBusy(false);
    }
  }, [apiBase, qc, tenantId]);

  const submitCollaboratorsConfirmContinue = useCallback(async () => {
    if (!server) {
      return;
    }
    setCollaboratorsSubmitError(null);
    setCollaboratorsBusy(true);
    try {
      const nextStep: OnboardingStep = collaboratorsIncludesStakeholderSelf(server.answers)
        ? "SLACK_TEAM_MEMBERS"
        : "ADMIN_ACCESS";
      await patchOnboarding(apiBase, { current_step: nextStep });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setCollaboratorsSubmitError(e instanceof Error ? e.message : "Could not continue.");
    } finally {
      setCollaboratorsBusy(false);
    }
  }, [apiBase, qc, tenantId, server]);

  const submitTeamMembersPick = useCallback(
    async (members: SlackCollaboratorMember[]) => {
      setSlackTeamSubmitError(null);
      setSlackTeamBusy(true);
      try {
        await patchOnboarding(apiBase, {
          current_step: "SLACK_TEAM_MEMBERS_CONFIRM",
          answers: { slack_team_members: { members } },
        });
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        }
      } catch (e) {
        setSlackTeamSubmitError(e instanceof Error ? e.message : "Could not save your team list.");
      } finally {
        setSlackTeamBusy(false);
      }
    },
    [apiBase, qc, tenantId],
  );

  const submitTeamMembersConfirmEdit = useCallback(async () => {
    setSlackTeamSubmitError(null);
    setSlackTeamBusy(true);
    try {
      await patchOnboarding(apiBase, { current_step: "SLACK_TEAM_MEMBERS" });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setSlackTeamSubmitError(e instanceof Error ? e.message : "Could not go back to edit.");
    } finally {
      setSlackTeamBusy(false);
    }
  }, [apiBase, qc, tenantId]);

  const submitTeamMembersConfirmContinue = useCallback(async () => {
    setSlackTeamSubmitError(null);
    setSlackTeamBusy(true);
    try {
      await patchOnboarding(apiBase, { current_step: "SLACK_WATCH_CHANNELS" });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setSlackTeamSubmitError(e instanceof Error ? e.message : "Could not continue.");
    } finally {
      setSlackTeamBusy(false);
    }
  }, [apiBase, qc, tenantId]);

  const submitWatchChannelsPick = useCallback(
    async (channels: { channel_id: string; name: string }[]) => {
      setSlackWatchChannelsSubmitError(null);
      setSlackWatchChannelsBusy(true);
      try {
        await patchOnboarding(apiBase, {
          current_step: "SLACK_WATCH_CHANNELS_CONFIRM",
          answers: { slack_watch_channels: { channels } },
        });
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        }
      } catch (e) {
        setSlackWatchChannelsSubmitError(
          e instanceof Error ? e.message : "Could not save your channel list.",
        );
      } finally {
        setSlackWatchChannelsBusy(false);
      }
    },
    [apiBase, qc, tenantId],
  );

  const submitWatchChannelsConfirmEdit = useCallback(async () => {
    setSlackWatchChannelsSubmitError(null);
    setSlackWatchChannelsBusy(true);
    try {
      await patchOnboarding(apiBase, { current_step: "SLACK_WATCH_CHANNELS" });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setSlackWatchChannelsSubmitError(e instanceof Error ? e.message : "Could not go back to edit.");
    } finally {
      setSlackWatchChannelsBusy(false);
    }
  }, [apiBase, qc, tenantId]);

  const submitWatchChannelsConfirmContinue = useCallback(async () => {
    setSlackWatchChannelsSubmitError(null);
    setSlackWatchChannelsBusy(true);
    try {
      await patchOnboarding(apiBase, { current_step: "ADMIN_ACCESS" });
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      }
    } catch (e) {
      setSlackWatchChannelsSubmitError(e instanceof Error ? e.message : "Could not continue.");
    } finally {
      setSlackWatchChannelsBusy(false);
    }
  }, [apiBase, qc, tenantId]);

  const continuePastCommPlaceholder = useCallback(() => {
    if (!server) {
      return;
    }
    const queue = effectiveConnectQueue(server.answers, server.current_step);
    if (queue[0] !== "comm_placeholder") {
      return;
    }
    const rest = queue.slice(1);
    if (rest.length === 0) {
      finishOnboardingMut.mutate();
    } else {
      const next = rest[0] as ConnectorQueueId;
      goToStep(NextConnectStep(next), {
        ...server.answers,
        connect_queue: rest,
        connect_plan: rest,
      });
    }
  }, [server, goToStep, finishOnboardingMut]);

  /**
   * Bootstrap: empty POST for the opening turn, merge cache, show branded opening copy locally.
   * ``server.version`` is a dep so restart (same row id, new version) re-runs after ``resetLocalOnboardingUi``
   * clears ``bootstrapCompletedForServerIdRef``. Merges from chat also bump version, but the early return
   * when ``bootstrapCompletedForServerIdRef`` already matches ``serverId`` prevents duplicate bootstraps.
   * Cleanup bumps ``openingBootstrapGenerationRef`` so Strict Mode’s first async cannot apply after unmount.
   */
  useEffect(() => {
    if (!server || !tenantId || displayStep !== "CHAT_PROFILE") {
      return;
    }
    const serverId = server.id;
    if (bootstrapCompletedForServerIdRef.current === serverId) {
      return;
    }

    const profilePhaseRaw = server.answers.profile_phase;
    const phase = typeof profilePhaseRaw === "string" ? profilePhaseRaw : "name";
    if (phase !== "name") {
      bootstrapCompletedForServerIdRef.current = serverId;
      return;
    }

    let cancelled = false;
    const generation = ++openingBootstrapGenerationRef.current;
    setIsTyping(true);

    void (async () => {
      try {
        const [res] = await Promise.all([
          postOnboardingChat(apiBase, { message: "" }),
          minTypingDelay(420, 780),
        ]);
        if (cancelled || generation !== openingBootstrapGenerationRef.current) {
          return;
        }
        mergeOnboardingFromChat(qc, apiBase, tenantId, { step: res.step, answers: res.answers });
        setMessages([
          {
            id: crypto.randomUUID(),
            role: "vector",
            content: ONBOARDING_OPENING_MESSAGE,
            timestamp: Date.now(),
          },
        ]);
        bootstrapCompletedForServerIdRef.current = serverId;
      } catch (e) {
        if (!cancelled && generation === openingBootstrapGenerationRef.current) {
          setMessages([
            {
              id: crypto.randomUUID(),
              role: "vector",
              content: e instanceof Error ? e.message : "Could not start the conversation.",
              timestamp: Date.now(),
            },
          ]);
        }
      } finally {
        if (!cancelled && generation === openingBootstrapGenerationRef.current) {
          setIsTyping(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      openingBootstrapGenerationRef.current += 1;
      setIsTyping(false);
    };
  }, [server?.id, server?.version, displayStep, apiBase, qc, tenantId]);

  const runChatTurn = useCallback(
    async (payload: { message: string | null; structured_action?: Record<string, unknown> | null }) => {
      if (!tenantId) {
        return;
      }
      setChatBusy(true);
      setIsTyping(true);
      try {
        const res = await postOnboardingChat(apiBase, payload);
        const segments =
          Array.isArray(res.assistant_messages) && res.assistant_messages.length > 0
            ? res.assistant_messages
            : [res.assistant_message];

        for (let i = 0; i < segments.length; i++) {
          if (i === 0) {
            await minTypingDelay(380, 880);
          } else {
            setIsTyping(true);
            await minTypingDelay(400, 900);
          }
          const content = segments[i]!;
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "vector",
              content,
              timestamp: Date.now(),
            },
          ]);
          setIsTyping(i < segments.length - 1);
        }

        mergeOnboardingFromChat(qc, apiBase, tenantId, { step: res.step, answers: res.answers });
      } catch (e) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "vector",
            content: e instanceof Error ? e.message : "Something went wrong.",
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setIsTyping(false);
        setChatBusy(false);
      }
    },
    [apiBase, qc, tenantId],
  );

  const sendChatMessage = useCallback(async () => {
    const text = chatInput.trim();
    if (!text || chatBusy) {
      return;
    }
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setChatInput("");
    await runChatTurn({ message: text, structured_action: null });
  }, [chatInput, chatBusy, runChatTurn]);

  const submitToolsPick = useCallback(async () => {
    if (chatBusy) {
      return;
    }
    if (
      (toolPick.communication ?? []).length === 0 ||
      (toolPick.pm ?? []).length === 0 ||
      (toolPick.engineering ?? []).length === 0
    ) {
      return;
    }
    const toolsPayload = toolPickToBackendPayload(toolPick);
    const structured = { type: "tools_selected" as const, tools: toolsPayload };
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: JSON.stringify(structured),
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    await runChatTurn({
      message: null,
      structured_action: structured,
    });
  }, [chatBusy, runChatTurn, toolPick]);

  const submitConnectorsIntroReady = useCallback(async () => {
    if (chatBusy) {
      return;
    }
    const structured = { type: "connectors_intro_ready" as const };
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: "I'm ready to choose tools",
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    await runChatTurn({
      message: null,
      structured_action: structured,
    });
  }, [chatBusy, runChatTurn]);

  const onConnectorsIntroAskChip = useCallback(() => {
    setConnectorsIntroChipMode("ready_only");
    window.requestAnimationFrame(() => {
      chatInputRef.current?.focus({ preventScroll: true });
    });
  }, []);

  const toggleTool = useCallback((categoryKey: string, toolId: string) => {
    setToolPick((prev) => {
      const cur = [...(prev[categoryKey] ?? [])];
      if (categoryKey === "communication") {
        if (cur.includes(toolId)) {
          return { ...prev, [categoryKey]: [] };
        }
        return { ...prev, [categoryKey]: [toolId] };
      }
      if (cur.includes(toolId)) {
        return { ...prev, [categoryKey]: cur.filter((id) => id !== toolId) };
      }
      return { ...prev, [categoryKey]: [...cur, toolId] };
    });
  }, []);

  /** Advance OAuth return for Linear, GitHub, or Slack during onboarding. */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gh = params.get("github_connected");
    const lin = params.get("linear_connected");
    const sl = params.get("slack_connected");
    if (gh !== "1" && lin !== "1" && sl !== "1") {
      oauthAdvanceLockRef.current = null;
      return;
    }
    if (!tenantId) {
      return;
    }
    const lockKey = `${tenantId}:${gh ?? ""}:${lin ?? ""}:${sl ?? ""}`;
    if (oauthAdvanceLockRef.current === lockKey) {
      return;
    }
    oauthAdvanceLockRef.current = lockKey;

    const stripOauthParams = () => {
      window.history.replaceState({}, "", "/app/onboarding");
    };

    void (async () => {
      try {
        setOauthReturnError(null);
        const fresh = await fetchOnboarding(apiBase);
        const provider: LiveConnectorId | null =
          gh === "1" ? "github" : lin === "1" ? "linear" : sl === "1" ? "slack" : null;
        if (!provider) {
          stripOauthParams();
          return;
        }
        if (!liveProviderConnected(provider, fresh)) {
          const label = provider === "slack" ? "Slack" : provider === "github" ? "GitHub" : "Linear";
          const msg =
            `${label} authorization may have finished in the browser, but this workspace is not linked yet. ` +
            (provider === "slack"
              ? "Common causes: token exchange failed (redirect URL in Slack app must exactly match SLACK_CALLBACK_URL), " +
                "or session cookie not sent to the API (use the same host for the app and VITE_API_BASE_URL, e.g. only localhost or only 127.0.0.1)."
              : "Check redirect URLs and that you are signed in on the same API host as the app.");
          setOauthReturnError(msg);
          console.error(`[onboarding] OAuth return: ${provider}_connected=1 in URL but GET /onboarding is false`);
          stripOauthParams();
          return;
        }

        const nextQueue = normalizeQueueAfterOAuth(fresh.answers, fresh.current_step, provider);
        const tools = fresh.answers.tools as Record<string, string[]> | undefined;
        const comm = tools?.communication ?? [];

        if (nextQueue.length === 0) {
          if (comm.includes("slack") && fresh.slack_connected) {
            await patchOnboarding(apiBase, {
              current_step: "SLACK_STAKEHOLDERS",
              answers: {
                ...fresh.answers,
                connect_queue: [],
                connect_plan: [],
              },
            });
          } else if (comm.includes("slack")) {
            await patchOnboarding(apiBase, {
              current_step: "CONNECT_COMMUNICATION",
              answers: {
                ...fresh.answers,
                connect_queue: ["slack"],
                connect_plan: ["slack"],
              },
            });
          } else if (comm.includes("ms_teams") || comm.includes("discord")) {
            await patchOnboarding(apiBase, {
              current_step: "CONNECT_COMMUNICATION",
              answers: {
                ...fresh.answers,
                connect_queue: ["comm_placeholder"],
                connect_plan: ["comm_placeholder"],
              },
            });
          } else {
            await patchOnboarding(apiBase, {
              current_step: "SCANNING",
              answers: {
                ...fresh.answers,
                connect_queue: [],
                connect_plan: [],
              },
            });
          }
        } else {
          const next = nextQueue[0] as ConnectorQueueId;
          await patchOnboarding(apiBase, {
            current_step: NextConnectStep(next),
            answers: {
              ...fresh.answers,
              connect_queue: nextQueue,
              connect_plan: nextQueue,
            },
          });
        }
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
        stripOauthParams();
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Could not update onboarding after OAuth.";
        setOauthReturnError(msg);
        console.error("[onboarding] OAuth return advance failed", e);
        stripOauthParams();
      } finally {
        oauthAdvanceLockRef.current = null;
      }
    })();
  }, [apiBase, qc, tenantId]);

  /** Older tenants mid GitHub/Linear/scanning flow: complete onboarding in one shot. */
  useEffect(() => {
    if (!server || !tenantId || server.status === "completed") {
      return;
    }
    const s = server.current_step;
    if (s !== "SCANNING") {
      return;
    }
    finishOnboardingMut.mutate();
  }, [server?.id, server?.current_step, server?.status, tenantId, finishOnboardingMut]);

  if (!tenantId) {
    return (
      <OnboardingChatLayout showHeader={false}>
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
          <p className="font-display text-sm font-medium text-zinc-500">Loading…</p>
        </div>
      </OnboardingChatLayout>
    );
  }

  if (ob.isError) {
    return (
      <>
        <OnboardingChatLayout showHeader={false}>
          <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 py-16">
            <p className="text-center text-sm text-red-700">{(ob.error as Error).message}</p>
            <button
              type="button"
              className={restartTextLinkClass}
              disabled={restartOnboardingMut.isPending}
              onClick={() => setRestartDialogOpen(true)}
            >
              Clear chat &amp; restart setup
            </button>
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (!server) {
    return (
      <OnboardingChatLayout showHeader={false}>
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-24">
          <p className="font-display text-sm font-medium text-zinc-500">Loading…</p>
        </div>
      </OnboardingChatLayout>
    );
  }

  if (thankYou) {
    return (
      <>
        <OnboardingChatLayout showHeader={false}>
          <div className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
            <div className="max-w-xl space-y-6">
              <h1 className="font-display text-3xl font-semibold tracking-tight text-zinc-900">
                You&apos;re early. We&apos;re learning with you.
              </h1>
              <p className="text-lg leading-relaxed text-zinc-600">
                You&apos;re in. Vector is processing activity from your connected tools. We&apos;re working with a small group of design
                partners. We&apos;ll be back soon with the first execution insights.
              </p>
              <button
                type="button"
                className="mt-2 rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                onClick={() => navigate("/app/connectors", { replace: true })}
              >
                Go to connectors
              </button>
              <p className="pt-2 text-sm text-zinc-500">
                <Link to="/app" className="text-[#E878BE] underline decoration-[#E878BE]/40 underline-offset-2 hover:text-[#BE5E94]">
                  App home
                </Link>
                <span className="mx-2 text-zinc-300" aria-hidden>
                  ·
                </span>
                <button
                  type="button"
                  className={`${restartTextLinkClass} align-baseline`}
                  disabled={restartOnboardingMut.isPending}
                  onClick={() => setRestartDialogOpen(true)}
                >
                  Run setup again
                </button>
              </p>
            </div>
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  const legacyOnboardingWizardStep = server.status !== "completed" && displayStep === "SCANNING";

  if (legacyOnboardingWizardStep) {
    return (
      <>
        <OnboardingChatLayout showHeader={false}>
          <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 py-24 text-center">
            {finishOnboardingError ? (
              <>
                <p className="max-w-md text-sm text-red-700">{finishOnboardingError}</p>
                <button
                  type="button"
                  className="rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                  onClick={() => finishOnboardingMut.mutate()}
                >
                  Try again
                </button>
              </>
            ) : (
              <p className="font-display text-sm font-medium text-zinc-500">Finishing your setup…</p>
            )}
            {finishOnboardingError ? (
              <button
                type="button"
                className={restartTextLinkClass}
                disabled={restartOnboardingMut.isPending}
                onClick={() => setRestartDialogOpen(true)}
              >
                Or clear everything and restart onboarding
              </button>
            ) : null}
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "ADMIN_ACCESS" && server) {
    const wrapUpPrimaryButtonClass =
      "w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white " +
      "shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] " +
      "disabled:cursor-not-allowed disabled:opacity-50 " +
      landingAccentText;
    const wrapUpSecondaryButtonClass =
      "w-full rounded-full border border-zinc-200 bg-white px-8 py-3 text-sm font-medium text-zinc-800 " +
      "transition hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto sm:min-w-[10rem]";

    const adminAccessFooter = (
      <div className="space-y-3 px-4 pb-4 pt-2 sm:px-5">
        {finishOnboardingError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-center text-sm text-red-950">
            {finishOnboardingError}
          </p>
        ) : null}
        {otherManagersForWrapUp.length > 0 ? (
          <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
            <button
              type="button"
              disabled={finishOnboardingMut.isPending}
              className={wrapUpPrimaryButtonClass}
              onClick={() => void patchConsentThenComplete("yes")}
            >
              {finishOnboardingMut.isPending ? "Saving…" : "Yes, go ahead"}
            </button>
            <button
              type="button"
              disabled={finishOnboardingMut.isPending}
              className={wrapUpSecondaryButtonClass}
              onClick={() => void patchConsentThenComplete("later")}
            >
              Maybe later
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={finishOnboardingMut.isPending}
            className={wrapUpPrimaryButtonClass}
            onClick={() => void patchConsentThenComplete("not_applicable")}
          >
            {finishOnboardingMut.isPending ? "Opening…" : "Finish the onboarding"}
          </button>
        )}
      </div>
    );

    return (
      <>
        <OnboardingChatLayout footer={adminAccessFooter} headerTrailing={onboardingHeaderTrailing}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList
              messages={adminAccessDisplayMessages}
              userDisplayName={userLabel}
              isTyping={isTyping}
            />
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_STAKEHOLDERS") {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackStakeholdersPanel
            priorChatMessages={messages}
            communicationToolLabel={primaryCommunicationToolLabel(server.answers)}
            signupEmail={me.data?.email ?? ""}
            members={slackMembersForStep.data ?? []}
            membersLoading={slackMembersForStep.isLoading}
            membersError={
              slackMembersForStep.error ? (slackMembersForStep.error as Error).message : null
            }
            submitError={stakeholdersSubmitError}
            submitting={stakeholdersBusy}
            onSubmit={submitSlackStakeholders}
            userDisplayName={userLabel}
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_COLLABORATORS_CONFIRM" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackCollaboratorsConfirmPanel
            priorChatMessages={messages}
            members={collaboratorsConfirmList}
            rosterMembers={slackMembersForStep.data ?? []}
            submitError={collaboratorsSubmitError}
            submitting={collaboratorsBusy}
            onEdit={() => void submitCollaboratorsConfirmEdit()}
            onContinue={() => void submitCollaboratorsConfirmContinue()}
            userDisplayName={userLabel}
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_WATCH_CHANNELS_CONFIRM" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackChannelsConfirmPanel
            priorChatMessages={messages}
            confirmIntroMessages={slackWatchConfirmIntroMessages}
            listTitle="Channels we will watch for your team"
            channels={watchChannelsConfirmList}
            submitError={slackWatchChannelsSubmitError}
            submitting={slackWatchChannelsBusy}
            onEdit={() => void submitWatchChannelsConfirmEdit()}
            onContinue={() => void submitWatchChannelsConfirmContinue()}
            userDisplayName={userLabel}
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_WATCH_CHANNELS" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackChannelsPickPanel
            priorChatMessages={messages}
            introMessages={slackWatchPickIntroMessages}
            channels={slackChannelsForStep.data ?? []}
            channelsLoading={slackChannelsForStep.isLoading}
            channelsError={
              slackChannelsForStep.error ? (slackChannelsForStep.error as Error).message : null
            }
            initialChannels={watchChannelsPickInitial}
            initialChannelsKey={String(server.version)}
            submitError={slackWatchChannelsSubmitError}
            submitting={slackWatchChannelsBusy}
            onContinue={(ch) => void submitWatchChannelsPick(ch)}
            userDisplayName={userLabel}
            emptyHint="No channels selected yet. Search below or continue with an empty list."
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_TEAM_MEMBERS_CONFIRM" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackPeopleMultiConfirmPanel
            priorChatMessages={messages}
            confirmIntroMessages={slackTeamConfirmIntroMessages}
            listTitle="Team members you selected"
            members={teamMembersConfirmList}
            rosterMembers={slackMembersForStep.data ?? []}
            submitError={slackTeamSubmitError}
            submitting={slackTeamBusy}
            onEdit={() => void submitTeamMembersConfirmEdit()}
            onContinue={() => void submitTeamMembersConfirmContinue()}
            userDisplayName={userLabel}
            requireNonEmpty={false}
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_TEAM_MEMBERS" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackPeopleMultiPickPanel
            priorChatMessages={messages}
            introMessages={slackTeamPickIntroMessages}
            members={slackMembersForStep.data ?? []}
            membersLoading={slackMembersForStep.isLoading}
            membersError={slackMembersForStep.error ? (slackMembersForStep.error as Error).message : null}
            excludeSlackUserIds={collaboratorSlackUserIdsExcludeForTeam}
            initialMembers={teamMembersPickInitial}
            initialMembersKey={String(server.version)}
            submitError={slackTeamSubmitError}
            submitting={slackTeamBusy}
            onContinue={(m) => void submitTeamMembersPick(m)}
            userDisplayName={userLabel}
            requireAtLeastOne={false}
            emptyHint="No teammates listed yet. You can add people below or continue with an empty list."
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "SLACK_COLLABORATORS" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <SlackCollaboratorsPickPanel
            priorChatMessages={messages}
            members={slackMembersForStep.data ?? []}
            membersLoading={slackMembersForStep.isLoading}
            membersError={slackMembersForStep.error ? (slackMembersForStep.error as Error).message : null}
            initialMembers={collaboratorsPickInitial}
            initialMembersKey={String(server.version)}
            submitError={collaboratorsSubmitError}
            submitting={collaboratorsBusy}
            onContinue={(m) => void submitCollaboratorsPick(m)}
            userDisplayName={userLabel}
          />
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  const connectorsIntroChipClass = [
    "cursor-pointer rounded-full border border-[#E878BE]/45 bg-gradient-to-br from-[#FDE8F4]/95 via-[#FCE8F2]/90 to-[#F8D4E8]/75",
    "px-3.5 py-1.5 text-[13px] font-semibold shadow-[0_8px_24px_-14px_rgba(232,120,190,0.55)]",
    "transition hover:border-[#E878BE]/60 hover:brightness-[1.02] active:scale-[0.99]",
    "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-40",
    landingAccentText,
  ].join(" ");

  if (displayStep === "CHAT_PROFILE") {
    const showTools = profilePhase === "tools";
    const showConnectorsIntro = profilePhase === "connectors_intro";
    const chatScrollArea = (
      <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
    );
    const connectorsIntroChips = showConnectorsIntro ? (
      <div className="shrink-0 border-t border-zinc-100/80 bg-gradient-to-b from-zinc-50/50 to-white px-3 py-2.5 sm:px-4">
        <div className="flex flex-wrap items-center justify-center gap-2">
          {connectorsIntroChipMode === "both" ? (
            <>
              <button
                type="button"
                className={connectorsIntroChipClass}
                disabled={chatBusy || isTyping}
                onClick={() => onConnectorsIntroAskChip()}
              >
                Ask a question
              </button>
              <button
                type="button"
                className={connectorsIntroChipClass}
                disabled={chatBusy || isTyping}
                onClick={() => void submitConnectorsIntroReady()}
              >
                I&apos;m ready to choose tools
              </button>
            </>
          ) : (
            <button
              type="button"
              className={connectorsIntroChipClass}
              disabled={chatBusy || isTyping}
              onClick={() => void submitConnectorsIntroReady()}
            >
              I&apos;m ready to choose tools
            </button>
          )}
        </div>
      </div>
    ) : null;

    if (showTools) {
      return (
        <>
          <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <div
                className={
                  "flex h-[min(30dvh,216px)] shrink-0 flex-col overflow-hidden border-b border-zinc-100/80 " +
                  "sm:h-[min(36dvh,276px)]"
                }
              >
                {chatScrollArea}
              </div>
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
                <ToolSelectorBlock
                  groups={toolGroupsUi}
                  value={toolPick}
                  onToggle={toggleTool}
                  onConfirm={() => void submitToolsPick()}
                  disabled={chatBusy}
                />
              </div>
            </div>
          </OnboardingChatLayout>
          {restartConfirmOverlay}
        </>
      );
    }

    const chatBody = (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {chatScrollArea}
        {connectorsIntroChips}
      </div>
    );
    return (
      <>
        <OnboardingChatLayout
          headerTrailing={onboardingHeaderTrailing}
          footer={
            showConnectorsIntro ? (
              <div className="shrink-0 border-t border-zinc-100/90 bg-white/80 px-2 pb-1 pt-0 backdrop-blur-sm sm:px-3">
                {connectorsIntroChipMode === "ready_only" ? (
                  <p className="px-2 pb-2 pt-1 text-center text-[12px] leading-relaxed text-zinc-500">
                    Type your question below. When you&apos;re set, use the tag above to open the tool picker.
                  </p>
                ) : (
                  <p className="px-2 pb-2 pt-1 text-center text-[12px] leading-relaxed text-zinc-500">
                    Choose a tag above to unlock the chat, or tap I&apos;m ready to skip straight to tools.
                  </p>
                )}
                <ChatInputBar
                  ref={chatInputRef}
                  value={chatInput}
                  onChange={setChatInput}
                  onSend={() => void sendChatMessage()}
                  disabled={
                    chatBusy ||
                    isTyping ||
                    (connectorsIntroChipMode === "both")
                  }
                />
              </div>
            ) : (
              <ChatInputBar
                ref={chatInputRef}
                value={chatInput}
                onChange={setChatInput}
                onSend={() => void sendChatMessage()}
                disabled={chatBusy || isTyping}
              />
            )
          }
        >
          {chatBody}
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "UNSUPPORTED_MANDATORY_TOOLS" && server) {
    const unsupportedSections = unsupportedMandatorySectionsFromAnswers(server.answers);
    const scopeText =
      unsupportedSections.length > 0 ? unsupportedMandatoryScopeDescription(unsupportedSections) : "those tools";
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
            <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
              <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-5 shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04] sm:p-6">
                <div className="mx-auto max-w-md text-left">
                  <h2 className="text-center text-lg font-semibold tracking-tight text-zinc-900 sm:text-left">
                    Thanks for telling us
                  </h2>
                  <div className="mt-4 space-y-3 text-pretty text-sm leading-relaxed text-zinc-600">
                    <p>
                      We&apos;re sorry — Vector doesn&apos;t fully support your picks yet for{" "}
                      <span className="font-medium text-zinc-800">{scopeText}</span>. We&apos;re on it, and
                      we&apos;ll email you as soon as you can finish onboarding when those tools are available.
                    </p>
                    <p>
                      You can still explore the app from the top nav. To change your tool picks, use{" "}
                      <span className="font-medium text-zinc-800">Edit tools</span> below.
                    </p>
                  </div>
                  <div className="mt-6 flex w-full flex-col border-t border-zinc-100/90 pt-5">
                    <button
                      type="button"
                      className={
                        CONNECTOR_STEP_FOOTER_LINK_CLASS +
                        " w-full py-2 text-center text-[13px] font-medium text-zinc-600 hover:text-zinc-800"
                      }
                      onClick={() =>
                        goToStep("CHAT_PROFILE", {
                          ...server.answers,
                          profile_phase: "tools",
                          unsupported_mandatory_sections: [],
                        })
                      }
                    >
                      Edit tools
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "CONNECT_PROJECT_MANAGEMENT" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
            <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
              <div className={ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS}>
                {oauthReturnError ? (
                  <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
                    {oauthReturnError}
                  </p>
                ) : null}
                {finishOnboardingError ? (
                  <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
                    {finishOnboardingError}
                  </p>
                ) : null}
                <h2 className="text-lg font-semibold text-zinc-900">Connect Linear</h2>
                {!server.linear_connected ? (
                  <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                    Link your Linear workspace so Vector can read lightweight project activity.
                  </p>
                ) : null}
                {server.linear_connected ? (
                  <div className="mt-3 space-y-1">
                    <p className="text-sm font-medium text-emerald-700">Linear is connected to this workspace.</p>
                    <p className="text-sm text-zinc-600">
                      When you&apos;re ready, continue—we&apos;ll connect your engineering tool next (or Slack if
                      you&apos;re done with Linear and GitHub).
                    </p>
                  </div>
                ) : null}
                <div className="mt-6 flex flex-col items-center gap-3">
                  {!server.linear_connected ? (
                    <a
                      className={ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS}
                      href={`${apiBase}/connectors/linear/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                    >
                      Connect Linear
                    </a>
                  ) : (
                    <button
                      type="button"
                      disabled={finishOnboardingMut.isPending}
                      className={`${ONBOARDING_PRIMARY_CTA_GRADIENT_BUTTON_CLASS} disabled:cursor-not-allowed disabled:opacity-50`}
                      onClick={() => continueAfterManualConnect("linear")}
                    >
                      {finishOnboardingMut.isPending ? "Finishing…" : "Continue"}
                    </button>
                  )}
                  <div className="mt-2 flex justify-center">
                    <button
                      type="button"
                      className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                      onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                    >
                      Edit tools
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "CONNECT_ENGINEERING" && server) {
    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
            <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
              <div className={ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS}>
                {oauthReturnError ? (
                  <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
                    {oauthReturnError}
                  </p>
                ) : null}
                {finishOnboardingError ? (
                  <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
                    {finishOnboardingError}
                  </p>
                ) : null}
                <h2 className="text-lg font-semibold text-zinc-900">Connect GitHub</h2>
                {!server.github_connected ? (
                  <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                    Authorize Vector on GitHub so we can pick up lightweight engineering signals.
                  </p>
                ) : null}
                {server.github_connected ? (
                  <div className="mt-3 space-y-1">
                    <p className="text-sm font-medium text-emerald-700">GitHub is connected to this workspace.</p>
                    <p className="text-sm text-zinc-600">
                      When you&apos;re ready, continue to connect Slack (or finish if you&apos;re all set).
                    </p>
                  </div>
                ) : null}
                <div className="mt-6 flex flex-col items-center gap-3">
                  {!server.github_connected ? (
                    <a
                      className={ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS}
                      href={`${apiBase}/connectors/github/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                    >
                      Connect GitHub
                    </a>
                  ) : (
                    <button
                      type="button"
                      disabled={finishOnboardingMut.isPending}
                      className={`${ONBOARDING_PRIMARY_CTA_GRADIENT_BUTTON_CLASS} disabled:cursor-not-allowed disabled:opacity-50`}
                      onClick={() => continueAfterManualConnect("github")}
                    >
                      {finishOnboardingMut.isPending ? "Finishing…" : "Continue"}
                    </button>
                  )}
                  <div className="mt-2 flex justify-center">
                    <button
                      type="button"
                      className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                      onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                    >
                      Edit tools
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  if (displayStep === "CONNECT_COMMUNICATION") {
    const commHead = (effectiveConnectQueue(server.answers, "CONNECT_COMMUNICATION")[0] ??
      connectQueueFromTools(server.answers)[0]) as ConnectorQueueId | undefined;

    if (commHead === "comm_placeholder") {
      const commLabel = unsupportedCommunicationPickLabel(server.answers);
      return (
        <>
          <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
            <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
              <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-5 shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04] sm:p-6">
                <div className="mx-auto max-w-md text-left">
                  <h2 className="text-center text-lg font-semibold tracking-tight text-zinc-900 sm:text-left">
                    Thanks for telling us
                  </h2>
                  <div className="mt-4 space-y-3 text-pretty text-sm leading-relaxed text-zinc-600">
                    <p>
                      Vector doesn&apos;t support{" "}
                      <span className="font-medium text-zinc-800">{commLabel}</span> yet. We&apos;re on
                      it, and we&apos;ll reach out when you can use Vector{'\u00A0'}there.
                    </p>
                    <p>
                      You can still explore the app. If you picked the wrong communication tool, use{" "}
                      <span className="font-medium text-zinc-800">Edit tools</span> below.
                    </p>
                  </div>
                  <div className="mt-6 flex w-full flex-col gap-2 border-t border-zinc-100/90 pt-5">
                    <button
                      type="button"
                      disabled={finishOnboardingMut.isPending}
                      className="w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => continuePastCommPlaceholder()}
                    >
                      {finishOnboardingMut.isPending ? "Finishing…" : "Finish and continue"}
                    </button>
                    <button
                      type="button"
                      className={
                        CONNECTOR_STEP_FOOTER_LINK_CLASS +
                        " w-full py-1 text-center text-[13px] font-medium text-zinc-600 hover:text-zinc-800"
                      }
                      onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                    >
                      Edit tools
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </OnboardingChatLayout>
          {restartConfirmOverlay}
        </>
      );
    }

    return (
      <>
        <OnboardingChatLayout headerTrailing={onboardingHeaderTrailing}>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
          <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
            <div className={ONBOARDING_CONNECTOR_PROMPT_CARD_CLASS}>
              {oauthReturnError ? (
                <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
                  {oauthReturnError}
                </p>
              ) : null}
              {finishOnboardingError ? (
                <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-left text-sm text-red-950">
                  {finishOnboardingError}
                </p>
              ) : null}
              <h2 className="text-lg font-semibold text-zinc-900">Connect Slack</h2>
              {!server.slack_connected ? (
                <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                  Invite Vector to your Slack workspace and get to work!
                </p>
              ) : null}
              {server.slack_connected ? (
                <div className="mt-3 space-y-1">
                  <p className="text-sm font-medium text-emerald-700">Slack is connected to this workspace.</p>
                  <p className="text-sm text-zinc-600">When you&apos;re ready, finish setup—you can connect more tools from Connectors later.</p>
                </div>
              ) : null}
              <div className="mt-6 flex flex-col items-center gap-3">
                {!server.slack_connected ? (
                  <a
                    className={ONBOARDING_PRIMARY_CTA_GRADIENT_LINK_CLASS}
                    href={`${apiBase}/connectors/slack/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                  >
                    Connect Slack
                  </a>
                ) : (
                  <button
                    type="button"
                    disabled={finishOnboardingMut.isPending}
                    className={`${ONBOARDING_PRIMARY_CTA_GRADIENT_BUTTON_CLASS} disabled:cursor-not-allowed disabled:opacity-50`}
                    onClick={() => continueAfterManualConnect("slack")}
                  >
                    {finishOnboardingMut.isPending ? "Finishing…" : "Finish setup"}
                  </button>
                )}
                <div className="mt-2 flex justify-center">
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                  >
                    Edit tools
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        </OnboardingChatLayout>
        {restartConfirmOverlay}
      </>
    );
  }

  return (
    <OnboardingChatLayout showHeader={false}>
      <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
        <p className="text-sm text-zinc-500">Unsupported onboarding step.</p>
      </div>
    </OnboardingChatLayout>
  );
}


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
import SlackStakeholdersPanel from "../../components/onboarding/SlackStakeholdersPanel";
import {
  ONB_SLACK_HANDOFF_EVENT_ID,
  slackHandoffSyntheticMessages,
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
  fetchSlackWorkspaceMembers,
  patchOnboarding,
  postOnboardingChat,
  postRestartOnboarding,
  type OnboardingMessagePayload,
  type OnboardingStatePayload,
  type OnboardingStep,
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
  if (next === "slack" || next === "comm_placeholder") {
    return "CONNECT_COMMUNICATION";
  }
  return "SCANNING";
}

/** Order matches backend `onboarding_flow._connect_queue_from_tools` (Slack / Teams-Discord placeholder only). */
function connectorOrderFromTools(answers: Record<string, unknown>): ConnectorQueueId[] {
  const t = answers.tools as Record<string, string[]> | undefined;
  if (!t) {
    return [];
  }
  const comm = t.communication ?? [];
  const order: ConnectorQueueId[] = [];
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
    pm: "project management tools outside Linear (for example Jira or ClickUp)",
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

function nextStepAfterUnsupportedMandatoryDismissed(
  answers: Record<string, unknown>,
  slackConnected: boolean,
): OnboardingStep {
  const rawQ = answers.connect_queue;
  const q = (Array.isArray(rawQ) ? rawQ : []).filter((x): x is string => typeof x === "string");
  if (q[0] === "slack" && !slackConnected) {
    return "CONNECT_COMMUNICATION";
  }
  if (q[0] === "comm_placeholder") {
    return "CONNECT_COMMUNICATION";
  }
  const tools = answers.tools as Record<string, string[]> | undefined;
  const comm = tools?.communication ?? [];
  if (comm.includes("slack") && slackConnected) {
    return "SLACK_STAKEHOLDERS";
  }
  return "SCANNING";
}

/** UI-only Slack handoff rows (not persisted); see ``slackHandoffSyntheticMessages``. */
function syntheticStakeholderStepMessages(answers: Record<string, unknown>, startTs: number): ChatMessage[] {
  return slackHandoffSyntheticMessages(primaryCommunicationToolLabel(answers), startTs);
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
  const last = msgs[msgs.length - 1];
  const lastIsStakeholderUser =
    last &&
    last.role === "user" &&
    stakeholderLine !== null &&
    last.content.trim() === stakeholderLine;

  if (lastIsStakeholderUser) {
    const rest = msgs.slice(0, -1);
    const lastTs = rest.length > 0 ? Math.max(...rest.map((m) => m.timestamp)) : Date.now();
    return [...rest, ...syntheticStakeholderStepMessages(answers, lastTs + 1), last];
  }

  const lastTs = msgs.length > 0 ? Math.max(...msgs.map((m) => m.timestamp)) : Date.now();
  return [...msgs, ...syntheticStakeholderStepMessages(answers, lastTs + 1)];
}

function buildStakeholderFarewellMessage(answers: Record<string, unknown>): string {
  const line = stakeholderAnswerDisplayLine(answers);
  if (line) {
    return `Perfect ${line}, I see you on Slack! Talk soon 😊`;
  }
  return "Perfect — I see you on Slack! Talk soon 😊";
}

function onboardingAppCtaStorageKey(tenantId: string): string {
  return `vector_onboarding_app_cta:${tenantId}`;
}

function effectiveConnectQueue(answers: Record<string, unknown>, currentStep: string): string[] {
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    return [...(q as string[])];
  }
  if (currentStep === "CONNECT_COMMUNICATION") {
    const order = connectorOrderFromTools(answers);
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
  if (queue.length === 0 && currentStep === "CONNECT_COMMUNICATION" && provider === "slack") {
    queue = ["slack"];
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
    enabled: Boolean(tenantId && ob.data?.current_step === "SLACK_STAKEHOLDERS"),
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
  const [adminFarewellMessage, setAdminFarewellMessage] = useState<ChatMessage | null>(null);
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
    setAdminFarewellMessage(null);
    setStakeholdersSubmitError(null);
    setFinishOnboardingError(null);
    oauthAdvanceLockRef.current = null;
    if (tenantId) {
      sessionStorage.removeItem(onboardingAppCtaStorageKey(tenantId));
    }
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
    setAdminFarewellMessage(null);
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

  /** Stakeholders step continues the same chat; hydrate from API so OAuth return / refresh keeps full history. */
  useEffect(() => {
    if (!server || server.current_step !== "SLACK_STAKEHOLDERS") {
      return;
    }
    const apiMsgs = server.messages;
    if (!apiMsgs?.length) {
      return;
    }
    setMessages(apiMsgs.map(mapServerMessageToChatMessage));
  }, [server?.current_step, server?.id, server?.version]);

  /** Post-stakeholders step: same persisted history as the rest of onboarding. */
  useEffect(() => {
    if (!server || server.current_step !== "ADMIN_ACCESS") {
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

  /** Leave ADMIN_ACCESS → drop UI-only farewell bubble (persisted chat stays from GET /onboarding). */
  useEffect(() => {
    if (displayStep !== "ADMIN_ACCESS") {
      setAdminFarewellMessage(null);
    }
  }, [displayStep]);

  /** Refresh / return: show farewell again without replaying typing when the CTA was already reached. */
  useEffect(() => {
    if (displayStep !== "ADMIN_ACCESS" || !server || !tenantId) {
      return;
    }
    if (sessionStorage.getItem(onboardingAppCtaStorageKey(tenantId)) !== "1") {
      return;
    }
    setAdminFarewellMessage((prev) => {
      if (prev) {
        return prev;
      }
      return {
        id: "admin-farewell-restored",
        role: "vector",
        content: buildStakeholderFarewellMessage(server.answers),
        timestamp: Date.now(),
      };
    });
  }, [displayStep, server, tenantId]);

  const adminAccessDisplayMessages = useMemo(() => {
    if (displayStep !== "ADMIN_ACCESS" || !server) {
      return [];
    }
    const base = buildAdminAccessStakeholderBase(messages, server.answers);
    return adminFarewellMessage ? [...base, adminFarewellMessage] : base;
  }, [displayStep, server, messages, adminFarewellMessage]);

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

  useEffect(() => {
    if (displayStep !== "ADMIN_ACCESS" || !server || !tenantId) {
      return;
    }
    if (sessionStorage.getItem(onboardingAppCtaStorageKey(tenantId)) === "1") {
      return;
    }
    let cancelled = false;
    void (async () => {
      setIsTyping(true);
      await minTypingDelay(400, 800);
      if (cancelled) {
        return;
      }
      const text = buildStakeholderFarewellMessage(server.answers);
      setAdminFarewellMessage({
        id: crypto.randomUUID(),
        role: "vector",
        content: text,
        timestamp: Date.now(),
      });
      setIsTyping(false);
      if (cancelled || !tenantId) {
        return;
      }
      sessionStorage.setItem(onboardingAppCtaStorageKey(tenantId), "1");
    })();
    return () => {
      cancelled = true;
      setIsTyping(false);
    };
  }, [displayStep, server, tenantId]);

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

  const [unsupportedMandatoryContinueBusy, setUnsupportedMandatoryContinueBusy] = useState(false);

  const continuePastUnsupportedMandatory = useCallback(async () => {
    if (!server) {
      return;
    }
    setFinishOnboardingError(null);
    setUnsupportedMandatoryContinueBusy(true);
    const cleared = { ...server.answers, unsupported_mandatory_sections: [] as string[] };
    const next = nextStepAfterUnsupportedMandatoryDismissed(cleared, server.slack_connected);
    try {
      if (next === "CONNECT_COMMUNICATION") {
        await patchOnboarding(apiBase, { current_step: "CONNECT_COMMUNICATION", answers: cleared });
      } else if (next === "SLACK_STAKEHOLDERS") {
        await patchOnboarding(apiBase, {
          current_step: "SLACK_STAKEHOLDERS",
          answers: { ...cleared, connect_queue: [], connect_plan: [] },
        });
      } else {
        await patchOnboarding(apiBase, { answers: cleared });
        await completeOnboarding(apiBase);
      }
      if (tenantId) {
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
      }
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    } catch (e) {
      setFinishOnboardingError(e instanceof Error ? e.message : "Could not continue.");
    } finally {
      setUnsupportedMandatoryContinueBusy(false);
    }
  }, [apiBase, qc, server, tenantId]);

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
          if (provider === "slack") {
            patchMut.mutate({
              current_step: "SLACK_STAKEHOLDERS",
              answers: { ...server.answers, connect_queue: [], connect_plan: [] },
            });
          } else {
            finishOnboardingMut.mutate();
          }
        } else {
          const next = queue[0] as ConnectorQueueId;
          goToStep(NextConnectStep(next), { ...server.answers, connect_queue: queue });
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
        goToStep(NextConnectStep(next), { ...server.answers, connect_queue: rest });
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
        await patchOnboarding(apiBase, {
          current_step: "ADMIN_ACCESS",
          answers: {
            slack_stakeholders: {
              raw_text: payload.text,
              slack_user_ids: payload.slack_user_ids,
              mention_labels: payload.mention_labels,
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
      goToStep(NextConnectStep(next), { ...server.answers, connect_queue: rest });
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

  /** Advance Slack OAuth return; GitHub/Linear query flags only refresh state (not part of in-flow onboarding). */
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
        if (gh === "1" || lin === "1") {
          await fetchOnboarding(apiBase);
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
          stripOauthParams();
          return;
        }
        const fresh = await fetchOnboarding(apiBase);
        if (!fresh.slack_connected) {
          const msg =
            "Slack authorization may have finished in the browser, but this workspace is not linked yet. " +
            "Common causes: token exchange failed (redirect URL in Slack app must exactly match SLACK_CALLBACK_URL), " +
            "or session cookie not sent to the API (use the same host for the app and VITE_API_BASE_URL, e.g. only localhost or only 127.0.0.1).";
          setOauthReturnError(msg);
          console.error("[onboarding] OAuth return: slack_connected=1 in URL but GET /onboarding.slack_connected is false");
          stripOauthParams();
          return;
        }
        const nextQueue = normalizeQueueAfterOAuth(fresh.answers, fresh.current_step, "slack");
        if (nextQueue.length === 0) {
          await patchOnboarding(apiBase, {
            current_step: "SLACK_STAKEHOLDERS",
            answers: {
              ...fresh.answers,
              connect_queue: [],
              connect_plan: [],
            },
          });
        } else {
          const next = nextQueue[0] as ConnectorQueueId;
          await patchOnboarding(apiBase, {
            current_step: NextConnectStep(next),
            answers: { connect_queue: nextQueue },
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
    const adminAccessFooter = adminFarewellMessage ? (
      <div className="px-4 pb-4 pt-2 sm:px-5">
        {finishOnboardingError ? (
          <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-center text-sm text-red-950">
            {finishOnboardingError}
          </p>
        ) : null}
        <button
          type="button"
          disabled={finishOnboardingMut.isPending}
          className="w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => {
            completeOnboardingGoAppRef.current = true;
            finishOnboardingMut.mutate();
          }}
        >
          {finishOnboardingMut.isPending ? "Opening…" : "Access your company space"}
        </button>
      </div>
    ) : null;

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
                      You can still explore the app. If you&apos;d like to choose different tools, use{" "}
                      <span className="font-medium text-zinc-800">Edit tools</span> below.
                    </p>
                  </div>
                  {finishOnboardingError ? (
                    <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-950">
                      {finishOnboardingError}
                    </p>
                  ) : null}
                  <div className="mt-6 flex w-full flex-col gap-2 border-t border-zinc-100/90 pt-5">
                    <button
                      type="button"
                      disabled={unsupportedMandatoryContinueBusy || finishOnboardingMut.isPending}
                      className="w-full rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-6 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03] disabled:cursor-not-allowed disabled:opacity-50"
                      onClick={() => void continuePastUnsupportedMandatory()}
                    >
                      {unsupportedMandatoryContinueBusy || finishOnboardingMut.isPending
                        ? "Continuing…"
                        : "Finish and continue"}
                    </button>
                    <button
                      type="button"
                      className={
                        CONNECTOR_STEP_FOOTER_LINK_CLASS +
                        " w-full py-1 text-center text-[13px] font-medium text-zinc-600 hover:text-zinc-800"
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

  if (displayStep === "CONNECT_COMMUNICATION") {
    const commHead = (effectiveConnectQueue(server.answers, "CONNECT_COMMUNICATION")[0] ??
      connectorOrderFromTools(server.answers)[0]) as ConnectorQueueId | undefined;

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


import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import ChatInputBar from "../../components/onboarding/ChatInputBar";
import ChatMessageList from "../../components/onboarding/ChatMessageList";
import OnboardingChatLayout from "../../components/onboarding/OnboardingChatLayout";
import ToolSelectorBlock from "../../components/onboarding/ToolSelectorBlock";
import {
  emptyToolPick,
  hydrateToolPickFromAnswers,
  ONBOARDING_TOOL_GROUPS,
  toolPickToBackendPayload,
  type ToolPickState,
} from "../../components/onboarding/onboardingToolGroups";
import { minTypingDelay } from "../../components/onboarding/chatDelay";
import type { ChatMessage } from "../../components/onboarding/types";
import { landingAccentText } from "../../components/landing/landingBrandPalette";
import {
  completeOnboarding,
  fetchOnboarding,
  patchOnboarding,
  postOnboardingChat,
  triggerGithubSync,
  type OnboardingMessagePayload,
  type OnboardingStatePayload,
  type OnboardingStep,
} from "../../lib/onboardingApi";
import { fetchMe, productApiBase } from "../../lib/meApi";

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
  if (next === "github") {
    return "CONNECT_GITHUB";
  }
  if (next === "linear") {
    return "CONNECT_LINEAR";
  }
  if (next === "slack" || next === "comm_placeholder") {
    return "CONNECT_COMMUNICATION";
  }
  return "SCANNING";
}

/** Next step + answers after skipping an optional Linear/GitHub OAuth card (queue filter + SCANNING when empty). */
function computeOptionalOAuthSkipNavigation(
  server: OnboardingStatePayload,
  provider: "linear" | "github",
): { step: OnboardingStep; answers: Record<string, unknown> } | null {
  if (provider === "linear" && server.linear_connected) {
    return null;
  }
  if (provider === "github" && server.github_connected) {
    return null;
  }
  const queue = [...effectiveConnectQueue(server.answers, server.current_step)];
  const filtered = queue.filter((p) => p !== provider);
  if (filtered.length === 0) {
    return { step: "SCANNING", answers: { ...server.answers, connect_queue: [] } };
  }
  const next = filtered[0] as ConnectorQueueId;
  return {
    step: NextConnectStep(next),
    answers: { ...server.answers, connect_queue: filtered },
  };
}

/** Short in-chat line after optional skip so the next screen feels continuous with earlier connector bridges. */
function vectorBridgeMessageAfterOptionalSkip(step: OnboardingStep): string | null {
  if (step === "CONNECT_GITHUB") {
    return (
      "All set for GitHub next. When you're ready, use Connect GitHub below - that's what lets us sync engineering activity for this workspace."
    );
  }
  if (step === "CONNECT_LINEAR") {
    return (
      "All set for Linear next. When you're ready, use Connect Linear below to authorize so we can pick up project and issue activity."
    );
  }
  if (step === "SCANNING") {
    return "Great. Next we'll sync what we can from your connected tools - hang tight while that runs.";
  }
  return null;
}

/** Order matches backend `onboarding_flow._connect_queue_from_tools`. */
function connectorOrderFromTools(answers: Record<string, unknown>): ConnectorQueueId[] {
  const t = answers.tools as Record<string, string[]> | undefined;
  if (!t) {
    return [];
  }
  const comm = t.communication ?? [];
  const pm = t.pm ?? [];
  const eng = t.engineering ?? [];
  const order: ConnectorQueueId[] = [];
  if (comm.includes("slack")) {
    order.push("slack");
  } else if (comm.includes("ms_teams") || comm.includes("discord")) {
    order.push("comm_placeholder");
  }
  if (pm.includes("linear")) {
    order.push("linear");
  }
  if (eng.includes("github")) {
    order.push("github");
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

const CONNECTOR_STEP_FOOTER_LINK_CLASS =
  "text-center text-sm leading-snug text-zinc-500 underline decoration-zinc-300 decoration-1 underline-offset-2 hover:text-zinc-700";

/**
 * Previous screen in the connector wizard (tool order). Restores connect_queue from that step so
 * e.g. Back from Linear lands on Slack with ["slack","linear",…] — not Edit tools — and Continue still works.
 */
function navigateBackFromConnectorStep(
  goToStep: (step: OnboardingStep, answers?: Record<string, unknown>) => void,
  currentId: ConnectorQueueId,
  server: OnboardingStatePayload,
) {
  const answers = server.answers;
  const order = connectorOrderFromTools(answers);
  const idx = order.indexOf(currentId);
  if (idx <= 0) {
    goToStep("CHAT_PROFILE", { ...answers, profile_phase: "tools" });
    return;
  }
  const prevIdx = idx - 1;
  const pid = order[prevIdx]!;
  const tail = order.slice(prevIdx).map(String);
  goToStep(NextConnectStep(pid), { ...answers, connect_queue: tail });
}

function effectiveConnectQueue(answers: Record<string, unknown>, currentStep: string): string[] {
  const q = answers.connect_queue;
  if (Array.isArray(q) && q.length > 0) {
    return [...(q as string[])];
  }
  if (currentStep === "CONNECT_COMMUNICATION") {
    const order = connectorOrderFromTools(answers);
    const q = answers.connect_queue;
    if (Array.isArray(q) && q.length > 0) {
      return [...(q as string[])];
    }
    return order.length ? [order[0]] : [];
  }
  if (currentStep === "CONNECT_GITHUB") {
    return ["github"];
  }
  if (currentStep === "CONNECT_LINEAR") {
    return ["linear"];
  }
  return [];
}

function isLiveConnectorId(id: string): id is LiveConnectorId {
  return id === "github" || id === "linear" || id === "slack";
}

/** OAuth-capable tools from the user's picks that are not connected yet, in sensible order (persisted queue first). */
function pendingOAuthConnectorsOrdered(
  answers: Record<string, unknown>,
  server: OnboardingStatePayload,
): LiveConnectorId[] {
  const fromTools = connectorOrderFromTools(answers);
  const pending: LiveConnectorId[] = [];
  for (const id of fromTools) {
    if (id === "comm_placeholder") {
      continue;
    }
    if (id === "slack" && !server.slack_connected) {
      pending.push("slack");
    } else if (id === "linear" && !server.linear_connected) {
      pending.push("linear");
    } else if (id === "github" && !server.github_connected) {
      pending.push("github");
    }
  }
  const cqRaw = answers.connect_queue;
  if (!Array.isArray(cqRaw) || cqRaw.length === 0) {
    return pending;
  }
  const cqFiltered = cqRaw.filter(
    (x): x is LiveConnectorId =>
      typeof x === "string" && isLiveConnectorId(x) && pending.includes(x),
  );
  if (cqFiltered.length === 0) {
    return pending;
  }
  const rest = pending.filter((p) => !cqFiltered.includes(p));
  return [...cqFiltered, ...rest];
}

function reorderQueueWithFirst(pending: LiveConnectorId[], pick: LiveConnectorId): string[] {
  const rest = pending.filter((x) => x !== pick);
  return [pick, ...rest];
}

function oauthConnectorLabel(id: LiveConnectorId): string {
  if (id === "github") {
    return "GitHub";
  }
  if (id === "linear") {
    return "Linear";
  }
  return "Slack";
}

function oauthInstallHref(apiBase: string, id: LiveConnectorId): string {
  const path =
    id === "github"
      ? "/connectors/github/install"
      : id === "linear"
        ? "/connectors/linear/install"
        : "/connectors/slack/install";
  return `${apiBase}${path}?return_to=${encodeURIComponent("/app/onboarding")}`;
}

/** In-chat copy when the user taps “Skip this step” on an optional OAuth card (Linear / GitHub). */
function optionalConnectorSkipVectorAsk(provider: "linear" | "github"): string {
  if (provider === "linear") {
    return (
      "Want to skip Linear for now? You’ll have less project and issue context until you connect it from Connectors. " +
      "Your communication tool is what we need to get started—Linear and GitHub just make execution signals richer when you add them."
    );
  }
  return (
    "Want to skip GitHub for now? You’ll have less engineering activity context until you connect it from Connectors. " +
    "Your communication tool is what we need to get started—Linear and GitHub just make execution signals richer when you add them."
  );
}

function ConnectorOptionalSkipTagBar({
  visible,
  onSkipAnyway,
  onKeepConnecting,
}: {
  visible: boolean;
  onSkipAnyway: () => void;
  onKeepConnecting: () => void;
}) {
  if (!visible) {
    return null;
  }
  const tagPrimary =
    "cursor-pointer rounded-full border border-[#E878BE]/50 bg-[#E878BE]/12 px-3.5 py-1.5 text-sm font-semibold " +
    `${landingAccentText} shadow-[0_8px_24px_-14px_rgba(232,120,190,0.65)] transition hover:brightness-[1.03] active:scale-[0.99]`;
  const tagSecondary =
    "cursor-pointer rounded-full border border-zinc-200/95 bg-white px-3.5 py-1.5 text-sm font-semibold text-zinc-800 shadow-sm transition hover:border-[#E878BE]/30 hover:bg-zinc-50/90 active:scale-[0.99]";
  return (
    <div
      className="shrink-0 border-t border-zinc-100/90 bg-gradient-to-b from-white to-zinc-50/90 px-4 pb-8 pt-3 sm:px-5 sm:pb-10"
      role="region"
      aria-label="Confirm skip"
    >
      <div className="flex flex-wrap items-center justify-center gap-2">
        <button type="button" className={tagSecondary} onClick={onKeepConnecting}>
          Keep connecting
        </button>
        <button type="button" className={tagPrimary} onClick={onSkipAnyway}>
          Skip for now
        </button>
      </div>
    </div>
  );
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
  if (queue.length === 0) {
    if (currentStep === "CONNECT_GITHUB" && provider === "github") {
      queue = ["github"];
    } else if (currentStep === "CONNECT_LINEAR" && provider === "linear") {
      queue = ["linear"];
    } else if (currentStep === "CONNECT_COMMUNICATION" && provider === "slack") {
      queue = ["slack"];
    }
  }
  if (queue[0] === provider) {
    return queue.slice(1);
  }
  return queue.filter((p) => p !== provider);
}

function onboardingQueryKey(apiBase: string, tenantId: string): [string, string, string] {
  return ["onboarding", apiBase, tenantId];
}

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

  const me = useQuery({
    queryKey: ["me", apiBase],
    queryFn: () => fetchMe(apiBase),
  });
  const tenantId = me.data?.tenant_id;

  const ob = useQuery({
    queryKey: onboardingQueryKey(apiBase, tenantId ?? ""),
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [toolPick, setToolPick] = useState<ToolPickState>(() => emptyToolPick());
  const [isTyping, setIsTyping] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);
  /** True while the chat pipeline or typing indicator is active; used to refocus input when idle. */
  const chatInputHadBusyRef = useRef(false);
  /** Set only after bootstrap succeeds for this onboarding row. Do not use a "started" ref: React Strict Mode remounts would skip the second run and leave the chat empty. */
  const bootstrapCompletedForServerIdRef = useRef<string | null>(null);

  const [scanBlurb, setScanBlurb] = useState(0);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanRetry, setScanRetry] = useState(0);
  const [scanSkipFinishBusy, setScanSkipFinishBusy] = useState(false);
  const scanStarted = useRef(false);
  /** Shown when ?*_connected=1 is in the URL but GET /onboarding does not reflect the link yet, or PATCH fails. */
  const [oauthReturnError, setOauthReturnError] = useState<string | null>(null);
  const oauthAdvanceLockRef = useRef<string | null>(null);
  const prevTenantForResetRef = useRef<string | undefined>(undefined);
  /** Connectors intro: both chips visible, or only "ready" after "Ask a question". */
  const [connectorsIntroChipMode, setConnectorsIntroChipMode] = useState<"both" | "ready_only">(
    "both",
  );
  /** In-chat confirm for skipping optional GitHub / Linear OAuth (replaces window.confirm). */
  const [optionalSkipPromptProvider, setOptionalSkipPromptProvider] = useState<
    null | "linear" | "github"
  >(null);
  const optionalSkipPromptBusyRef = useRef(false);

  const server = ob.data;

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
    setMessages([]);
    bootstrapCompletedForServerIdRef.current = null;
    setChatInput("");
    setToolPick(emptyToolPick());
    setIsTyping(false);
    setChatBusy(false);
    chatInputHadBusyRef.current = false;
    scanStarted.current = false;
    setScanBlurb(0);
    setScanError(null);
    setScanSkipFinishBusy(false);
    setOauthReturnError(null);
    oauthAdvanceLockRef.current = null;
    setConnectorsIntroChipMode("both");
    optionalSkipPromptBusyRef.current = false;
    setOptionalSkipPromptProvider(null);
  }, [tenantId]);

  /** Restore persisted chat from GET /onboarding before bootstrap; must run before the bootstrap effect. */
  useEffect(() => {
    if (!server) {
      return;
    }
    if (bootstrapCompletedForServerIdRef.current === server.id) {
      return;
    }
    const apiMsgs = server.messages;
    if (!apiMsgs?.length) {
      return;
    }
    setMessages(apiMsgs.map(mapServerMessageToChatMessage));
    bootstrapCompletedForServerIdRef.current = server.id;
  }, [server]);
  const displayStep: OnboardingStep | null = useMemo(() => {
    if (!server) {
      return null;
    }
    if (server.status === "completed") {
      return "THANK_YOU";
    }
    return server.current_step as OnboardingStep;
  }, [server]);

  const resetOptionalSkipPrompt = useCallback(() => {
    optionalSkipPromptBusyRef.current = false;
    setOptionalSkipPromptProvider(null);
  }, []);

  useEffect(() => {
    resetOptionalSkipPrompt();
  }, [displayStep, resetOptionalSkipPrompt]);

  const thankYou = Boolean(server && (server.status === "completed" || displayStep === "THANK_YOU"));

  const profilePhase = useMemo(() => {
    const p = server?.answers.profile_phase;
    return typeof p === "string" ? p : "name";
  }, [server?.answers.profile_phase, server?.version]);

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

  /** Tool picker UI: core categories only (CRM stays in state for backwards compatibility). */
  const toolGroupsUi = useMemo(() => ONBOARDING_TOOL_GROUPS.filter((g) => g.key !== "crm"), []);

  const wantsGithubSync = useMemo(() => {
    if (!server) {
      return false;
    }
    const ti = server.answers.tools_interest;
    if (Array.isArray(ti) && ti.includes("github")) {
      return true;
    }
    const t = server.answers.tools;
    if (t && typeof t === "object" && !Array.isArray(t)) {
      const eng = (t as Record<string, unknown>).engineering;
      return Array.isArray(eng) && eng.includes("github");
    }
    return false;
  }, [server]);

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

  const goToStep = useCallback(
    (step: OnboardingStep, answers?: Record<string, unknown>) => {
      patchMut.mutate({ current_step: step, answers });
    },
    [patchMut],
  );

  const pickOauthConnectorFromScanning = useCallback(
    (pick: LiveConnectorId) => {
      if (!server) {
        return;
      }
      scanStarted.current = false;
      setScanError(null);
      const pending = pendingOAuthConnectorsOrdered(server.answers, server);
      const newQueue = reorderQueueWithFirst(pending, pick);
      goToStep(NextConnectStep(pick), { ...server.answers, connect_queue: newQueue });
    },
    [server, goToStep],
  );

  const skipConnectorStepAndFinish = useCallback(async () => {
    if (!tenantId) {
      return;
    }
    scanStarted.current = false;
    setScanError(null);
    setScanSkipFinishBusy(true);
    try {
      await completeOnboarding(apiBase);
      await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    } catch (e) {
      setScanError(e instanceof Error ? e.message : "Could not finish onboarding.");
    } finally {
      setScanSkipFinishBusy(false);
    }
  }, [apiBase, qc, tenantId]);

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
          goToStep("SCANNING", { ...server.answers, connect_queue: [] });
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
        goToStep("SCANNING", { ...server.answers, connect_queue: [] });
      } else {
        const next = rest[0] as ConnectorQueueId;
        goToStep(NextConnectStep(next), { ...server.answers, connect_queue: rest });
      }
    },
    [server, goToStep],
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
      goToStep("SCANNING", { ...server.answers, connect_queue: [] });
    } else {
      const next = rest[0] as ConnectorQueueId;
      goToStep(NextConnectStep(next), { ...server.answers, connect_queue: rest });
    }
  }, [server, goToStep]);

  const requestOptionalConnectorSkip = useCallback(
    async (provider: "linear" | "github") => {
      if (optionalSkipPromptProvider === provider || optionalSkipPromptBusyRef.current) {
        return;
      }
      optionalSkipPromptBusyRef.current = true;
      setOptionalSkipPromptProvider(provider);
      setIsTyping(true);
      try {
        await minTypingDelay(320, 520);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "vector",
            content: optionalConnectorSkipVectorAsk(provider),
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setIsTyping(false);
        optionalSkipPromptBusyRef.current = false;
      }
    },
    [optionalSkipPromptProvider],
  );

  const confirmOptionalConnectorSkip = useCallback(
    async (provider: "linear" | "github") => {
      if (!server) {
        return;
      }
      const nav = computeOptionalOAuthSkipNavigation(server, provider);
      if (!nav) {
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "user",
          content: "Skip for now",
          timestamp: Date.now(),
        },
      ]);
      resetOptionalSkipPrompt();
      goToStep(nav.step, nav.answers);

      const bridge = vectorBridgeMessageAfterOptionalSkip(nav.step);
      if (!bridge) {
        return;
      }
      setIsTyping(true);
      try {
        await minTypingDelay(320, 520);
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "vector",
            content: bridge,
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setIsTyping(false);
      }
    },
    [server, resetOptionalSkipPrompt, goToStep],
  );

  /**
   * Bootstrap: brief typing indicator, then opening copy. POST syncs FSM (fast path, no LLM wait).
   * We parallelize API + min typing duration so the indicator is visible even when the request is instant.
   *
   * Completion is keyed by server id (not a fire-once ref): in dev, Strict Mode runs effect twice;
   * the first async is cancelled and must not permanently block the second run.
   */
  useEffect(() => {
    if (!server || displayStep !== "CHAT_PROFILE") {
      return;
    }
    const serverId = server.id;
    if (bootstrapCompletedForServerIdRef.current === serverId) {
      return;
    }

    const profilePhaseRaw = server.answers.profile_phase;
    const phase = typeof profilePhaseRaw === "string" ? profilePhaseRaw : "name";
    // Only the opening turn uses POST with an empty message. Past that, the same POST would
    // re-run the LLM and duplicate prompts (e.g. at the tools step on every refresh).
    if (phase !== "name") {
      bootstrapCompletedForServerIdRef.current = serverId;
      return;
    }

    let cancelled = false;
    setIsTyping(true);

    void (async () => {
      try {
        const [res] = await Promise.all([
          postOnboardingChat(apiBase, { message: "" }),
          minTypingDelay(420, 780),
        ]);
        if (cancelled) {
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
        if (!cancelled) {
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
        if (!cancelled) {
          setIsTyping(false);
        }
      }
    })();

    return () => {
      cancelled = true;
      setIsTyping(false);
    };
  }, [server?.id, displayStep, apiBase, qc, tenantId]);

  const runChatTurn = useCallback(
    async (payload: { message: string | null; structured_action?: Record<string, unknown> | null }) => {
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
      if (cur.includes(toolId)) {
        return { ...prev, [categoryKey]: [] };
      }
      return { ...prev, [categoryKey]: [toolId] };
    });
  }, []);

  /** Advance connector steps after OAuth return (?github_connected=1 etc.). */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const gh = params.get("github_connected");
    const lin = params.get("linear_connected");
    const sl = params.get("slack_connected");
    if (gh !== "1" && lin !== "1" && sl !== "1") {
      oauthAdvanceLockRef.current = null;
      return;
    }
    // Wait for tenant from /me; otherwise the first run cleared the query string via replaceState
    // before tenantId existed, and the second run saw no flags and never patched (stuck on Connect Slack).
    if (!tenantId) {
      return;
    }
    const provider: LiveConnectorId =
      gh === "1" ? "github" : sl === "1" ? "slack" : "linear";
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
        if (provider === "slack" && !fresh.slack_connected) {
          const msg =
            "Slack authorization may have finished in the browser, but this workspace is not linked yet. " +
            "Common causes: token exchange failed (redirect URL in Slack app must exactly match SLACK_CALLBACK_URL), " +
            "or session cookie not sent to the API (use the same host for the app and VITE_API_BASE_URL, e.g. only localhost or only 127.0.0.1).";
          setOauthReturnError(msg);
          console.error("[onboarding] OAuth return: slack_connected=1 in URL but GET /onboarding.slack_connected is false");
          stripOauthParams();
          return;
        }
        if (provider === "github" && !fresh.github_connected) {
          setOauthReturnError(
            "GitHub is not linked to this workspace yet. Try connecting again, or check API logs for the callback.",
          );
          console.error("[onboarding] OAuth return: github_connected mismatch");
          stripOauthParams();
          return;
        }
        if (provider === "linear" && !fresh.linear_connected) {
          setOauthReturnError(
            "Linear is not linked to this workspace yet. Try connecting again.",
          );
          console.error("[onboarding] OAuth return: linear_connected mismatch");
          stripOauthParams();
          return;
        }
        const nextQueue = normalizeQueueAfterOAuth(fresh.answers, fresh.current_step, provider);
        if (nextQueue.length === 0) {
          await patchOnboarding(apiBase, { current_step: "SCANNING", answers: { connect_queue: [] } });
        } else {
          const next = nextQueue[0] as ConnectorQueueId;
          await patchOnboarding(apiBase, {
            current_step: NextConnectStep(next),
            answers: { connect_queue: nextQueue },
          });
        }
        await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
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

  const scanMessages = [
    "Syncing data from your connected tools…",
    "Processing work activity…",
    "Building your activity graph…",
  ];
  useEffect(() => {
    if (displayStep !== "SCANNING" || server?.status === "completed" || scanError) {
      return;
    }
    const t = window.setInterval(() => {
      setScanBlurb((i) => (i + 1) % scanMessages.length);
    }, 2200);
    return () => window.clearInterval(t);
  }, [displayStep, server?.status, scanMessages.length, scanError]);

  useEffect(() => {
    if (displayStep !== "SCANNING" || server?.status === "completed" || !server) {
      return;
    }
    if (scanStarted.current) {
      return;
    }
    scanStarted.current = true;
    setScanError(null);
    void (async () => {
      try {
        if (wantsGithubSync) {
          if (!server.github_connected) {
            scanStarted.current = false;
            setScanError("GitHub is not connected.");
            return;
          }
          const run = await triggerGithubSync(apiBase);
          if (run.status !== "succeeded" && run.status !== "partial") {
            scanStarted.current = false;
            setScanError(run.error_summary || "Ingestion did not finish successfully.");
            return;
          }
        }
        await completeOnboarding(apiBase);
        if (tenantId) {
          await qc.invalidateQueries({ queryKey: onboardingQueryKey(apiBase, tenantId) });
        }
        await qc.invalidateQueries({ queryKey: ["me", apiBase] });
      } catch (e) {
        scanStarted.current = false;
        setScanError(e instanceof Error ? e.message : "Something went wrong.");
      }
    })();
  }, [apiBase, displayStep, qc, server, wantsGithubSync, scanRetry, tenantId]);

  useEffect(() => {
    if (displayStep !== "SCANNING") {
      scanStarted.current = false;
    }
  }, [displayStep]);

  /** After GitHub OAuth, clear the "not connected" error and retry ingestion automatically. */
  useEffect(() => {
    if (displayStep !== "SCANNING" || !server?.github_connected) {
      return;
    }
    if (scanError !== "GitHub is not connected.") {
      return;
    }
    scanStarted.current = false;
    setScanError(null);
    setScanRetry((n) => n + 1);
  }, [displayStep, server?.github_connected, scanError]);

  if (!tenantId || ob.isPending || !server) {
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
      <OnboardingChatLayout showHeader={false}>
        <div className="flex flex-1 flex-col items-center justify-center px-6 py-16">
          <p className="text-center text-sm text-red-700">{(ob.error as Error).message}</p>
        </div>
      </OnboardingChatLayout>
    );
  }

  if (thankYou) {
    return (
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
            </p>
          </div>
        </div>
      </OnboardingChatLayout>
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
    const chatBody = (
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
        {showConnectorsIntro ? (
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
        ) : null}
      </div>
    );
    return (
      <OnboardingChatLayout
        footer={
          showTools ? (
            <ToolSelectorBlock
              groups={toolGroupsUi}
              value={toolPick}
              onToggle={toggleTool}
              onConfirm={() => void submitToolsPick()}
              disabled={chatBusy}
            />
          ) : showConnectorsIntro ? (
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
    );
  }

  if (displayStep === "CONNECT_COMMUNICATION") {
    const commHead = (effectiveConnectQueue(server.answers, "CONNECT_COMMUNICATION")[0] ??
      connectorOrderFromTools(server.answers)[0]) as ConnectorQueueId | undefined;

    if (commHead === "comm_placeholder") {
      return (
        <OnboardingChatLayout>
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
            <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
              <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-6 text-center shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04]">
                <h2 className="text-lg font-semibold text-zinc-900">Teams &amp; Discord</h2>
                <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                  In-product connections for Microsoft Teams and Discord are not available yet. You can continue with
                  your other tools.
                </p>
                <div className="mt-6 flex flex-col items-center gap-3">
                  <button
                    type="button"
                    className="rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    onClick={() => continuePastCommPlaceholder()}
                  >
                    Continue
                  </button>
                  <button
                    type="button"
                    className="text-sm text-zinc-500 underline decoration-zinc-300 decoration-1 underline-offset-2"
                    onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                  >
                    Back
                  </button>
                </div>
              </div>
            </div>
          </div>
        </OnboardingChatLayout>
      );
    }

    return (
      <OnboardingChatLayout>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
          <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
            <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-6 text-center shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04]">
              {oauthReturnError ? (
                <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-950">
                  {oauthReturnError}
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
                  <p className="text-sm text-zinc-600">When you&apos;re ready, continue to the next integration.</p>
                </div>
              ) : null}
              <div className="mt-6 flex flex-col items-center gap-3">
                {!server.slack_connected ? (
                  <a
                    className="inline-flex rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white no-underline shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    href={`${apiBase}/connectors/slack/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                  >
                    Connect Slack
                  </a>
                ) : (
                  <button
                    type="button"
                    className="rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    onClick={() => continueAfterManualConnect("slack")}
                  >
                    Continue to next step
                  </button>
                )}
                <nav
                  className="mx-auto mt-1 grid w-full max-w-xs grid-cols-2 items-center justify-items-center gap-x-6 px-2 sm:max-w-sm sm:gap-x-10"
                  aria-label="Slack step actions"
                >
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => navigateBackFromConnectorStep(goToStep, "slack", server)}
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                  >
                    Edit tools
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </OnboardingChatLayout>
    );
  }

  if (displayStep === "CONNECT_GITHUB") {
    const showGithubConnectorCard =
      server.github_connected || optionalSkipPromptProvider !== "github";
    return (
      <OnboardingChatLayout>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
          <ConnectorOptionalSkipTagBar
            visible={optionalSkipPromptProvider === "github"}
            onKeepConnecting={resetOptionalSkipPrompt}
            onSkipAnyway={() => confirmOptionalConnectorSkip("github")}
          />
          {showGithubConnectorCard ? (
          <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
            <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-6 text-center shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04]">
              <h2 className="text-lg font-semibold text-zinc-900">Connect GitHub</h2>
              <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                Install the GitHub app for this workspace so we can sync engineering activity.
              </p>
              {server.github_connected ? (
                <div className="mt-3 space-y-1">
                  <p className="text-sm font-medium text-emerald-700">GitHub is connected to this workspace.</p>
                  <p className="text-sm text-zinc-600">When you&apos;re ready, continue to the next step.</p>
                </div>
              ) : null}
              <div className="mt-6 flex flex-col items-center gap-3">
                {!server.github_connected ? (
                  <a
                    className="inline-flex rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white no-underline shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    href={`${apiBase}/connectors/github/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                  >
                    Connect GitHub
                  </a>
                ) : (
                  <button
                    type="button"
                    className="rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    onClick={() => continueAfterManualConnect("github")}
                  >
                    Continue to next step
                  </button>
                )}
                <nav
                  className={
                    !server.github_connected
                      ? "mx-auto mt-1 grid w-full max-w-lg grid-cols-3 items-center justify-items-center gap-x-2 px-1 sm:px-4"
                      : "mx-auto mt-1 grid w-full max-w-xs grid-cols-2 items-center justify-items-center gap-x-6 px-2 sm:max-w-sm sm:gap-x-10"
                  }
                  aria-label="GitHub step actions"
                >
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => navigateBackFromConnectorStep(goToStep, "github", server)}
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                  >
                    Edit tools
                  </button>
                  {!server.github_connected ? (
                    <button
                      type="button"
                      className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                      onClick={() => {
                        void requestOptionalConnectorSkip("github");
                      }}
                    >
                      Skip this step
                    </button>
                  ) : null}
                </nav>
              </div>
            </div>
          </div>
          ) : null}
        </div>
      </OnboardingChatLayout>
    );
  }

  if (displayStep === "CONNECT_LINEAR") {
    const showLinearConnectorCard =
      server.linear_connected || optionalSkipPromptProvider !== "linear";
    return (
      <OnboardingChatLayout>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
          <ConnectorOptionalSkipTagBar
            visible={optionalSkipPromptProvider === "linear"}
            onKeepConnecting={resetOptionalSkipPrompt}
            onSkipAnyway={() => confirmOptionalConnectorSkip("linear")}
          />
          {showLinearConnectorCard ? (
          <div className="shrink-0 px-4 pb-8 pt-1 sm:px-5">
            <div className="rounded-2xl border border-[#E878BE]/20 bg-white/95 p-6 text-center shadow-[0_16px_44px_-28px_rgba(232,120,190,0.45)] ring-1 ring-zinc-950/[0.04]">
              <h2 className="text-lg font-semibold text-zinc-900">Connect Linear</h2>
              <p className="mt-2 text-sm leading-relaxed text-zinc-600">
                Authorize Linear for this workspace so we can sync project and issue activity.
              </p>
              {server.linear_connected ? (
                <div className="mt-3 space-y-1">
                  <p className="text-sm font-medium text-emerald-700">Linear is connected to this workspace.</p>
                  <p className="text-sm text-zinc-600">When you&apos;re ready, continue to the next step.</p>
                </div>
              ) : null}
              <div className="mt-6 flex flex-col items-center gap-3">
                {!server.linear_connected ? (
                  <a
                    className="inline-flex rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white no-underline shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    href={`${apiBase}/connectors/linear/install?return_to=${encodeURIComponent("/app/onboarding")}`}
                  >
                    Connect Linear
                  </a>
                ) : (
                  <button
                    type="button"
                    className="rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                    onClick={() => continueAfterManualConnect("linear")}
                  >
                    Continue to next step
                  </button>
                )}
                <nav
                  className={
                    !server.linear_connected
                      ? "mx-auto mt-1 grid w-full max-w-lg grid-cols-3 items-center justify-items-center gap-x-2 px-1 sm:px-4"
                      : "mx-auto mt-1 grid w-full max-w-xs grid-cols-2 items-center justify-items-center gap-x-6 px-2 sm:max-w-sm sm:gap-x-10"
                  }
                  aria-label="Linear step actions"
                >
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => navigateBackFromConnectorStep(goToStep, "linear", server)}
                  >
                    Back
                  </button>
                  <button
                    type="button"
                    className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                    onClick={() => goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" })}
                  >
                    Edit tools
                  </button>
                  {!server.linear_connected ? (
                    <button
                      type="button"
                      className={CONNECTOR_STEP_FOOTER_LINK_CLASS}
                      onClick={() => {
                        void requestOptionalConnectorSkip("linear");
                      }}
                    >
                      Skip this step
                    </button>
                  ) : null}
                </nav>
              </div>
            </div>
          </div>
          ) : null}
        </div>
      </OnboardingChatLayout>
    );
  }

  if (displayStep === "SCANNING") {
    const scanningIdle = !scanError;
    const pendingOauth = scanningIdle ? [] : pendingOAuthConnectorsOrdered(server.answers, server);
    const showOauthRecovery = !scanningIdle && pendingOauth.length > 0;
    const oauthRecoveryMuted = showOauthRecovery;
    return (
      <OnboardingChatLayout>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <ChatMessageList messages={messages} userDisplayName={userLabel} isTyping={isTyping} />
          <div className="shrink-0 px-4 pb-10 pt-3 text-center sm:px-5">
            <h2 className="text-lg font-semibold text-zinc-900">
              {scanningIdle
                ? "We're syncing your workspace"
                : showOauthRecovery
                  ? "Pick the next tool to connect"
                  : "We couldn't finish this step yet"}
            </h2>
            <p
              className={
                "mt-3 min-h-[1.75rem] text-sm " +
                (scanningIdle || oauthRecoveryMuted ? "text-zinc-600" : "text-red-700")
              }
            >
              {scanningIdle ? (
                scanMessages[scanBlurb]
              ) : showOauthRecovery ? (
                pendingOauth.length > 1 ? (
                  <>
                    The more tools we connect, the more accurate our signals and insights will be for you.
                    <br />
                    Pick the next one to connect - it only takes a minute!
                  </>
                ) : pendingOauth[0] === "github" && wantsGithubSync ? (
                  <>
                    You chose GitHub for engineering, but this workspace isn&apos;t connected to GitHub yet. Connect it
                    to pull activity, or change your tools below.
                  </>
                ) : pendingOauth[0] === "linear" ? (
                  <>
                    Linear isn&apos;t connected to this workspace yet. Connect it to sync project activity, or change
                    your tools below.
                  </>
                ) : pendingOauth[0] === "slack" ? (
                  <>
                    Slack isn&apos;t connected to this workspace yet. Connect it to pull messages and activity, or
                    change your tools below.
                  </>
                ) : (
                  <>Connect this tool to continue, or change your tools below.</>
                )
              ) : (
                scanError
              )}
            </p>
            {scanningIdle ? (
              <p className="mt-4 text-xs text-zinc-400">This usually takes under a minute.</p>
            ) : (
              <div className="mt-6 flex flex-col items-center gap-5">
                {showOauthRecovery ? (
                  pendingOauth.length === 1 ? (
                    <a
                      className="inline-flex cursor-pointer rounded-full bg-gradient-to-r from-[#BE5E94] to-[#E878BE] px-8 py-3 text-sm font-semibold text-white no-underline shadow-[0_14px_36px_-18px_rgba(232,120,190,0.55)] transition hover:brightness-[1.03]"
                      href={oauthInstallHref(apiBase, pendingOauth[0]!)}
                    >
                      Connect {oauthConnectorLabel(pendingOauth[0]!)}
                    </a>
                  ) : (
                    <div className="flex flex-wrap items-center justify-center gap-2">
                      {pendingOauth.map((id) => (
                        <button
                          key={id}
                          type="button"
                          className={
                            "cursor-pointer rounded-full border border-[#E878BE]/50 bg-[#E878BE]/12 px-3.5 py-1.5 text-sm font-semibold " +
                            `${landingAccentText} shadow-[0_8px_24px_-14px_rgba(232,120,190,0.65)] transition ` +
                            "hover:brightness-[1.03] active:scale-[0.99]"
                          }
                          onClick={() => pickOauthConnectorFromScanning(id)}
                        >
                          {oauthConnectorLabel(id)}
                        </button>
                      ))}
                    </div>
                  )
                ) : null}
                <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1">
                  <button
                    type="button"
                    disabled={scanSkipFinishBusy}
                    className="text-sm text-zinc-500 underline decoration-zinc-300 decoration-1 underline-offset-2 hover:text-zinc-700 disabled:cursor-not-allowed disabled:no-underline disabled:opacity-50"
                    onClick={() => {
                      scanStarted.current = false;
                      setScanError(null);
                      goToStep("CHAT_PROFILE", { ...server.answers, profile_phase: "tools" });
                    }}
                  >
                    Edit tools
                  </button>
                  <span className="select-none text-zinc-300" aria-hidden>
                    ·
                  </span>
                  <button
                    type="button"
                    disabled={scanSkipFinishBusy}
                    className="text-sm text-zinc-500 underline decoration-zinc-300 decoration-1 underline-offset-2 hover:text-zinc-700 disabled:cursor-not-allowed disabled:no-underline disabled:opacity-50"
                    title="Finish onboarding without connecting the rest. You can add tools anytime from Connectors."
                    onClick={() => void skipConnectorStepAndFinish()}
                  >
                    {scanSkipFinishBusy ? "Finishing…" : "Skip this step"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </OnboardingChatLayout>
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


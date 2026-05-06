import type { CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  type ConnectorRow,
  CONNECTOR_OAUTH_RETURN_PATH,
  disconnectConnector,
  fetchConnectors,
  startConnectorOAuthRedirect,
} from "../../lib/connectorsClient";
import { fetchOnboarding } from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import {
  emptyToolPick,
  hydrateToolPickFromAnswers,
  type ToolPickState,
} from "../onboarding/onboardingToolGroups";
import { workspaceFlatPanel } from "../marketing/marketingStyles";
import {
  workspacePrimaryButton,
  workspacePrimaryButtonSm,
  workspaceSecondaryButton,
  workspaceSignalBarActive,
  workspaceSignalGlyphActive,
  workspaceSpinner,
  workspaceSpinnerLg,
} from "./workspaceUiTokens";
import EditToolsModal from "./EditToolsModal";
import { buildSignalWorkspaceActions } from "./signalWorkspaceActions";
import { currentCoveragePresentation } from "./signalCoverageCopy";
import { isSlotActive, signalStrengthPercentLive, WORKSPACE_SIGNAL_SLOTS, type SignalSlot } from "./signalCatalog";
import { ToolLogo } from "./toolLogos";
import {
  categoryLabelsForStackRow,
  mergeConnectedProvidersIntoPick,
  orderedStackToolRows,
  toolLabelFromOnboarding,
} from "./workspaceStackPick";
import {
  getWorkspaceStackToolsPick,
  setWorkspaceStackToolsPick,
} from "./workspaceStackStorage";

type Props = {
  connectedConnectors: string[];
  useMockConnectors: boolean;
};

function segmentFlexStyle(weight: number): CSSProperties {
  return { flex: `${weight} 1 0%`, minHeight: 0 };
}

const btnConnect = workspacePrimaryButton;

const btnConnectSmall = workspacePrimaryButtonSm;

const disconnectBtnClass =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50";

const disabledConnectClass =
  "w-full cursor-not-allowed rounded-lg border border-zinc-200 bg-zinc-50 py-2 text-sm font-medium text-zinc-400";

const cardClass =
  "flex min-h-[10.5rem] flex-col rounded-2xl border border-zinc-100 bg-white p-4 sm:min-h-[11rem] sm:p-5";

/** People vs system buckets — same catalog entries, regrouped for clarity (order fixed). */
const PEOPLE_SIGNAL_IDS = ["communication", "calls", "calendar"] as const;
const SYSTEM_SIGNAL_IDS = ["engineering", "pm", "docs"] as const;

function catalogSlotsForIds(ids: readonly string[]): SignalSlot[] {
  return ids
    .map((id) => WORKSPACE_SIGNAL_SLOTS.find((s) => s.id === id))
    .filter((s): s is SignalSlot => s != null);
}

const PEOPLE_SIGNAL_SLOTS = catalogSlotsForIds(PEOPLE_SIGNAL_IDS);
const SYSTEM_SIGNAL_SLOTS = catalogSlotsForIds(SYSTEM_SIGNAL_IDS);

function bucketBarAriaLabel(slots: SignalSlot[], connected: Set<string>): string {
  return slots
    .map((s) => {
      if (isSlotActive(s, connected)) {
        return `${s.label} live`;
      }
      if (s.roadmap) {
        return `${s.label} planned`;
      }
      return `${s.label} off`;
    })
    .join("; ");
}

function BucketSignalBar({ slots, connected }: { slots: SignalSlot[]; connected: Set<string> }) {
  return (
    <div
      className="mt-1.5 flex h-4 w-full gap-px overflow-hidden rounded-full bg-zinc-200/80"
      role="img"
      aria-label={bucketBarAriaLabel(slots, connected)}
    >
      {slots.map((slot) => {
        const active = isSlotActive(slot, connected);
        let bg = "bg-zinc-300/80";
        if (active) {
          bg = workspaceSignalBarActive;
        } else if (slot.roadmap) {
          bg = "bg-zinc-300/60";
        }
        return (
          <div key={slot.id} style={segmentFlexStyle(slot.impactWeight)} className={`min-h-0 min-w-[3px] ${bg}`} />
        );
      })}
    </div>
  );
}

function slotScanVisual(
  slot: SignalSlot,
  connected: Set<string>,
): { char: string; glyphClass: string; chipClass: string } {
  if (isSlotActive(slot, connected)) {
    return { char: "●", glyphClass: workspaceSignalGlyphActive, chipClass: "" };
  }
  if (slot.roadmap) {
    return { char: "–", glyphClass: "text-zinc-400/70", chipClass: "opacity-45" };
  }
  return { char: "○", glyphClass: "text-zinc-400", chipClass: "opacity-75" };
}

function CompactSignalColumn({
  title,
  slots,
  connected,
}: {
  title: string;
  slots: SignalSlot[];
  connected: Set<string>;
}) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-semibold uppercase tracking-[0.1em] text-zinc-600 sm:text-sm">{title}</p>
      <BucketSignalBar slots={slots} connected={connected} />
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1.5 leading-snug sm:gap-x-4">
        {slots.map((slot) => {
          const { char, glyphClass, chipClass } = slotScanVisual(slot, connected);
          return (
            <span
              key={slot.id}
              className={`inline-flex items-baseline gap-1 text-sm font-semibold sm:text-base ${chipClass}`}
            >
              <span className={`shrink-0 text-base leading-none sm:text-lg ${glyphClass}`} aria-hidden>
                {char}
              </span>
              <span className="text-zinc-900">{slot.label}</span>
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default function WorkspaceSignalsTab({ connectedConnectors, useMockConnectors }: Props) {
  const apiBase = productApiBase();
  const qc = useQueryClient();
  const me = useProductMeQuery(apiBase);
  const tenantId = me.data?.tenant_id;
  const onboardingQ = useQuery({
    queryKey: ["onboarding", apiBase, tenantId ?? ""],
    queryFn: () => fetchOnboarding(apiBase),
    enabled: Boolean(tenantId),
  });
  const connected = new Set(connectedConnectors.map((c) => c.toLowerCase()));
  const pctLive = signalStrengthPercentLive(connected);
  const coverageUi = useMemo(() => currentCoveragePresentation(pctLive), [pctLive]);

  const [banner, setBanner] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [savedStackPick, setSavedStackPick] = useState<ToolPickState | null>(() => getWorkspaceStackToolsPick());
  const [editModalSeed, setEditModalSeed] = useState<ToolPickState>(() => emptyToolPick());

  const onboardingPick = useMemo(
    () => hydrateToolPickFromAnswers(onboardingQ.data?.answers ?? {}),
    [onboardingQ.data?.answers],
  );

  /** Saved edits win; otherwise onboarding answers from the API. */
  const effectiveStackPick = useMemo(
    () => savedStackPick ?? onboardingPick,
    [savedStackPick, onboardingPick],
  );

  const openEditTools = useCallback(() => {
    setEditModalSeed(mergeConnectedProvidersIntoPick(effectiveStackPick, connected));
    setEditOpen(true);
  }, [effectiveStackPick, connected]);

  const connectorsQ = useQuery({
    queryKey: ["connectors", apiBase],
    queryFn: () => fetchConnectors(apiBase),
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthErr = params.get("oauth_error");
    if (oauthErr === "state") {
      setBanner("Sign-in failed (invalid or expired state). Try again.");
    } else if (oauthErr === "token") {
      setBanner("Sign-in failed (could not validate account with Google).");
    }
    const gh = params.get("github_connected");
    const ghErr = params.get("github_error");
    const lin = params.get("linear_connected");
    const linErr = params.get("linear_error");
    const nt = params.get("notion_connected");
    const ntErr = params.get("notion_error");
    const sl = params.get("slack_connected");
    const slErr = params.get("slack_error");
    if (gh === "1" || lin === "1" || sl === "1" || nt === "1") {
      setBanner(null);
      void qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
      void qc.invalidateQueries({ queryKey: ["me", apiBase] });
    }
    if (ghErr === "state") {
      setBanner("GitHub connect failed (invalid or expired state).");
    } else if (ghErr === "oauth") {
      setBanner("GitHub OAuth failed. Check app credentials.");
    } else if (ghErr === "conflict") {
      setBanner("This GitHub installation is already linked to another workspace.");
    } else if (linErr === "state") {
      setBanner("Linear connect failed (invalid or expired state).");
    } else if (linErr === "oauth") {
      setBanner("Linear OAuth failed. Check LINEAR_CLIENT_* and redirect URI.");
    } else if (slErr === "state") {
      setBanner("Slack connect failed (invalid or expired state).");
    } else if (slErr === "oauth") {
      setBanner("Slack OAuth failed. Check SLACK_* and redirect URI.");
    } else if (slErr === "denied") {
      setBanner("Slack connection was cancelled or denied.");
    } else if (slErr === "workspace_taken") {
      setBanner("This Slack workspace is already linked to another Vector workspace.");
    } else if (ntErr === "state") {
      setBanner("Notion connect failed (invalid or expired state).");
    } else if (ntErr === "oauth") {
      setBanner("Notion OAuth failed. Check NOTION_* and redirect URI.");
    } else if (ntErr === "config") {
      setBanner("Notion OAuth is not configured on the API.");
    }
    if (
      oauthErr ||
      gh ||
      ghErr ||
      lin ||
      linErr ||
      nt ||
      ntErr ||
      params.get("oauth_ok") ||
      params.get("github_connected") ||
      params.get("linear_connected") ||
      params.get("slack_connected") ||
      params.get("slack_error") ||
      params.get("notion_connected") ||
      params.get("notion_error")
    ) {
      window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
    }
  }, [apiBase, qc]);

  const statusById = useMemo(() => {
    const m = new Map<string, ConnectorRow>();
    for (const row of connectorsQ.data?.items ?? []) {
      m.set(row.provider, row);
    }
    return m;
  }, [connectorsQ.data?.items]);

  const ghDisconnect = useMutation({
    mutationFn: () => disconnectConnector(apiBase, "github"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => setBanner(e.message),
  });
  const linDisconnect = useMutation({
    mutationFn: () => disconnectConnector(apiBase, "linear"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => setBanner(e.message),
  });
  const slackDisconnect = useMutation({
    mutationFn: () => disconnectConnector(apiBase, "slack"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => setBanner(e.message),
  });
  const notionDisconnect = useMutation({
    mutationFn: () => disconnectConnector(apiBase, "notion"),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["connectors", apiBase] });
      await qc.invalidateQueries({ queryKey: ["me", apiBase] });
    },
    onError: (e: Error) => setBanner(e.message),
  });

  const onStackSave = useCallback(
    (pick: ToolPickState) => {
      const finalized = mergeConnectedProvidersIntoPick(pick, connected);
      setWorkspaceStackToolsPick(finalized);
      setSavedStackPick(finalized);
    },
    [connected],
  );

  const slotById = useMemo(() => {
    const m = new Map<string, SignalSlot>();
    for (const s of WORKSPACE_SIGNAL_SLOTS) {
      m.set(s.id, s);
    }
    return m;
  }, []);

  /** Include connected OAuth tools in the grid even when the saved pick list is empty for that group. */
  const displayStackPick = useMemo(
    () => mergeConnectedProvidersIntoPick(effectiveStackPick, connected),
    [effectiveStackPick, connected],
  );

  const stackToolRows = useMemo(() => orderedStackToolRows(displayStackPick), [displayStackPick]);

  const stackPrefsReady = Boolean(savedStackPick) || onboardingQ.isSuccess || onboardingQ.isError;

  const workspaceActions = useMemo(() => {
    if (!stackPrefsReady) {
      return [];
    }
    return buildSignalWorkspaceActions(effectiveStackPick, connected, statusById, connectorsQ.isFetched);
  }, [stackPrefsReady, effectiveStackPick, connected, statusById, connectorsQ.isFetched]);

  return (
    <div className="space-y-6 lg:space-y-8">
      <div className={`${workspaceFlatPanel} p-6 sm:p-8 lg:p-10`}>
        <div className="border-b border-zinc-100 pb-4 text-center lg:pb-3">
          <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-500">Signal strength</p>
          <p
            className={`mt-1 text-5xl font-bold tracking-tight sm:text-6xl lg:text-7xl ${coverageUi.toneClass}`}
          >
            {coverageUi.label}
          </p>
          <p
            className={`mx-auto mt-3 max-w-2xl text-center text-sm leading-relaxed sm:text-base ${coverageUi.toneClass}`}
          >
            {coverageUi.headlineSentence}
          </p>
        </div>

        <div className="grid gap-4 pt-4 sm:gap-5 lg:grid-cols-2 lg:gap-8 lg:pt-4 xl:gap-10">
          <CompactSignalColumn title="People signals" slots={PEOPLE_SIGNAL_SLOTS} connected={connected} />
          <CompactSignalColumn title="System signals" slots={SYSTEM_SIGNAL_SLOTS} connected={connected} />
        </div>
      </div>

      <div className={`${workspaceFlatPanel} p-6 sm:p-8 lg:p-10`}>
        <div className="flex flex-wrap items-start justify-between gap-3 sm:items-center">
          <h2 className="min-w-0 text-xl font-bold tracking-tight text-zinc-900">
            Actions to improve your signals
          </h2>
          <button type="button" className={workspaceSecondaryButton} onClick={openEditTools}>
            Edit tools
          </button>
        </div>
        {!stackPrefsReady ? (
          <div className="mt-4 flex min-h-[4rem] items-center gap-3 text-sm text-zinc-500">
            <div
              className={workspaceSpinner}
              aria-hidden
            />
            Loading actions…
          </div>
        ) : workspaceActions.length > 0 ? (
          <ul className="mt-4 space-y-2">
            {workspaceActions.map((action) => (
              <li
                key={action.id}
                className="flex flex-col gap-2.5 rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-3"
              >
                {action.kind === "expand_stack" ? (
                  <>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-zinc-900">
                        <span className="mr-1.5 inline-block" aria-hidden>
                          ⚠️
                        </span>
                        {action.title}
                      </p>
                      <p className="mt-1 text-sm leading-relaxed text-zinc-600">{action.body}</p>
                    </div>
                    <button type="button" className={workspaceSecondaryButton} onClick={openEditTools}>
                      Edit tools
                    </button>
                  </>
                ) : (
                  <>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold text-zinc-900">{action.title}</p>
                      <p className="mt-1 text-sm leading-relaxed text-zinc-600">{action.body}</p>
                      {!action.configured ? (
                        <p className="mt-2 text-xs text-amber-900">
                          {action.provider === "github" && "GitHub isn’t configured on the API yet."}
                          {action.provider === "linear" && "Linear OAuth isn’t configured on the API yet."}
                          {action.provider === "notion" && "Notion OAuth isn’t configured on the API yet."}
                          {action.provider === "slack" && "Slack OAuth isn’t configured on the API yet."}
                        </p>
                      ) : null}
                    </div>
                    {action.configured ? (
                      <button
                        type="button"
                        className={`${btnConnectSmall} shrink-0 sm:px-5`}
                        onClick={() => {
                          void (async () => {
                            try {
                              await startConnectorOAuthRedirect(
                                apiBase,
                                action.provider,
                                CONNECTOR_OAUTH_RETURN_PATH,
                              );
                            } catch (e) {
                              window.alert(e instanceof Error ? e.message : "Could not start connect.");
                            }
                          })();
                        }}
                      >
                        {action.title}
                      </button>
                    ) : null}
                  </>
                )}
              </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-zinc-600">
              <span className="font-medium text-zinc-900">You&apos;re caught up.</span> No stack or connection
              steps pending right now.
            </p>
          )}
      </div>

      <div className={`${workspaceFlatPanel} p-6 sm:p-8 lg:p-10`}>
        <div className="flex flex-wrap items-start justify-between gap-3 sm:items-center">
          <h2 className="text-xl font-bold tracking-tight text-zinc-900">Connector status</h2>
          <button type="button" className={workspaceSecondaryButton} onClick={openEditTools}>
            Edit tools
          </button>
        </div>

        <div className="mt-4 space-y-4">
          {useMockConnectors ? (
            <p className="rounded-lg border-l-4 border-rose-400 bg-rose-50 py-3 pl-4 pr-4 text-sm text-rose-900">
              Development mode: mock connectors. OAuth flows may still hit real services; data can be sample-only.
            </p>
          ) : null}

          {banner ? (
            <div className="rounded-lg border border-amber-200/90 bg-amber-50 py-3 px-4 text-sm text-amber-950">
              {banner}
            </div>
          ) : null}

          {connectorsQ.isError ? (
            <p className="rounded-lg border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-900">
              {(connectorsQ.error as Error).message}
            </p>
          ) : null}

          {onboardingQ.isPending && savedStackPick == null ? (
            <div className="flex min-h-[8rem] items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50">
              <div className="flex flex-col items-center gap-3">
                <div
                  className={workspaceSpinnerLg}
                  aria-hidden
                />
                <p className="text-sm text-zinc-600">Loading stack preferences…</p>
              </div>
            </div>
          ) : connectorsQ.isPending ? (
            <div className="flex min-h-[12rem] items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50">
              <div className="flex flex-col items-center gap-3">
                <div
                  className={workspaceSpinnerLg}
                  aria-hidden
                />
                <p className="text-sm text-zinc-600">Loading connector status…</p>
              </div>
            </div>
          ) : (
            <>
              {stackToolRows.length === 0 ? (
                <p className="text-sm text-zinc-600">
                  Nothing in your stack yet. Use <span className="font-medium text-zinc-900">Edit tools</span> to add
                  tools—each selection appears here.
                </p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
                  {stackToolRows.map((row) => (
                    <StackToolCard
                      key={row.key}
                      groupKeys={row.groupKeys}
                      toolId={row.toolId}
                      apiBase={apiBase}
                      connected={connected}
                      statusById={statusById}
                      slotById={slotById}
                      ghDisconnect={ghDisconnect}
                      linDisconnect={linDisconnect}
                      notionDisconnect={notionDisconnect}
                      slackDisconnect={slackDisconnect}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <EditToolsModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        initialPick={editModalSeed}
        connected={connected}
        onSave={onStackSave}
      />
    </div>
  );
}

/** Signal catalog slot for roadmap strip (docs / calls / calendar). */
function roadmapSlotIdForStackRow(groupKeys: (keyof ToolPickState)[]): string | null {
  if (groupKeys.includes("docs")) {
    return "docs";
  }
  if (groupKeys.includes("calls")) {
    return "calls";
  }
  if (groupKeys.includes("calendars")) {
    return "calendar";
  }
  return null;
}

/** Pick one group for comm/PM/engineering “live tool today” copy when multiple groups share a row. */
function primaryGroupForNarrative(groupKeys: (keyof ToolPickState)[]): keyof ToolPickState {
  const priority: (keyof ToolPickState)[] = [
    "communication",
    "pm",
    "engineering",
    "calls",
    "docs",
    "calendars",
  ];
  for (const k of priority) {
    if (groupKeys.includes(k)) {
      return k;
    }
  }
  return groupKeys[0]!;
}

function comingSoonDescriptionForTool(
  groupKeys: (keyof ToolPickState)[],
  toolId: string,
  slotById: Map<string, SignalSlot>,
): string {
  if (toolId === "notion") {
    if (groupKeys.includes("docs")) {
      return slotById.get("docs")?.description ?? "Documentation ingestion is planned as we expand connectors.";
    }
    return (
      slotById.get("docs")?.description ??
      "Notion for plans and docs is planned as we expand PM and documentation connectors."
    );
  }

  const g = primaryGroupForNarrative(groupKeys);

  if (g === "calls") {
    return slotById.get("calls")?.description ?? "Recordings and transcripts are planned as we expand connectors.";
  }
  if (g === "docs") {
    return slotById.get("docs")?.description ?? "Documentation ingestion is planned as we expand connectors.";
  }
  if (g === "calendars") {
    return slotById.get("calendar")?.description ?? "Calendar intelligence is planned as we expand connectors.";
  }
  if (g === "communication" && toolId !== "slack") {
    return "Slack is the live integration today; we’ll add more communication tools as connectors ship.";
  }
  if (g === "pm" && toolId !== "linear") {
    return "Linear is the live integration today; we’ll add more PM tools as connectors ship.";
  }
  if (g === "engineering" && toolId !== "github") {
    return "GitHub is the live integration today; we’ll add more code hosts as connectors ship.";
  }
  return "Not available to connect yet.";
}

function StackToolCard({
  groupKeys,
  toolId,
  apiBase,
  connected,
  statusById,
  slotById,
  ghDisconnect,
  linDisconnect,
  notionDisconnect,
  slackDisconnect,
}: {
  groupKeys: (keyof ToolPickState)[];
  toolId: string;
  apiBase: string;
  connected: Set<string>;
  statusById: Map<string, ConnectorRow>;
  slotById: Map<string, SignalSlot>;
  ghDisconnect: UseMutationResult<void, Error, void, unknown>;
  linDisconnect: UseMutationResult<void, Error, void, unknown>;
  notionDisconnect: UseMutationResult<void, Error, void, unknown>;
  slackDisconnect: UseMutationResult<void, Error, void, unknown>;
}) {
  const name = toolLabelFromOnboarding(toolId);
  const categoryLabel = categoryLabelsForStackRow(groupKeys);

  if (toolId === "notion") {
    const pmSlot = slotById.get("pm");
    const docsSlot = slotById.get("docs");
    const description =
      groupKeys.includes("docs") && !groupKeys.includes("pm")
        ? docsSlot?.description ??
          "Specs and write-ups where decisions live—Notion can cover this alongside PM when linked."
        : groupKeys.includes("pm") && !groupKeys.includes("docs")
          ? pmSlot?.description ??
            "Pages and databases from Notion so execution lines up with how your team plans work."
          : [pmSlot?.description, docsSlot?.description].filter(Boolean).join(" ") ||
            "Link Notion for planning and documentation your team already maintains in one workspace.";

    return (
      <div className={cardClass}>
        <div className="flex items-start gap-3">
          <ToolLogo toolId={toolId} name={name} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-zinc-900">{name}</p>
            <p className="mt-0.5 text-xs text-zinc-500">{categoryLabel}</p>
            <p
              className={`mt-1 text-xs font-medium ${
                connected.has("notion") ? "text-emerald-700" : "text-amber-700"
              }`}
            >
              {connected.has("notion") ? "On" : "Off"}
            </p>
          </div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600">{description}</p>
        <div className="mt-auto pt-4">
          <LiveConnectorActions
            provider="notion"
            apiBase={apiBase}
            statusById={statusById}
            connected={connected}
            disconnect={notionDisconnect}
            connectLabel="Connect Notion"
          />
        </div>
      </div>
    );
  }

  const liveSlot: SignalSlot | undefined =
    toolId === "slack"
      ? slotById.get("communication")
      : toolId === "linear"
        ? slotById.get("pm")
        : toolId === "github"
          ? slotById.get("engineering")
          : undefined;

  if (liveSlot && !liveSlot.roadmap && liveSlot.liveConnector) {
    const active = isSlotActive(liveSlot, connected);
    const statusLabel = active ? "On" : "Off";
    const statusClass = active ? "text-emerald-700" : "text-amber-700";

    return (
      <div className={cardClass}>
        <div className="flex items-start gap-3">
          <ToolLogo toolId={toolId} name={name} />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-zinc-900">{name}</p>
            <p className="mt-0.5 text-xs text-zinc-500">{categoryLabel}</p>
            <p className={`mt-1 text-xs font-medium ${statusClass}`}>{statusLabel}</p>
          </div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-zinc-600">{liveSlot.description}</p>
        <div className="mt-auto pt-4">
          {liveSlot.liveConnector === "github" ? (
            <LiveConnectorActions
              provider="github"
              apiBase={apiBase}
              statusById={statusById}
              connected={connected}
              disconnect={ghDisconnect}
              connectLabel="Connect GitHub"
            />
          ) : liveSlot.liveConnector === "linear" ? (
            <LiveConnectorActions
              provider="linear"
              apiBase={apiBase}
              statusById={statusById}
              connected={connected}
              disconnect={linDisconnect}
              connectLabel="Connect Linear"
            />
          ) : (
            <LiveConnectorActions
              provider="slack"
              apiBase={apiBase}
              statusById={statusById}
              connected={connected}
              disconnect={slackDisconnect}
              connectLabel="Connect Slack"
            />
          )}
        </div>
      </div>
    );
  }

  const roadmapSlotId = roadmapSlotIdForStackRow(groupKeys);
  const roadmapSlot = roadmapSlotId ? slotById.get(roadmapSlotId) : undefined;

  return (
    <div className={cardClass}>
      <div className="flex items-start gap-3">
        <ToolLogo toolId={toolId} name={name} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-zinc-900">{name}</p>
          <p className="mt-0.5 text-xs text-zinc-500">{categoryLabel}</p>
          <p className="mt-1 text-xs font-medium text-zinc-400">Soon</p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-zinc-600">
        {roadmapSlot?.description ?? comingSoonDescriptionForTool(groupKeys, toolId, slotById)}
      </p>
      <div className="mt-auto pt-4">
        <p className="text-xs text-zinc-500">Shipping later.</p>
        <button type="button" disabled className={`${disabledConnectClass} mt-3 w-full`}>
          Connect
        </button>
      </div>
    </div>
  );
}

function LiveConnectorActions({
  provider,
  apiBase,
  statusById,
  connected,
  disconnect,
  connectLabel,
}: {
  provider: "github" | "linear" | "notion" | "slack";
  apiBase: string;
  statusById: Map<string, ConnectorRow>;
  connected: Set<string>;
  disconnect: UseMutationResult<void, Error, void, unknown>;
  connectLabel: string;
}) {
  const row = statusById.get(provider);
  const apiConnected = row?.connected === true;
  const configured = row?.connector_configured !== false;
  const inMe = connected.has(provider);

  if (apiConnected || inMe) {
    return (
      <button
        type="button"
        className={disconnectBtnClass}
        disabled={disconnect.isPending}
        onClick={() => disconnect.mutate()}
      >
        {disconnect.isPending ? "Disconnecting…" : "Disconnect"}
      </button>
    );
  }
  if (!configured) {
    return (
      <p className="text-xs leading-snug text-amber-900">
        {provider === "github" && "GitHub is not configured on the API."}
        {provider === "linear" && "Linear OAuth is not configured on the API."}
        {provider === "notion" && "Notion OAuth is not configured on the API."}
        {provider === "slack" && "Slack OAuth is not configured on the API."}
      </p>
    );
  }
  return (
    <button
      type="button"
      className={btnConnect}
      onClick={() => {
        void (async () => {
          try {
            await startConnectorOAuthRedirect(apiBase, provider, CONNECTOR_OAUTH_RETURN_PATH);
          } catch (e) {
            window.alert(e instanceof Error ? e.message : "Could not start connect.");
          }
        })();
      }}
    >
      {connectLabel}
    </button>
  );
}

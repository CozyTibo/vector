import type { CSSProperties } from "react";
import { useMutation, useQuery, useQueryClient, type UseMutationResult } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  type ConnectorRow,
  connectorInstallUrl,
  disconnectConnector,
  fetchConnectors,
} from "../../lib/connectorsClient";
import { fetchOnboarding } from "../../lib/onboardingApi";
import { productApiBase, useProductMeQuery } from "../../lib/meApi";
import {
  emptyToolPick,
  hydrateToolPickFromAnswers,
  ONBOARDING_TOOL_GROUPS,
  type ToolPickState,
} from "../onboarding/onboardingToolGroups";
import { workspaceFlatPanel } from "../marketing/marketingStyles";
import EditToolsModal from "./EditToolsModal";
import { buildSignalWorkspaceActions } from "./signalWorkspaceActions";
import { currentCoveragePresentation, signalSliceConcept } from "./signalCoverageCopy";
import {
  isSlotActive,
  orderedThermometerSlots,
  signalStrengthPercentLive,
  WORKSPACE_SIGNAL_SLOTS,
  type SignalSlot,
} from "./signalCatalog";
import { ToolLogo } from "./toolLogos";
import {
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

const btnConnect =
  "inline-flex w-full items-center justify-center rounded-lg bg-[#E878BE] px-3 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#df6aad] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E878BE]";

const btnConnectSmall =
  "inline-flex items-center justify-center rounded-lg bg-[#E878BE] px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-colors hover:bg-[#df6aad] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E878BE] sm:px-4 sm:py-2 sm:text-sm";

const disconnectBtnClass =
  "w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-900 shadow-sm transition hover:border-zinc-300 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50";

const disabledConnectClass =
  "w-full cursor-not-allowed rounded-lg border border-zinc-200 bg-zinc-50 py-2 text-sm font-medium text-zinc-400";

const cardClass =
  "flex min-h-[10.5rem] flex-col rounded-2xl border border-zinc-100 bg-white p-4 sm:min-h-[11rem] sm:p-5";

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

  const thermSlots = orderedThermometerSlots(connected);

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
    const sl = params.get("slack_connected");
    const slErr = params.get("slack_error");
    if (gh === "1" || lin === "1" || sl === "1") {
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
    }
    if (
      oauthErr ||
      gh ||
      ghErr ||
      lin ||
      linErr ||
      params.get("oauth_ok") ||
      params.get("github_connected") ||
      params.get("linear_connected") ||
      params.get("slack_connected") ||
      params.get("slack_error")
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
    return buildSignalWorkspaceActions(
      effectiveStackPick,
      connected,
      statusById,
      apiBase,
      connectorsQ.isFetched,
    );
  }, [
    stackPrefsReady,
    effectiveStackPick,
    connected,
    statusById,
    apiBase,
    connectorsQ.isFetched,
  ]);

  const btnSecondary =
    "inline-flex shrink-0 items-center justify-center rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50";

  return (
    <div className="space-y-12 lg:space-y-14">
      <div className={`${workspaceFlatPanel} p-8 sm:p-10 lg:p-12`}>
        <div className="flex flex-col gap-12 lg:flex-row lg:items-stretch lg:gap-14 xl:gap-16">
          <div className="flex min-w-0 flex-1 gap-3 sm:gap-4 lg:gap-5">
            <div
              className="mx-auto flex h-[min(52vh,22rem)] w-4 shrink-0 flex-col gap-px overflow-hidden rounded-full bg-zinc-200/80 sm:h-[min(50vh,24rem)] lg:mx-0 lg:h-[min(56vh,26rem)]"
              role="img"
              aria-label={`Signal ladder, signal strength ${coverageUi.label}, ${pctLive} percent of live tools`}
            >
              {thermSlots.map((slot, i) => (
                <ThermometerSegment
                  key={slot.id}
                  slot={slot}
                  connected={connected}
                  isFirst={i === 0}
                  isLast={i === thermSlots.length - 1}
                />
              ))}
            </div>

            <div className="flex min-h-[min(52vh,22rem)] min-w-0 flex-1 flex-col sm:min-h-[min(50vh,24rem)] lg:min-h-[min(56vh,26rem)]">
              {thermSlots.map((slot) => (
                <div
                  key={`label-${slot.id}`}
                  style={segmentFlexStyle(slot.impactWeight)}
                  className="flex min-h-0 flex-col justify-center border-b border-zinc-100 py-2.5 first:pt-0 last:border-b-0 last:pb-0"
                >
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-base font-semibold leading-snug text-zinc-900 sm:text-lg">{slot.label}</p>
                      <ThermometerRowStatus slot={slot} connected={connected} />
                    </div>
                    <div className="flex min-w-[8.5rem] flex-1 flex-col items-end justify-center sm:min-w-[10rem]">
                      <p className="text-right text-sm font-medium text-zinc-600 sm:text-base">
                        {signalSliceConcept(slot.impactWeight)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex w-full shrink-0 flex-col justify-start border-t border-zinc-100 pt-10 lg:w-[min(100%,17.5rem)] lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.1em] text-zinc-500">Signal strength</p>
              <p
                className={`mt-2 text-4xl font-bold tracking-tight sm:text-5xl ${coverageUi.toneClass}`}
              >
                {coverageUi.label}
              </p>
            </div>
          </div>
        </div>

        <div className="mt-10 border-t border-zinc-100 pt-10 lg:mt-12 lg:pt-12">
          <h2 className="text-xl font-bold tracking-tight text-zinc-900">Actions</h2>
          <p className="mt-2 max-w-2xl text-sm text-zinc-600">
            Steps that strengthen your signals: connect tools you&apos;ve already added, then fill gaps in Edit tools
            where needed.
          </p>
          {!stackPrefsReady ? (
            <div className="mt-4 flex min-h-[4rem] items-center gap-3 text-sm text-zinc-500">
              <div
                className="h-5 w-5 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
                aria-hidden
              />
              Loading actions…
            </div>
          ) : workspaceActions.length > 0 ? (
            <ul className="mt-5 space-y-3">
              {workspaceActions.map((action) => (
                <li
                  key={action.id}
                  className="flex flex-col gap-3 rounded-xl border border-zinc-100 bg-zinc-50/60 p-4 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
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
                      <button type="button" className={btnSecondary} onClick={openEditTools}>
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
                            {action.provider === "slack" && "Slack OAuth isn’t configured on the API yet."}
                          </p>
                        ) : null}
                      </div>
                      {action.configured ? (
                        <a className={`${btnConnectSmall} shrink-0 sm:px-5`} href={action.installUrl}>
                          {action.title}
                        </a>
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

        <div className="mt-10 border-t border-zinc-100 pt-10 lg:mt-12 lg:pt-12">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-xl font-bold tracking-tight text-zinc-900">Stack coverage</h2>
            <button
              type="button"
              className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-800 shadow-sm transition hover:bg-zinc-50"
              onClick={openEditTools}
            >
              Edit tools
            </button>
          </div>

          {useMockConnectors ? (
            <p className="mt-4 rounded-lg border-l-4 border-rose-400 bg-rose-50 py-3 pl-4 pr-4 text-sm text-rose-900">
              Development mode: mock connectors. OAuth flows may still hit real services; data can be sample-only.
            </p>
          ) : null}

          {banner ? (
            <div className="mt-4 rounded-lg border border-amber-200/90 bg-amber-50 py-3 px-4 text-sm text-amber-950">
              {banner}
            </div>
          ) : null}

          {connectorsQ.isError ? (
            <p className="mt-4 rounded-lg border border-red-200/80 bg-red-50/90 px-4 py-3 text-sm text-red-900">
              {(connectorsQ.error as Error).message}
            </p>
          ) : null}

          {onboardingQ.isPending && savedStackPick == null ? (
            <div className="mt-6 flex min-h-[8rem] items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50">
              <div className="flex flex-col items-center gap-3">
                <div
                  className="h-8 w-8 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
                  aria-hidden
                />
                <p className="text-sm text-zinc-600">Loading stack preferences…</p>
              </div>
            </div>
          ) : connectorsQ.isPending ? (
            <div className="mt-6 flex min-h-[12rem] items-center justify-center rounded-2xl border border-dashed border-zinc-200 bg-zinc-50/50">
              <div className="flex flex-col items-center gap-3">
                <div
                  className="h-8 w-8 animate-spin rounded-full border-2 border-[#E878BE]/25 border-t-[#E878BE]"
                  aria-hidden
                />
                <p className="text-sm text-zinc-600">Loading connector status…</p>
              </div>
            </div>
          ) : (
            <>
              {stackToolRows.length === 0 ? (
                <p className="mt-6 text-sm text-zinc-600">
                  Nothing in your stack yet. Use <span className="font-medium text-zinc-900">Edit tools</span> to add
                  tools—each selection appears here.
                </p>
              ) : (
                <div className="mt-6 grid gap-3 sm:grid-cols-2 sm:gap-4 lg:grid-cols-3">
                  {stackToolRows.map((row) => (
                    <StackToolCard
                      key={row.key}
                      groupKey={row.groupKey}
                      toolId={row.toolId}
                      apiBase={apiBase}
                      connected={connected}
                      statusById={statusById}
                      slotById={slotById}
                      ghDisconnect={ghDisconnect}
                      linDisconnect={linDisconnect}
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

function comingSoonDescriptionForTool(
  groupKey: keyof ToolPickState,
  toolId: string,
  slotById: Map<string, SignalSlot>,
): string {
  if (groupKey === "calls") {
    return slotById.get("calls")?.description ?? "Recordings and transcripts are planned as we expand connectors.";
  }
  if (groupKey === "docs") {
    return slotById.get("docs")?.description ?? "Documentation ingestion is planned as we expand connectors.";
  }
  if (groupKey === "calendars") {
    return slotById.get("calendar")?.description ?? "Calendar intelligence is planned as we expand connectors.";
  }
  if (groupKey === "communication" && toolId !== "slack") {
    return "Slack is the live integration today; we’ll add more communication tools as connectors ship.";
  }
  if (groupKey === "pm" && toolId !== "linear") {
    return "Linear is the live integration today; we’ll add more PM tools as connectors ship.";
  }
  if (groupKey === "engineering" && toolId !== "github") {
    return "GitHub is the live integration today; we’ll add more code hosts as connectors ship.";
  }
  return "Not available to connect yet.";
}

function StackToolCard({
  groupKey,
  toolId,
  apiBase,
  connected,
  statusById,
  slotById,
  ghDisconnect,
  linDisconnect,
  slackDisconnect,
}: {
  groupKey: keyof ToolPickState;
  toolId: string;
  apiBase: string;
  connected: Set<string>;
  statusById: Map<string, ConnectorRow>;
  slotById: Map<string, SignalSlot>;
  ghDisconnect: UseMutationResult<void, Error, void, unknown>;
  linDisconnect: UseMutationResult<void, Error, void, unknown>;
  slackDisconnect: UseMutationResult<void, Error, void, unknown>;
}) {
  const name = toolLabelFromOnboarding(toolId);
  const categoryLabel = ONBOARDING_TOOL_GROUPS.find((g) => g.key === groupKey)?.label ?? "";

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
        <p className="mt-3 text-sm text-zinc-600">{signalSliceConcept(liveSlot.impactWeight)}</p>
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

  const roadmapSlotId =
    groupKey === "calls" ? "calls" : groupKey === "docs" ? "docs" : groupKey === "calendars" ? "calendar" : null;
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
        {roadmapSlot?.description ?? comingSoonDescriptionForTool(groupKey, toolId, slotById)}
      </p>
      {roadmapSlot ? (
        <p className="mt-3 text-sm text-zinc-600">{signalSliceConcept(roadmapSlot.impactWeight)}</p>
      ) : null}
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
  provider: "github" | "linear" | "slack";
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
        {provider === "slack" && "Slack OAuth is not configured on the API."}
      </p>
    );
  }
  return (
    <a className={btnConnect} href={connectorInstallUrl(apiBase, provider)}>
      {connectLabel}
    </a>
  );
}

function ThermometerSegment({
  slot,
  connected,
  isFirst,
  isLast,
}: {
  slot: SignalSlot;
  connected: Set<string>;
  isFirst: boolean;
  isLast: boolean;
}) {
  const active = isSlotActive(slot, connected);
  const round =
    isFirst && isLast ? "rounded-full" : isFirst ? "rounded-t-full" : isLast ? "rounded-b-full" : "";

  let inner: string;
  if (slot.roadmap) {
    inner = "bg-zinc-300/50";
  } else if (active) {
    inner = "bg-[#E878BE]";
  } else {
    inner = "bg-zinc-200";
  }

  return (
    <div style={segmentFlexStyle(slot.impactWeight)} className="min-h-0 w-full min-h-[4px]">
      <div
        className={`h-full w-full ${round} ${inner}`}
        title={`${slot.label}: ${signalSliceConcept(slot.impactWeight)}`}
      />
    </div>
  );
}

/** Thermometer rows: On/Off only — roadmap slots omit status; connect/disconnect lives on stack cards. */
function ThermometerRowStatus({ slot, connected }: { slot: SignalSlot; connected: Set<string> }) {
  if (slot.roadmap) {
    return null;
  }
  const active = isSlotActive(slot, connected);
  if (active) {
    return <p className="mt-1 text-sm text-zinc-600">On</p>;
  }
  return <p className="mt-1 text-sm text-amber-700">Off</p>;
}

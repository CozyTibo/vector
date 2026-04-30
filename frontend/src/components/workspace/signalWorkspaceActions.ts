import type { ConnectorRow } from "../../lib/connectorsClient";
import { connectorInstallUrl } from "../../lib/connectorsClient";
import type { ToolPickState } from "../onboarding/onboardingToolGroups";

export type ExpandStackAction = {
  kind: "expand_stack";
  id: string;
  groupKey: keyof ToolPickState;
  title: string;
  body: string;
};

export type ConnectToolAction = {
  kind: "connect";
  id: string;
  provider: "slack" | "linear" | "github";
  title: string;
  body: string;
  configured: boolean;
  installUrl: string;
};

export type SignalWorkspaceAction = ExpandStackAction | ConnectToolAction;

const EXPAND_ROWS: {
  groupKey: keyof ToolPickState;
  title: string;
  body: string;
}[] = [
  {
    groupKey: "communication",
    title: "Add communication tools",
    body: "Nothing in this category yet. Use Edit tools to choose Slack, Microsoft Teams, or Discord—then connect Slack below when you’re ready.",
  },
  {
    groupKey: "pm",
    title: "Add project management tools",
    body: "Nothing in this category yet. Use Edit tools to choose Linear, Jira, ClickUp, or Notion—then connect Linear below when it’s available.",
  },
  {
    groupKey: "engineering",
    title: "Add engineering tools",
    body: "Nothing in this category yet. Use Edit tools to choose GitHub, GitLab, or Bitbucket—then connect GitHub below when it’s available.",
  },
  {
    groupKey: "calls",
    title: "Add video / meeting tools",
    body: "Nothing in this category yet. Use Edit tools to reflect Zoom, Meet, Teams, or Webex so we know what to prioritize next.",
  },
  {
    groupKey: "docs",
    title: "Add documentation tools",
    body: "Nothing in this category yet. Use Edit tools to include Notion, Confluence, or Google Docs in your stack.",
  },
  {
    groupKey: "calendars",
    title: "Add calendar tools",
    body: "Nothing in this category yet. Use Edit tools to include Google Calendar, Outlook, Apple Calendar, or Calendly.",
  },
];

function connectMeta(provider: "slack" | "linear" | "github"): { brand: string } {
  if (provider === "slack") {
    return { brand: "Slack" };
  }
  if (provider === "linear") {
    return { brand: "Linear" };
  }
  return { brand: "GitHub" };
}

/**
 * Ordered checklist: connect OAuth tools first (selected in stack but not linked), then “add category”
 * nudges (Edit tools). When connector status isn’t loaded yet, only expand nudges are returned.
 */
export function buildSignalWorkspaceActions(
  pick: ToolPickState,
  connected: Set<string>,
  statusById: Map<string, ConnectorRow>,
  apiBase: string,
  connectorsLoaded: boolean,
): SignalWorkspaceAction[] {
  const expandActions: SignalWorkspaceAction[] = [];

  for (const row of EXPAND_ROWS) {
    const arr = pick[row.groupKey] ?? [];
    if (row.groupKey === "communication" && arr.length === 0 && connected.has("slack")) {
      continue;
    }
    if (row.groupKey === "pm" && arr.length === 0 && connected.has("linear")) {
      continue;
    }
    if (row.groupKey === "engineering" && arr.length === 0 && connected.has("github")) {
      continue;
    }
    if (arr.length === 0) {
      expandActions.push({
        kind: "expand_stack",
        id: `expand-${String(row.groupKey)}`,
        groupKey: row.groupKey,
        title: row.title,
        body: row.body,
      });
    }
  }

  if (!connectorsLoaded) {
    return expandActions;
  }

  const connectActions: SignalWorkspaceAction[] = [];
  const connectCandidates: {
    provider: "slack" | "linear" | "github";
    selected: boolean;
  }[] = [
    { provider: "slack", selected: pick.communication?.includes("slack") ?? false },
    { provider: "linear", selected: pick.pm?.includes("linear") ?? false },
    { provider: "github", selected: pick.engineering?.includes("github") ?? false },
  ];

  /** Prefer higher signal weight first when multiple connects apply. */
  const order = { slack: 0, linear: 1, github: 2 };
  connectCandidates.sort((a, b) => order[a.provider] - order[b.provider]);

  for (const c of connectCandidates) {
    if (!c.selected) {
      continue;
    }
    if (connected.has(c.provider)) {
      continue;
    }
    const row = statusById.get(c.provider);
    const configured = row?.connector_configured !== false;
    const { brand } = connectMeta(c.provider);
    connectActions.push({
      kind: "connect",
      id: `connect-${c.provider}`,
      provider: c.provider,
      title: `Connect ${brand}`,
      body: `${brand} is in your stack but not connected yet. Connecting unlocks live signal for this lane.`,
      configured,
      installUrl: connectorInstallUrl(apiBase, c.provider),
    });
  }

  return [...connectActions, ...expandActions];
}

import type { ToolGroupDef } from "./ToolSelectorBlock";

/** Backend keys for ``answers_json.tools``. Keep ids in sync with
 * ``ONBOARDING_TOOL_OPTIONS`` in ``backend/src/vector/domains/onboarding/constants.py``.
 * Section order: Communication → PM → Engineering → Video calls → Documentation → Calendars.
 */
export const ONBOARDING_TOOL_GROUPS: ToolGroupDef[] = [
  {
    key: "communication",
    label: "Communication",
    items: [
      { id: "slack", label: "Slack" },
      { id: "ms_teams", label: "Microsoft Teams" },
      { id: "discord", label: "Discord" },
    ],
  },
  {
    key: "pm",
    label: "Project management",
    items: [
      { id: "linear", label: "Linear" },
      { id: "jira", label: "Jira" },
      { id: "clickup", label: "ClickUp" },
    ],
  },
  {
    key: "engineering",
    label: "Engineering",
    items: [
      { id: "github", label: "GitHub" },
      { id: "gitlab", label: "GitLab" },
      { id: "bitbucket", label: "Bitbucket" },
    ],
  },
  {
    key: "calls",
    label: "Video calls",
    items: [
      { id: "zoom", label: "Zoom" },
      { id: "google_meet", label: "Google Meet" },
      { id: "ms_teams", label: "Microsoft Teams" },
      { id: "webex", label: "Webex" },
    ],
  },
  {
    key: "docs",
    label: "Documentation",
    items: [
      { id: "notion", label: "Notion" },
      { id: "confluence", label: "Confluence" },
      { id: "google_docs", label: "Google Docs" },
    ],
  },
  {
    key: "calendars",
    label: "Calendars",
    items: [
      { id: "google_calendar", label: "Google Calendar" },
      { id: "outlook_calendar", label: "Outlook / Microsoft 365" },
      { id: "apple_calendar", label: "Apple Calendar" },
      { id: "calendly", label: "Calendly" },
    ],
  },
];

export type ToolPickState = Record<string, string[]>;

export function emptyToolPick(): ToolPickState {
  return Object.fromEntries(ONBOARDING_TOOL_GROUPS.map((g) => [g.key, [] as string[]]));
}

/** Payload keys sent to backend onboarding_flow `tools_selected`. */
export function toolPickToBackendPayload(pick: ToolPickState): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const g of ONBOARDING_TOOL_GROUPS) {
    out[g.key] = [...(pick[g.key] ?? [])].sort();
  }
  return out;
}

const TOOL_ID_TO_LABEL: Record<string, string> = {};
for (const g of ONBOARDING_TOOL_GROUPS) {
  for (const it of g.items) {
    TOOL_ID_TO_LABEL[it.id] = it.label;
  }
}

/** Human label for a stored tool id (e.g. `github` → GitHub). */
function labelForToolId(toolId: string): string {
  return TOOL_ID_TO_LABEL[toolId] ?? toolId;
}

/**
 * Display name for the communication tool the user chose (Slack, Microsoft Teams, or Discord).
 * Used for onboarding copy; order matches a single primary pick (slack, then Teams, then Discord).
 */
export function primaryCommunicationToolLabel(answers: Record<string, unknown>): string {
  const raw = answers.tools;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return "Slack";
  }
  const comm = (raw as Record<string, unknown>).communication;
  if (!Array.isArray(comm)) {
    return "Slack";
  }
  if (comm.includes("slack")) {
    return "Slack";
  }
  if (comm.includes("ms_teams")) {
    return "Microsoft Teams";
  }
  if (comm.includes("discord")) {
    return "Discord";
  }
  return "Slack";
}

/** Sorted unique display labels for a tools payload (same shape as backend `tools`). */
export function labelsForToolsPayload(tools: Record<string, string[]>): string[] {
  const labels = new Set<string>();
  for (const ids of Object.values(tools)) {
    for (const id of ids) {
      labels.add(labelForToolId(id));
    }
  }
  return [...labels].sort((a, b) => a.localeCompare(b));
}

export function hydrateToolPickFromAnswers(answers: Record<string, unknown>): ToolPickState {
  const next = emptyToolPick();
  const raw = answers.tools;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return next;
  }
  const o = raw as Record<string, unknown>;
  for (const g of ONBOARDING_TOOL_GROUPS) {
    const arr = o[g.key];
    if (Array.isArray(arr)) {
      next[g.key] = arr.filter((x): x is string => typeof x === "string");
    }
  }
  return next;
}

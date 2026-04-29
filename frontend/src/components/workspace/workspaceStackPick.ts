import { ONBOARDING_TOOL_GROUPS, type ToolPickState } from "../onboarding/onboardingToolGroups";

/**
 * Selected tools in onboarding group order, then item order — one UI row per selection (supports multiple
 * tools per category).
 */
export function orderedStackToolRows(pick: ToolPickState): { key: string; groupKey: keyof ToolPickState; toolId: string }[] {
  const rows: { key: string; groupKey: keyof ToolPickState; toolId: string }[] = [];
  for (const g of ONBOARDING_TOOL_GROUPS) {
    const selected = new Set(pick[g.key] ?? []);
    for (const item of g.items) {
      if (selected.has(item.id)) {
        rows.push({ key: `${String(g.key)}:${item.id}`, groupKey: g.key, toolId: item.id });
      }
    }
  }
  return rows;
}

export function cloneToolPick(pick: ToolPickState): ToolPickState {
  return Object.fromEntries(
    ONBOARDING_TOOL_GROUPS.map((g) => [g.key, [...(pick[g.key] ?? [])]]),
  ) as ToolPickState;
}

function uniq(ids: string[]): string[] {
  return [...new Set(ids)];
}

/** Ensure OAuth-connected products stay in the pick (cannot be hidden while connected). */
export function mergeConnectedProvidersIntoPick(
  pick: ToolPickState,
  connected: Set<string>,
): ToolPickState {
  const next = cloneToolPick(pick);
  if (connected.has("slack")) {
    next.communication = uniq([...(next.communication ?? []), "slack"]);
  }
  if (connected.has("linear")) {
    next.pm = uniq([...(next.pm ?? []), "linear"]);
  }
  if (connected.has("github")) {
    next.engineering = uniq([...(next.engineering ?? []), "github"]);
  }
  return next;
}

export function toolLabelFromOnboarding(toolId: string): string {
  for (const g of ONBOARDING_TOOL_GROUPS) {
    const it = g.items.find((x) => x.id === toolId);
    if (it) {
      return it.label;
    }
  }
  return toolId;
}

/** Live OAuth products we can lock in the edit modal while connected. */
export function isLiveConnectorToolId(toolId: string): boolean {
  return toolId === "slack" || toolId === "linear" || toolId === "github";
}

export function isToolLockedByConnection(toolId: string, connected: Set<string>): boolean {
  if (toolId === "slack") {
    return connected.has("slack");
  }
  if (toolId === "linear") {
    return connected.has("linear");
  }
  if (toolId === "github") {
    return connected.has("github");
  }
  return false;
}

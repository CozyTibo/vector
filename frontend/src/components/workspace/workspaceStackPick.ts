import { ONBOARDING_TOOL_GROUPS, type ToolPickState } from "../onboarding/onboardingToolGroups";

/**
 * One connector-status card per physical tool (`toolId`). The same id may appear in multiple groups in
 * `ToolPickState` (e.g. Notion under PM and Documentation); `groupKeys` preserves every group so actions
 * and payloads stay distinct while the UI does not duplicate the connector.
 */
export type StackToolRow = {
  /** Stable React key — unique per `toolId`. */
  key: string;
  toolId: string;
  /** Groups where this tool is selected (order = first seen walking `ONBOARDING_TOOL_GROUPS`). */
  groupKeys: (keyof ToolPickState)[];
};

/**
 * Selected tools in onboarding group order — one row per `toolId` (deduped across groups).
 */
export function orderedStackToolRows(pick: ToolPickState): StackToolRow[] {
  const byTool = new Map<string, { toolId: string; groupKeys: (keyof ToolPickState)[] }>();
  const order: string[] = [];

  for (const g of ONBOARDING_TOOL_GROUPS) {
    const selected = new Set(pick[g.key] ?? []);
    for (const item of g.items) {
      if (!selected.has(item.id)) {
        continue;
      }
      const existing = byTool.get(item.id);
      if (existing) {
        if (!existing.groupKeys.includes(g.key)) {
          existing.groupKeys.push(g.key);
        }
      } else {
        byTool.set(item.id, { toolId: item.id, groupKeys: [g.key] });
        order.push(item.id);
      }
    }
  }

  return order.map((toolId) => {
    const row = byTool.get(toolId)!;
    return { key: toolId, toolId, groupKeys: row.groupKeys };
  });
}

/** Human-readable category line for a deduped row (e.g. "Project management · Documentation"). */
export function categoryLabelsForStackRow(groupKeys: (keyof ToolPickState)[]): string {
  return groupKeys
    .map((k) => ONBOARDING_TOOL_GROUPS.find((g) => g.key === k)?.label ?? String(k))
    .join(" · ");
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

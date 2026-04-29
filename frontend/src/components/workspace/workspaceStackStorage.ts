import { ALL_CATALOG_TOOL_IDS } from "./connectorCatalog";
import {
  emptyToolPick,
  ONBOARDING_TOOL_GROUPS,
  type ToolPickState,
} from "../onboarding/onboardingToolGroups";
import { cloneToolPick } from "./workspaceStackPick";

const STORAGE_KEY_PICK = "vector:workspaceStackToolsPick";
const LEGACY_IDS_KEY = "vector:workspaceStackToolIds";

function uniq(ids: string[]): string[] {
  return [...new Set(ids)];
}

function migrateLegacyCatalogIdsToPick(): ToolPickState | null {
  try {
    const raw = localStorage.getItem(LEGACY_IDS_KEY);
    if (raw == null || raw === "") {
      return null;
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      localStorage.removeItem(LEGACY_IDS_KEY);
      return null;
    }
    const ids = parsed.filter((x): x is string => typeof x === "string");
    const allowed = new Set(ALL_CATALOG_TOOL_IDS);
    const pick = emptyToolPick();
    for (const id of ids) {
      if (!allowed.has(id)) {
        continue;
      }
      if (id === "slack") {
        pick.communication.push("slack");
      } else if (id === "linear") {
        pick.pm.push("linear");
      } else if (id === "github") {
        pick.engineering.push("github");
      } else if (id === "gitlab") {
        pick.engineering.push("gitlab");
      } else if (id === "jira") {
        pick.pm.push("jira");
      } else if (id === "notion") {
        pick.pm.push("notion");
      }
    }
    for (const g of ONBOARDING_TOOL_GROUPS) {
      pick[g.key] = uniq(pick[g.key] ?? []);
    }
    localStorage.removeItem(LEGACY_IDS_KEY);
    const any = ONBOARDING_TOOL_GROUPS.some((g) => (pick[g.key]?.length ?? 0) > 0);
    return any ? pick : null;
  } catch {
    return null;
  }
}

/** `null` = no saved override; use onboarding answers from the API. */
export function getWorkspaceStackToolsPick(): ToolPickState | null {
  try {
    const rawPick = localStorage.getItem(STORAGE_KEY_PICK);
    if (rawPick != null && rawPick !== "") {
      const parsed = JSON.parse(rawPick) as unknown;
      if (parsed != null && typeof parsed === "object" && !Array.isArray(parsed)) {
        const o = parsed as Record<string, unknown>;
        const pick = emptyToolPick();
        let any = false;
        for (const g of ONBOARDING_TOOL_GROUPS) {
          const arr = o[g.key];
          if (Array.isArray(arr)) {
            pick[g.key] = uniq(arr.filter((x): x is string => typeof x === "string"));
            if (pick[g.key].length > 0) {
              any = true;
            }
          }
        }
        if (any) {
          return pick;
        }
      }
    }

    const migrated = migrateLegacyCatalogIdsToPick();
    if (migrated) {
      setWorkspaceStackToolsPick(migrated);
      return migrated;
    }
    return null;
  } catch {
    return null;
  }
}

export function setWorkspaceStackToolsPick(pick: ToolPickState): void {
  try {
    localStorage.setItem(STORAGE_KEY_PICK, JSON.stringify(cloneToolPick(pick)));
  } catch {
    /* ignore quota */
  }
}

export function clearWorkspaceStackToolsPick(): void {
  try {
    localStorage.removeItem(STORAGE_KEY_PICK);
  } catch {
    /* ignore */
  }
}

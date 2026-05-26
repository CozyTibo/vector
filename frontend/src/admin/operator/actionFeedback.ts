import type { OperatorActionKind, OperatorActionResponse } from "./operatorTypes";

export type ActionFeedbackTone = "ok" | "warn" | "error" | "pending";

export type ActionFeedback = {
  tone: ActionFeedbackTone;
  title: string;
  detail: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value != null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function deletedRowsTotal(cleared: Record<string, unknown> | null): number | null {
  if (!cleared) return null;
  const total = cleared.deleted_rows_total;
  if (typeof total === "number") return total;
  const byTable = cleared.deleted_rows_by_table;
  if (byTable && typeof byTable === "object" && !Array.isArray(byTable)) {
    return Object.values(byTable as Record<string, unknown>).reduce<number>(
      (sum, n) => sum + (typeof n === "number" ? n : 0),
      0,
    );
  }
  return null;
}

function restartSummary(restarted: Record<string, unknown> | null): string {
  if (!restarted) return "Execution restart status unknown.";
  const reran = restarted.reran === true || restarted.restarted === true;
  if (reran) {
    const cursor = restarted.phase_cursor;
    const enqueue = asRecord(restarted.enqueue);
    const taskId = enqueue?.celery_task_id ?? enqueue?.task_id;
    const parts = ["Execution restarted from canonical."];
    if (typeof cursor === "string" && cursor) parts.push(`Cursor: ${cursor}.`);
    if (typeof taskId === "string" && taskId) parts.push(`Worker task ${taskId.slice(0, 8)}… enqueued.`);
    else parts.push("Convergence slice enqueued — watch Runtime for phase movement.");
    return parts.join(" ");
  }
  const reason = typeof restarted.reason === "string" ? restarted.reason : "unknown";
  const hint = typeof restarted.hint === "string" ? restarted.hint : null;
  return [`Execution did not restart (${reason.replace(/_/g, " ")}).`, hint].filter(Boolean).join(" ");
}

function executionRestarted(execution: Record<string, unknown> | null): boolean {
  const restarted = asRecord(execution?.restarted);
  if (!restarted) return false;
  return restarted.reran === true || restarted.restarted === true;
}

function flushFeedback(action: "flush_derived" | "flush_all", result: Record<string, unknown>): ActionFeedback {
  const execution = asRecord(result.execution);
  const cleared = asRecord(execution?.cleared);
  const restarted = asRecord(execution?.restarted);
  const deleted = deletedRowsTotal(cleared);
  const flushLabel = action === "flush_all" ? "Raw + derived data flushed" : "Derived data flushed";
  const deletedLine =
    deleted != null ? `${deleted.toLocaleString()} derived rows deleted.` : "Derived substrate cleared.";
  const restartLine = restartSummary(restarted);
  const syncs = Array.isArray(result.connector_syncs) ? result.connector_syncs : [];
  const syncOk = syncs.filter((row) => asRecord(row)?.ok === true).length;
  const syncLine =
    action === "flush_all" && syncs.length > 0
      ? `${syncOk}/${syncs.length} connector syncs queued.`
      : null;

  const reran = executionRestarted(execution);
  return {
    tone: reran ? "ok" : "warn",
    title: reran ? `${flushLabel} — pipeline rerun started` : `${flushLabel} — rerun may not have started`,
    detail: [deletedLine, restartLine, syncLine].filter(Boolean).join(" "),
  };
}

export function pendingActionFeedback(action: OperatorActionKind): ActionFeedback {
  switch (action) {
    case "flush_derived":
      return {
        tone: "pending",
        title: "Flushing derived data and rerunning from canonical…",
        detail: "This can take up to a minute. Do not close the tab.",
      };
    case "flush_all":
      return {
        tone: "pending",
        title: "Flushing raw + derived data and rerunning pipeline…",
        detail: "This can take up to a minute. Connector syncs will queue after flush.",
      };
    case "run_from_ingestion":
      return {
        tone: "pending",
        title: "Queueing ingestion syncs…",
        detail: null,
      };
    case "rebuild_retrieval_index":
      return {
        tone: "pending",
        title: "Rebuilding retrieval index…",
        detail: null,
      };
    case "rebuild_identities":
      return {
        tone: "pending",
        title: "Resetting identity repair cursor…",
        detail: "Marks tenant dirty; convergence worker runs phase-03 repair slices (no replay job).",
      };
    default:
      return {
        tone: "pending",
        title: `Running ${action.replace(/_/g, " ")}…`,
        detail: null,
      };
  }
}

export function formatActionFeedback(data: OperatorActionResponse): ActionFeedback {
  const { action, result } = data;

  if (action === "flush_derived" || action === "flush_all") {
    return flushFeedback(action, result);
  }

  if (action === "run_from_phase") {
    const execution = asRecord(result.execution);
    const restarted = asRecord(execution?.restarted);
    const reran = executionRestarted(execution);
    const phase = typeof result.start_phase === "string" ? result.start_phase : "selected phase";
    return {
      tone: reran ? "ok" : "warn",
      title: reran ? `Pipeline rerun started from ${phase}` : `Rerun from ${phase} did not start`,
      detail: restartSummary(restarted),
    };
  }

  if (action === "run_from_ingestion") {
    const syncs = Array.isArray(result.connector_syncs) ? result.connector_syncs : [];
    const ok = syncs.filter((row) => asRecord(row)?.ok === true).length;
    return {
      tone: ok > 0 ? "ok" : "warn",
      title: ok > 0 ? `Ingestion sync queued for ${ok} connector(s)` : "No connector syncs were queued",
      detail:
        typeof result.hint === "string"
          ? result.hint
          : "Check Integrations for active connections, then watch Runtime.",
    };
  }

  if (action === "restart_execution") {
    const restarted = asRecord(result.restarted) ?? asRecord(result);
    const reran = restarted?.reran === true || restarted?.restarted === true;
    return {
      tone: reran ? "ok" : "warn",
      title: reran ? "Execution restarted" : "Execution restart did not run",
      detail: restartSummary(restarted),
    };
  }

  if (action === "clear_derived") {
    const deleted = deletedRowsTotal(asRecord(result.cleared) ?? result);
    return {
      tone: "ok",
      title: "Derived outputs cleared",
      detail: deleted != null ? `${deleted.toLocaleString()} rows deleted.` : null,
    };
  }

  if (action === "rebuild_retrieval_index") {
    return {
      tone: "ok",
      title: "Retrieval index rebuild started",
      detail: typeof result.hint === "string" ? result.hint : "Watch Retrieval inspect for epoch progress.",
    };
  }

  if (action === "rebuild_identities") {
    const dispatch = asRecord(result.convergence_dispatch);
    const scheduled = dispatch?.scheduled === true;
    const anchors = asRecord(result.counts_before)?.identity_anchors;
    return {
      tone: scheduled ? "ok" : "warn",
      title: scheduled ? "Repair cursor reset — convergence scheduled" : "Repair cursor reset",
      detail: [
        typeof result.hint === "string" ? result.hint : null,
        anchors != null ? `${Number(anchors).toLocaleString()} anchors in scope.` : null,
        "Watch Runtime or Substrate truth for slice progress (same path as phase 03).",
      ]
        .filter(Boolean)
        .join(" "),
    };
  }

  if (action === "p0_recover") {
    return {
      tone: "ok",
      title: "P0 recovery completed",
      detail: null,
    };
  }

  const actionLabel = String(action).replace(/_/g, " ");
  return {
    tone: "ok",
    title: `${actionLabel} completed`,
    detail: null,
  };
}

export function isLongRunningAction(action: OperatorActionKind): boolean {
  return (
    action === "flush_derived" ||
    action === "flush_all" ||
    action === "rebuild_retrieval_index" ||
    action === "rebuild_identities"
  );
}

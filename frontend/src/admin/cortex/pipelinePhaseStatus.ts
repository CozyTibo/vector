import type { ExecutionInspect, OperatorPhase, PhaseOverview, PhaseStatus } from "./pipelineTypes";
import { OPERATOR_PHASES } from "./pipelineTypes";

const PHASE_ID_TO_OPERATOR: Record<string, OperatorPhase> = {
  "02_canonical": "canonical",
  "03_identity": "identity",
  "04_graph": "graph",
  "05_traversal": "graph",
  "06_tcre": "reconstruction",
  "07_retrieval": "retrieval",
  "08_synthesis": "synthesis",
};

const FSM_TO_OPERATOR: Record<string, OperatorPhase> = {
  CANONICAL: "canonical",
  CANONICAL_DRAINING: "canonical",
  IDENTITY: "identity",
  GRAPH: "graph",
  TRAVERSAL: "graph",
  TCRE: "reconstruction",
  AWAITING_TCRE: "reconstruction",
  RETRIEVAL: "retrieval",
  SYNTHESIS: "synthesis",
  BLOCKED: "canonical",
  IDLE: "synthesis",
};

function mirrorStatusToPhaseStatus(raw: string | undefined, receiptOutcome: string | null): PhaseStatus {
  const st = (raw || "").toLowerCase();
  if (receiptOutcome === "BLOCKED") return "blocked";
  if (st === "failed") return "blocked";
  if (st === "running") return "running";
  if (st === "waiting") return "waiting";
  if (st === "completed" || st === "skipped") return "healthy";
  if (st === "queued") return "waiting";
  return "waiting";
}

export function buildPhaseOverviews(inspect: ExecutionInspect | null): PhaseOverview[] {
  const lease = inspect?.lease;
  const phaseStatus = inspect?.progression?.phase_status ?? {};
  const receiptOutcome =
    inspect?.progression?.execution_lease?.last_phase_receipt_outcome ?? null;
  const activeOperator = lease?.fsm_state
    ? FSM_TO_OPERATOR[lease.fsm_state] ?? null
    : null;
  const blockReason = lease?.block_reason_code ?? inspect?.progression?.stop_reason ?? null;

  return OPERATOR_PHASES.map(({ phase, label, route }) => {
    if (phase === "ingestion") {
      return {
        phase,
        label,
        status: "healthy" as PhaseStatus,
        detail: "Pre-execution: connector sync",
        route,
      };
    }

    const mirrorKey = Object.entries(PHASE_ID_TO_OPERATOR).find(([, op]) => op === phase)?.[0];
    const rawMirror = mirrorKey ? phaseStatus[mirrorKey] : undefined;
    let status = mirrorStatusToPhaseStatus(rawMirror, null);

    if (activeOperator === phase && lease?.status === "RUNNING") {
      status = "running";
    }
    if (activeOperator === phase && lease?.fsm_state === "BLOCKED") {
      status = "blocked";
    }
    if (receiptOutcome === "BLOCKED" && activeOperator === phase) {
      status = "blocked";
    }

    const detail =
      status === "blocked" && blockReason
        ? blockReason
        : rawMirror
          ? `mirror: ${rawMirror}`
          : lease?.fsm_state && FSM_TO_OPERATOR[lease.fsm_state] === phase
            ? lease.fsm_state
            : null;

    return { phase, label, status, detail, route };
  });
}

export function collectAttention(phases: PhaseOverview[]): string[] {
  const out: string[] = [];
  for (const p of phases) {
    if (p.status === "blocked" && p.detail) {
      out.push(`${p.label} blocked: ${p.detail}`);
    } else if (p.status === "blocked") {
      out.push(`${p.label} is blocked`);
    } else if (p.status === "degraded") {
      out.push(`${p.label} degraded`);
    }
  }
  return out.slice(0, 5);
}

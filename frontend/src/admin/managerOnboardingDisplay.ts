/**
 * Business-facing labels for manager Slack onboarding collected answers.
 * ``backendStep`` aligns with backend ``STEP_ORDER`` (excl. COMPLETED).
 */

const MANAGER_STEP_ORDER = [
  "Q1_SCOPE_INTENT",
  "Q1B_PEER_HANDLES",
  "Q2_TEAM_SCOPE",
  "Q3_TEAM_MEMBERS",
  "Q4_OBSERVED_CHANNELS",
  "Q5_REPORTS_TO",
  "Q5B_REPORTS_WHO",
  "Q6_KPIS",
] as const;

type CollectedAnswerStatus = "complete" | "pending" | "attention";

function stepOrderIndex(step: string): number {
  if (step === "COMPLETED") {
    return MANAGER_STEP_ORDER.length;
  }
  const i = MANAGER_STEP_ORDER.indexOf(step as (typeof MANAGER_STEP_ORDER)[number]);
  return i >= 0 ? i : MANAGER_STEP_ORDER.length;
}

/** Green = captured, gray = not yet / waiting, red = stuck or data gap. */
export function collectedAnswerStatus(opts: {
  sessionStatus: string;
  currentStep: string;
  backendStep: string;
  hasValue: boolean;
}): CollectedAnswerStatus {
  if (opts.hasValue) {
    return "complete";
  }
  const cur = stepOrderIndex(opts.currentStep);
  const row = stepOrderIndex(opts.backendStep);
  const st = opts.sessionStatus.trim().toLowerCase();
  const badSession = st === "needs_review" || st === "failed" || st === "paused";
  if (badSession && row === cur) {
    return "attention";
  }
  if (row < cur) {
    return "attention";
  }
  return "pending";
}

export function statusIndicatorEmoji(status: CollectedAnswerStatus): string {
  if (status === "complete") return "✅";
  if (status === "attention") return "⚠️";
  return "⬚";
}

export function statusIndicatorClass(status: CollectedAnswerStatus): string {
  if (status === "complete") return "text-emerald-700";
  if (status === "attention") return "text-red-600";
  return "text-stone-400";
}

/** Resolved Slack display strings for admin collected-answers (from session API). */
type ManagerOnboardingAnswerLabels = {
  users: Record<string, string>;
  channels: Record<string, string>;
};

type CollectedStepRow = {
  order: number;
  backendStep: string;
  title: string;
  hint: string;
  hasValue: (answers: Record<string, unknown>) => boolean;
  formatDisplay: (answers: Record<string, unknown>, labels: ManagerOnboardingAnswerLabels) => string;
};

function str(v: unknown): string {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  return String(v);
}

function formatUserIdList(v: unknown, labels: Record<string, string>): string {
  if (!Array.isArray(v) || v.length === 0) {
    return "—";
  }
  return v
    .map((x) => {
      if (typeof x !== "string") {
        return String(x);
      }
      const t = x.trim();
      const k = t.toUpperCase();
      return labels[t] ?? labels[k] ?? t;
    })
    .join(", ");
}

function formatChannelIdList(v: unknown, labels: Record<string, string>): string {
  if (!Array.isArray(v) || v.length === 0) {
    return "—";
  }
  return v
    .map((x) => {
      if (typeof x !== "string") {
        return String(x);
      }
      const t = x.trim();
      const k = t.toUpperCase();
      return labels[t] ?? labels[k] ?? t;
    })
    .join(", ");
}

function scopeLabel(v: unknown): string {
  const s = str(v);
  if (s === "just_me") return "Just this manager";
  if (s === "other_managers") return "This manager plus other managers";
  return s || "—";
}

function yesNoUnknown(v: unknown): string {
  if (v === true) return "Yes";
  if (v === false) return "No";
  return "—";
}

export const MANAGER_COLLECTED_STEPS: CollectedStepRow[] = [
  {
    order: 1,
    backendStep: "Q1_SCOPE_INTENT",
    title: "Onboarding scope",
    hint: "Whether Vector is only talking to this manager or onboarding peers too.",
    hasValue: (a) => Boolean(str(a.scope_intent)),
    formatDisplay: (a, _labels) => scopeLabel(a.scope_intent),
  },
  {
    order: 2,
    backendStep: "Q1B_PEER_HANDLES",
    title: "Other managers (Slack)",
    hint: "Additional managers to include when scope covers more than one person.",
    hasValue: (a) => {
      if (str(a.scope_intent) === "just_me") {
        return true;
      }
      return (
        Array.isArray(a.peer_slack_user_ids) && (a.peer_slack_user_ids as unknown[]).length > 0
      );
    },
    formatDisplay: (a, labels) => {
      if (str(a.scope_intent) === "just_me") {
        return "Not needed (solo manager)";
      }
      return formatUserIdList(a.peer_slack_user_ids, labels.users);
    },
  },
  {
    order: 3,
    backendStep: "Q2_TEAM_SCOPE",
    title: "What this team does",
    hint: "Short description of the team’s mission or scope of work.",
    hasValue: (a) => Boolean(str(a.team_scope)),
    formatDisplay: (a, _labels) => str(a.team_scope) || "—",
  },
  {
    order: 4,
    backendStep: "Q3_TEAM_MEMBERS",
    title: "People on the team",
    hint: "Slack people the manager named for their team.",
    hasValue: (a) =>
      (Array.isArray(a.team_member_slack_ids) && (a.team_member_slack_ids as unknown[]).length > 0) ||
      (Array.isArray(a.team_members) && (a.team_members as unknown[]).length > 0),
    formatDisplay: (a, labels) =>
      formatUserIdList(a.team_member_slack_ids, labels.users) !== "—"
        ? formatUserIdList(a.team_member_slack_ids, labels.users)
        : formatUserIdList(a.team_members, labels.users),
  },
  {
    order: 5,
    backendStep: "Q4_OBSERVED_CHANNELS",
    title: "Channels Vector should watch",
    hint: "Slack channels for execution signals (or skipped if they chose not to list any).",
    hasValue: (a) =>
      a.observed_channels_skipped === true ||
      (Array.isArray(a.observed_channel_ids) && (a.observed_channel_ids as unknown[]).length > 0),
    formatDisplay: (a, labels) => {
      if (a.observed_channels_skipped === true) return "Skipped (no channels listed)";
      return formatChannelIdList(a.observed_channel_ids, labels.channels);
    },
  },
  {
    order: 6,
    backendStep: "Q5_REPORTS_TO",
    title: "Reports to a leader",
    hint: "Whether this manager reports to someone above them.",
    hasValue: (a) => a.reports_to_yes !== null && a.reports_to_yes !== undefined,
    formatDisplay: (a, _labels) => yesNoUnknown(a.reports_to_yes),
  },
  {
    order: 7,
    backendStep: "Q5B_REPORTS_WHO",
    title: "Who they report to",
    hint: "Slack people in their management chain.",
    hasValue: (a) => {
      if (a.reports_to_yes === false) return true;
      if (a.reports_to_yes === true) {
        return (
          Array.isArray(a.reports_to_slack_ids) && (a.reports_to_slack_ids as unknown[]).length > 0
        );
      }
      return false;
    },
    formatDisplay: (a, labels) => {
      if (a.reports_to_yes === false) return "Not needed (they don't report to anyone)";
      return formatUserIdList(a.reports_to_slack_ids, labels.users);
    },
  },
  {
    order: 8,
    backendStep: "Q6_KPIS",
    title: "Success / KPI expectations",
    hint: "What “good” looks like for this team from the manager’s perspective.",
    hasValue: (a) => {
      if (a.reports_to_yes === false) return true;
      if (a.reports_to_yes === true) return Boolean(str(a.kpi_expectations));
      return false;
    },
    formatDisplay: (a, _labels) => {
      if (a.reports_to_yes === false) {
        return "Not asked — we only ask this when they report to someone";
      }
      return str(a.kpi_expectations) || "—";
    },
  },
];

export function managerStatusBusinessLabel(status: string): string {
  const x = status.trim().toLowerCase();
  switch (x) {
    case "completed":
      return "Finished";
    case "waiting_for_user":
      return "Waiting on the manager";
    case "active":
      return "In progress";
    case "needs_review":
      return "Needs internal review";
    case "paused":
      return "Paused";
    case "failed":
      return "Blocked / error";
    default:
      return status || "—";
  }
}

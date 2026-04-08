/** Canonical step ids (mirror backend ``STEP_ORDER`` minus COMPLETED). */
export const MANAGER_ONBOARDING_STEPS = [
  "Q1_SCOPE_INTENT",
  "Q1B_PEER_HANDLES",
  "Q2_TEAM_SCOPE",
  "Q3_TEAM_MEMBERS",
  "Q4_OBSERVED_CHANNELS",
  "Q5_REPORTS_TO",
  "Q5B_REPORTS_WHO",
  "Q6_KPIS",
] as const;

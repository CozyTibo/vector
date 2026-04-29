/**
 * Signal “slots” for the workspace Signals gauge. Each slot maps to a live connector when available,
 * or is marked roadmap-only until Vector ships ingestion for that category.
 *
 * `impactWeight` — relative contribution to risk/signal quality when connected (sum = 100).
 * Calendar is intentionally the smallest lever; communication & execution stack matter most.
 */
export type SignalSlot = {
  id: string;
  label: string;
  description: string;
  /** Provider key from GET /me `connected_connectors` when this slot is live today. */
  liveConnector?: "slack" | "linear" | "github";
  roadmap: boolean;
  /** Share of total signal potential (all slots sum to 100). */
  impactWeight: number;
};

export const WORKSPACE_SIGNAL_SLOTS: SignalSlot[] = [
  {
    id: "communication",
    label: "Communication",
    description: "Slack messages and DMs where work actually gets discussed.",
    liveConnector: "slack",
    roadmap: false,
    impactWeight: 30,
  },
  {
    id: "pm",
    label: "Project management",
    description: "Issues and cycles from your PM tool so execution lines up with plans.",
    liveConnector: "linear",
    roadmap: false,
    impactWeight: 22,
  },
  {
    id: "engineering",
    label: "Engineering",
    description: "Repos, PRs, and commits from your code host.",
    liveConnector: "github",
    roadmap: false,
    impactWeight: 22,
  },
  {
    id: "calls",
    label: "Meetings & calls",
    description: "Recordings and transcripts (coming as we expand connectors).",
    roadmap: true,
    impactWeight: 12,
  },
  {
    id: "docs",
    label: "Documentation",
    description: "Specs and write-ups where decisions live.",
    roadmap: true,
    impactWeight: 8,
  },
  {
    id: "calendar",
    label: "Calendar",
    description: "How time is allocated across teams and milestones.",
    roadmap: true,
    impactWeight: 6,
  },
];

/** Sum of impact weights (should be 100). */
export const SIGNAL_WEIGHT_TOTAL = WORKSPACE_SIGNAL_SLOTS.reduce((s, x) => s + x.impactWeight, 0);

/**
 * Canonical top → bottom order for slots **within** a group (roadmap, connectable, or connected).
 * Full thermometer order is built dynamically so roadmap stays at the top, “can connect” in the middle,
 * and completed connectors at the bottom — avoiding a grey segment between pink bands.
 */
export const THERMOMETER_SLOT_ORDER: string[] = [
  "calendar",
  "docs",
  "calls",
  "engineering",
  "pm",
  "communication",
];

export function slotById(id: string): SignalSlot | undefined {
  return WORKSPACE_SIGNAL_SLOTS.find((s) => s.id === id);
}

function slotOrderIndex(id: string): number {
  const i = THERMOMETER_SLOT_ORDER.indexOf(id);
  return i === -1 ? 999 : i;
}

function sortSlotsByThermometerOrder(slots: SignalSlot[]): SignalSlot[] {
  return [...slots].sort((a, b) => slotOrderIndex(a.id) - slotOrderIndex(b.id));
}

export function isSlotActive(slot: SignalSlot, connected: Set<string>): boolean {
  if (slot.liveConnector) {
    return connected.has(slot.liveConnector);
  }
  return false;
}

/**
 * Thermometer + label column order: not available yet (roadmap) → can still connect → connected.
 * Keeps completed segments grouped at the bottom of the bar.
 */
export function orderedThermometerSlots(connected: Set<string>): SignalSlot[] {
  const roadmap = WORKSPACE_SIGNAL_SLOTS.filter((s) => s.roadmap);
  const live = WORKSPACE_SIGNAL_SLOTS.filter((s) => !s.roadmap && s.liveConnector);
  const connectable = live.filter((s) => !isSlotActive(s, connected));
  const complete = live.filter((s) => isSlotActive(s, connected));
  return [
    ...sortSlotsByThermometerOrder(roadmap),
    ...sortSlotsByThermometerOrder(connectable),
    ...sortSlotsByThermometerOrder(complete),
  ];
}

/** Points earned from connected tools only (roadmap slots contribute 0 until shipped). */
export function earnedSignalPoints(connected: Set<string>): number {
  let sum = 0;
  for (const slot of WORKSPACE_SIGNAL_SLOTS) {
    if (isSlotActive(slot, connected)) {
      sum += slot.impactWeight;
    }
  }
  return sum;
}

/** Maximum points achievable with today’s live connectors only. */
export function maxLiveSignalPoints(): number {
  return WORKSPACE_SIGNAL_SLOTS.filter((s) => !s.roadmap).reduce((s, x) => s + x.impactWeight, 0);
}

/**
 * 0–100 strength vs what you can connect **right now** (all live tools on = 100).
 * Roadmap categories are excluded from this score so finishing Slack/Linear/GitHub feels complete.
 */
export function signalStrengthPercentLive(connected: Set<string>): number {
  const max = maxLiveSignalPoints();
  if (max <= 0) {
    return 0;
  }
  const liveEarned = WORKSPACE_SIGNAL_SLOTS.filter((s) => !s.roadmap && isSlotActive(s, connected)).reduce(
    (acc, s) => acc + s.impactWeight,
    0,
  );
  return Math.round((liveEarned / max) * 100);
}

/**
 * 0–100 share of **full future** stack (includes roadmap weights in denominator).
 * Shows headroom until Calendar, Docs, Calls ship.
 */
export function signalStrengthPercentFullStack(connected: Set<string>): number {
  if (SIGNAL_WEIGHT_TOTAL <= 0) {
    return 0;
  }
  return Math.round((earnedSignalPoints(connected) / SIGNAL_WEIGHT_TOTAL) * 100);
}

/** @deprecated Use signalStrengthPercentLive for headline or signalStrengthPercentFullStack for tube fill. */
export function signalStrengthPercent(connected: Set<string>): number {
  return signalStrengthPercentLive(connected);
}

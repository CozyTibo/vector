export type CoveragePresentation = {
  label: "High" | "Medium" | "Low";
  /** Same Tailwind text color for band label, page subtitle, and emphasis. */
  toneClass: string;
  /** Workspace hero subtitle — matches coverage band color. */
  headlineSentence: string;
};

/**
 * Live coverage % → band + colored headline (tertiles).
 */
export function currentCoveragePresentation(pct: number): CoveragePresentation {
  if (pct >= 67) {
    return {
      label: "High",
      toneClass: "text-emerald-600",
      headlineSentence:
        "Your ingested signals look strong—connect more tools to sharpen coverage further.",
    };
  }
  if (pct >= 34) {
    return {
      label: "Medium",
      toneClass: "text-amber-600",
      headlineSentence:
        "Your signals are building—each new connection strengthens what we can detect.",
    };
  }
  return {
    label: "Low",
    toneClass: "text-rose-600",
    headlineSentence: "Your signals are still light—connect priority tools to improve coverage.",
  };
}

/**
 * Human-readable “size” of a thermometer / stack row (no numeric weights in UI).
 */
export function signalSliceConcept(impactWeight: number): string {
  if (impactWeight >= 22) {
    return "Strong signal";
  }
  if (impactWeight >= 10) {
    return "Moderate signal";
  }
  return "Light signal";
}

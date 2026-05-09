import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

export type TimeRangePreset = "1h" | "24h" | "7d" | "all";

export type CanonicalOperatorFilters = {
  connector: string;
  bundle: string;
  objectKind: string;
  status: string;
  confidenceClass: string;
  replayClass: string;
  timeRange: TimeRangePreset;
};

const defaults: CanonicalOperatorFilters = {
  connector: "",
  bundle: "",
  objectKind: "",
  status: "",
  confidenceClass: "",
  replayClass: "",
  timeRange: "all",
};

type Ctx = {
  filters: CanonicalOperatorFilters;
  setFilters: (patch: Partial<CanonicalOperatorFilters>) => void;
};

const CanonicalFiltersContext = createContext<Ctx | null>(null);

export function CanonicalOperatorFiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setF] = useState(defaults);
  const setFilters = useCallback((patch: Partial<CanonicalOperatorFilters>) => {
    setF((s) => ({ ...s, ...patch }));
  }, []);
  const value = useMemo(() => ({ filters, setFilters }), [filters, setFilters]);
  return <CanonicalFiltersContext.Provider value={value}>{children}</CanonicalFiltersContext.Provider>;
}

export function useCanonicalOperatorFilters(): Ctx {
  const c = useContext(CanonicalFiltersContext);
  if (!c) {
    throw new Error("CanonicalOperatorFiltersProvider missing");
  }
  return c;
}

/** Client-side time filter for feed rows with ISO timestamps. */
export function matchesTimeRange(iso: string | null | undefined, preset: TimeRangePreset): boolean {
  if (!iso || preset === "all") return true;
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t)) return true;
  const windowsMs: Record<Exclude<TimeRangePreset, "all">, number> = {
    "1h": 3600_000,
    "24h": 86_400_000,
    "7d": 604_800_000,
  };
  return Date.now() - t <= windowsMs[preset];
}

import type { ReactNode } from "react";

import type { CortexCanonicalControlPlane } from "../cortexAdminTypes.ts";
import { formatRelativeAge } from "../cortexAdminTypes.ts";
import { HealthTone, pillLabel, toneChipCls } from "./operatorUi.tsx";

type ReplayInspector = {
  recent_jobs?: Array<{
    job_id: string;
    status: string;
    pinned_bundle_id?: string | null;
    counts_by_divergence_class?: Record<string, number>;
    completed_at?: string | null;
    created_at?: string | null;
  }>;
};

function chip(tone: HealthTone, label: string, value: ReactNode, hint?: string) {
  return (
    <div
      className={`min-w-[9.5rem] flex-1 rounded-lg border px-3 py-2 shadow-sm ${toneChipCls(tone)}`}
      title={hint}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold">{value}</p>
      <p className="mt-0.5 text-[10px] font-semibold uppercase">{pillLabel(tone)}</p>
    </div>
  );
}

function replayStability(divTotals: Record<string, number> | undefined): { tone: HealthTone; label: string } {
  if (!divTotals || Object.keys(divTotals).length === 0) return { tone: "ok", label: "no receipts" };
  const bad = (divTotals.C3 ?? 0) + (divTotals.C4 ?? 0) + (divTotals.C5 ?? 0);
  const total = Object.values(divTotals).reduce((a, b) => a + (typeof b === "number" ? b : 0), 0);
  if (total === 0) return { tone: "ok", label: "no class tallies" };
  const pct = Math.max(0, Math.min(100, Math.round(100 * (1 - bad / total))));
  if (bad > 0) return { tone: "warn", label: `${pct}% stable` };
  return { tone: "ok", label: `${pct}% stable` };
}

function verificationTone(c: CortexCanonicalControlPlane): HealthTone {
  const passed = c.health_overview.last_verification_passed;
  const fresh = c.health_overview.verification_freshness_label !== "stale";
  if (passed === false) return "bad";
  if (passed === true && fresh) return "ok";
  return "warn";
}

export function CanonicalHealthStrip({ c }: { c: CortexCanonicalControlPlane }) {
  const h = c.health_overview;
  const replayInsp = c.inspectors?.replay_rebuild_inspector as ReplayInspector | undefined;
  const recent = replayInsp?.recent_jobs ?? [];
  const lastReplay = recent[0];
  const vt = c.verification_truth as Record<string, unknown> | null | undefined;
  const lastVerAt = typeof vt?.created_at === "string" ? vt.created_at : null;
  const mappingInsp = c.inspectors?.mapping_inspector as { pin_count?: number } | undefined;
  const bundleHead = (c.inspectors?.canonical_overview_inspector as { bundle_inventory_head?: string[] } | undefined)
    ?.bundle_inventory_head;

  const activePinHint =
    mappingInsp?.pin_count === 0 ? "No tenant pins — bundle resolution may be implicit." : undefined;

  const stab = replayStability(h.replay_divergence_class_totals_recent_completed);

  const oracleTone: HealthTone = lastVerAt ? "ok" : "warn";

  return (
    <section className="rounded-xl border border-indigo-100 bg-gradient-to-r from-indigo-50/90 via-white to-white p-4 shadow-sm ring-1 ring-indigo-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-wide text-indigo-800">Canonical control plane</p>
          <h2 className="mt-0.5 text-lg font-semibold text-stone-900">Operational health</h2>
          <p className="mt-1 max-w-3xl text-xs text-stone-600">
            Deterministic substrate snapshot — counts, replay divergence pressure, verification freshness, ambiguity,
            and registry posture.
          </p>
        </div>
        <div className="rounded-md border border-stone-200 bg-white px-3 py-2 font-mono text-[11px] text-stone-700 shadow-inner">
          schema v{c.canonical_control_plane_schema_version}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {chip("ok", "Canonical rows", h.materialization_row_count.toLocaleString())}
        {chip(stab.tone, "Replay stability", stab.label, "Recent completed jobs — C3/C4/C5 divergence totals")}
        {chip(
          mappingInsp?.pin_count ? "ok" : "warn",
          "Active bundle (pin)",
          bundleHead?.[0] ?? (mappingInsp?.pin_count ? `${mappingInsp.pin_count} pin(s)` : "none"),
          activePinHint,
        )}
        {chip(
          h.ambiguity_explosion_warn ? "bad" : h.ambiguity_open_count > 0 ? "warn" : "ok",
          "Open ambiguities",
          h.ambiguity_open_count.toLocaleString(),
          h.ambiguity_explosion_warn ? "Above explosion warning threshold" : undefined,
        )}
        {chip(
          h.active_canonical_failure_count > 0 ? "bad" : "ok",
          "Drift / failures",
          h.active_canonical_failure_count.toLocaleString(),
          "Active canonical failure cases",
        )}
        {chip(verificationTone(c), "Verification", h.last_verification_passed === false ? "last FAIL" : "ledger ok")}
        {chip(
          oracleTone,
          "Last verification run",
          lastVerAt ? formatRelativeAge(lastVerAt) : "never",
          typeof vt?.passed === "boolean" ? `passed=${String(vt.passed)}` : undefined,
        )}
        {chip(
          lastReplay?.status === "failed" ? "bad" : lastReplay?.status === "running" ? "warn" : "ok",
          "Last replay job",
          lastReplay ? `${lastReplay.status}` : "none",
          lastReplay?.job_id,
        )}
        {chip("ok", "Bundle inventory", h.mapping_bundle_inventory_count.toLocaleString())}
      </div>
    </section>
  );
}

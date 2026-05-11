import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { CortexMemoryControlPlane } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

function toneForTrust(state: string): "ok" | "warn" | "bad" | "neutral" {
  if (state === "healthy" || state === "replay-safe" || state === "reconstruction-safe") return "ok";
  if (state === "partial" || state === "degraded" || state === "lineage-incomplete") return "warn";
  if (state === "corrupted" || state === "continuity-broken" || state === "replay-diverged") return "bad";
  return "neutral";
}

export default function AdminCortexMemoryPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const controlQ = useQuery({
    queryKey: ["admin-cortex-memory-control-plane", tenantId],
    queryFn: () => adminJson<CortexMemoryControlPlane>(`/admin/tenants/${tenantId}/cortex/memory/control-plane`),
    enabled: Boolean(tenantId),
  });

  const recoveryMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/memory/recovery/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apply_repairs: true }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-memory-control-plane", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-overview", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-recent-runs", tenantId] });
    },
  });

  const retentionDryRunMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(`/admin/tenants/${tenantId}/cortex/memory/retention/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dry_run: true,
          archive_after_days: 30,
          delete_after_days: 365,
          allow_delete: false,
        }),
      });
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-memory-control-plane", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (controlQ.isPending) return <p className="text-sm text-stone-600">Loading Cortex memory control plane…</p>;
  if (controlQ.isError) return <p className="text-sm text-red-700">{(controlQ.error as Error).message}</p>;

  const c = controlQ.data;
  const h = c.health_overview;
  const trustTone = toneForTrust(h.trust_state);

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Raw Memory Control Plane</h2>
            <p className="text-sm text-stone-600">
              Operational memory truth: replay, provenance, temporal continuity, corruption, recovery.
            </p>
          </div>
          <StatusBadge tone={trustTone}>{h.trust_state}</StatusBadge>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Severity</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.severity}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Continuity gaps</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.continuity_gap_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Active failures</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.active_failure_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Replay jobs</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">
              {c.inspectors.replay_inspector.active_jobs} active / {c.inspectors.replay_inspector.jobs_count} total
            </p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Proof quality</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">
              {h.proof_quality_primary ?? "n/a"}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Verification freshness</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">
              {h.verification_freshness ?? "n/a"}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Critical pointer integrity</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">
              {h.critical_integrity_state ??
                (h.critical_integrity_passed === undefined ? "n/a" : h.critical_integrity_passed ? "passed" : "failed")}
            </p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Operational trust proof</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">
              {h.operational_trust_state ??
                (h.operational_trust_passed === undefined ? "n/a" : h.operational_trust_passed ? "passed" : "failed")}
            </p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-sm text-indigo-900"
            onClick={() => recoveryMut.mutate()}
            disabled={recoveryMut.isPending}
          >
            {recoveryMut.isPending ? "Running recovery validation…" : "Run recovery validation"}
          </button>
          <button
            type="button"
            className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-800"
            onClick={() => retentionDryRunMut.mutate()}
            disabled={retentionDryRunMut.isPending}
          >
            {retentionDryRunMut.isPending ? "Running retention dry-run…" : "Run retention dry-run"}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Continuity & corruption inspection</h3>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-xs">
            <thead className="bg-stone-50 text-left text-stone-700">
              <tr>
                <th className="px-2 py-2">gap id</th>
                <th className="px-2 py-2">failure class</th>
                <th className="px-2 py-2">gap type</th>
                <th className="px-2 py-2">trust impact</th>
                <th className="px-2 py-2">recoverability</th>
                <th className="px-2 py-2">recovery status</th>
              </tr>
            </thead>
            <tbody>
              {c.inspectors.corruption_continuity_inspector.active_failures.map((f) => (
                <tr key={f.gap_id} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono">{f.gap_id}</td>
                  <td className="px-2 py-2">{f.failure_class}</td>
                  <td className="px-2 py-2">{f.gap_type}</td>
                  <td className="px-2 py-2">{f.trust_state_impact}</td>
                  <td className="px-2 py-2">{f.recoverability_class}</td>
                  <td className="px-2 py-2">{f.recovery_status}</td>
                </tr>
              ))}
              {c.inspectors.corruption_continuity_inspector.active_failures.length === 0 ? (
                <tr>
                  <td className="px-2 py-2 text-stone-500" colSpan={6}>
                    No active failure cases.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

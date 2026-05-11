import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import type { CortexStabilizationProofReport, CortexStabilizationProofRunsList } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexCanonicalStabilizationPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const snapQ = useQuery({
    queryKey: ["admin-cortex-canonical-stabilization-proof", tenantId],
    queryFn: () =>
      adminJson<CortexStabilizationProofReport>(
        `/admin/tenants/${tenantId}/cortex/canonical/stabilization-proof`,
      ),
    enabled: Boolean(tenantId),
  });

  const runsQ = useQuery({
    queryKey: ["admin-cortex-canonical-stabilization-proof-runs", tenantId],
    queryFn: () =>
      adminJson<CortexStabilizationProofRunsList>(
        `/admin/tenants/${tenantId}/cortex/canonical/stabilization-proof/runs?limit=10`,
      ),
    enabled: Boolean(tenantId),
  });

  const runMut = useMutation({
    mutationFn: async (persist: boolean) => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/canonical/stabilization-proof/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ persist }),
        },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<CortexStabilizationProofReport>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-stabilization-proof", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-stabilization-proof-runs", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (snapQ.isPending) return <p className="text-sm text-stone-600">Loading stabilization proof…</p>;
  if (snapQ.isError) return <p className="text-sm text-red-700">{(snapQ.error as Error).message}</p>;

  const s = snapQ.data;
  const hardTone = s.hard_fail_passed ? "ok" : "bad";
  const warnTone = s.warn_only_all_passed ? "ok" : "warn";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Stabilization + economics proof (Phase 03 Step 17)</h2>
            <p className="mt-1 text-sm text-stone-600">
              Deterministic substrate scale, replay timing/scope probes, verification recency, ambiguity pressure —
              receipts for soak / large-tenant readiness (not semantic dashboards).
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={hardTone}>hard gates</StatusBadge>
            <StatusBadge tone={warnTone}>warn gates</StatusBadge>
          </div>
        </div>
        <p className="mt-2 font-mono text-xs text-stone-500">
          schema v{s.stabilization_proof_schema_version} · tenant {s.tenant_id}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
            disabled={runMut.isPending}
            onClick={() => runMut.mutate(false)}
          >
            {runMut.isPending ? "Running…" : "POST run (no persist)"}
          </button>
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-3 py-1.5 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
            disabled={runMut.isPending}
            onClick={() => runMut.mutate(true)}
          >
            POST run + persist ledger
          </button>
        </div>
        {runMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(runMut.error as Error).message}</p>
        ) : null}
        {runMut.isSuccess ? (
          <p className="mt-2 text-sm text-emerald-800">
            Last run: hard {String(runMut.data.hard_fail_passed)} · warn {String(runMut.data.warn_only_all_passed)}
            {runMut.data.persisted_run_id != null ? ` · ledger id ${runMut.data.persisted_run_id}` : ""}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Substrate scale</h3>
        <pre className="mt-2 overflow-x-auto rounded-md bg-stone-50 p-3 font-mono text-xs text-stone-800">
          {JSON.stringify(s.substrate_scale, null, 2)}
        </pre>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Replay economics</h3>
        <pre className="mt-2 overflow-x-auto rounded-md bg-stone-50 p-3 font-mono text-xs text-stone-800">
          {JSON.stringify(s.replay_economics, null, 2)}
        </pre>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Proof checklist</h3>
        <ul className="mt-3 divide-y divide-stone-200 text-sm">
          {s.proof_checklist.map((it) => (
            <li key={it.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="font-mono text-xs text-stone-600">{it.id}</span>
              <span className="text-xs text-stone-500">{String(it.severity)}</span>
              <StatusBadge tone={it.passed ? "ok" : it.severity === "warn_only" ? "warn" : "bad"}>
                {it.passed ? "pass" : "fail"}
              </StatusBadge>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Persisted runs</h3>
        {runsQ.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading runs…</p>
        ) : runsQ.isError ? (
          <p className="mt-2 text-sm text-red-700">{(runsQ.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-2 font-mono text-xs text-stone-800">
            {runsQ.data!.runs.map((r) => (
              <li key={r.id} className="rounded-md border border-stone-100 bg-stone-50 p-2">
                id {r.id} · passed {String(r.passed)} · {String(r.created_at)}
              </li>
            ))}
            {runsQ.data!.runs.length === 0 ? <li className="text-stone-500">No persisted runs yet.</li> : null}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
        <h3 className="text-base font-semibold text-amber-950">Warnings</h3>
        <ul className="mt-2 list-inside list-disc text-sm text-amber-950">
          {s.warnings.must_not_assume.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import type { CortexCanonicalVerificationRunsList } from "./cortexAdminTypes";
import { formatRelativeAge } from "./cortexAdminTypes";
import { CanonicalFilterToolbar, CompactTable, OperatorDrawer } from "./canonical/operatorUi";
import { matchesTimeRange, useCanonicalOperatorFilters } from "./canonical/operatorFilters";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexCanonicalVerificationTabPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const { filters, setFilters } = useCanonicalOperatorFilters();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [verifPersist, setVerifPersist] = useState(true);
  const [verifSampleLimit, setVerifSampleLimit] = useState("50");

  const qRuns = useQuery({
    queryKey: ["admin-cortex-canonical-verification-runs", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalVerificationRunsList>(
        `/admin/tenants/${tenantId}/cortex/canonical/verification/runs?limit=40`,
      ),
    enabled: Boolean(tenantId),
  });

  const verificationRunMut = useMutation({
    mutationFn: async () => {
      const lim = Number.parseInt(verifSampleLimit, 10);
      return adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/canonical/verification/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            persist: verifPersist,
            materialization_sample_limit: Number.isFinite(lim) ? lim : 50,
          }),
        },
      );
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-verification-runs", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
    },
  });

  const rows = useMemo(() => {
    const runs = qRuns.data?.runs ?? [];
    return runs.filter((r) => matchesTimeRange(r.created_at, filters.timeRange));
  }, [qRuns.data?.runs, filters.timeRange]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Verification · Ledger</h2>
            <p className="mt-1 text-sm text-stone-600">
              Deterministic invariant sweep — gate matrix persisted for audit replay when enabled.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800"
            onClick={() => setDrawerOpen(true)}
          >
            Run verification…
          </button>
        </div>
      </section>

      <CanonicalFilterToolbar filters={filters} onChange={setFilters} />

      {qRuns.isPending ? (
        <p className="text-sm text-stone-600">Loading verification runs…</p>
      ) : qRuns.isError ? (
        <p className="text-sm text-red-700">{(qRuns.error as Error).message}</p>
      ) : (
        <CompactTable
          columns={[
            { key: "vid", label: "verification_id" },
            { key: "gates", label: "gates_passed" },
            { key: "fail", label: "failed_invariants" },
            { key: "st", label: "status" },
            { key: "samples", label: "sample_count" },
            { key: "ts", label: "timestamp" },
          ]}
          rows={rows.map((r) => {
            const passedGates = r.gates.filter((g) => g.passed).length;
            const failedNames = r.gates.filter((g) => !g.passed).map((g) => g.name || g.id);
            const ev = r.evidence as Record<string, unknown>;
            const samples =
              typeof ev?.materialization_sample_limit === "number"
                ? ev.materialization_sample_limit
                : typeof ev?.sample_count === "number"
                  ? ev.sample_count
                  : "—";
            return {
              vid: r.id,
              gates: `${passedGates}/${r.gates.length}`,
              fail: failedNames.join(", ") || "—",
              st: (
                <span className="inline-flex items-center gap-2">
                  {r.passed ? <StatusBadge tone="ok">PASS</StatusBadge> : <StatusBadge tone="bad">FAIL</StatusBadge>}
                </span>
              ),
              samples,
              ts: formatRelativeAge(r.created_at),
            };
          })}
        />
      )}

      <OperatorDrawer open={drawerOpen} title="Run canonical verification" onClose={() => setDrawerOpen(false)}>
        <div className="space-y-3 text-sm">
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={verifPersist} onChange={(e) => setVerifPersist(e.target.checked)} />
            persist run to ledger
          </label>
          <label className="block text-xs text-stone-600">
            materialization_sample_limit (1–200)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={verifSampleLimit}
              onChange={(e) => setVerifSampleLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            disabled={verificationRunMut.isPending}
            onClick={() => verificationRunMut.mutate()}
          >
            {verificationRunMut.isPending ? "Running…" : "POST verification/run"}
          </button>
          {verificationRunMut.isError ? (
            <p className="text-sm text-red-700">{(verificationRunMut.error as Error).message}</p>
          ) : null}
          {verificationRunMut.isSuccess ? (
            <pre className="max-h-64 overflow-auto rounded border bg-stone-50 p-2 font-mono text-[11px]">
              {JSON.stringify(verificationRunMut.data, null, 2)}
            </pre>
          ) : null}
        </div>
      </OperatorDrawer>
    </div>
  );
}

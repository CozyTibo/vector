import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import type {
  CortexCanonicalCertificationArchiveResult,
  CortexCanonicalCertificationPack,
  CortexCanonicalCertificationArchivesList,
} from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexCanonicalCertificationPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const packQ = useQuery({
    queryKey: ["admin-cortex-canonical-certification-pack", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalCertificationPack>(
        `/admin/tenants/${tenantId}/cortex/canonical/certification-pack`,
      ),
    enabled: Boolean(tenantId),
  });

  const archivesQ = useQuery({
    queryKey: ["admin-cortex-canonical-certification-archives", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalCertificationArchivesList>(
        `/admin/tenants/${tenantId}/cortex/canonical/certification-pack/archives?limit=10`,
      ),
    enabled: Boolean(tenantId),
  });

  const archiveMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/canonical/certification-pack/archive`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ materialization_sample_limit: 50 }),
        },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<CortexCanonicalCertificationArchiveResult>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-certification-pack", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-certification-archives", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (packQ.isPending) return <p className="text-sm text-stone-600">Loading certification pack…</p>;
  if (packQ.isError) return <p className="text-sm text-red-700">{(packQ.error as Error).message}</p>;

  const p = packQ.data;
  const matrix = p.closure_gate_matrix;
  const hardOk = matrix.filter((g) => g.severity === "hard_fail").every((g) => g.passed);
  const contractOk = p.certification_pack_contract.passed;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Phase 03 Step 18 — closure certification pack</h2>
            <p className="mt-1 text-sm text-stone-600">
              Operator-visible excerpts (verification, stabilization, control plane, replay, ambiguity, mapping) plus
              closure gate matrix G-P03-14–G-P03-21. Archive persists only when every hard-fail gate passes.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={contractOk ? "ok" : "bad"}>structural contract</StatusBadge>
            <StatusBadge tone={hardOk ? "ok" : "warn"}>hard closure slice</StatusBadge>
          </div>
        </div>
        <p className="mt-2 font-mono text-xs text-stone-500">
          pack schema v{p.certification_pack_schema_version} · tenant {p.tenant_id}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-stone-800 disabled:opacity-50"
            disabled={archiveMut.isPending}
            onClick={() => archiveMut.mutate()}
          >
            {archiveMut.isPending ? "Archiving…" : "POST archive (requires full PASS)"}
          </button>
        </div>
        {archiveMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(archiveMut.error as Error).message}</p>
        ) : null}
        {archiveMut.isSuccess ? (
          <p className="mt-2 text-sm text-emerald-800">
            persisted {String(archiveMut.data.persisted)} · passed {String(archiveMut.data.passed)}
            {archiveMut.data.archive_id != null ? ` · archive id ${archiveMut.data.archive_id}` : ""}
          </p>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Closure gate matrix</h3>
        <ul className="mt-3 divide-y divide-stone-200 text-sm">
          {matrix.map((it) => (
            <li key={it.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span className="font-mono text-xs text-stone-600">{it.id}</span>
              <span className="max-w-md truncate text-xs text-stone-700">{it.name}</span>
              <span className="text-xs text-stone-500">{it.severity}</span>
              <StatusBadge tone={it.passed ? "ok" : it.severity === "warn_only" ? "warn" : "bad"}>
                {it.passed ? "pass" : "fail"}
              </StatusBadge>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Verification excerpt</h3>
        <pre className="mt-2 overflow-x-auto rounded-md bg-stone-50 p-3 font-mono text-xs text-stone-800">
          {JSON.stringify(p.verification_matrix_excerpt, null, 2)}
        </pre>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Archived packs</h3>
        {archivesQ.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading archives…</p>
        ) : archivesQ.isError ? (
          <p className="mt-2 text-sm text-red-700">{(archivesQ.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-2 font-mono text-xs text-stone-800">
            {archivesQ.data!.archives.map((a) => (
              <li key={a.id} className="rounded-md border border-stone-100 bg-stone-50 p-2">
                id {a.id} · passed {String(a.passed)} · {String(a.created_at)}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

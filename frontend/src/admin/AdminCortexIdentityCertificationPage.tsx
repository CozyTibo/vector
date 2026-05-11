import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import type {
  CortexOrgIdentityCertificationArchiveResult,
  CortexOrgIdentityCertificationArchivesList,
  CortexOrgIdentityCertificationClosureGate,
  CortexOrgIdentityCertificationPack,
} from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

function stringifyIds(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string" && x.length > 0);
}

function ClosureGateRowDetail({ gate }: { gate: CortexOrgIdentityCertificationClosureGate }) {
  const d = gate.detail;
  if (!d || typeof d !== "object") return null;

  if (gate.id === "G-P04-CLOSE-MAP-01") {
    const failed = stringifyIds((d as { failed_hard_fail_gate_ids?: unknown }).failed_hard_fail_gate_ids);
    if (!failed.length && gate.passed) return null;
    return (
      <div className="mt-2 rounded-md bg-stone-50 p-2 text-xs text-stone-700">
        <p className="font-medium text-stone-800">Full canonical verification — failing hard-fail gates</p>
        {failed.length ? (
          <ul className="mt-1 list-disc space-y-0.5 pl-4 font-mono">
            {failed.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-stone-600">No id list returned (see canonical verification run for full gate list).</p>
        )}
      </div>
    );
  }

  if (gate.id === "G-P04-CLOSE-MAP-02") {
    const failed = stringifyIds((d as { failed_phase04_hard_fail_gate_ids?: unknown }).failed_phase04_hard_fail_gate_ids);
    if (!failed.length && gate.passed) return null;
    return (
      <div className="mt-2 rounded-md bg-stone-50 p-2 text-xs text-stone-700">
        <p className="font-medium text-stone-800">Phase 04 slice (G-P04-*) — failing hard-fail gates</p>
        {failed.length ? (
          <ul className="mt-1 list-disc space-y-0.5 pl-4 font-mono">
            {failed.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        ) : (
          <p className="mt-1 text-stone-600">None (slice passed).</p>
        )}
      </div>
    );
  }

  if (gate.id === "G-P04-CLOSE-01") {
    const struct = (d as { structural_contract?: { passed?: boolean; errors?: unknown } }).structural_contract;
    const errs = Array.isArray(struct?.errors) ? struct!.errors!.filter((e): e is string => typeof e === "string") : [];
    const pre = (d as { closure_pre_rows_passed?: unknown }).closure_pre_rows_passed;
    if (gate.passed && !errs.length) return null;
    return (
      <div className="mt-2 rounded-md bg-stone-50 p-2 text-xs text-stone-700">
        <p>
          Pre-rows (MAP-01/02) ok:{" "}
          <span className="font-mono">{String(pre)}</span>
        </p>
        {errs.length ? (
          <>
            <p className="mt-1 font-medium text-stone-800">Structural contract errors</p>
            <ul className="mt-0.5 list-disc pl-4 font-mono">
              {errs.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
    );
  }

  return null;
}

export default function AdminCortexIdentityCertificationPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const packQ = useQuery({
    queryKey: ["admin-cortex-org-identity-certification-pack", tenantId],
    queryFn: () =>
      adminJson<CortexOrgIdentityCertificationPack>(
        `/admin/tenants/${tenantId}/cortex/identity/certification-pack`,
      ),
    enabled: Boolean(tenantId),
  });

  const archivesQ = useQuery({
    queryKey: ["admin-cortex-org-identity-certification-archives", tenantId],
    queryFn: () =>
      adminJson<CortexOrgIdentityCertificationArchivesList>(
        `/admin/tenants/${tenantId}/cortex/identity/certification-pack/archives?limit=10`,
      ),
    enabled: Boolean(tenantId),
  });

  const archiveMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/identity/certification-pack/archive`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ materialization_sample_limit: 50 }),
        },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json() as Promise<CortexOrgIdentityCertificationArchiveResult>;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-org-identity-certification-pack", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-org-identity-certification-archives", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (packQ.isPending) return <p className="text-sm text-stone-600">Loading org certification pack…</p>;
  if (packQ.isError) return <p className="text-sm text-red-700">{(packQ.error as Error).message}</p>;

  const p = packQ.data;
  const matrix = p.closure_gate_matrix;
  const hardOk = matrix.filter((g) => g.severity === "hard_fail").every((g) => g.passed);
  const contractOk = p.org_identity_certification_pack_contract.passed;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Phase 04 Step 22 — org identity certification</h2>
            <p className="mt-1 text-sm text-stone-600">
              Closure excerpts (canonical verification, Phase 04 gate slice, control plane, readiness economics, last
              org verification) plus closure matrix <span className="font-mono">G-P04-CLOSE-MAP-01/02</span> and{" "}
              <span className="font-mono">G-P04-CLOSE-01</span>. Archive persists only when every hard-fail row passes.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge tone={contractOk ? "ok" : "bad"}>structural contract</StatusBadge>
            <StatusBadge tone={hardOk ? "ok" : "warn"}>hard closure slice</StatusBadge>
          </div>
        </div>
        <p className="mt-2 font-mono text-xs text-stone-500">
          pack schema v{p.org_certification_pack_schema_version} · tenant {p.tenant_id}
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
        <h3 className="text-sm font-semibold text-stone-900">Closure gate matrix</h3>
        <p className="mt-2 text-sm text-stone-600">
          <span className="font-mono text-stone-800">G-P04-CLOSE-MAP-01</span> requires every gate marked{" "}
          <span className="font-medium text-stone-800">hard_fail</span> in the full canonical verification run to pass
          (Phase 03 and Phase 04). <span className="font-mono text-stone-800">G-P04-CLOSE-MAP-02</span> only checks the{" "}
          <span className="font-mono">G-P04-*</span> slice. If MAP-02 passes but MAP-01 fails, the blockers are almost
          always non–Phase-04 canonical checks: fix mapping/materialization/verification for those gate ids, then reload
          this page.
        </p>
        <p className="mt-2 text-sm text-stone-600">
          <Link
            className="font-medium text-indigo-700 hover:text-indigo-900"
            to={`/admin/tenants/${tenantId}/cortex/canonical/advanced/verification`}
          >
            Open canonical verification
          </Link>{" "}
          to see every gate result; org archive is blocked until MAP-01, MAP-02, and{" "}
          <span className="font-mono">G-P04-CLOSE-01</span> all pass. When{" "}
          <span className="font-mono">G-P03-01</span> fails, use Canonical → Verification →{" "}
          <span className="font-medium text-stone-800">Repair oracle determinism drift</span> before re-running
          verification.
        </p>
        {stringifyIds(p.canonical_verification_excerpt?.hard_fail_failed_ids_sample).length ? (
          <p className="mt-2 text-xs text-stone-500">
            Sample failing ids from pack excerpt:{" "}
            <span className="font-mono text-stone-700">
              {stringifyIds(p.canonical_verification_excerpt.hard_fail_failed_ids_sample).join(", ")}
            </span>
            {p.canonical_verification_excerpt.gate_count != null ? (
              <>
                {" "}
                (of {String(p.canonical_verification_excerpt.gate_count)} gates)
              </>
            ) : null}
          </p>
        ) : null}
        <ul className="mt-4 divide-y divide-stone-100">
          {matrix.map((g) => (
            <li key={g.id} className="py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <span className="font-mono text-xs text-stone-700">{g.id}</span>
                  {g.name ? (
                    <span className="ml-2 text-xs text-stone-500">
                      ({g.name.replace(/_/g, " ")})
                    </span>
                  ) : null}
                </div>
                <StatusBadge tone={g.passed ? "ok" : "bad"}>{g.passed ? "PASS" : "FAIL"}</StatusBadge>
              </div>
              <ClosureGateRowDetail gate={g} />
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Recent archives</h3>
        {archivesQ.isPending ? <p className="mt-2 text-sm text-stone-600">Loading…</p> : null}
        {archivesQ.isError ? (
          <p className="mt-2 text-sm text-red-700">{(archivesQ.error as Error).message}</p>
        ) : null}
        {archivesQ.data?.archives?.length ? (
          <ul className="mt-2 space-y-1 font-mono text-xs text-stone-700">
            {archivesQ.data.archives.map((a) => (
              <li key={a.id}>
                id {a.id} · passed {String(a.passed)} · {String(a.created_at)}
              </li>
            ))}
          </ul>
        ) : archivesQ.data ? (
          <p className="mt-2 text-sm text-stone-600">No archives yet.</p>
        ) : null}
      </section>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CortexCanonicalControlPlane } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

export default function AdminCortexCanonicalControlPlanePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const q = useQuery({
    queryKey: ["admin-cortex-canonical-control-plane", tenantId],
    queryFn: () =>
      adminJson<CortexCanonicalControlPlane>(`/admin/tenants/${tenantId}/cortex/canonical/control-plane`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading canonical control plane…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  const c = q.data;
  const h = c.health_overview;
  const checklistTone = c.verification_checklist.passed ? "ok" : "warn";

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Canonical control plane (Phase 03 Step 16)</h2>
            <p className="mt-1 text-sm text-stone-600">
              Deterministic substrate metrics, inspector slices, certification-style checklist, safe action entry
              points, and logical IA route hints (surfaces A–H)—not semantic dashboards.
            </p>
          </div>
          <StatusBadge tone={checklistTone}>
            checklist {c.verification_checklist.passed ? "all pass" : "items failing"}
          </StatusBadge>
        </div>
        <p className="mt-2 font-mono text-xs text-stone-500">
          schema v{c.canonical_control_plane_schema_version} · tenant {c.tenant_id}
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Materializations</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.materialization_row_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Field lineage rows</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.field_lineage_row_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Active canonical failures</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.active_canonical_failure_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Verification freshness</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.verification_freshness_label}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Open ambiguity</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.ambiguity_open_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Mapping bundles (inventory)</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.mapping_bundle_inventory_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Mapping pins (tenant)</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.mapping_pin_row_count}</p>
          </div>
          <div className="rounded-md border border-stone-200 p-3">
            <p className="text-xs uppercase tracking-wide text-stone-500">Replay jobs (recent window)</p>
            <p className="mt-1 text-sm font-semibold text-stone-900">{h.replay_jobs_in_window}</p>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Logical information architecture (A–H)</h3>
        <p className="mt-1 text-sm text-stone-600">Route hints for operator obligations; open specialist panels from the ontology page.</p>
        <ul className="mt-3 space-y-2 text-sm text-stone-800">
          {Object.entries(c.logical_information_architecture).map(([k, v]) => (
            <li key={k} className="rounded-md border border-stone-100 bg-stone-50 p-3">
              <p className="font-mono text-xs text-stone-500">{k}</p>
              <p className="mt-1 text-sm">{typeof v === "object" && v && "summary" in v ? String(v.summary) : ""}</p>
              {"admin_route_hints" in (v as object) && Array.isArray((v as { admin_route_hints?: string[] }).admin_route_hints) ? (
                <ul className="mt-2 list-inside list-disc font-mono text-[11px] text-stone-700">
                  {(v as { admin_route_hints: string[] }).admin_route_hints.map((r) => (
                    <li key={r}>{r}</li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Operator checklist</h3>
        <ul className="mt-3 divide-y divide-stone-200 text-sm">
          {c.verification_checklist.items.map((it) => (
            <li key={it.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
              <span className="font-mono text-xs text-stone-600">{it.id}</span>
              <StatusBadge tone={it.passed ? "ok" : "warn"}>{it.passed ? "pass" : "fail"}</StatusBadge>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Safe actions</h3>
        <ul className="mt-3 space-y-2 font-mono text-xs text-stone-800">
          {c.actions.map((a) => (
            <li key={a.id} className="rounded-md border border-stone-100 bg-stone-50 p-2">
              <span className="text-stone-500">{a.method}</span> {a.path}
              <div className="mt-1 text-[11px] text-stone-600">{a.expected_impact}</div>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-amber-200 bg-amber-50 p-5">
        <h3 className="text-base font-semibold text-amber-950">Warnings</h3>
        <ul className="mt-2 list-inside list-disc text-sm text-amber-950">
          {c.warnings.must_not_assume.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

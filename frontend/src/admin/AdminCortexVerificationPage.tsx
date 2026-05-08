import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CortexMemoryControlPlane } from "./cortexAdminTypes";
import { StatusBadge } from "./ui/StatusBadge";

function gateTone(decision: string): "ok" | "warn" | "bad" | "neutral" {
  if (decision === "pass") return "ok";
  if (decision === "warn_only") return "neutral";
  if (decision === "hard_fail") return "bad";
  return "warn";
}

export default function AdminCortexVerificationPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const controlQ = useQuery({
    queryKey: ["admin-cortex-memory-control-plane", tenantId],
    queryFn: () => adminJson<CortexMemoryControlPlane>(`/admin/tenants/${tenantId}/cortex/memory/control-plane`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (controlQ.isPending) return <p className="text-sm text-stone-600">Loading verification…</p>;
  if (controlQ.isError) return <p className="text-sm text-red-700">{(controlQ.error as Error).message}</p>;

  const closure = controlQ.data.phase_closure;
  const checklist = controlQ.data.verification_checklist;
  const vt = controlQ.data.verification_truth as
    | {
        proof_quality?: {
          primary?: string;
          measured?: boolean;
          inferred?: boolean;
          stale_snapshot?: boolean;
          partial?: boolean;
          unverifiable?: boolean;
        };
        freshness?: { label?: string; from_cache?: boolean; snapshot_at?: string };
        precedence?: { trust_g1_g7_matches_closure?: boolean };
      }
    | null
    | undefined;
  if (!closure) {
    return <p className="text-sm text-stone-600">Closure details not available yet. Refresh in a moment.</p>;
  }

  const pq = vt?.proof_quality;
  const fr = vt?.freshness;

  return (
    <div className="space-y-6">
      {pq ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-stone-900">Trust signals (verification truth)</h2>
            <StatusBadge tone={pq.primary === "measured" && fr?.label === "fresh" ? "ok" : "warn"}>
              {pq.primary ?? "unknown"}
            </StatusBadge>
          </div>
          <p className="mt-2 text-sm text-stone-600">
            Freshness: <span className="font-medium text-stone-800">{fr?.label ?? "n/a"}</span>
            {fr?.snapshot_at ? (
              <>
                {" "}
                · snapshot {fr.snapshot_at}
              </>
            ) : null}
          </p>
          <p className="mt-1 text-xs text-stone-500">
            Trust slice matches closure gates:{" "}
            {vt?.precedence?.trust_g1_g7_matches_closure === false ? "no (inferred risk)" : "yes"}
          </p>
          <dl className="mt-3 grid gap-2 text-sm md:grid-cols-2 lg:grid-cols-5">
            <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
              <dt className="text-xs text-stone-500">measured</dt>
              <dd className="font-medium">{pq.measured ? "yes" : "no"}</dd>
            </div>
            <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
              <dt className="text-xs text-stone-500">inferred</dt>
              <dd className="font-medium">{pq.inferred ? "yes" : "no"}</dd>
            </div>
            <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
              <dt className="text-xs text-stone-500">stale snapshot</dt>
              <dd className="font-medium">{pq.stale_snapshot ? "yes" : "no"}</dd>
            </div>
            <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
              <dt className="text-xs text-stone-500">partial gates</dt>
              <dd className="font-medium">{pq.partial ? "yes" : "no"}</dd>
            </div>
            <div className="rounded border border-stone-100 bg-stone-50 px-2 py-1">
              <dt className="text-xs text-stone-500">unverifiable</dt>
              <dd className="font-medium">{pq.unverifiable ? "yes" : "no"}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-stone-900">Phase 02 closure gate</h2>
          <StatusBadge tone={closure.passed ? "ok" : "warn"}>{closure.phase_status}</StatusBadge>
        </div>
        <p className="mt-2 text-sm text-stone-600">
          hard fail: {closure.summary.hard_fail_count} / soft fail: {closure.summary.soft_fail_count} / warn only:{" "}
          {closure.summary.warn_only_count}
        </p>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {Object.entries(closure.gate_results).map(([gateId, gate]) => (
            <div key={gateId} className="rounded-md border border-stone-200 p-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-stone-900">{gateId}</span>
                <StatusBadge tone={gateTone(gate.decision)}>{gate.decision}</StatusBadge>
              </div>
              <p className="mt-1 text-xs text-stone-600">{gate.reason}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-base font-semibold text-stone-900">Verification checklist</h3>
          <StatusBadge tone={checklist.passed ? "ok" : "warn"}>{checklist.passed ? "pass" : "fail"}</StatusBadge>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {checklist.items.map((item) => (
            <div key={item.id} className="rounded-md border border-stone-200 p-2 text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-stone-900">{item.id}</span>
                <StatusBadge tone={item.passed ? "ok" : "warn"}>{item.passed ? "pass" : "fail"}</StatusBadge>
              </div>
              <p className="mt-1 text-xs text-stone-600">{String(item.detail ?? "")}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

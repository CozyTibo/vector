import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";

type IdentityCard = {
  value?: number | string;
  histogram?: Record<string, number>;
  computed_at?: string;
  drilldown?: string;
  freshness_label?: string;
};

type IdentityControlPlanePayload = {
  identity_control_plane_runtime_schema_version?: number;
  schema_version: string;
  tenant_id: string;
  computed_at: string;
  freshness_label: "fresh" | "stale";
  cards: Record<string, IdentityCard>;
  continuity_substrate?: {
    candidate_link_rows_total_retained?: number;
    candidate_link_rows_latest_batch?: number;
  };
  last_authoritative_replay_job: Record<string, unknown> | null;
  last_candidate_regen_job: Record<string, unknown> | null;
  last_continuity_rebuild_job: Record<string, unknown> | null;
  verification_pointer: { last_org_verification_run_id: number | null };
};

type ReadinessEconomicsPayload = {
  schema_version: string;
  tenant_id: string;
  computed_at: string;
  overall_posture: "ok" | "warn" | "critical";
  warnings: Array<{ level?: string; message?: string; code?: string }>;
  storage_estimate_bytes: number;
  regen_replay_cost_hints: { candidate_regen_relative_units?: number; authoritative_replay_relative_units?: number };
};

const CARD_ORDER: Array<{ key: string; title: string }> = [
  { key: "org_handles", title: "Org handles" },
  { key: "persona_bindings", title: "Persona bindings" },
  { key: "authoritative_links", title: "Authoritative links" },
  { key: "candidate_links", title: "Candidate links (latest batch)" },
  { key: "ambiguous_identities", title: "Open ambiguities" },
  { key: "pending_merges", title: "Pending merges" },
  { key: "replay_drift", title: "Replay drift (receipts)" },
  { key: "bundle_equivalence_gaps", title: "Bundle equivalence gaps" },
  { key: "primitive_instances", title: "Primitive instances" },
  { key: "orphaned_references", title: "Orphaned references" },
];

function formatValue(card: IdentityCard | undefined): string {
  if (!card) return "—";
  if (card.histogram && typeof card.value === "number") {
    const entries = Object.entries(card.histogram).filter(([, n]) => n > 0);
    if (!entries.length) return `${card.value} total`;
    return `${card.value} · ${entries.map(([k, v]) => `${k}:${v}`).join(" ")}`;
  }
  if (typeof card.value === "number") return String(card.value);
  if (typeof card.value === "string") return card.value;
  return "—";
}

export default function AdminCortexIdentityOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();

  const q = useQuery({
    queryKey: ["admin-cortex-identity-control-plane", tenantId],
    queryFn: () =>
      adminJson<IdentityControlPlanePayload>(
        `/admin/tenants/${tenantId}/cortex/identity/control-plane`,
      ),
    enabled: Boolean(tenantId),
  });
  const eco = useQuery({
    queryKey: ["admin-cortex-identity-readiness-economics", tenantId],
    queryFn: () =>
      adminJson<ReadinessEconomicsPayload>(
        `/admin/tenants/${tenantId}/cortex/identity/readiness-economics`,
      ),
    enabled: Boolean(tenantId),
  });

  const identityRerunMut = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/execution/rerun?from_phase=IDENTITY`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(await readErrorDetail(res));
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-identity-control-plane", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-execution", tenantId] });
    },
  });

  return (
    <div className="space-y-5">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Phase 04</p>
        <h1 className="mt-1 text-xl font-semibold text-stone-900">Identity &amp; continuity — Overview</h1>
        <p className="mt-1 text-sm text-stone-600">
          Execution Continuity Operator Console aggregate (<code>identity_control_plane_v1</code>). Cards link to
          list routes for drill-down.
        </p>
        <p className="mt-2 text-xs text-stone-500">
          A large <strong className="font-medium text-stone-700">Org handles</strong> count with other cards near
          zero is common right after canonical materialization + anchor→org backfill: one org entity per identity
          anchor, while links, candidates, merges, and replay receipts only appear after later identity jobs or
          operator actions.
        </p>

        <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/60 p-4">
          <p className="text-sm font-medium text-indigo-950">Rebuild identities</p>
          <p className="mt-1 text-xs text-indigo-900/90">
            Enqueues execution from the identity phase via the engine (same as Overview → Start from step → Identity).
          </p>
          <button
            type="button"
            disabled={!tenantId || identityRerunMut.isPending}
            onClick={() => identityRerunMut.mutate()}
            className="mt-3 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {identityRerunMut.isPending ? "Starting…" : "Rebuild identities"}
          </button>
          {identityRerunMut.isError ? (
            <p className="mt-2 text-xs text-red-700">{(identityRerunMut.error as Error).message}</p>
          ) : null}
        </div>
      </header>

      {q.isLoading ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-red-700">Could not load control plane. Check admin auth and tenant id.</p>
      ) : null}

      {eco.data ? (
        <section
          className={`rounded-xl border p-4 shadow-sm ${
            eco.data.overall_posture === "critical"
              ? "border-red-200 bg-red-50"
              : eco.data.overall_posture === "warn"
                ? "border-amber-200 bg-amber-50"
                : "border-stone-200 bg-white"
          }`}
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-indigo-700">Readiness economics (P04-21)</p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-stone-600">
            <span>
              Posture{" "}
              <span className="font-mono font-medium text-stone-900">{eco.data.overall_posture}</span>
            </span>
            <span>
              Storage est.{" "}
              <span className="font-mono text-stone-800">{eco.data.storage_estimate_bytes.toLocaleString()} B</span>
            </span>
            <span>
              Regen units{" "}
              <span className="font-mono text-stone-800">
                {eco.data.regen_replay_cost_hints?.candidate_regen_relative_units ?? "—"}
              </span>
            </span>
            <span>
              Replay units{" "}
              <span className="font-mono text-stone-800">
                {eco.data.regen_replay_cost_hints?.authoritative_replay_relative_units ?? "—"}
              </span>
            </span>
          </div>
          {eco.data.warnings?.length ? (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-stone-800">
              {eco.data.warnings.map((w, i) => (
                <li key={`${w.code ?? i}-${i}`}>
                  <span className="font-medium">{w.level ?? "warn"}</span>: {w.message ?? w.code ?? "threshold"}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-stone-600">No economics warnings for current thresholds.</p>
          )}
        </section>
      ) : null}
      {eco.isError ? (
        <p className="text-sm text-red-700">Could not load readiness economics snapshot.</p>
      ) : null}

      {q.data ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-3 text-xs text-stone-600">
            <span>
              Schema <span className="font-mono text-stone-800">{q.data.schema_version}</span>
            </span>
            <span>
              Computed <span className="font-mono text-stone-800">{q.data.computed_at}</span>
            </span>
            <span
              className={
                q.data.freshness_label === "fresh"
                  ? "rounded bg-emerald-50 px-2 py-0.5 text-emerald-900 ring-1 ring-emerald-200"
                  : "rounded bg-amber-50 px-2 py-0.5 text-amber-900 ring-1 ring-amber-200"
              }
            >
              {q.data.freshness_label}
            </span>
            <span>
              Last org verification run id:{" "}
              <span className="font-mono text-stone-800">
                {q.data.verification_pointer.last_org_verification_run_id ?? "—"}
              </span>
            </span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {CARD_ORDER.map(({ key, title }) => {
              const card = q.data!.cards[key];
              const href = card?.drilldown?.startsWith("/") ? card.drilldown : undefined;
              const sub = q.data!.continuity_substrate;
              const retained =
                key === "candidate_links" &&
                typeof sub?.candidate_link_rows_total_retained === "number" &&
                typeof card?.value === "number" &&
                sub.candidate_link_rows_total_retained > card.value
                  ? sub.candidate_link_rows_total_retained
                  : null;
              const inner = (
                <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                  <p className="text-xs font-medium uppercase tracking-wide text-stone-500">{title}</p>
                  <p className="mt-2 text-2xl font-semibold text-stone-900">{formatValue(card)}</p>
                  {retained !== null ? (
                    <p className="mt-1 text-xs text-stone-500">
                      All batches retained in DB:{" "}
                      <span className="font-mono text-stone-700">{retained.toLocaleString()}</span> rows (storage /
                      economics)
                    </p>
                  ) : null}
                  {card?.freshness_label ? (
                    <p className="mt-1 text-xs text-stone-500">Card freshness: {card.freshness_label}</p>
                  ) : null}
                </div>
              );
              return href ? (
                <Link key={key} to={href} className="block no-underline hover:opacity-95">
                  {inner}
                </Link>
              ) : (
                <div key={key}>{inner}</div>
              );
            })}
          </div>

          <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 text-xs text-stone-700">
            <p className="font-medium text-stone-900">Last replay jobs</p>
            <dl className="mt-2 grid gap-1 sm:grid-cols-2">
              <dt className="text-stone-500">Authoritative replay</dt>
              <dd className="font-mono">
                {q.data.last_authoritative_replay_job
                  ? String((q.data.last_authoritative_replay_job as { id?: string }).id ?? "")
                  : "—"}
              </dd>
              <dt className="text-stone-500">Candidate regen</dt>
              <dd className="font-mono">
                {q.data.last_candidate_regen_job
                  ? String((q.data.last_candidate_regen_job as { id?: string }).id ?? "")
                  : "—"}
              </dd>
              <dt className="text-stone-500">Continuity rebuild (operator)</dt>
              <dd className="font-mono">
                {q.data.last_continuity_rebuild_job
                  ? String((q.data.last_continuity_rebuild_job as { id?: string }).id ?? "")
                  : "—"}
              </dd>
            </dl>
            {q.data.last_continuity_rebuild_job ? (
              <dl className="mt-3 grid gap-1 border-t border-stone-200 pt-3 sm:grid-cols-2">
                <dt className="text-stone-500">replay_lane</dt>
                <dd className="font-mono text-stone-900">
                  {String((q.data.last_continuity_rebuild_job as { replay_lane?: string }).replay_lane ?? "—")}
                </dd>
                <dt className="text-stone-500">candidate_set_sha256</dt>
                <dd className="break-all font-mono text-stone-800">
                  {String(
                    (q.data.last_continuity_rebuild_job as { candidate_set_sha256?: string }).candidate_set_sha256 ??
                      "—",
                  ).slice(0, 24)}
                  …
                </dd>
                <dt className="text-stone-500">anchor_evidence_input_sha256</dt>
                <dd className="break-all font-mono text-stone-800">
                  {String(
                    (q.data.last_continuity_rebuild_job as { anchor_evidence_input_sha256?: string })
                      .anchor_evidence_input_sha256 ?? "—",
                  ).slice(0, 24)}
                  …
                </dd>
                <dt className="text-stone-500">candidates / ambiguities (summary)</dt>
                <dd className="font-mono text-stone-800">
                  {(q.data.last_continuity_rebuild_job as { candidates_generated_count?: number })
                    .candidates_generated_count ?? "—"}{" "}
                  /{" "}
                  {(q.data.last_continuity_rebuild_job as { ambiguity_opened_total?: number }).ambiguity_opened_total ??
                    "—"}
                </dd>
              </dl>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

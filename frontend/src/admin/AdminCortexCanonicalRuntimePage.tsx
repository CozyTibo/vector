import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { formatRelativeAge, type CortexCanonicalMaterializeBacklogAsyncResponse } from "./cortexAdminTypes";
import { CanonicalFilterToolbar, CompactTable, OperatorDrawer } from "./canonical/operatorUi";
import { matchesTimeRange, useCanonicalOperatorFilters } from "./canonical/operatorFilters";

type ConfidenceSummaryPayload = {
  tenant_id: string;
  field_lineage_rows_total: number;
  by_confidence_class: Record<string, number>;
  confidence_non_ranking_semantics: string;
};

type TransformMaterializationRow = {
  id: string;
  raw_record_id: number;
  canonical_object_kind: string;
  bundle_id: string;
  created_at?: string | null;
  canonical_processed_at?: string | null;
  last_replay_job_id?: string | null;
  confidence_rollup: { by_confidence_class: Record<string, number> };
};

type TransformLineagePayload = {
  tenant_id: string;
  materializations: TransformMaterializationRow[];
};

type MaterializeBacklogResponse = {
  transform_runtime_schema_version: number;
  tenant_id: string;
  bundle_id: string;
  dry_run: boolean;
  stub_resource_pairs_selected: string[];
  scope_connector?: string | null;
  scope_resource_type?: string | null;
  batch_limit_applied: number;
  candidate_more_remain: boolean;
  attempted: number;
  attempted_by_resource_type?: Record<string, number>;
  succeeded: number;
  succeeded_by_resource_type?: Record<string, number>;
  failures: Array<{ raw_record_id: number; detail: string }>;
  raw_record_ids_sample: number[];
  duration_ms?: number | null;
  throughput_rows_per_second?: number | null;
};

export default function AdminCortexCanonicalRuntimePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const { filters, setFilters } = useCanonicalOperatorFilters();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [backlogDrawerOpen, setBacklogDrawerOpen] = useState(false);
  const [matRawId, setMatRawId] = useState("");
  const [matBundleId, setMatBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [backlogConnector, setBacklogConnector] = useState("");
  const [backlogResourceType, setBacklogResourceType] = useState("");
  const [backlogLimit, setBacklogLimit] = useState("200");

  const qLineage = useQuery({
    queryKey: ["admin-cortex-transform-lineage", tenantId, "runtime"],
    queryFn: () =>
      adminJson<TransformLineagePayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/lineage?limit=120`,
      ),
    enabled: Boolean(tenantId),
  });

  const qConfidence = useQuery({
    queryKey: ["admin-cortex-confidence-summary", tenantId],
    queryFn: () =>
      adminJson<ConfidenceSummaryPayload>(`/admin/tenants/${tenantId}/cortex/canonical/confidence/summary`),
    enabled: Boolean(tenantId),
  });

  const materializeMut = useMutation({
    mutationFn: async () => {
      const rawId = Number.parseInt(matRawId, 10);
      if (!Number.isFinite(rawId)) throw new Error("raw_record_id must be a decimal integer");
      return adminJson<{ materialization: TransformMaterializationRow }>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/materialize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_record_id: rawId, bundle_id: matBundleId }),
        },
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-confidence-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
    },
  });

  const backlogMut = useMutation({
    mutationFn: async (opts: { dryRun: boolean }) => {
      const lim = Number.parseInt(backlogLimit, 10);
      const connector = backlogConnector.trim() || undefined;
      const resourceType = backlogResourceType.trim() || undefined;
      return adminJson<MaterializeBacklogResponse>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/materialize-backlog`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            bundle_id: matBundleId.trim(),
            connector,
            resource_type: resourceType,
            batch_limit: Number.isFinite(lim) ? lim : 200,
            dry_run: opts.dryRun,
          }),
        },
      );
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-confidence-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
    },
  });

  const backlogAsyncMut = useMutation({
    mutationFn: () =>
      adminJson<CortexCanonicalMaterializeBacklogAsyncResponse>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/materialize-backlog-async`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) },
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-confidence-summary", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage-overview", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  const mats = (qLineage.data?.materializations ?? []).filter((m) => {
    if (!matchesTimeRange(m.created_at ?? m.canonical_processed_at, filters.timeRange)) return false;
    if (filters.bundle && !m.bundle_id.includes(filters.bundle)) return false;
    if (filters.objectKind && m.canonical_object_kind !== filters.objectKind) return false;
    return true;
  });

  function confSummary(m: TransformMaterializationRow): string {
    return (
      Object.entries(m.confidence_rollup.by_confidence_class || {})
        .map(([k, v]) => `${k}:${v}`)
        .join(", ") || "—"
    );
  }

  const matsFiltered = mats.filter((m) => {
    if (!filters.confidenceClass) return true;
    return confSummary(m).includes(filters.confidenceClass);
  });

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Runtime · Materializations</h2>
        <p className="mt-1 text-sm text-stone-600">
          Canonical rows emitted by deterministic route transforms — lineage-backed confidence rollup per record
          (non-ranking).
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            className="rounded-md bg-emerald-800 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-emerald-900 disabled:opacity-50"
            disabled={backlogAsyncMut.isPending}
            onClick={() => void backlogAsyncMut.mutate()}
          >
            {backlogAsyncMut.isPending ? "Enqueueing…" : "Drain ingested backlog (async)"}
          </button>
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
            onClick={() => setBacklogDrawerOpen(true)}
          >
            Advanced: synchronous batches…
          </button>
          <button
            type="button"
            className="rounded-md border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
            onClick={() => setDrawerOpen(true)}
          >
            Materialize single raw row…
          </button>
        </div>
        {backlogAsyncMut.isError ? (
          <p className="mt-3 text-sm text-red-700">{(backlogAsyncMut.error as Error).message}</p>
        ) : null}
        {backlogAsyncMut.isSuccess ? (
          <p className="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/80 px-3 py-2 font-mono text-[11px] text-emerald-950">
            Queued Celery task {backlogAsyncMut.data.celery_task_id} · bundle {backlogAsyncMut.data.bundle_id_used} ·
            scope {backlogAsyncMut.data.scope_connector ?? "all-connectors"}/
            {backlogAsyncMut.data.scope_resource_type ?? "all-resource-types"}
          </p>
        ) : null}
        <p className="mt-3 text-xs text-stone-500">
          Async drain runs in the worker until registered transform routes for the resolved bundle are idle (see
          Coverage tab for routable <span className="font-mono">connector/resource_type</span> pairs — includes
          GitHub PRs, Linear issues, Slack messages). Use synchronous batches only when you need per-request limits,
          connector filters, or dry-run previews.
        </p>
      </section>

      <CanonicalFilterToolbar filters={filters} onChange={setFilters} />

      {qConfidence.isSuccess ? (
        <section className="rounded-xl border border-stone-200 bg-stone-50/80 p-4 shadow-inner">
          <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Confidence rollup (tenant)</p>
          <p className="mt-2 font-mono text-xs text-stone-800">
            lineage rows {qConfidence.data.field_lineage_rows_total} ·{" "}
            {Object.entries(qConfidence.data.by_confidence_class)
              .map(([k, v]) => `${k}=${v}`)
              .join(" · ") || "—"}
          </p>
          <p className="mt-2 text-xs text-stone-600">{qConfidence.data.confidence_non_ranking_semantics}</p>
        </section>
      ) : null}

      {qLineage.isPending ? (
        <p className="text-sm text-stone-600">Loading materializations…</p>
      ) : qLineage.isError ? (
        <p className="text-sm text-red-700">{(qLineage.error as Error).message}</p>
      ) : (
        <CompactTable
          columns={[
            { key: "raw", label: "raw_record_id" },
            { key: "kind", label: "canonical kind" },
            { key: "bundle", label: "bundle" },
            { key: "conf", label: "confidence classes" },
            { key: "stat", label: "status" },
            { key: "ts", label: "timestamp" },
          ]}
          rows={matsFiltered.map((m) => ({
            raw: m.raw_record_id,
            kind: m.canonical_object_kind,
            bundle: m.bundle_id,
            conf: confSummary(m),
            stat: m.last_replay_job_id ? `replay ${m.last_replay_job_id.slice(0, 8)}…` : "materialized",
            ts: formatRelativeAge(m.created_at ?? m.canonical_processed_at),
          }))}
        />
      )}

      <OperatorDrawer
        open={backlogDrawerOpen}
        title="Canonicalize ingested backlog (advanced)"
        onClose={() => setBacklogDrawerOpen(false)}
      >
        <p className="text-sm text-stone-600">
          Synchronous batches via{" "}
          <span className="font-mono text-xs">
            POST …/cortex/canonical/transform/materialize-backlog
          </span>
          . Prefer <span className="font-semibold">Drain ingested backlog (async)</span> above for a full drain without
          manual limits. Only registered deterministic transform routes participate.
        </p>
        <div className="mt-4 space-y-3">
          <label className="block text-xs text-stone-600">
            bundle_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-sm"
              value={matBundleId}
              onChange={(e) => setMatBundleId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            Connector filter (optional)
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 text-sm"
              value={backlogConnector}
              onChange={(e) => setBacklogConnector(e.target.value)}
            >
              <option value="">All routable connectors</option>
              <option value="slack">slack</option>
              <option value="github">github</option>
              <option value="linear">linear</option>
              <option value="notion">notion</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            resource_type filter (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-sm"
              value={backlogResourceType}
              onChange={(e) => setBacklogResourceType(e.target.value)}
              placeholder="e.g. notion.block"
            />
          </label>
          <label className="block text-xs text-stone-600">
            batch_limit (1–2000 per request)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-sm"
              value={backlogLimit}
              onChange={(e) => setBacklogLimit(e.target.value)}
            />
          </label>
          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              className="rounded-md border border-stone-400 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50 disabled:opacity-50"
              disabled={backlogMut.isPending}
              onClick={() => backlogMut.mutate({ dryRun: true })}
            >
              {backlogMut.isPending ? "Planning…" : "Preview plan (dry run)"}
            </button>
            <button
              type="button"
              className="rounded-md bg-emerald-800 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-900 disabled:opacity-50"
              disabled={backlogMut.isPending}
              onClick={() => backlogMut.mutate({ dryRun: false })}
            >
              {backlogMut.isPending ? "Running…" : "Run batch materialize"}
            </button>
          </div>
          {backlogMut.isError ? (
            <p className="text-sm text-red-700">{(backlogMut.error as Error).message}</p>
          ) : null}
          {backlogMut.isSuccess ? (
            <div className="rounded-lg border border-stone-200 bg-stone-50 p-3 text-xs text-stone-800">
              <p className="font-semibold text-stone-900">
                {backlogMut.data.dry_run ? "Dry run" : "Executed"} · attempted {backlogMut.data.attempted} · succeeded{" "}
                {backlogMut.data.succeeded}
                {backlogMut.data.candidate_more_remain ? " · more rows remain — run again" : " · batch covered tail"}
              </p>
              <p className="mt-2 font-mono text-[11px] text-stone-600">
                pairs: {backlogMut.data.stub_resource_pairs_selected.join(", ")}
              </p>
              <p className="mt-1 font-mono text-[11px] text-stone-600">
                scope: {backlogMut.data.scope_connector ?? "all-connectors"} /{" "}
                {backlogMut.data.scope_resource_type ?? "all-resource-types"} · duration{" "}
                {backlogMut.data.duration_ms ?? 0}ms · throughput{" "}
                {backlogMut.data.throughput_rows_per_second ?? 0} rows/s
              </p>
              {backlogMut.data.attempted_by_resource_type &&
              Object.keys(backlogMut.data.attempted_by_resource_type).length > 0 ? (
                <p className="mt-1 font-mono text-[11px] text-stone-600">
                  attempted_by_rt:{" "}
                  {Object.entries(backlogMut.data.attempted_by_resource_type)
                    .map(([k, v]) => `${k}:${v}`)
                    .join(", ")}
                </p>
              ) : null}
              {backlogMut.data.failures.length > 0 ? (
                <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto font-mono text-[11px] text-red-900">
                  {backlogMut.data.failures.map((f) => (
                    <li key={f.raw_record_id}>
                      raw #{f.raw_record_id}: {f.detail}
                    </li>
                  ))}
                </ul>
              ) : null}
              {backlogMut.data.raw_record_ids_sample.length > 0 ? (
                <p className="mt-2 font-mono text-[11px] text-stone-600">
                  sample ids: {backlogMut.data.raw_record_ids_sample.join(", ")}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      </OperatorDrawer>

      <OperatorDrawer open={drawerOpen} title="Materialize raw record" onClose={() => setDrawerOpen(false)}>
        <p className="text-sm text-stone-600">
          Executes deterministic route transform for one raw row; persists lineage + canonical substrate rows.
        </p>
        <div className="mt-4 space-y-3">
          <label className="block text-xs text-stone-600">
            raw_record_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-sm"
              value={matRawId}
              onChange={(e) => setMatRawId(e.target.value)}
              placeholder="e.g. 42"
            />
          </label>
          <label className="block text-xs text-stone-600">
            bundle_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-sm"
              value={matBundleId}
              onChange={(e) => setMatBundleId(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={materializeMut.isPending}
            onClick={() => materializeMut.mutate()}
          >
            {materializeMut.isPending ? "Materializing…" : "POST materialize"}
          </button>
          {materializeMut.isError ? (
            <p className="text-sm text-red-700">{(materializeMut.error as Error).message}</p>
          ) : null}
          {materializeMut.isSuccess ? (
            <p className="text-sm text-emerald-800">
              Materialized {materializeMut.data.materialization.canonical_object_kind} for raw #
              {materializeMut.data.materialization.raw_record_id}.
            </p>
          ) : null}
        </div>
      </OperatorDrawer>
    </div>
  );
}

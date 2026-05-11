import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type IdentityAnchorRow = {
  canonical_entity_id: string;
  canonical_object_kind: string;
  connector: string;
  raw_record_id: number;
  bundle_id: string;
  phase04_boundary: Record<string, unknown>;
};

type IdentityAnchorsPayload = {
  identity_runtime_schema_version: number;
  anchors: IdentityAnchorRow[];
};

type ProvenanceRecordRow = {
  id: number;
  materialization_id: string;
  canonical_object_kind: string;
  bundle_id: string;
  raw_record_id: number;
  logical_key_hash: string;
  rule_ids_involved: string[];
};

type ProvenanceByRawPayload = {
  provenance_runtime_schema_version: number;
  raw_record_id: number;
  records: ProvenanceRecordRow[];
};

type TemporalSupersessionRow = {
  id: number;
  bundle_id: string;
  predecessor_materialization_id: string;
  successor_materialization_id: string | null;
  causing_raw_record_id: number;
};

type TemporalSupersessionsPayload = {
  temporal_runtime_schema_version: number;
  items: TemporalSupersessionRow[];
};

type TemporalRebuildPreviewPayload = {
  ordered: Array<{ raw_record_id: number; replay_sequence: number; occurred_at: string }>;
};

type CanonicalQueryResponsePayload = {
  canonical_query_runtime_schema_version: number;
  query_class: string;
  result_kind: string;
  payload: Record<string, unknown>;
  truncation: Record<string, unknown> | null;
};

type FailuresPayload = {
  failure_remediation_runtime_schema_version: number;
  active_failure_count: number;
  active_failure_classes: Record<string, number>;
  cases: Array<{
    gap_id: string;
    failure_class: string;
    degradation_state: string;
    scope_kind: string;
    detail_json: Record<string, unknown>;
    source: string;
  }>;
  recent_remediation_validations: Array<{
    id: number;
    remediation_class: string;
    result_status: string;
    created_at: string | null;
  }>;
};

export default function AdminCortexCanonicalDebugTabPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/canonical`;
  const qc = useQueryClient();

  const [provRawId, setProvRawId] = useState("");
  const [temporalPreviewIds, setTemporalPreviewIds] = useState("");
  const [cqClass, setCqClass] = useState("point_lookup_materialization");
  const [cqIntent, setCqIntent] = useState("evidence_retrieval");
  const [cqQueryText, setCqQueryText] = useState("");
  const [cqParamsJson, setCqParamsJson] = useState("{}");
  const [cqLimit, setCqLimit] = useState("30");
  const [remediationClass, setRemediationClass] = useState<"scoped_rebuild" | "ambiguity_triage_ack">(
    "scoped_rebuild",
  );
  const [remediationDryRun, setRemediationDryRun] = useState(true);
  const [remediationConfirm, setRemediationConfirm] = useState(false);
  const [remediationGapId, setRemediationGapId] = useState("");
  const [remediationPayloadJson, setRemediationPayloadJson] = useState(
    '{"pinned_bundle_id":"bundle.phase03.step03.logical_keys.v1","job_kind":"rebuild","raw_record_ids":[]}',
  );

  const qIdentity = useQuery({
    queryKey: ["admin-cortex-identity-anchors", tenantId, "debug"],
    queryFn: () =>
      adminJson<IdentityAnchorsPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/identity/anchors?limit=60`,
      ),
    enabled: Boolean(tenantId),
  });

  const provRawIdNum = Number.parseInt(provRawId.trim(), 10);
  const qProv = useQuery({
    queryKey: ["admin-cortex-provenance-by-raw", tenantId, provRawIdNum],
    queryFn: () =>
      adminJson<ProvenanceByRawPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/provenance/raw-records/${provRawIdNum}?limit=60`,
      ),
    enabled: Boolean(tenantId) && Number.isFinite(provRawIdNum) && provRawIdNum > 0,
  });

  const qTemporal = useQuery({
    queryKey: ["admin-cortex-temporal-supersessions", tenantId],
    queryFn: () =>
      adminJson<TemporalSupersessionsPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/temporal/supersessions?limit=40`,
      ),
    enabled: Boolean(tenantId),
  });

  const qFailures = useQuery({
    queryKey: ["admin-cortex-canonical-failures", tenantId],
    queryFn: () => adminJson<FailuresPayload>(`/admin/tenants/${tenantId}/cortex/canonical/failures`),
    enabled: Boolean(tenantId),
  });

  const temporalPreviewMut = useMutation({
    mutationFn: async () => {
      const ids = temporalPreviewIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      return adminJson<TemporalRebuildPreviewPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/temporal/rebuild-preview`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_record_ids: ids }),
        },
      );
    },
  });

  const canonicalQueryMut = useMutation({
    mutationFn: async () => {
      let params: Record<string, unknown>;
      try {
        params = JSON.parse(cqParamsJson.trim() || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("params must be valid JSON object");
      }
      const lim = Number.parseInt(cqLimit, 10);
      return adminJson<CanonicalQueryResponsePayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query_class: cqClass,
            intent: cqIntent,
            query_text: cqQueryText.trim() || undefined,
            params,
            limit: Number.isFinite(lim) ? lim : 30,
          }),
        },
      );
    },
  });

  const remediationMut = useMutation({
    mutationFn: async () => {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(remediationPayloadJson.trim() || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("payload must be valid JSON object");
      }
      return adminJson<{
        tenant_id: string;
        remediation_class: string;
        validation: Record<string, unknown>;
      }>(`/admin/tenants/${tenantId}/cortex/canonical/remediation/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          remediation_class: remediationClass,
          dry_run: remediationDryRun,
          confirm_execution: remediationConfirm,
          failure_case_gap_id: remediationGapId.trim() || undefined,
          payload,
        }),
      });
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-amber-200 bg-amber-50/60 p-5 shadow-sm ring-1 ring-amber-100">
        <h2 className="text-lg font-semibold text-amber-950">Debug · Advanced operator POST tooling</h2>
        <p className="mt-2 text-sm text-amber-950/90">
          Provenance traces, temporal previews, bounded canonical query, and remediation receipts. Primary flows live on{" "}
          <Link className="font-semibold text-indigo-800 underline" to={`${base}/advanced/runtime`}>
            Runtime
          </Link>
          ,{" "}
          <Link className="font-semibold text-indigo-800 underline" to={`${base}/advanced/replay`}>
            Replay
          </Link>
          , and{" "}
          <Link className="font-semibold text-indigo-800 underline" to={`${base}/advanced/verification`}>
            Verification
          </Link>
          .
        </p>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Identity anchors</h3>
        {qIdentity.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading…</p>
        ) : qIdentity.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qIdentity.error as Error).message}</p>
        ) : (
          <ul className="mt-3 max-h-56 space-y-2 overflow-y-auto font-mono text-[11px] text-stone-800">
            {qIdentity.data.anchors.map((a) => (
              <li key={a.canonical_entity_id} className="rounded border border-stone-100 bg-stone-50 px-2 py-2">
                {a.canonical_entity_id.slice(0, 13)}… · {a.canonical_object_kind} · {a.connector} · raw #
                {a.raw_record_id}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Provenance (raw → canonical)</h3>
        <label className="mt-3 block text-xs text-stone-600">
          raw_record_id
          <input
            className="mt-1 w-full max-w-xs rounded border border-stone-200 px-2 py-1 font-mono text-xs"
            value={provRawId}
            onChange={(e) => setProvRawId(e.target.value)}
          />
        </label>
        {qProv.isSuccess ? (
          <ul className="mt-3 space-y-2 font-mono text-[11px]">
            {qProv.data.records.map((r) => (
              <li key={r.id} className="rounded border border-stone-100 bg-stone-50 px-2 py-2">
                mat {r.materialization_id.slice(0, 12)}… · {r.canonical_object_kind} · bundle {r.bundle_id}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-xs text-stone-500">Enter a positive raw_record_id to load provenance rows.</p>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Temporal supersessions + rebuild preview</h3>
        {qTemporal.isSuccess ? (
          <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto font-mono text-[11px]">
            {qTemporal.data.items.map((s) => (
              <li key={s.id} className="rounded border border-stone-100 px-2 py-1">
                #{s.id} · bundle {s.bundle_id} · raw {s.causing_raw_record_id}
              </li>
            ))}
          </ul>
        ) : null}
        <label className="mt-4 block text-xs text-stone-600">
          raw_record_ids for rebuild-order preview
          <input
            className="mt-1 w-full max-w-md rounded border border-stone-200 px-2 py-1 font-mono text-xs"
            value={temporalPreviewIds}
            onChange={(e) => setTemporalPreviewIds(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="mt-2 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          disabled={temporalPreviewMut.isPending}
          onClick={() => temporalPreviewMut.mutate()}
        >
          Preview rebuild order
        </button>
        {temporalPreviewMut.isSuccess ? (
          <pre className="mt-3 max-h-48 overflow-auto rounded bg-stone-50 p-2 font-mono text-[11px]">
            {JSON.stringify(temporalPreviewMut.data.ordered, null, 2)}
          </pre>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Bounded canonical query</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block text-xs text-stone-600">
            query_class
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqClass}
              onChange={(e) => setCqClass(e.target.value)}
            >
              <option value="point_lookup_materialization">point_lookup_materialization</option>
              <option value="replay_debug_snapshot">replay_debug_snapshot</option>
              <option value="forward_trace">forward_trace</option>
              <option value="evidence_backtrace">evidence_backtrace</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            intent
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 text-xs"
              value={cqIntent}
              onChange={(e) => setCqIntent(e.target.value)}
            >
              <option value="evidence_retrieval">evidence_retrieval</option>
              <option value="replay_debug">replay_debug</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600 md:col-span-2">
            query_text (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqQueryText}
              onChange={(e) => setCqQueryText(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600 md:col-span-2">
            params JSON
            <textarea
              className="mt-1 w-full min-h-[4rem] rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={cqParamsJson}
              onChange={(e) => setCqParamsJson(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            limit
            <input
              className="mt-1 w-24 rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqLimit}
              onChange={(e) => setCqLimit(e.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          disabled={canonicalQueryMut.isPending}
          onClick={() => canonicalQueryMut.mutate()}
        >
          Run query
        </button>
        {canonicalQueryMut.isSuccess ? (
          <pre className="mt-3 max-h-64 overflow-auto rounded bg-stone-50 p-3 font-mono text-[11px]">
            {JSON.stringify(canonicalQueryMut.data, null, 2)}
          </pre>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Failures + remediation validation</h3>
        {qFailures.isSuccess ? (
          <>
            <p className="mt-2 text-xs text-stone-600">
              Active {qFailures.data.active_failure_count} · classes{" "}
              {Object.entries(qFailures.data.active_failure_classes)
                .map(([k, v]) => `${k}:${v}`)
                .join(", ") || "—"}
            </p>
            <ul className="mt-3 max-h-40 space-y-2 overflow-y-auto font-mono text-[11px]">
              {qFailures.data.cases.map((c) => (
                <li key={c.gap_id} className="rounded border border-stone-100 bg-stone-50 px-2 py-2">
                  {c.failure_class} · {c.gap_id.slice(0, 10)}…
                </li>
              ))}
            </ul>
          </>
        ) : null}
        <div className="mt-4 space-y-3 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
          <label className="block text-xs text-stone-600">
            remediation_class
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={remediationClass}
              onChange={(e) => setRemediationClass(e.target.value as "scoped_rebuild" | "ambiguity_triage_ack")}
            >
              <option value="scoped_rebuild">scoped_rebuild</option>
              <option value="ambiguity_triage_ack">ambiguity_triage_ack</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={remediationDryRun} onChange={(e) => setRemediationDryRun(e.target.checked)} />
            dry_run
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={remediationConfirm} onChange={(e) => setRemediationConfirm(e.target.checked)} />
            confirm_execution
          </label>
          <label className="block text-xs text-stone-600">
            failure_case_gap_id (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={remediationGapId}
              onChange={(e) => setRemediationGapId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            payload JSON
            <textarea
              className="mt-1 w-full min-h-[5rem] rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={remediationPayloadJson}
              onChange={(e) => setRemediationPayloadJson(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            disabled={remediationMut.isPending}
            onClick={() => remediationMut.mutate()}
          >
            POST remediation/validate
          </button>
          {remediationMut.isSuccess ? (
            <pre className="max-h-48 overflow-auto rounded border bg-white p-2 font-mono text-[10px]">
              {JSON.stringify(remediationMut.data, null, 2)}
            </pre>
          ) : null}
        </div>
      </section>
    </div>
  );
}

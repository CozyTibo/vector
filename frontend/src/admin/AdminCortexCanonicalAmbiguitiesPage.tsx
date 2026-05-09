import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { formatRelativeAge } from "./cortexAdminTypes";
import { CanonicalFilterToolbar, CompactTable, OperatorDrawer } from "./canonical/operatorUi";
import { matchesTimeRange, useCanonicalOperatorFilters } from "./canonical/operatorFilters";

type AmbiguityRecordRow = {
  id: string;
  bundle_id: string;
  ambiguity_class: string;
  scope: string;
  primary_connector?: string | null;
  primary_resource_type?: string | null;
  status: string;
  raw_record_ids: number[];
  created_at?: string | null;
};

type AmbiguityListPayload = {
  tenant_id: string;
  records: AmbiguityRecordRow[];
};

export default function AdminCortexCanonicalAmbiguitiesPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const { filters, setFilters } = useCanonicalOperatorFilters();
  const [openDrawer, setOpenDrawer] = useState(false);
  const [lifecycleDrawer, setLifecycleDrawer] = useState(false);
  const [ambBundleId, setAmbBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [ambClass, setAmbClass] = useState("competing_canonical_candidates");
  const [ambScope, setAmbScope] = useState("issue.status_transition");
  const [ambRawIds, setAmbRawIds] = useState("");
  const [ambHandle, setAmbHandle] = useState("");
  const [ambLifecycleId, setAmbLifecycleId] = useState("");
  const [ambLifecycleTarget, setAmbLifecycleTarget] = useState("void");
  const [ambLifecycleNote, setAmbLifecycleNote] = useState("");

  const qAmbiguity = useQuery({
    queryKey: ["admin-cortex-canonical-ambiguity", tenantId],
    queryFn: () =>
      adminJson<AmbiguityListPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/ambiguity?limit=120`,
      ),
    enabled: Boolean(tenantId),
  });

  const openAmbiguityMut = useMutation({
    mutationFn: async () => {
      const ids = ambRawIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      return adminJson<{ record: AmbiguityRecordRow }>(`/admin/tenants/${tenantId}/cortex/canonical/ambiguity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bundle_id: ambBundleId,
          ambiguity_class: ambClass,
          scope: ambScope,
          raw_record_ids: ids,
          record_handle: ambHandle.trim() || undefined,
          rule_ids_involved: [],
        }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-ambiguity", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
    },
  });

  const ambiguityLifecycleMut = useMutation({
    mutationFn: async () => {
      const id = ambLifecycleId.trim();
      if (!id) throw new Error("ambiguity UUID required");
      return adminJson<{ record: AmbiguityRecordRow }>(
        `/admin/tenants/${tenantId}/cortex/canonical/ambiguity/${id}/lifecycle`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_status: ambLifecycleTarget,
            supersession_note: ambLifecycleNote.trim() || undefined,
          }),
        },
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-ambiguity", tenantId] });
    },
  });

  const rows = useMemo(() => {
    const recs = qAmbiguity.data?.records ?? [];
    return recs.filter((r) => {
      if (!matchesTimeRange(r.created_at, filters.timeRange)) return false;
      if (filters.bundle && !r.bundle_id.includes(filters.bundle)) return false;
      if (filters.objectKind && !r.ambiguity_class.includes(filters.objectKind)) return false;
      if (filters.connector && !(r.primary_connector ?? "").includes(filters.connector)) return false;
      if (filters.status && r.status !== filters.status) return false;
      return true;
    });
  }, [qAmbiguity.data?.records, filters]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Ambiguities · Open queue</h2>
            <p className="mt-1 text-sm text-stone-600">
              Durable ambiguity receipts with lifecycle supersession — counts also surface on the Overview health strip.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md border border-stone-300 bg-white px-3 py-2 text-sm font-medium text-stone-800 hover:bg-stone-50"
              onClick={() => setLifecycleDrawer(true)}
            >
              Lifecycle transition…
            </button>
            <button
              type="button"
              className="rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white hover:bg-stone-800"
              onClick={() => setOpenDrawer(true)}
            >
              Open new ambiguity…
            </button>
          </div>
        </div>
      </section>

      <CanonicalFilterToolbar filters={filters} onChange={setFilters} />

      {qAmbiguity.isPending ? (
        <p className="text-sm text-stone-600">Loading ambiguity records…</p>
      ) : qAmbiguity.isError ? (
        <p className="text-sm text-red-700">{(qAmbiguity.error as Error).message}</p>
      ) : (
        <CompactTable
          columns={[
            { key: "cls", label: "ambiguity_class" },
            { key: "conn", label: "connector" },
            { key: "scope", label: "scope" },
            { key: "life", label: "lifecycle_state" },
            { key: "cnt", label: "affected_records" },
            { key: "at", label: "created_at" },
          ]}
          rows={rows.map((r) => ({
            cls: r.ambiguity_class,
            conn: `${r.primary_connector ?? "—"}/${r.primary_resource_type ?? "—"}`,
            scope: r.scope,
            life: r.status,
            cnt: r.raw_record_ids.length,
            at: formatRelativeAge(r.created_at),
          }))}
        />
      )}

      <OperatorDrawer open={openDrawer} title="Open ambiguity record" onClose={() => setOpenDrawer(false)}>
        <div className="space-y-3 text-sm">
          <label className="block text-xs text-stone-600">
            bundle_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambBundleId}
              onChange={(e) => setAmbBundleId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            ambiguity_class
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambClass}
              onChange={(e) => setAmbClass(e.target.value)}
            >
              <option value="unresolved_mapping">unresolved_mapping</option>
              <option value="unresolved_identity">unresolved_identity</option>
              <option value="conflicting_evidence">conflicting_evidence</option>
              <option value="competing_canonical_candidates">competing_canonical_candidates</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            scope
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambScope}
              onChange={(e) => setAmbScope(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            raw_record_ids
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambRawIds}
              onChange={(e) => setAmbRawIds(e.target.value)}
              placeholder="comma / space separated"
            />
          </label>
          <label className="block text-xs text-stone-600">
            record_handle (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambHandle}
              onChange={(e) => setAmbHandle(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            disabled={openAmbiguityMut.isPending}
            onClick={() => openAmbiguityMut.mutate()}
          >
            {openAmbiguityMut.isPending ? "Opening…" : "POST ambiguity"}
          </button>
          {openAmbiguityMut.isError ? (
            <p className="text-sm text-red-700">{(openAmbiguityMut.error as Error).message}</p>
          ) : null}
        </div>
      </OperatorDrawer>

      <OperatorDrawer open={lifecycleDrawer} title="Ambiguity lifecycle transition" onClose={() => setLifecycleDrawer(false)}>
        <div className="space-y-3 text-sm">
          <label className="block text-xs text-stone-600">
            ambiguity_id (UUID)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambLifecycleId}
              onChange={(e) => setAmbLifecycleId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            target_status
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambLifecycleTarget}
              onChange={(e) => setAmbLifecycleTarget(e.target.value)}
            >
              <option value="superseded_by_evidence">superseded_by_evidence</option>
              <option value="superseded_by_mapping_version">superseded_by_mapping_version</option>
              <option value="void">void</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            note (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={ambLifecycleNote}
              onChange={(e) => setAmbLifecycleNote(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            disabled={ambiguityLifecycleMut.isPending}
            onClick={() => ambiguityLifecycleMut.mutate()}
          >
            {ambiguityLifecycleMut.isPending ? "Applying…" : "POST lifecycle"}
          </button>
          {ambiguityLifecycleMut.isError ? (
            <p className="text-sm text-red-700">{(ambiguityLifecycleMut.error as Error).message}</p>
          ) : null}
        </div>
      </OperatorDrawer>
    </div>
  );
}

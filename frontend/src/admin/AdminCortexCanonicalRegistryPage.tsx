import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { CanonicalFilterToolbar, CompactTable } from "./canonical/operatorUi";
import { useCanonicalOperatorFilters } from "./canonical/operatorFilters";

type MappingRegistryPayload = {
  registry_schema_version: number;
  bundles: Array<{
    bundle_id: string;
    lifecycle_state: string;
    manifest_hash: string;
    owner_team: string;
  }>;
  compatibility_edges: Array<{
    from_bundle_id: string;
    to_bundle_id: string;
    edge_kind: string;
    is_breaking: boolean;
  }>;
  pins_for_tenant: Array<{
    pin_id: string;
    bundle_id: string;
    scope_kind: string;
    scope_marker: string;
  }>;
  changelog_entries: Array<{
    bundle_id: string;
    sequence_number: number;
    summary: string;
    breaking_classification: string;
  }>;
};

export default function AdminCortexCanonicalRegistryPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const { filters, setFilters } = useCanonicalOperatorFilters();

  const qRegistry = useQuery({
    queryKey: ["admin-cortex-canonical-mapping-registry", tenantId],
    queryFn: () =>
      adminJson<MappingRegistryPayload>(`/admin/tenants/${tenantId}/cortex/canonical/mapping-registry`),
    enabled: Boolean(tenantId),
  });

  const bundles = useMemo(() => {
    const b = qRegistry.data?.bundles ?? [];
    if (!filters.bundle) return b;
    return b.filter((x) => x.bundle_id.includes(filters.bundle));
  }, [qRegistry.data?.bundles, filters.bundle]);

  const pins = useMemo(() => {
    const p = qRegistry.data?.pins_for_tenant ?? [];
    if (!filters.bundle) return p;
    return p.filter((x) => x.bundle_id.includes(filters.bundle));
  }, [qRegistry.data?.pins_for_tenant, filters.bundle]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Registry · Mapping bundles</h2>
        <p className="mt-1 text-sm text-stone-600">
          Bundle inventory, compatibility edges, tenant pins, and changelog — governance substrate for deterministic
          transforms.
        </p>
      </section>

      <CanonicalFilterToolbar filters={filters} onChange={setFilters} />

      {qRegistry.isPending ? (
        <p className="text-sm text-stone-600">Loading registry…</p>
      ) : qRegistry.isError ? (
        <p className="text-sm text-red-700">{(qRegistry.error as Error).message}</p>
      ) : (
        <>
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-stone-900">Bundles</h3>
            <CompactTable
              columns={[
                { key: "id", label: "bundle_id" },
                { key: "st", label: "lifecycle_state" },
                { key: "hash", label: "manifest_hash" },
                { key: "own", label: "owner_team" },
              ]}
              rows={bundles.map((b) => ({
                id: b.bundle_id,
                st: b.lifecycle_state,
                hash: b.manifest_hash,
                own: b.owner_team,
              }))}
            />
          </section>
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-stone-900">Compatibility edges</h3>
            <CompactTable
              columns={[
                { key: "from", label: "from_bundle" },
                { key: "to", label: "to_bundle" },
                { key: "kind", label: "edge_kind" },
                { key: "brk", label: "breaking" },
              ]}
              rows={(qRegistry.data?.compatibility_edges ?? []).map((e) => ({
                from: e.from_bundle_id,
                to: e.to_bundle_id,
                kind: e.edge_kind,
                brk: e.is_breaking ? "yes" : "no",
              }))}
              empty="No compatibility edges declared yet."
            />
          </section>
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-stone-900">Tenant pins</h3>
            <CompactTable
              columns={[
                { key: "pin", label: "pin_id" },
                { key: "b", label: "bundle_id" },
                { key: "sk", label: "scope_kind" },
                { key: "sm", label: "scope_marker" },
              ]}
              rows={pins.map((p) => ({
                pin: p.pin_id,
                b: p.bundle_id,
                sk: p.scope_kind,
                sm: p.scope_marker || "—",
              }))}
              empty="No pins for this tenant."
            />
          </section>
          <section className="rounded-xl border border-stone-200 bg-stone-50/80 p-4 shadow-inner">
            <h3 className="text-sm font-semibold text-stone-900">Changelog</h3>
            <ul className="mt-3 space-y-2 text-xs text-stone-800">
              {(qRegistry.data?.changelog_entries ?? []).map((c) => (
                <li key={`${c.bundle_id}-${c.sequence_number}`} className="rounded-md border border-stone-100 bg-white p-3">
                  <span className="font-mono text-stone-900">{c.bundle_id}</span> · seq {c.sequence_number}{" "}
                  <span className="text-stone-500">({c.breaking_classification})</span>
                  <p className="mt-1 text-sm text-stone-700">{c.summary}</p>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

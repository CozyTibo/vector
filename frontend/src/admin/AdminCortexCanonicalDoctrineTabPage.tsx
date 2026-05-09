import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { AccordionSection } from "./canonical/operatorUi";

/** Minimal ontology projection for Doctrine tab — matches backend ontology document fields used here. */
type DoctrineOntologyPayload = {
  ontology_schema_version: number;
  phase: string;
  implementation_step: number;
  completed_implementation_steps: number[];
  name: string;
  layers: string[];
  object_kinds: Array<{
    id: string;
    layer: string;
    taxonomy_family: string;
    structural_role: string;
    structural_examples: string[];
    description: string;
  }>;
  structural_arcs: Array<{ from_kind: string; edge_kind: string; to_kind: string }>;
  taxonomy_families: Array<{ id: string; boundary_definition: string }>;
  kind_taxonomy: Array<{
    object_kind_id: string;
    taxonomy_family: string;
    structural_role: string;
    structural_examples: string[];
  }>;
  taxonomy_hard_rules: string[];
  logical_key_profile_version: number;
  logical_key_global_rules: string[];
  logical_keys_by_kind: Array<{
    canonical_object_kind: string;
    idempotency_tuple_fields: string[];
    tie_break_notes?: string | null;
  }>;
  logical_key_doctrine_anchors: string[];
  mapping_contract_schema_version: number;
  evidence_grades: Array<{ id: string; label: string; definition: string }>;
  determinism_criteria: string[];
  structural_extraction_definition: string;
  semantic_inference_forbidden_definition: string;
  allowed_deterministic_operations: Array<{ id: string; description: string }>;
  forbidden_operations: string[];
  field_emission_posture_rules: string[];
  mapping_versioning_rules: string[];
  mapping_table_row_shape: Array<{
    column: string;
    value_type: string;
    required: boolean;
    description: string;
  }>;
  mapping_contract_doctrine_anchors: string[];
  mapping_registry_admin_route: string;
  transform_materialize_route: string;
  transform_lineage_route: string;
  doctrine_anchors: string[];
};

type OracleManifestPayload = {
  oracle_manifest_schema_version: number;
  mapping_bundle_id: string;
  engine_build_ref: string;
  vectors: Array<{
    fixture_id: string;
    coverage_tags: string[];
    allowed_divergence_classes: string[];
    raw_snapshot_ref: string;
  }>;
};

export default function AdminCortexCanonicalDoctrineTabPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const qOnt = useQuery({
    queryKey: ["admin-cortex-canonical-ontology-doctrine", tenantId],
    queryFn: () => adminJson<DoctrineOntologyPayload>(`/admin/tenants/${tenantId}/cortex/canonical/ontology`),
    enabled: Boolean(tenantId),
  });

  const qOracle = useQuery({
    queryKey: ["admin-cortex-canonical-oracle-manifest", tenantId],
    queryFn: () =>
      adminJson<OracleManifestPayload>(`/admin/tenants/${tenantId}/cortex/canonical/oracle-manifest`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (qOnt.isPending) return <p className="text-sm text-stone-600">Loading ontology…</p>;
  if (qOnt.isError) return <p className="text-sm text-red-700">{(qOnt.error as Error).message}</p>;

  const d = qOnt.data;

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Doctrine · Canonical substrate specification</h2>
        <p className="mt-2 text-sm text-stone-600">
          Structural kinds, taxonomy boundaries, logical keys, deterministic mapping contracts, and oracle vectors.
          Progressive disclosure — expand only what you need for audits or promotions.
        </p>
        <dl className="mt-4 grid gap-2 text-xs text-stone-800 md:grid-cols-3">
          <div>
            <dt className="uppercase tracking-wide text-stone-500">Ontology schema</dt>
            <dd className="font-mono">{d.ontology_schema_version}</dd>
          </div>
          <div>
            <dt className="uppercase tracking-wide text-stone-500">Phase / Step</dt>
            <dd className="font-mono">
              {d.phase} · Step {d.implementation_step}
            </dd>
          </div>
          <div>
            <dt className="uppercase tracking-wide text-stone-500">Mapping contract schema</dt>
            <dd className="font-mono">{d.mapping_contract_schema_version}</dd>
          </div>
        </dl>
      </section>

      <AccordionSection
        title="Implementation routes & frozen anchors"
        subtitle="Where operators POST/GET — secondary to runtime tabs."
      >
        <div className="space-y-2 font-mono text-[11px] text-stone-800">
          <div>
            <span className="text-stone-500">registry · </span>
            {d.mapping_registry_admin_route}
          </div>
          <div>
            <span className="text-stone-500">materialize · </span>
            {d.transform_materialize_route}
          </div>
          <div>
            <span className="text-stone-500">lineage · </span>
            {d.transform_lineage_route}
          </div>
          <div className="mt-3 text-stone-600">
            Completed steps:{" "}
            <span className="text-stone-900">{d.completed_implementation_steps.join(", ")}</span>
          </div>
          <div className="mt-2 space-y-1">
            {d.doctrine_anchors.map((p) => (
              <div key={p}>{p}</div>
            ))}
          </div>
        </div>
      </AccordionSection>

      <AccordionSection title="Taxonomy & layers" subtitle="Structural discriminants — not provider catalogs.">
        <div className="flex flex-wrap gap-2">
          {d.layers.map((layer) => (
            <span key={layer} className="rounded-md bg-stone-100 px-2 py-1 font-mono text-xs text-stone-900">
              {layer}
            </span>
          ))}
        </div>
        <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-stone-500">Families</h4>
        <ul className="mt-2 space-y-3 text-sm text-stone-800">
          {d.taxonomy_families.map((fam) => (
            <li key={fam.id} className="rounded-lg border border-stone-100 bg-stone-50/80 p-3">
              <div className="font-mono text-xs font-semibold text-stone-900">{fam.id}</div>
              <p className="mt-1 leading-relaxed text-stone-700">{fam.boundary_definition}</p>
            </li>
          ))}
        </ul>
        <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-stone-500">Hard rules</h4>
        <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
          {d.taxonomy_hard_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </AccordionSection>

      <AccordionSection title="Logical-key doctrine" subtitle={`Profile v${d.logical_key_profile_version}`}>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Global rules</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
              {d.logical_key_global_rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Anchors</h4>
            <div className="mt-2 space-y-1 font-mono text-xs text-stone-700">
              {d.logical_key_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">canonical_object_kind</th>
                <th className="px-2 py-2">idempotency_tuple_fields</th>
                <th className="px-2 py-2">tie_break_notes</th>
              </tr>
            </thead>
            <tbody>
              {d.logical_keys_by_kind.map((row) => (
                <tr key={row.canonical_object_kind} className="border-t border-stone-100">
                  <td className="px-2 py-2 align-top font-mono text-stone-900">{row.canonical_object_kind}</td>
                  <td className="px-2 py-2 align-top font-mono text-[11px] text-stone-800">
                    {row.idempotency_tuple_fields.join(", ")}
                  </td>
                  <td className="px-2 py-2 align-top text-stone-700">{row.tie_break_notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AccordionSection>

      <AccordionSection title="Deterministic mapping contracts" subtitle={`Schema v${d.mapping_contract_schema_version}`}>
        <div className="grid gap-4 md:grid-cols-2">
          {d.evidence_grades.map((g) => (
            <div key={g.id} className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-4">
              <div className="font-mono text-xs font-semibold text-indigo-900">{g.label}</div>
              <p className="mt-2 text-sm leading-relaxed text-stone-800">{g.definition}</p>
            </div>
          ))}
        </div>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-stone-700">
          {d.determinism_criteria.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
        <div className="mt-6 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">column</th>
                <th className="px-2 py-2">type</th>
                <th className="px-2 py-2">required</th>
                <th className="px-2 py-2">description</th>
              </tr>
            </thead>
            <tbody>
              {d.mapping_table_row_shape.map((col) => (
                <tr key={col.column} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono text-stone-900">{col.column}</td>
                  <td className="px-2 py-2 font-mono text-stone-800">{col.value_type}</td>
                  <td className="px-2 py-2 font-mono">{col.required ? "yes" : "no"}</td>
                  <td className="px-2 py-2 text-stone-700">{col.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-4 font-mono text-xs text-stone-600">
          {d.mapping_contract_doctrine_anchors.map((p) => (
            <div key={p}>{p}</div>
          ))}
        </div>
      </AccordionSection>

      <AccordionSection title="Object kinds" subtitle={`${d.object_kinds.length} structural kinds`}>
        <div className="overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">id</th>
                <th className="px-2 py-2">layer</th>
                <th className="px-2 py-2">role</th>
                <th className="px-2 py-2">examples</th>
              </tr>
            </thead>
            <tbody>
              {d.object_kinds.map((row) => (
                <tr key={row.id} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono text-stone-900">{row.id}</td>
                  <td className="px-2 py-2 font-mono">{row.layer}</td>
                  <td className="px-2 py-2 font-mono">{row.structural_role}</td>
                  <td className="px-2 py-2 font-mono text-[11px] text-stone-700">{row.structural_examples.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AccordionSection>

      <AccordionSection title="Kind taxonomy index" subtitle={`${d.kind_taxonomy.length} rows`}>
        <div className="overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">object_kind_id</th>
                <th className="px-2 py-2">taxonomy_family</th>
                <th className="px-2 py-2">structural_role</th>
              </tr>
            </thead>
            <tbody>
              {d.kind_taxonomy.map((row) => (
                <tr key={row.object_kind_id} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono text-stone-900">{row.object_kind_id}</td>
                  <td className="px-2 py-2 font-mono">{row.taxonomy_family}</td>
                  <td className="px-2 py-2 font-mono">{row.structural_role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AccordionSection>

      <AccordionSection title="Structural arcs" subtitle={`${d.structural_arcs.length} linkage shapes`}>
        <div className="overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">from_kind</th>
                <th className="px-2 py-2">edge_kind</th>
                <th className="px-2 py-2">to_kind</th>
              </tr>
            </thead>
            <tbody>
              {d.structural_arcs.map((row, i) => (
                <tr key={`${row.from_kind}-${row.edge_kind}-${row.to_kind}-${i}`} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono">{row.from_kind}</td>
                  <td className="px-2 py-2 font-mono">{row.edge_kind}</td>
                  <td className="px-2 py-2 font-mono">{row.to_kind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </AccordionSection>

      <AccordionSection title="Oracle manifest (pre-runtime vectors)" subtitle="CI / harness inventory">
        {qOracle.isPending ? (
          <p className="text-sm text-stone-600">Loading oracle manifest…</p>
        ) : qOracle.isError ? (
          <p className="text-sm text-red-700">{(qOracle.error as Error).message}</p>
        ) : (
          <>
            <dl className="grid gap-2 text-xs md:grid-cols-2">
              <div>
                <dt className="uppercase tracking-wide text-stone-500">Manifest schema</dt>
                <dd className="font-mono">{qOracle.data.oracle_manifest_schema_version}</dd>
              </div>
              <div>
                <dt className="uppercase tracking-wide text-stone-500">Stub bundle</dt>
                <dd className="break-all font-mono">{qOracle.data.mapping_bundle_id}</dd>
              </div>
            </dl>
            <div className="mt-4 overflow-x-auto rounded border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-stone-700">
                  <tr>
                    <th className="px-2 py-2">fixture_id</th>
                    <th className="px-2 py-2">coverage_tags</th>
                    <th className="px-2 py-2">allowed_divergence</th>
                  </tr>
                </thead>
                <tbody>
                  {qOracle.data.vectors.map((v) => (
                    <tr key={v.fixture_id} className="border-t border-stone-100">
                      <td className="px-2 py-2 font-mono">{v.fixture_id}</td>
                      <td className="px-2 py-2 font-mono text-[11px]">{v.coverage_tags.join(", ")}</td>
                      <td className="px-2 py-2 font-mono">{v.allowed_divergence_classes.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </AccordionSection>
    </div>
  );
}

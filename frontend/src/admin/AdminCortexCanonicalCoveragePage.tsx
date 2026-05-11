import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { titleConnector } from "./cortexAdminTypes";
import {
  rollupConnectors,
  untreatedReason,
  untreatedResourceRows,
  type CoveragePayload,
  type CoverageRow,
} from "./canonical/coverageMatrixTypes";
import { CompactTable } from "./canonical/operatorUi";

function pctBar(value: number, max: number) {
  if (max <= 0) return 0;
  return Math.min(100, Math.round((100 * value) / max));
}

function ConnectorBlock(props: { title: string; rows: CoverageRow[] }) {
  const routable = props.rows.filter((r) => r.routable);
  const ingested = props.rows.filter((r) => r.ingest_supported);
  const rawSum = props.rows.reduce((a, r) => a + (r.tenant_raw_row_count || 0), 0);
  const matSum = props.rows.reduce((a, r) => a + (r.tenant_materialized_row_count || 0), 0);
  const replaySafe = props.rows.filter((r) => r.routable && (r.replay_count ?? 0) > 0).length;
  const unsupported = props.rows.filter((r) => r.ingest_supported && !r.routable && (r.tenant_raw_row_count || 0) > 0);

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="text-base font-semibold text-stone-900">{props.title}</h3>
        <span className="text-xs text-stone-500">
          {props.rows.length} pairs · raw {rawSum.toLocaleString()}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-[10px] font-semibold uppercase text-stone-500">Ingested types</p>
          <p className="mt-1 text-lg font-semibold text-stone-900">{ingested.length}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-2 rounded-full bg-sky-500"
              style={{ width: `${pctBar(ingested.length, props.rows.length || 1)}%` }}
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase text-stone-500">Routable</p>
          <p className="mt-1 text-lg font-semibold text-stone-900">{routable.length}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-2 rounded-full bg-indigo-500"
              style={{ width: `${pctBar(routable.length, props.rows.length || 1)}%` }}
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase text-stone-500">Materialized volume</p>
          <p className="mt-1 text-lg font-semibold text-stone-900">{matSum.toLocaleString()}</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-2 rounded-full bg-emerald-500"
              style={{ width: `${pctBar(matSum, rawSum || 1)}%` }}
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] font-semibold uppercase text-stone-500">Replay exercised</p>
          <p className="mt-1 text-lg font-semibold text-stone-900">{replaySafe}</p>
          <p className="mt-1 text-xs text-stone-500">Pairs with replay_count &gt; 0</p>
        </div>
      </div>
      {unsupported.length > 0 ? (
        <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <span className="font-semibold">{unsupported.length}</span> resource types have raw rows but no transform
          route (unsupported for canonical).
        </p>
      ) : null}
    </section>
  );
}

export default function AdminCortexCanonicalCoveragePage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["admin-cortex-canonical-coverage-matrix", tenantId],
    queryFn: () => adminJson<CoveragePayload>(`/admin/tenants/${tenantId}/cortex/canonical/coverage-matrix`),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading coverage…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  const d = q.data;
  const byConnector = new Map<string, CoverageRow[]>();
  for (const r of d.rows) {
    const arr = byConnector.get(r.connector) ?? [];
    arr.push(r);
    byConnector.set(r.connector, arr);
  }
  const roll = rollupConnectors(d.rows);
  const untreated = untreatedResourceRows(d.rows).sort((a, b) => {
    const gap =
      Math.max(0, (b.tenant_raw_row_count || 0) - (b.tenant_materialized_row_count || 0)) -
      Math.max(0, (a.tenant_raw_row_count || 0) - (a.tenant_materialized_row_count || 0));
    if (gap !== 0) return gap;
    return `${a.connector}:${a.resource_type}`.localeCompare(`${b.connector}:${b.resource_type}`);
  });

  return (
    <div className="space-y-8">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Substrate coverage</h2>
        <p className="mt-1 text-sm text-stone-600">
          What is ingested, routable, materialized, and replay-tested — grouped by connector for quick scanning.
        </p>
        <p className="mt-2 font-mono text-[11px] text-stone-500">
          routing v{d.transform_routing_registry_version} · matrix schema {d.canonical_coverage_matrix_schema_version} ·{" "}
          {d.summary.routable_pair_count} routable pairs
        </p>
      </section>

      {roll.map((r) => (
        <ConnectorBlock
          key={r.connector}
          title={titleConnector(r.connector)}
          rows={byConnector.get(r.connector) ?? []}
        />
      ))}

      <section id="untreated" className="scroll-mt-24 rounded-xl border border-amber-200 bg-amber-50/40 p-5 shadow-sm ring-1 ring-amber-100">
        <h2 className="text-lg font-semibold text-amber-950">Untreated raw → canonical</h2>
        <p className="mt-1 text-sm text-amber-900/90">
          Rows with backlog, unsupported ingest, replay failures, or topology orphans. Primary reason is heuristic from
          coverage flags.
        </p>
        <p className="mt-2 text-xs font-medium text-amber-900">
          Summary: {d.summary.routable_unmaterialized_raw_row_count.toLocaleString()} routable-unmaterialized raw rows ·{" "}
          {d.summary.unsupported_ingest_raw_row_count.toLocaleString()} unsupported-ingest raw rows
        </p>
        <div className="mt-4 overflow-x-auto rounded-lg border border-amber-100 bg-white">
          <CompactTable
            columns={[
              { key: "c", label: "Connector" },
              { key: "rt", label: "Resource type" },
              { key: "raw", label: "Raw #" },
              { key: "mat", label: "Mat #" },
              { key: "gap", label: "Gap" },
              { key: "why", label: "Why untreated" },
              { key: "route", label: "Routable" },
              { key: "rf", label: "Replay fail" },
              { key: "or", label: "Orphans" },
            ]}
            rows={untreated.slice(0, 80).map((r) => ({
              c: r.connector,
              rt: r.resource_type,
              raw: r.tenant_raw_row_count,
              mat: r.tenant_materialized_row_count,
              gap: Math.max(0, (r.tenant_raw_row_count || 0) - (r.tenant_materialized_row_count || 0)),
              why: untreatedReason(r),
              route: r.routable ? "yes" : "no",
              rf: r.replay_failure_count ?? 0,
              or: r.orphan_count ?? 0,
            }))}
            empty="Nothing flagged as untreated in this snapshot."
          />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-stone-50/50 p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-800">Full matrix (compact)</h3>
        <p className="mt-1 text-xs text-stone-600">Complete pair listing for power users.</p>
        <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200 bg-white">
          <CompactTable
            columns={[
              { key: "c", label: "c" },
              { key: "rt", label: "resource_type" },
              { key: "raw", label: "raw" },
              { key: "m", label: "mat" },
              { key: "pct", label: "%" },
              { key: "route", label: "route" },
              { key: "kind", label: "kind" },
            ]}
            rows={d.rows.map((r) => ({
              c: r.connector,
              rt: r.resource_type,
              raw: r.tenant_raw_row_count,
              m: r.tenant_materialized_row_count,
              pct: r.tenant_materialization_pct_of_raw != null ? String(r.tenant_materialization_pct_of_raw) : "—",
              route: r.routable ? "y" : "n",
              kind: r.canonical_object_kind ?? "—",
            }))}
          />
        </div>
      </section>
    </div>
  );
}

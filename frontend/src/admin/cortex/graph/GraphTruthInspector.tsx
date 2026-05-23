import type { ReactNode } from "react";

import { PhaseExplorer } from "../PhaseExplorer";
import { SectionSkeleton } from "../SectionSkeleton";
import { StatusBadge } from "../../ui/StatusBadge";
import type { PromotionByRuleRow } from "../pipelineTypes";
import type { GraphTruthEdgeTypeRow, GraphTruthInspectorPayload } from "./graphInspectorTypes";

function dupTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
}

type Props = {
  data: GraphTruthInspectorPayload | undefined;
  loading: boolean;
  error: string | null;
};

export function GraphTruthInspector({ data, loading, error }: Props) {
  if (loading && !data) {
    return (
      <div className="space-y-4">
        <SectionSkeleton variant="cards" />
        <SectionSkeleton variant="table" />
      </div>
    );
  }
  if (error) {
    return <p className="text-sm text-red-700">{error}</p>;
  }
  if (!data) {
    return <p className="text-sm text-stone-600">Graph truth inspector unavailable.</p>;
  }

  const graph = data.graph_truth;
  const inflation = data.inflation_signals ?? {};
  const continuity = data.continuity_signals ?? {};
  const edgeTypes = data.edge_type_distribution ?? [];
  const promos = graph.promotions_by_rule_id ?? [];
  const mirrorDominates = Boolean(inflation.topology_mirror_dominates);

  return (
    <div className="space-y-6">
      {mirrorDominates ? (
        <section className="rounded-xl border border-amber-300 bg-amber-50 p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-amber-950">Topology mirror dominance</h3>
          <p className="mt-1 text-sm text-amber-900">
            <span className="font-mono">{inflation.topology_mirror_link_type}</span> accounts for{" "}
            {inflation.topology_mirror_row_pct ?? 0}% of authoritative rows. This is identity
            topology, not execution continuity — inspect edge lineage below before trusting graph
            size.
          </p>
        </section>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Unique semantic pairs (primary)"
          value={graph.unique_auth_pairs.toLocaleString()}
          highlight
        />
        <MetricCard
          label="Dup factor"
          value={
            <span className="flex items-center gap-2">
              {graph.dup_factor ?? "—"}
              <StatusBadge tone={dupTone(graph.dup_factor_severity)}>{graph.dup_factor_severity}</StatusBadge>
            </span>
          }
        />
        <MetricCard
          label="Cross-system unique pairs"
          value={`${continuity.cross_system_unique_pair_pct ?? 0}%`}
          hint="Non topology-mirror link types"
        />
        <MetricCard
          label="Unpromoted candidates"
          value={(data.unpromoted_candidates ?? 0).toLocaleString()}
          hint={`${data.candidates?.total ?? 0} total candidate rows`}
        />
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Edge-type distribution</h3>
        <p className="mt-1 text-xs text-stone-500">
          Authoritative active edges only. Row inflation vs unique pairs must be visible per type.
        </p>
        {edgeTypes.length === 0 ? (
          <p className="mt-3 text-sm text-stone-600">No authoritative edges.</p>
        ) : (
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2">link_type</th>
                  <th className="px-3 py-2">unique pairs</th>
                  <th className="px-3 py-2">rows</th>
                  <th className="px-3 py-2">dup</th>
                  <th className="px-3 py-2">% rows</th>
                  <th className="px-3 py-2">% unique</th>
                  <th className="px-3 py-2">rules</th>
                </tr>
              </thead>
              <tbody>
                {edgeTypes.map((row: GraphTruthEdgeTypeRow) => (
                  <tr key={row.link_type} className="border-b border-stone-100">
                    <td className="px-3 py-2 font-mono text-xs">
                      {row.link_type}
                      {row.is_topology_mirror ? (
                        <span className="ml-2 text-[10px] uppercase text-amber-700">mirror</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{row.unique_pairs.toLocaleString()}</td>
                    <td className="px-3 py-2 tabular-nums text-stone-500">
                      {row.auth_edge_rows.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 tabular-nums">{row.dup_factor ?? "—"}</td>
                    <td className="px-3 py-2 tabular-nums">{row.pct_of_auth_rows}%</td>
                    <td className="px-3 py-2 tabular-nums">{row.pct_of_unique_pairs}%</td>
                    <td className="px-3 py-2 tabular-nums">{row.rule_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {promos.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Promotion rule diversity</h3>
          <p className="mt-1 text-xs text-stone-500">
            {graph.promotion_rule_count} rules with unique pairs. Low diversity often means a single
            topology mirror rule dominates.
          </p>
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2">rule_id</th>
                  <th className="px-3 py-2">unique pairs</th>
                  <th className="px-3 py-2">rows</th>
                </tr>
              </thead>
              <tbody>
                {promos.map((row: PromotionByRuleRow) => (
                  <tr key={row.rule_id} className="border-b border-stone-100">
                    <td className="px-3 py-2 font-mono text-xs">{row.rule_id}</td>
                    <td className="px-3 py-2 tabular-nums">{row.unique_pairs.toLocaleString()}</td>
                    <td className="px-3 py-2 tabular-nums text-stone-500">
                      {row.auth_edge_rows.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Edge lineage explorer</h3>
        <p className="mt-1 text-xs text-stone-500">
          Every row expands to raw evidence refs, promotion rule, candidate lineage, and metadata.
          No summaries — inspect receipts.
        </p>
        <div className="mt-4">
          <PhaseExplorer phase="graph" />
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-xs text-stone-600">
        <p>
          Entities in auth graph: {graph.entities_in_auth_graph_pct}% (
          {graph.entities_isolated?.toLocaleString() ?? 0} isolated of{" "}
          {graph.active_entities?.toLocaleString() ?? 0} active). Diagnostic only — isolation alone
          does not prove continuity failure.
        </p>
        {data.captured_at_utc ? (
          <p className="mt-1 text-stone-500">Captured {new Date(data.captured_at_utc).toLocaleString()}</p>
        ) : null}
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  hint,
  highlight = false,
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={[
        "rounded-lg border p-4 shadow-sm",
        highlight ? "border-emerald-200 bg-emerald-50" : "border-stone-200 bg-white",
      ].join(" ")}
    >
      <p className={["text-xs uppercase", highlight ? "text-emerald-800" : "text-stone-500"].join(" ")}>
        {label}
      </p>
      <div className="mt-1 text-lg font-semibold tabular-nums text-stone-950">{value}</div>
      {hint ? <p className="mt-1 text-xs text-stone-500">{hint}</p> : null}
    </div>
  );
}


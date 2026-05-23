import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { PhaseRerunCta } from "./cortex/PhaseRerunCta";
import { StatusBadge } from "./ui/StatusBadge";

type GraphSummary = PhaseSummaryPayload & {
  graph_metrics?: Record<string, unknown>;
  graph_truth?: {
    unique_auth_pairs?: number;
    auth_edge_rows?: number;
    dup_factor?: number | null;
    dup_factor_severity?: string;
    promotion_rule_count?: number;
    promotions_by_rule_id?: Array<{
      rule_id: string;
      unique_pairs: number;
      auth_edge_rows: number;
    }>;
  };
  node_count?: number;
  unique_auth_pairs?: number;
  auth_edge_rows?: number;
  dup_factor?: number | null;
  dup_factor_severity?: string;
  promotion_rule_count?: number;
  promotions_by_rule_id?: Array<{
    rule_id: string;
    unique_pairs: number;
    auth_edge_rows: number;
  }>;
  edge_count?: number;
  orphan_count?: number;
  degraded_count?: number;
};

function dupTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
}

export default function AdminCortexGraphPage() {
  return (
    <PhasePageShell
      phase="graph"
      title="Graph"
      description="Supporting topology for retrieval scope — unique auth pairs matter, not inflated link rows."
      summaryContent={(summary) => {
        const s = summary as GraphSummary;
        const m = s.graph_metrics ?? {};
        const uniquePairs = Number(s.unique_auth_pairs ?? s.graph_truth?.unique_auth_pairs ?? 0);
        const authRows = Number(s.auth_edge_rows ?? s.edge_count ?? 0);
        const dupFactor = s.dup_factor ?? s.graph_truth?.dup_factor;
        const dupSev = String(s.dup_factor_severity ?? s.graph_truth?.dup_factor_severity ?? "unknown");
        const promos = s.promotions_by_rule_id ?? s.graph_truth?.promotions_by_rule_id ?? [];
        return (
          <>
            <PhaseRerunCta
              phase="graph"
              label="Rebuild graph"
              description="Enqueues execution from the graph phase via the pipeline API."
            />
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
                <p className="text-xs uppercase text-emerald-800">Unique auth pairs (primary)</p>
                <p className="mt-1 text-lg font-semibold text-emerald-950">
                  {uniquePairs.toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Auth link rows (diagnostic)</p>
                <p className="mt-1 text-lg font-semibold">{authRows.toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Dup factor</p>
                <p className="mt-1 flex items-center gap-2">
                  <span className="text-lg font-semibold">{dupFactor ?? "—"}</span>
                  <StatusBadge tone={dupTone(dupSev)}>{dupSev}</StatusBadge>
                </p>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
                <p className="text-xs uppercase text-amber-800">Orphan nodes</p>
                <p className="mt-1 text-lg font-semibold text-amber-950">
                  {(s.orphan_count ?? 0).toLocaleString()}
                </p>
              </div>
            </section>
            <p className="text-sm text-stone-600">
              Nodes {(s.node_count ?? 0).toLocaleString()} · promotion rules with edges{" "}
              {Number(s.promotion_rule_count ?? s.graph_truth?.promotion_rule_count ?? 0)}
              {typeof m.graph_connectivity_percent === "number"
                ? ` · connectivity ${String(m.graph_connectivity_percent)}%`
                : null}
            </p>
            {promos.length > 0 ? (
              <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200 bg-white text-sm">
                <table className="min-w-full text-left">
                  <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                    <tr>
                      <th className="px-3 py-2">rule_id</th>
                      <th className="px-3 py-2">unique pairs</th>
                      <th className="px-3 py-2">rows</th>
                    </tr>
                  </thead>
                  <tbody>
                    {promos.map((row) => (
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
            ) : null}
          </>
        );
      }}
      explorerContent={<PhaseExplorer phase="graph" />}
    />
  );
}

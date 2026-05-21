import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { PhaseRerunCta } from "./cortex/PhaseRerunCta";

type GraphSummary = PhaseSummaryPayload & {
  graph_metrics?: Record<string, unknown>;
  node_count?: number;
  edge_count?: number;
  orphan_count?: number;
  degraded_count?: number;
};

export default function AdminCortexGraphPage() {
  return (
    <PhasePageShell
      phase="graph"
      title="Graph"
      description="Relationship graph and traversal substrate (merged). Walk legality and corruption scans are not operator actions."
      summaryContent={(summary) => {
        const s = summary as GraphSummary;
        const m = s.graph_metrics ?? {};
        return (
          <>
            <PhaseRerunCta
              phase="graph"
              label="Rebuild graph"
              description="Enqueues execution from the graph phase via the pipeline API."
            />
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Nodes</p>
                <p className="mt-1 text-lg font-semibold">{(s.node_count ?? 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Authoritative links</p>
                <p className="mt-1 text-lg font-semibold">{(s.edge_count ?? 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 shadow-sm">
                <p className="text-xs uppercase text-amber-800">Orphan nodes</p>
                <p className="mt-1 text-lg font-semibold text-amber-950">
                  {(s.orphan_count ?? 0).toLocaleString()}
                </p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Degraded signals</p>
                <p className="mt-1 text-lg font-semibold">{(s.degraded_count ?? 0).toLocaleString()}</p>
              </div>
            </section>
            {typeof m.graph_connectivity_percent === "number" ? (
              <p className="text-sm text-stone-600">
                Connectivity {String(m.graph_connectivity_percent)}% · maturity{" "}
                {String(m.graph_maturity_stage ?? "—")}
              </p>
            ) : null}
          </>
        );
      }}
      explorerContent={<PhaseExplorer phase="graph" />}
    />
  );
}

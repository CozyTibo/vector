import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";
import { PhaseRerunCta } from "./cortex/PhaseRerunCta";

type RetrievalSummary = PhaseSummaryPayload & {
  indexed_count?: number;
  coverage_percent?: number;
  published_index_epoch?: string | null;
  substrate_state?: string;
};

export default function AdminCortexRetrievalPage() {
  return (
    <PhasePageShell
      phase="retrieval"
      title="Retrieval"
      description="Published indexes for query and synthesis. Rebuild via Overview or the action below."
      summaryContent={(summary) => {
        const s = summary as RetrievalSummary;
        return (
          <>
            <PhaseRerunCta
              phase="retrieval"
              label="Rebuild indexes"
              description="Enqueues execution from the retrieval phase via the pipeline API."
            />
            <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Indexed objects</p>
                <p className="mt-1 text-lg font-semibold">{(s.indexed_count ?? 0).toLocaleString()}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Coverage</p>
                <p className="mt-1 text-lg font-semibold">{s.coverage_percent ?? 0}%</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Substrate</p>
                <p className="mt-1 text-lg font-semibold">{s.substrate_state ?? "—"}</p>
              </div>
              <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
                <p className="text-xs uppercase text-stone-500">Published epoch</p>
                <p className="mt-1 font-mono text-xs">{s.published_index_epoch ?? "—"}</p>
              </div>
            </section>
          </>
        );
      }}
      explorerContent={<PhaseExplorer phase="retrieval" />}
    />
  );
}

import { PhaseExplorer } from "./cortex/PhaseExplorer";
import { PhasePageShell, type PhaseSummaryPayload } from "./cortex/PhasePageShell";

type SynthesisSummary = PhaseSummaryPayload & {
  eligible_scopes?: number;
  synthesized_scopes?: number;
  coverage_percent?: number;
  health_strip?: { substrate_state?: string; replay_posture?: string };
};

export default function AdminCortexSynthesisPage() {
  return (
    <PhasePageShell
      phase="synthesis"
      title="Synthesis"
      description="Generated artifacts and publication state. Runs automatically via the execution engine."
      summaryContent={(summary) => {
        const s = summary as SynthesisSummary;
        const health = s.health_strip;
        return (
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Eligible scopes</p>
              <p className="mt-1 text-lg font-semibold">{(s.eligible_scopes ?? 0).toLocaleString()}</p>
            </div>
            <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Synthesized</p>
              <p className="mt-1 text-lg font-semibold">{(s.synthesized_scopes ?? 0).toLocaleString()}</p>
            </div>
            <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Coverage</p>
              <p className="mt-1 text-lg font-semibold">{s.coverage_percent ?? 0}%</p>
            </div>
            <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase text-stone-500">Substrate</p>
              <p className="mt-1 text-lg font-semibold">{health?.substrate_state ?? "—"}</p>
            </div>
          </section>
        );
      }}
      explorerContent={<PhaseExplorer phase="synthesis" />}
    />
  );
}

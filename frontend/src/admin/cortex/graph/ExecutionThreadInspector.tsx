export function ExecutionThreadInspector() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-950">
        <p className="font-medium">Phase G5 — execution thread inspector</p>
        <p className="mt-1 text-indigo-900">
          Replay how Cortex reconstructed a real execution situation: issue → discussion → PR →
          deployment → follow-up. Searchable by PR, issue, Slack thread, incident, retrieval entry, or
          synthesis artifact. Every event expands to raw evidence — no hallucinated summaries.
        </p>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-sm font-semibold text-stone-900">Planned surface</h3>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-stone-700">
          <li>Timeline reconstruction with timestamp, actor, source system, linked entities</li>
          <li>Connected work items, walks, retrieval entries, synthesis outputs</li>
          <li>Causal continuity query over OCTS walks, canonical mats, TCRE, evidence refs</li>
        </ul>
        <p className="mt-4 text-xs text-stone-500">
          Substrate exists (walks, materializations, transition log). G5 adds the execution thread
          assembler and timeline materialization endpoint — not a new graph model.
        </p>
      </section>
    </div>
  );
}

import type { ReactNode } from "react";

import type { GraphTruthInspectorPayload } from "./graphInspectorTypes";

type Props = {
  data: GraphTruthInspectorPayload | undefined;
};

export function IslandInspector({ data }: Props) {
  const components = data?.graph_truth?.connected_components ?? {};
  const sizes = components.component_sizes_top_10 ?? [];

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-950">
        <p className="font-medium">Phase G4 — island inspector</p>
        <p className="mt-1 text-indigo-900">
          Connected execution islands with retrieval/synthesis scope, recurrence, and WHY entities
          belong together. This slice shows connected-component truth from the auth graph; per-island
          scope IDs and walk/retrieval timestamps ship in G4.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Components" value={components.component_count?.toLocaleString() ?? "—"} />
        <Metric label="Largest island" value={components.largest_component_size?.toLocaleString() ?? "—"} />
        <Metric label="Islands size ≥ 2" value={components.components_size_ge_2?.toLocaleString() ?? "—"} />
        <Metric
          label="Cross-system unique pairs"
          value={`${data?.continuity_signals?.cross_system_unique_pair_pct ?? 0}%`}
        />
      </section>

      {sizes.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Top component sizes</h3>
          <p className="mt-1 text-xs text-stone-500">
            Entity counts per connected component (authoritative graph). Not vanity density — inspect
            whether islands carry execution continuity.
          </p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {sizes.map((size: number, idx: number) => (
              <li
                key={`${size}-${idx}`}
                className="rounded-md border border-stone-200 bg-stone-50 px-3 py-1.5 text-sm tabular-nums"
              >
                #{idx + 1}: {size.toLocaleString()} entities
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {"error" in components && components.error ? (
        <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Component computation error: {String(components.error)}
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700">
        <p>
          Island registry (scope id, last walk, last retrieval epoch) lives on pipeline overview KPI
          and execution inspect today. G4 will unify component topology with execution island
          registry receipts.
        </p>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase text-stone-500">{label}</p>
      <div className="mt-1 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  );
}

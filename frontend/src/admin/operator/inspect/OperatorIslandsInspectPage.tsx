import { useParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import { GraphComponentRefreshSection } from "../GraphComponentRefreshSection";
import { useOperatorIslandsList } from "../useOperatorInspect";

export default function OperatorIslandsInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const islandsQ = useOperatorIslandsList();

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Islands inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Registry-first island list — no connected-component scan on load. Use refresh for async sizes.
        </p>
      </header>

      {tenantId ? <GraphComponentRefreshSection tenantId={tenantId} /> : null}

      {islandsQ.isPending && !islandsQ.data ? (
        <SectionSkeleton variant="table" />
      ) : islandsQ.isError ? (
        <p className="text-sm text-red-700">{(islandsQ.error as Error).message}</p>
      ) : islandsQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-stone-700">{islandsQ.data.island_count} islands in registry</p>
          {islandsQ.data.islands.length === 0 ? (
            <p className="mt-3 text-sm text-stone-500">No islands persisted yet for this tenant.</p>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                  <tr>
                    <th className="px-3 py-2">Scope</th>
                    <th className="px-3 py-2">Entities</th>
                    <th className="px-3 py-2">Auth edges</th>
                    <th className="px-3 py-2">Last walk</th>
                    <th className="px-3 py-2">Retrieval epoch</th>
                  </tr>
                </thead>
                <tbody>
                  {islandsQ.data.islands.map((row) => (
                    <tr key={String(row.island_scope_id)} className="border-b border-stone-100">
                      <td className="px-3 py-2 font-mono text-xs">{String(row.island_scope_id)}</td>
                      <td className="px-3 py-2 tabular-nums">{String(row.entity_count ?? "—")}</td>
                      <td className="px-3 py-2 tabular-nums">{String(row.authoritative_edge_count ?? "—")}</td>
                      <td className="px-3 py-2 text-xs">{String(row.last_walk_at ?? "—")}</td>
                      <td className="px-3 py-2 font-mono text-xs">{String(row.last_retrieval_epoch ?? "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}

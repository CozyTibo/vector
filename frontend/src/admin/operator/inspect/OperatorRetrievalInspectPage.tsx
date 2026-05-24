import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import {
  useOperatorRetrievalEntries,
  useOperatorRetrievalEpochs,
  useOperatorRetrievalLineage,
} from "../useOperatorInspectChains";
import { LineageChainPanel } from "./LineageChainPanel";

function fmtTime(iso: unknown): string {
  if (!iso || typeof iso !== "string") return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function OperatorRetrievalInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const epochsQ = useOperatorRetrievalEpochs(5);
  const [draft, setDraft] = useState({
    entity_id: "",
    scope_ref: "",
    index_kind: "",
    walk_id: "",
    external_url: "",
  });
  const [submitted, setSubmitted] = useState<Record<string, string>>({});
  const entriesQ = useOperatorRetrievalEntries(submitted, Boolean(Object.values(submitted).some(Boolean)));
  const [lineageTarget, setLineageTarget] = useState<{ kind: string; ref: string } | null>(null);
  const lineageQ = useOperatorRetrievalLineage(
    lineageTarget?.kind ?? "",
    lineageTarget?.ref ?? "",
    Boolean(lineageTarget),
  );

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Retrieval inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Published epochs on load. Entry search and lineage chain on demand.
        </p>
      </header>

      {epochsQ.isPending && !epochsQ.data ? (
        <SectionSkeleton variant="table" />
      ) : epochsQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-stone-900">Recent index epochs</h2>
          {epochsQ.data.epochs.length === 0 ? (
            <p className="mt-3 text-sm text-stone-500">No retrieval epochs for this tenant yet.</p>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200">
              <table className="min-w-full text-left text-sm">
                <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                  <tr>
                    <th className="px-3 py-2">Epoch</th>
                    <th className="px-3 py-2">State</th>
                    <th className="px-3 py-2">Entries</th>
                    <th className="px-3 py-2">Mix</th>
                    <th className="px-3 py-2">Published</th>
                  </tr>
                </thead>
                <tbody>
                  {epochsQ.data.epochs.map((row) => (
                    <tr key={String(row.index_epoch)} className="border-b border-stone-100">
                      <td className="px-3 py-2 font-mono text-xs">{String(row.index_epoch)}</td>
                      <td className="px-3 py-2">{String(row.build_state)}</td>
                      <td className="px-3 py-2 tabular-nums">{String(row.entry_count ?? "—")}</td>
                      <td className="px-3 py-2 text-xs">{String(row.mix_note ?? "—")}</td>
                      <td className="px-3 py-2 text-xs">{fmtTime(row.published_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-900">Index entry search</h2>
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted({ ...draft });
            setLineageTarget(null);
          }}
        >
          {(
            [
              ["entity_id", "Entity id"],
              ["scope_ref", "Scope ref"],
              ["index_kind", "Index kind"],
              ["walk_id", "Walk id"],
              ["external_url", "External URL / PR"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="block text-sm">
              <span className="text-xs font-medium text-stone-600">{label}</span>
              <input
                className="mt-1 w-full rounded-md border border-stone-300 px-3 py-2 font-mono text-sm"
                value={draft[key]}
                onChange={(e) => setDraft((prev) => ({ ...prev, [key]: e.target.value }))}
              />
            </label>
          ))}
          <div className="flex items-end sm:col-span-2">
            <button
              type="submit"
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search entries
            </button>
          </div>
        </form>
      </section>

      {entriesQ.isPending ? <SectionSkeleton variant="table" /> : null}
      {entriesQ.isError ? (
        <p className="text-sm text-red-700">
          {(entriesQ.error as Error).message === "search_query_required"
            ? "Provide at least one search field."
            : (entriesQ.error as Error).message}
        </p>
      ) : null}
      {entriesQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">
            {entriesQ.data.total} entr{entriesQ.data.total === 1 ? "y" : "ies"}
          </h3>
          <ul className="mt-4 divide-y divide-stone-100">
            {entriesQ.data.items.map((item) => {
              const kind = String(item.lineage_artifact_kind ?? "");
              const ref = String(item.lineage_artifact_ref ?? "");
              return (
                <li key={String(item.entry_id)} className="py-3">
                  <p className="text-sm font-medium text-stone-900">
                    {String(item.index_kind)} · {String(item.index_key)}
                  </p>
                  <p className="mt-1 font-mono text-xs text-stone-600">
                    {String(item.retrieval_lookup_id)} · epoch {String(item.index_epoch ?? "—")}
                  </p>
                  {kind && ref ? (
                    <button
                      type="button"
                      className="mt-2 text-xs font-medium text-indigo-700"
                      onClick={() => setLineageTarget({ kind, ref })}
                    >
                      View lineage chain →
                    </button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      {lineageTarget ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold text-stone-900">
              Lineage · {lineageTarget.kind} / {lineageTarget.ref}
            </h3>
            <Link
              to={`/admin/tenants/${tenantId}/cortex/inspect/retrieval/lineage?kind=${encodeURIComponent(lineageTarget.kind)}&ref=${encodeURIComponent(lineageTarget.ref)}`}
              className="text-xs font-medium text-indigo-700 no-underline hover:underline"
            >
              Open full lineage view
            </Link>
          </div>
          {lineageQ.isPending ? <SectionSkeleton variant="attention" /> : null}
          {lineageQ.isError ? (
            <p className="mt-3 text-sm text-red-700">{(lineageQ.error as Error).message}</p>
          ) : null}
          {lineageQ.data ? (
            <div className="mt-4">
              <LineageChainPanel chain={lineageQ.data.chain} />
            </div>
          ) : null}
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}

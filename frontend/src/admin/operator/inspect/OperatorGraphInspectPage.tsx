import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { SectionSkeleton } from "../../cortex/SectionSkeleton";
import { DeployInfoFooter } from "../DeployInfoFooter";
import { GraphComponentRefreshSection } from "../GraphComponentRefreshSection";
import { useOperatorEdgeProvenance, useOperatorGraphSnapshot } from "../useOperatorInspect";

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function OperatorGraphInspectPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const snapshotQ = useOperatorGraphSnapshot();
  const [draft, setDraft] = useState({ source: "", target: "", link_type: "", rule_id: "" });
  const [submitted, setSubmitted] = useState<Record<string, string>>({});
  const edgesQ = useOperatorEdgeProvenance(submitted, Boolean(Object.values(submitted).some(Boolean)));

  const snapshot = snapshotQ.data;
  const graph = snapshot?.graph_summary;

  return (
    <div className="space-y-6">
      <header className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h1 className="text-lg font-semibold text-stone-900">Graph inspect</h1>
        <p className="mt-1 text-sm text-stone-600">
          Snapshot summary from materialized continuity row. Edge lookup runs only on search submit.
        </p>
      </header>

      {snapshotQ.isPending && !snapshot ? (
        <SectionSkeleton variant="attention" />
      ) : snapshotQ.isError ? (
        <p className="text-sm text-red-700">{(snapshotQ.error as Error).message}</p>
      ) : snapshot ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-stone-900">Graph snapshot</h2>
            {snapshot.stale ? (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                Snapshot stale ({snapshot.stale_after_minutes}m+)
              </span>
            ) : snapshot.available ? (
              <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-900">
                Fresh
              </span>
            ) : null}
          </div>
          <p className="mt-3 text-sm text-stone-800">{snapshot.prose_summary}</p>
          <p className="mt-2 text-xs text-stone-500">
            Captured {fmtTime(snapshot.captured_at_utc)}
            {!snapshot.available ? " · snapshot row pending" : ""}
          </p>
          {graph ? (
            <div className="mt-4 overflow-x-auto rounded-lg border border-stone-200">
              <table className="min-w-full text-left text-sm">
                <tbody>
                  {Object.entries(graph).map(([key, value]) => (
                    <tr key={key} className="border-b border-stone-100">
                      <td className="px-3 py-2 text-xs uppercase text-stone-500">{key.replace(/_/g, " ")}</td>
                      <td className="px-3 py-2 font-mono text-xs">{String(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </section>
      ) : null}

      <GraphComponentRefreshSection tenantId={tenantId} />

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-stone-900">Edge provenance lookup</h2>
        <p className="mt-1 text-xs text-stone-500">
          Why does this edge exist? Provide source entity id, target, link type, or rule id.
        </p>
        <form
          className="mt-4 grid gap-3 sm:grid-cols-2"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted({ ...draft });
          }}
        >
          {(
            [
              ["source", "Source entity id"],
              ["target", "Target entity id"],
              ["link_type", "Link type"],
              ["rule_id", "Rule id"],
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
              Search edges
            </button>
          </div>
        </form>
      </section>

      {edgesQ.isPending ? <SectionSkeleton variant="table" /> : null}
      {edgesQ.isError ? (
        <p className="text-sm text-red-700">
          {(edgesQ.error as Error).message === "edge_query_required"
            ? "Provide at least one search field."
            : (edgesQ.error as Error).message}
        </p>
      ) : null}
      {edgesQ.data ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">
            {edgesQ.data.total} edge{edgesQ.data.total === 1 ? "" : "s"}
          </h3>
          <div className="mt-3 space-y-3">
            {edgesQ.data.edges.map((edge, idx) => (
              <div key={String(edge.link_id ?? idx)} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                <p className="text-sm font-medium text-stone-900">
                  {String(edge.link_type ?? "unknown")} · {String(edge.rule_id ?? edge.rule_version ?? "—")}
                </p>
                <p className="mt-1 font-mono text-xs text-stone-600">
                  {String(edge.source_entity_id ?? edge.source_handle_id ?? "—")} →{" "}
                  {String(edge.target_entity_id ?? edge.target ?? "—")}
                </p>
                {edge.promoted_from_candidate_id ? (
                  <p className="mt-1 text-xs text-stone-500">
                    Promoted from candidate {String(edge.promoted_from_candidate_id)}
                  </p>
                ) : null}
                <Link
                  to={`/admin/tenants/${tenantId}/cortex/inspect/identity/e/${String(edge.source_entity_id ?? edge.source_handle_id ?? "")}`}
                  className="mt-2 inline-block text-xs font-medium text-indigo-700 no-underline hover:underline"
                >
                  Inspect source entity →
                </Link>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <DeployInfoFooter />
    </div>
  );
}

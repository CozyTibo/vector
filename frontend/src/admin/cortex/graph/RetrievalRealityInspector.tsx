import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "../../ui/StatusBadge";
import type { GraphTruthInspectorPayload } from "./graphInspectorTypes";

type Props = {
  data: GraphTruthInspectorPayload | undefined;
};

function pctTone(sev: string | undefined): "ok" | "warn" | "bad" {
  if (sev === "ok") return "ok";
  if (sev === "bad") return "bad";
  return "warn";
}

export function RetrievalRealityInspector({ data }: Props) {
  const retrieval = data?.retrieval;
  const laws = data?.product_laws ?? {};
  const orgPct = retrieval?.org_link_pct;
  const execPct = retrieval?.execution_index_pct;
  const kinds = retrieval?.index_kind_counts ?? [];

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-indigo-200 bg-indigo-50 p-4 text-sm text-indigo-950">
        <p className="font-medium">Phase G3 — retrieval reality inspector</p>
        <p className="mt-1 text-indigo-900">
          Inspect what entered retrieval — composition, omissions, and exclusion reasons. Hard laws:
          org_link mirrors ≤{laws.retrieval_org_link_pct_max ?? 30}%, execution-state entries ≥
          {laws.retrieval_execution_index_pct_min ?? 60}%.
        </p>
      </section>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Published epoch" value={retrieval?.published_index_epoch ?? "—"} mono />
        <Metric label="Entry count" value={(retrieval?.entry_count ?? 0).toLocaleString()} />
        <Metric
          label="org_link %"
          value={
            <span className="flex items-center gap-2">
              {orgPct ?? "—"}%
              <StatusBadge tone={pctTone(retrieval?.org_link_pct_severity)}>
                {retrieval?.org_link_pct_severity ?? "unknown"}
              </StatusBadge>
            </span>
          }
        />
        <Metric
          label="Execution index %"
          value={
            <span className="flex items-center gap-2">
              {execPct ?? "—"}%
              <StatusBadge tone={pctTone(retrieval?.execution_index_pct_severity)}>
                {retrieval?.execution_index_pct_severity ?? "unknown"}
              </StatusBadge>
            </span>
          }
        />
      </section>

      {kinds.length > 0 ? (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-stone-900">Retrieval composition by index kind</h3>
          <div className="mt-3 overflow-x-auto rounded-lg border border-stone-200">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b bg-stone-50 text-xs uppercase text-stone-500">
                <tr>
                  <th className="px-3 py-2">index_kind</th>
                  <th className="px-3 py-2">count</th>
                  <th className="px-3 py-2">% of epoch</th>
                </tr>
              </thead>
              <tbody>
                {kinds.map((row: Record<string, unknown>) => {
                  const count = Number(row.count ?? row.n ?? 0);
                  const total = retrieval?.entry_count ?? 0;
                  const pct = total > 0 ? Math.round((100 * count) / total) : 0;
                  const kind = String(row.index_kind ?? "—");
                  return (
                    <tr key={kind} className="border-b border-stone-100">
                      <td className="px-3 py-2 font-mono text-xs">{kind}</td>
                      <td className="px-3 py-2 tabular-nums">{count.toLocaleString()}</td>
                      <td className="px-3 py-2 tabular-nums">{pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700">
        <p>
          Freshness: {retrieval?.freshness_minutes ?? "—"} minutes since publish. Per-epoch omission
          receipts and island-scoped composition materialization ship in G3 — see{" "}
          <Link className="font-medium text-indigo-700 underline" to="../retrieval">
            Retrieval tab
          </Link>{" "}
          for coverage until then.
        </p>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase text-stone-500">{label}</p>
      <div className={["mt-1 text-lg font-semibold tabular-nums", mono ? "font-mono text-sm" : ""].join(" ")}>
        {value}
      </div>
    </div>
  );
}

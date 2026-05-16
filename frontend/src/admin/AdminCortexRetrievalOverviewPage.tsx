import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { StatusBadge } from "./ui/StatusBadge";

type Coverage = {
  indexed_count: number;
  replay_safe_count: number;
  coverage_percent: number;
};

type Legality = {
  retrieval_policy_digest: string;
  legality_classes: string[];
};

export default function AdminCortexRetrievalOverviewPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const coverage = useQuery({
    queryKey: ["retrieval-coverage", tenantId],
    queryFn: () => adminJson<Coverage>(`/admin/tenants/${tenantId}/cortex/retrieval/coverage`),
  });
  const legality = useQuery({
    queryKey: ["retrieval-legality", tenantId],
    queryFn: () => adminJson<Legality>(`/admin/tenants/${tenantId}/cortex/retrieval/legality`),
  });

  const c = coverage.data;
  const l = legality.data;

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Replay-safe retrieval coverage</h2>
        {coverage.isLoading && <p className="mt-2 text-sm text-stone-500">Loading…</p>}
        {c && (
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-stone-500">Indexed lawful artifacts</dt>
              <dd className="text-2xl font-semibold">{c.indexed_count}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Replay-safe</dt>
              <dd className="text-2xl font-semibold text-emerald-800">{c.replay_safe_count}</dd>
            </div>
            <div>
              <dt className="text-stone-500">Coverage</dt>
              <dd className="text-2xl font-semibold">{c.coverage_percent}%</dd>
            </div>
          </dl>
        )}
      </section>
      {l && (
        <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h3 className="font-semibold text-stone-900">Retrieval policy</h3>
          <p className="mt-1 font-mono text-xs text-stone-600">{l.retrieval_policy_digest}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {l.legality_classes.map((cls) => (
              <StatusBadge key={cls} tone={cls.includes("safe") ? "ok" : "warn"}>
                {cls}
              </StatusBadge>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

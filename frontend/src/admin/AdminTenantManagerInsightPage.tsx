import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type ReliabilityTier = "high" | "medium" | "low";

type ConnectorReliabilityDetail = {
  tier: ReliabilityTier;
  reasons: string[];
};

type DataReliabilityReport = {
  slack: ConnectorReliabilityDetail;
  github: ConnectorReliabilityDetail;
  linear: ConnectorReliabilityDetail;
  notion: ConnectorReliabilityDetail;
  calls: ConnectorReliabilityDetail;
  overall_confidence: ReliabilityTier;
};

type ConnectorFetchResult = {
  connector: string;
  status: string;
  fetched_at: string | null;
  window_start: string;
  window_end: string;
  caps_applied: string[];
  errors: string[];
  payload: Record<string, unknown>;
};

type FetchActivityBundle = {
  run_id: string;
  tenant_id: string;
  window_days: number;
  connectors: Record<string, ConnectorFetchResult>;
};

type ManagerInsightFetchDebugResponse = {
  fetch: FetchActivityBundle;
  data_reliability: DataReliabilityReport;
};

function tierBadge(tier: ReliabilityTier) {
  const cls =
    tier === "high"
      ? "bg-emerald-50 text-emerald-900 ring-emerald-200"
      : tier === "medium"
        ? "bg-amber-50 text-amber-950 ring-amber-200"
        : "bg-rose-50 text-rose-900 ring-rose-200";
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${cls}`}>
      {tier}
    </span>
  );
}

export default function AdminTenantManagerInsightPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();

  const q = useQuery({
    queryKey: ["admin-manager-insight-fetch", tenantId],
    queryFn: () =>
      adminJson<ManagerInsightFetchDebugResponse>(
        `/admin/tenants/${tenantId}/manager-insight/fetch-debug?window_days=30`,
      ),
    enabled: Boolean(tenantId),
  });

  if (!tenantId) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-stone-900">Manager insight</h1>
        <p className="mt-1 text-sm text-stone-600">
          Step 1 (FetchActivity) + Step 0.5 (data reliability). Re-fetch to see live connector
          probes for this tenant.
        </p>
      </div>

      {q.isLoading ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-rose-700" role="alert">
          {(q.error as Error).message}
        </p>
      ) : null}

      {q.data ? (
        <div className="space-y-6">
          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Data reliability (Step 0.5)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Overall: {tierBadge(q.data.data_reliability.overall_confidence)}
            </p>
            <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {(
                ["slack", "github", "linear", "notion", "calls"] as const
              ).map((key) => {
                const d = q.data.data_reliability[key];
                return (
                  <li
                    key={key}
                    className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-sm"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium capitalize text-stone-800">{key}</span>
                      {tierBadge(d.tier)}
                    </div>
                    {d.reasons.length ? (
                      <ul className="mt-1 list-inside list-disc text-xs text-stone-600">
                        {d.reasons.map((r) => (
                          <li key={r}>{r}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">FetchActivity (Step 1)</h2>
            <p className="mt-1 font-mono text-xs text-stone-500">run_id: {q.data.fetch.run_id}</p>
            <div className="mt-4 space-y-4">
              {Object.values(q.data.fetch.connectors).map((c) => (
                <details
                  key={c.connector}
                  className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2"
                >
                  <summary className="cursor-pointer text-sm font-medium text-stone-800">
                    {c.connector}{" "}
                    <span className="font-normal text-stone-500">({c.status})</span>
                  </summary>
                  <dl className="mt-2 grid gap-1 text-xs text-stone-600">
                    <div>
                      <dt className="font-medium text-stone-700">fetched_at</dt>
                      <dd className="font-mono">{c.fetched_at ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-stone-700">window</dt>
                      <dd className="font-mono">
                        {c.window_start} → {c.window_end}
                      </dd>
                    </div>
                    {c.caps_applied.length ? (
                      <div>
                        <dt className="font-medium text-stone-700">caps_applied</dt>
                        <dd>{c.caps_applied.join(", ")}</dd>
                      </div>
                    ) : null}
                    {c.errors.length ? (
                      <div>
                        <dt className="font-medium text-rose-800">errors</dt>
                        <dd className="text-rose-800">{c.errors.join(" · ")}</dd>
                      </div>
                    ) : null}
                  </dl>
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-stone-900/90 p-2 text-xs text-stone-100">
                    {JSON.stringify(c.payload, null, 2)}
                  </pre>
                </details>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}

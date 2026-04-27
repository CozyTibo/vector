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
  coverage?: Record<string, number>;
  completeness?: Record<string, number>;
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
  work_items: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      source: string;
      type: string;
      title: string;
      summary: string | null;
      status: string | null;
      url: string | null;
      project: string | null;
      owner: string | null;
      participants: string[];
      created_at: string | null;
      updated_at: string | null;
      closed_at: string | null;
      source_ref: Record<string, string>;
    }>;
  };
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
    enabled: false,
  });

  if (!tenantId) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-stone-900">Manager insight</h1>
        <p className="mt-1 text-sm text-stone-600">
          Step 1 (FetchActivity) + Step 0.5 (data reliability) + Step 2 (WorkItem normalization).
          Click run to fetch live connector probes and deterministic normalized work items.
        </p>
        <div className="mt-3">
          <button
            type="button"
            className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-900 hover:bg-blue-100 disabled:opacity-50"
            disabled={q.isFetching}
            onClick={() => {
              void q.refetch();
            }}
          >
            {q.isFetching ? "Running…" : "Run Step 1 → 0.5 → 2"}
          </button>
        </div>
      </div>

      {q.isLoading ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-rose-700" role="alert">
          {(q.error as Error).message}
        </p>
      ) : null}
      {!q.data && !q.isFetching && !q.isError ? (
        <p className="text-sm text-stone-600">
          No run yet. Click <span className="font-medium">Run Step 1 → 0.5 → 2</span> to fetch and
          display results.
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
                    {c.coverage ? (
                      <div>
                        <dt className="font-medium text-stone-700">coverage</dt>
                        <dd className="font-mono">{JSON.stringify(c.coverage)}</dd>
                      </div>
                    ) : null}
                    {c.completeness ? (
                      <div>
                        <dt className="font-medium text-stone-700">completeness</dt>
                        <dd className="font-mono">{JSON.stringify(c.completeness)}</dd>
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

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">WorkItems (Step 2)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Normalized items: {q.data.work_items.items.length} · run_id {q.data.work_items.run_id}
            </p>
            <div className="mt-4 space-y-3">
              {q.data.work_items.items.length === 0 ? (
                <p className="text-xs text-stone-500">
                  No normalized work items produced from current fetch payloads.
                </p>
              ) : null}
              {q.data.work_items.items.map((item) => (
                <details
                  key={item.id}
                  className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2"
                >
                  <summary className="cursor-pointer text-sm font-medium text-stone-800">
                    {item.title}{" "}
                    <span className="font-normal text-stone-500">
                      ({item.source} / {item.type})
                    </span>
                  </summary>
                  <dl className="mt-2 grid gap-1 text-xs text-stone-600">
                    <div>
                      <dt className="font-medium text-stone-700">id</dt>
                      <dd className="font-mono">{item.id}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-stone-700">status</dt>
                      <dd>{item.status ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-stone-700">summary</dt>
                      <dd>{item.summary ?? "—"}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-stone-700">updated_at</dt>
                      <dd className="font-mono">{item.updated_at ?? "—"}</dd>
                    </div>
                  </dl>
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-stone-900/90 p-2 text-xs text-stone-100">
                    {JSON.stringify(item, null, 2)}
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

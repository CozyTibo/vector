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
  evidence: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    discarded_without_evidence: number;
    action_items: Array<{
      id: string;
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: string;
      source_type: string;
      source_ref: Record<string, string>;
    }>;
    blockers: Array<{
      id: string;
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: string;
      source_type: string;
      source_ref: Record<string, string>;
    }>;
    decisions: Array<{
      id: string;
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: string;
      source_type: string;
      source_ref: Record<string, string>;
    }>;
  };
  links: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    work_items_capped: number;
    links: Array<{
      id: string;
      from_work_item_id: string;
      to_work_item_id: string;
      link_type: string;
      confidence: ReliabilityTier;
      similarity: number;
      method: string;
      evidence: string;
    }>;
  };
  gaps: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    gaps: Array<{
      id: string;
      type: string;
      description: string;
      evidence_pointers: Record<string, string[]>;
    }>;
  };
  key_achievements: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      title: string;
      linked_items: string[];
      evidence: string[];
      sort_at: string | null;
    }>;
  };
  raw_highlights: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      text: string;
      sources: string[];
    }>;
  };
  signals: {
    delivery_strength: "low" | "moderate" | "high";
    urgent_pressure: "low" | "moderate" | "high";
    expectation_coverage: "high" | "partial" | "low";
    follow_through: "strong" | "partial" | "weak";
    blocker_visibility: "visible" | "partial" | "not_visible";
    repeated_discussion_present: boolean;
    execution_momentum: "accelerating" | "steady" | "slowing";
    documentation_linkage: "linked" | "partially_linked" | "not_linked";
    focus: "focused" | "moderate" | "fragmented";
    collaboration_intensity: "low" | "moderate" | "high";
    support_pattern: "gives_help" | "asks_for_help" | "balanced";
    feedback_reception: "proactive" | "neutral" | "defensive";
    coordination_role: "driving" | "contributing" | "peripheral";
    interaction_friction: "present" | "unclear" | "absent";
    explain: Record<string, string>;
  };
  interpretations: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    generated_via: "llm" | "fallback";
    fallback_reason: string | null;
    model: string | null;
    latency_ms: number | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    llm_response_text: string | null;
    llm_response_truncated: boolean;
    llm_parsed_interpretation_rows: number | null;
    rejected_interpretations: Array<{
      index: number;
      reason: string;
      raw: Record<string, unknown>;
    }>;
    llm_error: string | null;
    items: Array<{
      id: string;
      type: string;
      description: string;
      based_on_signals: string[];
      evidence: string[];
      based_on_gaps: string[];
      based_on_blockers: string[];
      based_on_highlights: string[];
      confidence: "high" | "medium" | "low";
    }>;
  };
  insights: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    generated_via: "llm" | "fallback";
    fallback_reason: string | null;
    model: string | null;
    latency_ms: number | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    llm_response_text: string | null;
    llm_response_truncated: boolean;
    llm_parsed_insight_rows: number | null;
    rejected_insights: Array<{
      index: number;
      reason: string;
      raw: Record<string, unknown>;
    }>;
    llm_error: string | null;
    items: Array<{
      id: string;
      observation: string;
      interpretation: string;
      implication: string;
      evidence: string[];
      evidence_ids: string[];
      based_on_interpretations: string[];
      based_on_signals: string[];
      primary_work_item_ids: string[];
      supporting_work_item_ids: string[];
      primary_entities: Array<{ name: string; kind: "project" | "feature" | "system" }>;
      based_on_gaps: string[];
      based_on_blockers: string[];
      based_on_highlights: string[];
      confidence: "high" | "medium" | "low";
      priority: "critical" | "high" | "medium" | "low";
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
          Step 1 (Fetch) + 0.5 (reliability) + 2 (WorkItems) + 3 (Evidence) + 4 (Links) + 5 (Gaps) +
          5.5 (Key achievements) + 5.6 (Raw highlights) + 6 (Signals) + 7 (Interpretations) + 8
          (Insights). Click run to fetch and inspect each stage.
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
            {q.isFetching
              ? "Running…"
              : "Run Step 1 → 0.5 → 2 → 3 → 4 → 5 → 5.5 → 5.6 → 6 → 7 → 8"}
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
          No run yet. Click{" "}
          <span className="font-medium">
            Run Step 1 → 0.5 → 2 → 3 → 4 → 5 → 5.5 → 5.6 → 6 → 7 → 8
          </span>{" "}
          to fetch and display results.
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

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Evidence extraction (Step 3)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Action items: {q.data.evidence.action_items.length} · Blockers:{" "}
              {q.data.evidence.blockers.length} · Decisions: {q.data.evidence.decisions.length} ·
              Discarded (no verifiable quote): {q.data.evidence.discarded_without_evidence}
            </p>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              {(
                [
                  ["Action items", q.data.evidence.action_items],
                  ["Blockers", q.data.evidence.blockers],
                  ["Decisions", q.data.evidence.decisions],
                ] as const
              ).map(([label, rows]) => (
                <div key={label} className="rounded-md border border-stone-100 bg-stone-50 p-3">
                  <h3 className="text-sm font-semibold text-stone-800">{label}</h3>
                  {rows.length === 0 ? (
                    <p className="mt-2 text-xs text-stone-500">No items extracted.</p>
                  ) : (
                    <ul className="mt-2 space-y-2">
                      {rows.map((row) => (
                        <li key={row.id} className="rounded border border-stone-200 bg-white p-2 text-xs">
                          <p className="font-medium text-stone-800">{row.statement}</p>
                          <p className="mt-1 text-stone-600">Quote: "{row.evidence}"</p>
                          <p className="mt-1 font-mono text-stone-500">{row.source_work_item_id}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Semantic links (Step 4)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Best-effort edges (not ground truth). High: {q.data.links.links.filter((L) => L.confidence === "high").length} ·
              medium: {q.data.links.links.filter((L) => L.confidence === "medium").length} · low:{" "}
              {q.data.links.links.filter((L) => L.confidence === "low").length} · run_id {q.data.links.run_id}
              {q.data.links.work_items_capped > 0 ? (
                <span>
                  {" "}
                  · linking capped to first {q.data.links.work_items_capped} work items (by id) for
                  cost bounds
                </span>
              ) : null}
            </p>
            {q.data.links.links.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">
                No links above the minimum similarity floor. Add more overlapping titles or shared
                issue keys (e.g. NEX-12) across tools.
              </p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.links.links.map((L) => (
                  <li
                    key={L.id}
                    className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs"
                  >
                    <div className="flex flex-wrap items-center gap-2 text-stone-800">
                      <span className="font-mono">{L.from_work_item_id}</span>
                      <span className="text-stone-400">→</span>
                      <span className="font-mono">{L.to_work_item_id}</span>
                      <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-[10px] uppercase text-stone-600">
                        {L.link_type.replace("_", " ")}
                      </span>
                      {tierBadge(L.confidence)}
                      <span className="text-stone-500">sim {L.similarity.toFixed(3)}</span>
                    </div>
                    <p className="mt-1 text-stone-600">{L.evidence}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-stone-400">{L.method}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Gaps (Step 5)</h2>
            <p className="mt-1 text-xs text-stone-500">
              expected_not_executed:{" "}
              {q.data.gaps.gaps.filter((g) => g.type === "expected_not_executed").length} ·
              discussed_not_linked_to_work:{" "}
              {q.data.gaps.gaps.filter((g) => g.type === "discussed_not_linked_to_work").length} ·
              blocker_not_tracked:{" "}
              {q.data.gaps.gaps.filter((g) => g.type === "blocker_not_tracked").length} ·
              doc_not_connected_to_execution:{" "}
              {q.data.gaps.gaps.filter((g) => g.type === "doc_not_connected_to_execution").length} ·
              run_id {q.data.gaps.run_id}
            </p>
            {q.data.gaps.gaps.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">
                No deterministic gaps found from current work items, evidence, and links.
              </p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.gaps.gaps.map((g) => (
                  <li key={g.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2 text-stone-800">
                      <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-[10px] uppercase text-stone-600">
                        {g.type.replace(/_/g, " ")}
                      </span>
                      <span className="font-mono text-stone-500">{g.id}</span>
                    </div>
                    <p className="mt-1 text-stone-700">{g.description}</p>
                    <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                      {JSON.stringify(g.evidence_pointers, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Key achievements (Step 5.5)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Closed issues + merged/closed PRs (deterministic). Count: {q.data.key_achievements.items.length}{" "}
              · run_id {q.data.key_achievements.run_id}
            </p>
            {q.data.key_achievements.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No closed/merged execution items in window.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.key_achievements.items.map((k) => (
                  <li key={k.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="font-medium text-stone-800">{k.title}</p>
                    <p className="mt-0.5 font-mono text-[10px] text-stone-500">{k.id}</p>
                    <p className="mt-1 text-stone-600">Linked: {k.linked_items.join(", ")}</p>
                    <ul className="mt-1 list-inside list-disc text-stone-600">
                      {k.evidence.map((e) => (
                        <li key={e} className="text-[11px]">
                          {e}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Raw highlights (Step 5.6)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Factual lines only. Count: {q.data.raw_highlights.items.length} · run_id{" "}
              {q.data.raw_highlights.run_id}
            </p>
            {q.data.raw_highlights.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No raw highlights for this run.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.raw_highlights.items.map((h) => (
                  <li key={h.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="text-stone-800">{h.text}</p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">sources: {h.sources.join(", ")}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Signals (Step 6)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Deterministic state vector computed from Steps 2–5.6. Includes explain strings for
              operator QA.
            </p>
            <ul className="mt-3 grid gap-2 sm:grid-cols-2">
              {(
                [
                  ["delivery_strength", q.data.signals.delivery_strength],
                  ["urgent_pressure", q.data.signals.urgent_pressure],
                  ["expectation_coverage", q.data.signals.expectation_coverage],
                  ["follow_through", q.data.signals.follow_through],
                  ["blocker_visibility", q.data.signals.blocker_visibility],
                  ["repeated_discussion_present", String(q.data.signals.repeated_discussion_present)],
                  ["execution_momentum", q.data.signals.execution_momentum],
                  ["documentation_linkage", q.data.signals.documentation_linkage],
                  ["focus", q.data.signals.focus],
                  ["collaboration_intensity", q.data.signals.collaboration_intensity],
                  ["support_pattern", q.data.signals.support_pattern],
                  ["feedback_reception", q.data.signals.feedback_reception],
                  ["coordination_role", q.data.signals.coordination_role],
                  ["interaction_friction", q.data.signals.interaction_friction],
                ] as const
              ).map(([key, value]) => (
                <li key={key} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                  <p className="font-mono text-stone-700">{key}</p>
                  <p className="mt-0.5 text-sm font-semibold text-stone-900">{value}</p>
                  <p className="mt-1 text-stone-600">{q.data.signals.explain[key] ?? "—"}</p>
                </li>
              ))}
            </ul>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Interpretations (Step 7)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Count: {q.data.interpretations.items.length} · generated_via{" "}
              {q.data.interpretations.generated_via}
              {q.data.interpretations.generated_via === "fallback" &&
              q.data.interpretations.fallback_reason
                ? ` (${q.data.interpretations.fallback_reason})`
                : ""}
              {q.data.interpretations.model ? ` · model ${q.data.interpretations.model}` : ""}
              {q.data.interpretations.latency_ms !== null
                ? ` · latency ${q.data.interpretations.latency_ms}ms`
                : ""}
            </p>
            {q.data.interpretations.llm_parsed_interpretation_rows !== null ? (
              <p className="mt-1 text-xs text-stone-500">
                LLM JSON rows (dict objects) parsed: {q.data.interpretations.llm_parsed_interpretation_rows} ·
                rejected rows: {q.data.interpretations.rejected_interpretations.length}
                {q.data.interpretations.llm_response_truncated ? " · llm_response_text truncated" : ""}
              </p>
            ) : null}
            {q.data.interpretations.llm_error ? (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                LLM issue: {q.data.interpretations.llm_error}
              </p>
            ) : null}
            {q.data.interpretations.llm_response_text ||
            q.data.interpretations.rejected_interpretations.length > 0 ? (
              <details className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3">
                <summary className="cursor-pointer text-xs font-semibold text-stone-900">
                  Rejected / raw LLM output (debug)
                </summary>
                {q.data.interpretations.rejected_interpretations.length > 0 ? (
                  <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
                    {q.data.interpretations.rejected_interpretations.map((r) => (
                      <li key={r.index} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-xs">
                        <p className="font-mono text-[10px] text-stone-500">row_index={r.index}</p>
                        <p className="mt-1 text-stone-800">{r.reason}</p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                          {JSON.stringify(r.raw, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-stone-500">No per-row rejections recorded.</p>
                )}
                {q.data.interpretations.llm_response_text ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-900">Raw assistant text</p>
                    <pre className="mt-2 max-h-72 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                      {q.data.interpretations.llm_response_text}
                    </pre>
                  </div>
                ) : null}
              </details>
            ) : null}
            {q.data.interpretations.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No interpretations produced.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.interpretations.items.map((it) => (
                  <li key={it.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="font-medium text-stone-900">
                      {it.type.replace(/_/g, " ")} · {it.confidence}
                    </p>
                    <p className="mt-1 text-stone-700">{it.description}</p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_gaps: {it.based_on_gaps.join(", ") || "—"} · based_on_blockers:{" "}
                      {it.based_on_blockers.join(", ") || "—"} · based_on_highlights:{" "}
                      {it.based_on_highlights.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_signals: {it.based_on_signals.join(", ") || "—"}
                    </p>
                    <ul className="mt-1 list-inside list-disc text-stone-600">
                      {it.evidence.map((ev) => (
                        <li key={ev} className="text-[11px]">
                          {ev}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">Insights (Step 8)</h2>
            <p className="mt-1 text-xs text-stone-500">
              Count: {q.data.insights.items.length} · generated_via {q.data.insights.generated_via}
              {q.data.insights.generated_via === "fallback" && q.data.insights.fallback_reason
                ? ` (${q.data.insights.fallback_reason})`
                : ""}
              {q.data.insights.model ? ` · model ${q.data.insights.model}` : ""}
              {q.data.insights.latency_ms !== null ? ` · latency ${q.data.insights.latency_ms}ms` : ""}
            </p>
            {q.data.insights.llm_parsed_insight_rows !== null ? (
              <p className="mt-1 text-xs text-stone-500">
                LLM JSON rows (dict objects) parsed: {q.data.insights.llm_parsed_insight_rows} · rejected
                rows: {q.data.insights.rejected_insights.length}
                {q.data.insights.llm_response_truncated ? " · llm_response_text truncated" : ""}
              </p>
            ) : null}
            {q.data.insights.llm_error ? (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                LLM issue: {q.data.insights.llm_error}
              </p>
            ) : null}
            {q.data.insights.llm_response_text || q.data.insights.rejected_insights.length > 0 ? (
              <details className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3">
                <summary className="cursor-pointer text-xs font-semibold text-stone-900">
                  Rejected / raw LLM output (debug)
                </summary>
                {q.data.insights.rejected_insights.length > 0 ? (
                  <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
                    {q.data.insights.rejected_insights.map((r) => (
                      <li key={r.index} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-xs">
                        <p className="font-mono text-[10px] text-stone-500">row_index={r.index}</p>
                        <p className="mt-1 text-stone-800">{r.reason}</p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                          {JSON.stringify(r.raw, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-stone-500">No per-row rejections recorded.</p>
                )}
                {q.data.insights.llm_response_text ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-900">Raw assistant text</p>
                    <pre className="mt-2 max-h-72 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                      {q.data.insights.llm_response_text}
                    </pre>
                  </div>
                ) : null}
              </details>
            ) : null}
            {q.data.insights.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No insights produced.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.insights.items.map((it) => (
                  <li key={it.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="font-medium text-stone-900">
                      priority {it.priority} · confidence {it.confidence}
                    </p>
                    <p className="mt-1 text-stone-800">
                      <span className="font-semibold">Observation:</span> {it.observation}
                    </p>
                    <p className="mt-1 text-stone-700">
                      <span className="font-semibold">Interpretation:</span> {it.interpretation}
                    </p>
                    <p className="mt-1 text-stone-700">
                      <span className="font-semibold">Implication:</span> {it.implication}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_gaps: {it.based_on_gaps.join(", ") || "—"} · based_on_blockers:{" "}
                      {it.based_on_blockers.join(", ") || "—"} · based_on_highlights:{" "}
                      {it.based_on_highlights.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      evidence_ids: {it.evidence_ids.join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      primary_work_item_ids: {it.primary_work_item_ids.join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      supporting_work_item_ids: {it.supporting_work_item_ids.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      primary_entities:{" "}
                      {it.primary_entities.map((e) => `${e.name} (${e.kind})`).join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_interpretations: {it.based_on_interpretations.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_signals: {it.based_on_signals.join(", ")}
                    </p>
                    <ul className="mt-1 list-inside list-disc text-stone-600">
                      {it.evidence.map((ev) => (
                        <li key={ev} className="text-[11px]">
                          {ev}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

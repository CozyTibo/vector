import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { formatRelativeAge } from "./cortexAdminTypes";
import { CompactTable } from "./canonical/operatorUi";
import { StatusBadge } from "./ui/StatusBadge.tsx";

type FailureCase = {
  gap_id: string;
  failure_class: string;
  degradation_state: string;
  scope_kind: string;
  scope_json: Record<string, unknown>;
  detail_json: Record<string, unknown>;
  source: string;
  created_at?: string | null;
  updated_at?: string | null;
};

type FailuresPayload = {
  failure_remediation_runtime_schema_version: number;
  tenant_id: string;
  active_failure_count: number;
  active_failure_classes: Record<string, number>;
  cases: FailureCase[];
};

const FAILURE_FEED_TAIL = 250;

type GroupKey = string;

function errorMessage(c: FailureCase): string {
  const m = c.detail_json?.message;
  return typeof m === "string" && m.trim() ? m.trim() : "(no detail_json.message)";
}

function groupKey(c: FailureCase): GroupKey {
  const msg = errorMessage(c);
  return `${c.failure_class}::${c.scope_kind}::${c.source}::${msg}`;
}

function pickConnector(c: FailureCase): string {
  const s = c.scope_json ?? {};
  const d = c.detail_json ?? {};
  const fromScope = typeof s.connector === "string" ? s.connector.trim() : "";
  if (fromScope) return fromScope;
  const fromDetail = typeof d.connector === "string" ? d.connector.trim() : "";
  if (fromDetail) return fromDetail;
  const msg = typeof d.message === "string" ? d.message : "";
  for (const prefix of ["github", "slack", "linear", "notion", "calls"]) {
    if (msg.toLowerCase().includes(prefix)) return prefix;
  }
  return "—";
}

function pickResourceType(c: FailureCase): string {
  const s = c.scope_json ?? {};
  const rt = typeof s.resource_type === "string" ? s.resource_type.trim() : "";
  return rt || "—";
}

function materializeOperatorHint(message: string): string | null {
  const hints: Record<string, string> = {
    workflow_run_missing_repository_provider_id:
      "Raw GitHub workflow_run payload lacked repository metadata. Re-run materialize backlog after upgrading mocks / runtime, or re-sync GitHub so payloads include repository.",
    execution_check_missing_repository_provider_id:
      "Check run payload missing repository; confirm mock or REST payload includes repository or external_id with repo prefix.",
    execution_check_completed_status_missing_conclusion:
      "GitHub requires conclusion when status is completed; fix mock or source API row.",
    no_transform_route:
      "No transform route registered for this connector/resource_type pair — extend transform_routing_registry.",
    unknown_bundle:
      "Bundle id not found or not eligible for transform — check mapping pins / bundle lifecycle.",
    raw_record_not_found:
      "Raw row was deleted or wrong tenant — verify raw_record_id.",
  };
  for (const [prefix, hint] of Object.entries(hints)) {
    if (message === prefix || message.startsWith(`${prefix}:`)) return hint;
  }
  return null;
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

export default function AdminCortexCanonicalFailuresPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const base = `/admin/tenants/${tenantId}/cortex/canonical`;
  const [open, setOpen] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["admin-cortex-canonical-failures", tenantId],
    queryFn: () => adminJson<FailuresPayload>(`/admin/tenants/${tenantId}/cortex/canonical/failures`),
    enabled: Boolean(tenantId),
  });

  const groups = useMemo(() => {
    const cases = q.data?.cases ?? [];
    const m = new Map<
      GroupKey,
      {
        key: GroupKey;
        cases: FailureCase[];
        failure_class: string;
        scope_kind: string;
        source: string;
        message: string;
      }
    >();
    for (const c of cases) {
      const k = groupKey(c);
      const msg = errorMessage(c);
      let g = m.get(k);
      if (!g) {
        g = { key: k, cases: [], failure_class: c.failure_class, scope_kind: c.scope_kind, source: c.source, message: msg };
        m.set(k, g);
      }
      g.cases.push(c);
    }
    return [...m.values()].sort((a, b) => b.cases.length - a.cases.length);
  }, [q.data?.cases]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (q.isPending) return <p className="text-sm text-stone-600">Loading failures…</p>;
  if (q.isError) return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;

  const atTailCap = (q.data.cases?.length ?? 0) >= FAILURE_FEED_TAIL;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Active failures</h2>
            <p className="mt-1 text-sm text-stone-600">
              Grouped by failure class, scope, source, and error message. Each row lists up to {FAILURE_FEED_TAIL}{" "}
              most recently updated cases (tail of the registry). Full JSON remediation flows stay under{" "}
              <Link className="font-medium text-indigo-700 hover:underline" to={`${base}/advanced/debug`}>
                Advanced → Debug
              </Link>
              .
            </p>
            {atTailCap ? (
              <p className="mt-2 text-xs font-medium text-amber-800">
                Showing the latest {FAILURE_FEED_TAIL} cases by recency. If Health still reports a higher active count,
                older rows are not in this list — resolve visible cases first, or query the API with a higher limit later.
              </p>
            ) : null}
          </div>
          <StatusBadge tone={q.data.active_failure_count > 0 ? "bad" : "ok"}>
            {q.data.active_failure_count} in feed
          </StatusBadge>
        </div>
      </section>

      {groups.length === 0 ? (
        <p className="text-sm text-stone-600">No active failure cases.</p>
      ) : (
        <ul className="space-y-3">
          {groups.map((g) => {
            const sample = g.cases[0];
            const expanded = open === g.key;
            const conn = pickConnector(sample);
            const rt = pickResourceType(sample);
            const hint = materializeOperatorHint(g.message);
            return (
              <li key={g.key} className="rounded-xl border border-stone-200 bg-white shadow-sm">
                <button
                  type="button"
                  className="flex w-full flex-wrap items-center justify-between gap-2 px-4 py-3 text-left hover:bg-stone-50"
                  onClick={() => setOpen(expanded ? null : g.key)}
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-sm font-semibold text-stone-900">{g.failure_class}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-red-900/90">{g.message}</p>
                    <p className="mt-1 text-xs text-stone-600">
                      {g.scope_kind} · {g.source} ·{" "}
                      <span className="font-medium text-stone-800">
                        {conn} / {rt}
                      </span>
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="text-sm font-semibold tabular-nums text-stone-800">{g.cases.length} cases</span>
                    <span className="text-xs text-stone-500">{expanded ? "▼" : "▶"}</span>
                  </div>
                </button>
                {expanded ? (
                  <div className="space-y-4 border-t border-stone-100 px-4 py-3 text-sm">
                    {hint ? (
                      <div className="rounded-lg border border-indigo-100 bg-indigo-50/60 px-3 py-2 text-xs text-indigo-950">
                        <span className="font-semibold">Operator hint:</span> {hint}
                      </div>
                    ) : null}
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Cases in this group</p>
                      <div className="mt-2">
                        <CompactTable
                          columns={[
                            { key: "raw", label: "raw_record_id" },
                            { key: "conn", label: "connector" },
                            { key: "res", label: "resource_type" },
                            { key: "ext", label: "external_id" },
                            { key: "gap", label: "gap_id" },
                            { key: "when", label: "updated" },
                          ]}
                          rows={g.cases.map((c) => {
                            const sj = c.scope_json ?? {};
                            const rid = sj.raw_record_id;
                            const rawId = typeof rid === "number" ? String(rid) : typeof rid === "string" ? rid : "—";
                            const ext = typeof sj.external_id === "string" ? truncate(sj.external_id, 48) : "—";
                            return {
                              raw: rawId,
                              conn: pickConnector(c),
                              res: pickResourceType(c),
                              ext: <span className="font-mono text-[10px] text-stone-700">{ext}</span>,
                              gap: <span className="font-mono text-[10px] text-stone-600">{truncate(c.gap_id, 20)}</span>,
                              when: c.updated_at ? formatRelativeAge(c.updated_at) : c.created_at ? formatRelativeAge(c.created_at) : "—",
                            };
                          })}
                          empty="No rows."
                        />
                      </div>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Representative scope</p>
                      <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-stone-900/95 p-3 font-mono text-[11px] text-emerald-100">
                        {JSON.stringify(sample.scope_json, null, 2)}
                      </pre>
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-stone-500">Representative detail</p>
                      <pre className="mt-1 max-h-32 overflow-auto rounded-md bg-stone-900/95 p-3 font-mono text-[11px] text-emerald-100">
                        {JSON.stringify(sample.detail_json, null, 2)}
                      </pre>
                    </div>
                    <p className="text-xs text-stone-500">
                      Representative row last touched{" "}
                      {sample.updated_at
                        ? formatRelativeAge(sample.updated_at)
                        : sample.created_at
                          ? formatRelativeAge(sample.created_at)
                          : "—"}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        className="rounded-md bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-stone-800"
                        to={`${base}/advanced/debug`}
                      >
                        Open debug / remediation
                      </Link>
                      <Link
                        className="rounded-md border border-stone-300 px-3 py-1.5 text-xs font-semibold hover:bg-stone-50"
                        to={`${base}/advanced/runtime`}
                      >
                        Materialize tools
                      </Link>
                      <Link
                        className="rounded-md border border-stone-300 px-3 py-1.5 text-xs font-semibold hover:bg-stone-50"
                        to={`${base}/coverage`}
                      >
                        Connector coverage
                      </Link>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

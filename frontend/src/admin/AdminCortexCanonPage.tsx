import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import type { CanonPassRunItem, CanonReadiness } from "./cortexAdminTypes";
import CanonEntitiesTab from "./cortex/CanonEntitiesTab";
import { useCanonReadiness } from "./cortex/useCanonReadiness";
import { CortexPageSkeleton } from "./cortex/CortexPageSkeleton";

const TRIGGER_PHRASE = "RUN CANON MATERIALIZATION PASS";

type Tab = "overview" | "passes" | "entities";

export default function AdminCortexCanonPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [tab, setTab] = useState<Tab>("overview");
  const [confirm, setConfirm] = useState("");
  const qc = useQueryClient();
  const readinessQ = useCanonReadiness();
  const passesQ = useQuery({
    queryKey: ["admin-cortex-canon-passes", tenantId],
    queryFn: () =>
      adminJson<{ items: CanonPassRunItem[]; total_count: number }>(
        `/admin/tenants/${tenantId}/cortex/canon/recent-passes?limit=20`,
      ),
    enabled: Boolean(tenantId),
  });

  const triggerM = useMutation({
    mutationFn: async () => {
      const res = await adminFetch(
        `/admin/tenants/${tenantId}/cortex/canon/actions/trigger-pass`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ confirmation: confirm }),
        },
      );
      if (!res.ok) {
        const err = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new Error(err.detail ?? res.statusText);
      }
      return res.json();
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canon-readiness", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canon-passes", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canon-entities", tenantId] });
      setConfirm("");
    },
  });

  if (readinessQ.isLoading) {
    return <CortexPageSkeleton label="Loading canon readiness" />;
  }
  if (readinessQ.isError || !readinessQ.data) {
    return <p className="text-sm text-red-700">Failed to load canon readiness.</p>;
  }

  const data: CanonReadiness = readinessQ.data;
  const inv = data.raw_inventory;
  const lag = data.materialization_lag;
  const cls = data.resource_type_classification;

  return (
    <div className="space-y-6">
      <nav className="flex gap-2 border-b border-stone-200 pb-2">
        {(["overview", "passes", "entities"] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={
              tab === t
                ? "rounded-md bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-900"
                : "rounded-md px-3 py-1 text-sm text-stone-600 hover:bg-stone-100"
            }
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </nav>

      {tab === "overview" && (
        <>
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-stone-900">Canon readiness</h2>
            <p className="mt-1 text-sm text-stone-600">
              Mapper v{data.mapper_version} · scheduler{" "}
              {data.scheduler.enabled ? "on" : "off"} ({data.scheduler.interval_seconds}s)
            </p>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-xs font-medium uppercase text-stone-500">Live raw rows</dt>
                <dd className="text-lg font-semibold">{inv.total_live_rows}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase text-stone-500">Pending raw (est.)</dt>
                <dd className="text-lg font-semibold">{lag.pending_raw_rows_estimate}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase text-stone-500">Mapped types</dt>
                <dd className="text-lg font-semibold">{cls.mapped.length}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase text-stone-500">Dirty queue</dt>
                <dd className="text-lg font-semibold">{data.dirty_queue_depth}</dd>
              </div>
            </dl>
          </section>

          <section className="rounded-xl border border-amber-100 bg-amber-50 p-4">
            <h3 className="text-sm font-semibold text-amber-950">Trigger materialization pass</h3>
            <p className="mt-1 text-xs text-amber-900">
              Type exactly: <code className="font-mono">{TRIGGER_PHRASE}</code>
            </p>
            <div className="mt-2 flex flex-wrap gap-2">
              <input
                className="min-w-[280px] flex-1 rounded border border-amber-200 px-2 py-1 text-sm"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
              <button
                type="button"
                disabled={confirm !== TRIGGER_PHRASE || triggerM.isPending}
                onClick={() => triggerM.mutate()}
                className="rounded bg-indigo-600 px-3 py-1 text-sm text-white disabled:opacity-50"
              >
                {triggerM.isPending ? "Enqueueing…" : "Run pass"}
              </button>
            </div>
            {triggerM.isError ? (
              <p className="mt-2 text-xs text-red-700">{(triggerM.error as Error).message}</p>
            ) : null}
          </section>
        </>
      )}

      {tab === "passes" && (
        <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold">Recent passes</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {(passesQ.data?.items ?? []).length === 0 ? (
              <li className="text-stone-500">No canon passes yet.</li>
            ) : (
              passesQ.data?.items.map((p) => (
                <li key={p.id} className="rounded border border-stone-100 px-3 py-2">
                  <span className="font-medium">{p.status}</span>
                  <span className="text-stone-500"> · {p.source_trigger}</span>
                  {p.stats ? (
                    <span className="block text-xs text-stone-500">
                      materialized {String((p.stats as Record<string, unknown>).materialized ?? "?")}
                    </span>
                  ) : null}
                </li>
              ))
            )}
          </ul>
        </section>
      )}

      {tab === "entities" && <CanonEntitiesTab />}
    </div>
  );
}

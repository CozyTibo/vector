import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";
import { formatRelativeAge } from "./cortexAdminTypes";
import { CanonicalFilterToolbar, CompactTable, OperatorDrawer } from "./canonical/operatorUi";
import { matchesTimeRange, useCanonicalOperatorFilters } from "./canonical/operatorFilters";

type ReplayJobRow = {
  id: string;
  pinned_bundle_id: string;
  source_bundle_id?: string | null;
  job_kind: string;
  status: string;
  dry_run: boolean;
  scope_raw_record_ids: number[];
  summary_json: Record<string, unknown>;
  error_detail?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

type ReplayJobsListPayload = {
  tenant_id: string;
  jobs: ReplayJobRow[];
};

type ReplayJobDetailPayload = {
  job: ReplayJobRow;
};

export default function AdminCortexCanonicalReplayTabPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const { filters, setFilters } = useCanonicalOperatorFilters();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [replayRawIds, setReplayRawIds] = useState("");
  const [replayBundleId, setReplayBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [replayJobKind, setReplayJobKind] = useState<"rebuild" | "regeneration">("rebuild");
  const [replaySourceBundle, setReplaySourceBundle] = useState("");
  const [replayDryRun, setReplayDryRun] = useState(true);

  const qJobs = useQuery({
    queryKey: ["admin-cortex-replay-jobs-tab", tenantId],
    queryFn: () =>
      adminJson<ReplayJobsListPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/replay-jobs?limit=80`,
      ),
    enabled: Boolean(tenantId),
  });

  const replayRunMut = useMutation({
    mutationFn: async () => {
      const ids = replayRawIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      const body: Record<string, unknown> = {
        pinned_bundle_id: replayBundleId.trim(),
        job_kind: replayJobKind,
        raw_record_ids: ids,
        dry_run: replayDryRun,
      };
      const src = replaySourceBundle.trim();
      if (replayJobKind === "regeneration" && src) body.source_bundle_id = src;
      return adminJson<ReplayJobDetailPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/replay-jobs/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-cortex-replay-jobs-tab", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-canonical-control-plane", tenantId] });
      void qc.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
    },
  });

  const rows = useMemo(() => {
    const jobs = qJobs.data?.jobs ?? [];
    return jobs.filter((j) => {
      if (!matchesTimeRange(j.created_at, filters.timeRange)) return false;
      if (filters.bundle && !j.pinned_bundle_id.includes(filters.bundle)) return false;
      if (filters.status && j.status !== filters.status) return false;
      return true;
    });
  }, [qJobs.data?.jobs, filters]);

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-stone-900">Replay · Jobs</h2>
            <p className="mt-1 text-sm text-stone-600">
              Canonical replay jobs emit C0–C5 receipts; regeneration requires declared compatibility edges.
            </p>
          </div>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-800"
            onClick={() => setDrawerOpen(true)}
          >
            Start replay job…
          </button>
        </div>
      </section>

      <CanonicalFilterToolbar filters={filters} onChange={setFilters} />

      {qJobs.isPending ? (
        <p className="text-sm text-stone-600">Loading replay jobs…</p>
      ) : qJobs.isError ? (
        <p className="text-sm text-red-700">{(qJobs.error as Error).message}</p>
      ) : (
        <CompactTable
          columns={[
            { key: "id", label: "replay_job_id" },
            { key: "src", label: "source_bundle" },
            { key: "tgt", label: "target_bundle" },
            { key: "cls", label: "replay_class (summary)" },
            { key: "st", label: "status" },
            { key: "dur", label: "duration" },
            { key: "at", label: "created_at" },
          ]}
          rows={rows.map((j) => {
            const sj = j.summary_json || {};
            const counts = (sj.counts_by_divergence_class || {}) as Record<string, number>;
            const cls = Object.entries(counts)
              .map(([k, v]) => `${k}:${v}`)
              .join(", ");
            const started = j.started_at ? new Date(j.started_at).getTime() : NaN;
            const ended = j.completed_at ? new Date(j.completed_at).getTime() : NaN;
            const dur =
              Number.isFinite(started) && Number.isFinite(ended)
                ? `${Math.max(0, Math.round((ended - started) / 1000))}s`
                : j.status === "running"
                  ? "in flight"
                  : "—";
            return {
              id: j.id,
              src: j.source_bundle_id ?? "—",
              tgt: j.pinned_bundle_id,
              cls: cls || `${j.job_kind}${j.dry_run ? " · dry_run" : ""}`,
              st: j.status,
              dur,
              at: formatRelativeAge(j.created_at),
            };
          })}
        />
      )}

      <OperatorDrawer open={drawerOpen} title="Start replay job" onClose={() => setDrawerOpen(false)}>
        <div className="space-y-3 text-sm">
          <label className="block text-xs text-stone-600">
            raw_record_ids (comma / space)
            <textarea
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              rows={3}
              value={replayRawIds}
              onChange={(e) => setReplayRawIds(e.target.value)}
              placeholder="e.g. 101 102"
            />
          </label>
          <label className="block text-xs text-stone-600">
            pinned bundle_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={replayBundleId}
              onChange={(e) => setReplayBundleId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            job_kind
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 text-xs"
              value={replayJobKind}
              onChange={(e) => setReplayJobKind(e.target.value as "rebuild" | "regeneration")}
            >
              <option value="rebuild">rebuild</option>
              <option value="regeneration">regeneration</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            source_bundle_id (regeneration)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={replaySourceBundle}
              onChange={(e) => setReplaySourceBundle(e.target.value)}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={replayDryRun} onChange={(e) => setReplayDryRun(e.target.checked)} />
            dry_run (receipts only)
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            disabled={replayRunMut.isPending}
            onClick={() => replayRunMut.mutate()}
          >
            {replayRunMut.isPending ? "Running…" : "POST replay-jobs/run"}
          </button>
          {replayRunMut.isError ? (
            <p className="text-sm text-red-700">{(replayRunMut.error as Error).message}</p>
          ) : null}
          {replayRunMut.isSuccess ? (
            <pre className="max-h-48 overflow-auto rounded border bg-stone-50 p-2 font-mono text-[11px]">
              {JSON.stringify(replayRunMut.data.job, null, 2)}
            </pre>
          ) : null}
        </div>
      </OperatorDrawer>
    </div>
  );
}

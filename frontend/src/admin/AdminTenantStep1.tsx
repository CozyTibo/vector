import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { adminFetch, adminJson } from "../lib/adminFetch";
import { readErrorDetail } from "../lib/canonicalApi";
import { summarizeRawIngestionDetail } from "./rawIngestionSummary";

type Row = {
  id: number;
  connector: string;
  replay_sequence: number;
  resource_type: string;
  external_id: string;
  fetched_at: string;
  http_status: number;
};

type RawDetail = {
  id: number;
  connection_id: string;
  run_id: string;
  connector: string;
  source_trigger: string;
  replay_sequence: number;
  resource_type: string;
  external_id: string;
  api_endpoint: string;
  query_params: Record<string, unknown>;
  payload_hash: string;
  http_status: number;
  fetched_at: string;
  payload_body: Record<string, unknown>;
};

const PAGE = 80;

/** Must match ``STEP1_RAW_RESET_CONFIRMATION_PHRASE`` in ``step1_reset.py`` (case-sensitive). */
const STEP1_RAW_RESET_CONFIRMATION_PHRASE = "DELETE ALL STEP1 RAW DATA";

export default function AdminTenantStep1() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const qc = useQueryClient();
  const [page, setPage] = useState(0);
  const [inspectId, setInspectId] = useState<number | null>(null);

  useEffect(() => {
    setInspectId(null);
  }, [tenantId, page]);

  const q = useQuery({
    queryKey: ["admin-raw", tenantId, page],
    queryFn: () =>
      adminJson<{ items: Row[]; total: number; limit: number; offset: number }>(
        `/admin/tenants/${tenantId}/raw-ingestion?limit=${PAGE}&offset=${page * PAGE}`,
      ),
    enabled: Boolean(tenantId),
  });

  const detailQ = useQuery({
    queryKey: ["admin-raw-detail", tenantId, inspectId],
    queryFn: () =>
      adminJson<{ item: RawDetail }>(
        `/admin/tenants/${tenantId}/raw-ingestion/${inspectId}`,
      ),
    enabled: Boolean(tenantId && inspectId != null),
  });

  const [syncPending, setSyncPending] = useState(false);
  const [syncErr, setSyncErr] = useState<string | null>(null);
  const [syncOk, setSyncOk] = useState<string | null>(null);

  const [resetOpen, setResetOpen] = useState(false);
  const [resetPhrase, setResetPhrase] = useState("");
  const [resetPending, setResetPending] = useState(false);
  const [resetErr, setResetErr] = useState<string | null>(null);
  const [resetOk, setResetOk] = useState<string | null>(null);

  const resetPhraseOk = resetPhrase === STEP1_RAW_RESET_CONFIRMATION_PHRASE;

  const runSync = async (which: "github" | "linear") => {
    setSyncPending(true);
    setSyncErr(null);
    setSyncOk(null);
    try {
      const path =
        which === "github"
          ? `/admin/tenants/${tenantId}/ingestion/github-sync`
          : `/admin/tenants/${tenantId}/ingestion/linear-sync`;
      const res = await adminFetch(path, { method: "POST" });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      const body = (await res.json()) as { status: string; error_summary: string | null };
      setSyncOk(
        `${body.status}${body.error_summary ? ` — ${body.error_summary}` : ""}`,
      );
      void qc.invalidateQueries({ queryKey: ["admin-raw", tenantId] });
    } catch (e) {
      setSyncErr((e as Error).message);
    } finally {
      setSyncPending(false);
    }
  };

  const runStep1Reset = async () => {
    if (!resetPhraseOk) return;
    setResetPending(true);
    setResetErr(null);
    setResetOk(null);
    try {
      const res = await adminFetch(`/admin/tenants/${tenantId}/raw-ingestion/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmation: STEP1_RAW_RESET_CONFIRMATION_PHRASE }),
      });
      if (res.status === 401) {
        throw new Error("Invalid admin password");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      const body = (await res.json()) as {
        deleted_raw_records: number;
        deleted_ingestion_runs: number;
        deleted_sync_state_rows: number;
      };
      setResetOk(
        `Removed ${body.deleted_raw_records} raw rows, ${body.deleted_ingestion_runs} runs, ` +
          `${body.deleted_sync_state_rows} sync-state rows.`,
      );
      setResetOpen(false);
      setResetPhrase("");
      void qc.invalidateQueries({ queryKey: ["admin-raw", tenantId] });
    } catch (e) {
      setResetErr((e as Error).message);
    } finally {
      setResetPending(false);
    }
  };

  if (q.isPending) {
    return <p className="text-sm text-stone-600">Loading…</p>;
  }
  if (q.isError) {
    return <p className="text-sm text-red-700">{(q.error as Error).message}</p>;
  }

  const maxPage = Math.max(0, Math.ceil(q.data.total / PAGE) - 1);

  return (
    <div>
      <p className="mb-3 text-sm text-stone-600">
        Rows are written when <strong>Step 1 sync</strong> runs, not when you connect OAuth. Use the
        buttons below for this tenant, or the product routes{" "}
        <code className="rounded bg-stone-100 px-1">POST /connectors/github/sync</code> and{" "}
        <code className="rounded bg-stone-100 px-1">POST /connectors/linear/sync</code> with a user
        session. With <code className="rounded bg-stone-100 px-1">docker compose up</code>, the{" "}
        <code className="rounded bg-stone-100 px-1">mock-connectors</code> service starts automatically
        and the API uses it (no manual mock). For a backend on the host only, run{" "}
        <code className="rounded bg-stone-100 px-1">make -f Makefile.mock mock-connectors-up</code> and
        keep <code className="rounded bg-stone-100 px-1">VECTOR_MOCK_CONNECTOR_BASE_URL</code> on{" "}
        <code className="rounded bg-stone-100 px-1">http://127.0.0.1:9183</code>.
      </p>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded border border-stone-400 bg-white px-3 py-1.5 text-sm hover:bg-stone-50 disabled:opacity-40"
          disabled={syncPending}
          onClick={() => void runSync("github")}
        >
          Run GitHub Step 1 sync
        </button>
        <button
          type="button"
          className="rounded border border-stone-400 bg-white px-3 py-1.5 text-sm hover:bg-stone-50 disabled:opacity-40"
          disabled={syncPending}
          onClick={() => void runSync("linear")}
        >
          Run Linear Step 1 sync
        </button>
        {syncOk ? <span className="text-sm text-emerald-800">Last sync: {syncOk}</span> : null}
        {syncErr ? <span className="text-sm text-red-700">{syncErr}</span> : null}
        <button
          type="button"
          className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-900 hover:bg-red-100 disabled:opacity-40"
          disabled={syncPending || resetPending}
          onClick={() => {
            setResetOpen(true);
            setResetPhrase("");
            setResetErr(null);
            setResetOk(null);
          }}
        >
          Reset Step 1 raw data…
        </button>
        {resetOk ? <span className="text-sm text-emerald-800">{resetOk}</span> : null}
        {resetErr ? <span className="text-sm text-red-700">{resetErr}</span> : null}
      </div>
      {resetOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="step1-reset-title"
        >
          <div className="max-w-lg rounded-lg border border-stone-200 bg-white p-5 shadow-lg">
            <h2 id="step1-reset-title" className="text-lg font-semibold text-stone-900">
              Reset all Step 1 data for this tenant?
            </h2>
            <p className="mt-2 text-sm text-stone-700">
              This removes every <strong>raw_ingestion_records</strong> row, all{" "}
              <strong>ingestion_runs</strong>, and <strong>connector_sync_state</strong> (poll
              watermarks) for this workspace. <strong>OAuth connections are not touched</strong> and
              nothing is pulled from GitHub/Linear. Step 2/3 projections and canonical data are{" "}
              <strong>not</strong> deleted — they may look stale until you re-run downstream steps or
              reset those separately.
            </p>
            <p className="mt-3 text-sm font-medium text-stone-800">
              Type the phrase below exactly (case-sensitive) to enable reset:
            </p>
            <code className="mt-1 block rounded bg-stone-100 px-2 py-1.5 text-xs text-stone-800">
              {STEP1_RAW_RESET_CONFIRMATION_PHRASE}
            </code>
            <input
              type="text"
              className="mt-3 w-full rounded border border-stone-300 px-2 py-1.5 text-sm"
              placeholder="Type confirmation phrase…"
              value={resetPhrase}
              onChange={(e) => setResetPhrase(e.target.value)}
              autoComplete="off"
              autoFocus
            />
            <div className="mt-4 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="rounded border border-stone-300 bg-white px-3 py-1.5 text-sm hover:bg-stone-50"
                disabled={resetPending}
                onClick={() => {
                  setResetOpen(false);
                  setResetPhrase("");
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded border border-red-600 bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-40"
                disabled={!resetPhraseOk || resetPending}
                onClick={() => void runStep1Reset()}
              >
                {resetPending ? "Resetting…" : "Reset Step 1 data"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-sm disabled:opacity-40"
          disabled={page <= 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          Previous
        </button>
        <span className="text-sm text-stone-600">
          Page {page + 1} / {maxPage + 1} — {q.data.total} rows
        </span>
        <button
          type="button"
          className="rounded border border-stone-300 px-2 py-1 text-sm disabled:opacity-40"
          disabled={page >= maxPage}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-stone-200 bg-white">
        <table className="data-table text-xs">
          <thead>
            <tr>
              <th>connector</th>
              <th>replay_sequence</th>
              <th>resource_type</th>
              <th>external_id</th>
              <th>fetched_at</th>
              <th>http_status</th>
              <th className="w-24"> </th>
            </tr>
          </thead>
          <tbody>
            {q.data.items.map((r) => (
              <Fragment key={r.id}>
                <tr className={inspectId === r.id ? "bg-amber-50/60" : undefined}>
                  <td>{r.connector}</td>
                  <td>{r.replay_sequence}</td>
                  <td className="whitespace-nowrap">{r.resource_type}</td>
                  <td className="max-w-[14rem] truncate font-mono" title={r.external_id}>
                    {r.external_id}
                  </td>
                  <td className="whitespace-nowrap">{new Date(r.fetched_at).toLocaleString()}</td>
                  <td>{r.http_status}</td>
                  <td>
                    <button
                      type="button"
                      className="rounded border border-stone-300 px-2 py-0.5 text-stone-700 hover:bg-stone-100"
                      onClick={() => {
                        setInspectId((id) => (id === r.id ? null : r.id));
                      }}
                    >
                      {inspectId === r.id ? "Hide" : "Inspect"}
                    </button>
                  </td>
                </tr>
                {inspectId === r.id ? (
                  <tr key={`${r.id}-detail`} className="border-t border-stone-200 bg-stone-50">
                    <td colSpan={7} className="align-top p-4 text-left text-sm text-stone-800">
                      {detailQ.isPending ? (
                        <p className="text-stone-500">Loading payload…</p>
                      ) : null}
                      {detailQ.isError ? (
                        <p className="text-red-700">{(detailQ.error as Error).message}</p>
                      ) : null}
                      {detailQ.data ? (
                        <RawIngestionInspectPanel item={detailQ.data.item} />
                      ) : null}
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RawIngestionInspectPanel({ item }: { item: RawDetail }) {
  const summary = summarizeRawIngestionDetail({
    resourceType: item.resource_type,
    externalId: item.external_id,
    apiEndpoint: item.api_endpoint,
    queryParams: item.query_params,
    payloadBody: item.payload_body,
  });

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-stone-900">{summary.headline}</h3>
        <p className="mt-0.5 font-mono text-xs text-stone-500">{item.resource_type}</p>
        {summary.bullets.length > 0 ? (
          <ul className="mt-2 list-inside list-disc space-y-0.5 text-stone-700">
            {summary.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        ) : null}
      </div>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
        <div>
          <dt className="text-stone-500">run_id</dt>
          <dd className="font-mono break-all">{item.run_id}</dd>
        </div>
        <div>
          <dt className="text-stone-500">connection_id</dt>
          <dd className="font-mono break-all">{item.connection_id}</dd>
        </div>
        <div>
          <dt className="text-stone-500">source_trigger</dt>
          <dd>{item.source_trigger}</dd>
        </div>
        <div>
          <dt className="text-stone-500">payload_hash</dt>
          <dd className="font-mono break-all text-[11px]">{item.payload_hash}</dd>
        </div>
      </dl>
      <details className="rounded border border-stone-200 bg-white">
        <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-stone-600">
          Query params (JSON)
        </summary>
        <pre className="max-h-48 overflow-auto border-t border-stone-100 p-3 text-[11px] leading-relaxed">
          {JSON.stringify(item.query_params, null, 2)}
        </pre>
      </details>
      <details className="rounded border border-stone-200 bg-white">
        <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-stone-600">
          Full payload (JSON)
        </summary>
        <pre className="max-h-[min(70vh,32rem)] overflow-auto border-t border-stone-100 p-3 text-[11px] leading-relaxed">
          {JSON.stringify(item.payload_body, null, 2)}
        </pre>
      </details>
    </div>
  );
}

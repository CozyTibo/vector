import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

type IngestionRunItem = {
  id: string;
  connection_id: string;
  status: string;
  source_trigger: string;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
  records_written: number;
};

type IngestionRunsResponse = {
  items: IngestionRunItem[];
};

type RawRecordItem = {
  id: number;
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

type RecordsPageResponse = {
  run_id: string;
  total: number;
  limit: number;
  offset: number;
  items: RawRecordItem[];
};

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { detail?: string | unknown };
    if (typeof data.detail === "string") {
      return data.detail;
    }
  } catch {
    /* ignore */
  }
  return `HTTP ${res.status}`;
}

async function fetchRuns(base: string): Promise<IngestionRunsResponse> {
  const res = await fetch(`${base}/connectors/github/ingestion/runs`, {
    credentials: "include",
  });
  if (res.status === 401) {
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<IngestionRunsResponse>;
}

async function fetchRecords(
  base: string,
  runId: string,
  limit: number,
  offset: number,
): Promise<RecordsPageResponse> {
  const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const res = await fetch(
    `${base}/connectors/github/ingestion/runs/${encodeURIComponent(runId)}/records?${q}`,
    { credentials: "include" },
  );
  if (res.status === 401) {
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    throw new Error(await readErrorDetail(res));
  }
  return res.json() as Promise<RecordsPageResponse>;
}

const PAGE_SIZE = 75;

export default function GithubIngestionPage() {
  const apiBase = useMemo(() => import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ""), []);
  const [searchParams, setSearchParams] = useSearchParams();
  const runId = searchParams.get("run") ?? "";
  const pageStr = searchParams.get("page") ?? "0";
  const page = Math.max(0, parseInt(pageStr, 10) || 0);
  const offset = page * PAGE_SIZE;

  const runsQuery = useQuery({
    queryKey: ["github-ingestion-runs", apiBase],
    queryFn: () => fetchRuns(apiBase),
  });

  const recordsQuery = useQuery({
    queryKey: ["github-ingestion-records", apiBase, runId, page],
    queryFn: () => fetchRecords(apiBase, runId, PAGE_SIZE, offset),
    enabled: Boolean(runId),
  });

  function selectRun(id: string) {
    setSearchParams({ run: id, page: "0" });
  }

  function setPage(next: number) {
    const p = new URLSearchParams(searchParams);
    p.set("page", String(next));
    if (runId) {
      p.set("run", runId);
    }
    setSearchParams(p);
  }

  return (
    <div className="app">
      <header className="header">
        <h1>GitHub — synced raw data</h1>
        <p className="subtitle">
          Step 1 ingestion: one row per resource per observation. Order matches replay:{" "}
          <code>replay_sequence</code>, then <code>id</code>.
        </p>
        <p className="meta">
          <Link to="/">← Back to dashboard</Link>
        </p>
      </header>

      {runsQuery.isError ? (
        <p className="banner error">
          {(runsQuery.error as Error).message}
        </p>
      ) : null}

      <section className="card">
        <h2>Ingestion runs</h2>
        <p className="meta">
          Each sync creates a run; <code>records_written</code> counts rows stored for that run.
        </p>
        {runsQuery.isPending ? (
          <p className="status loading">Loading runs…</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Started (UTC)</th>
                  <th>Status</th>
                  <th>Trigger</th>
                  <th>Rows</th>
                  <th>Error</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {runsQuery.data?.items.map((r) => (
                  <tr key={r.id} className={r.id === runId ? "row-selected" : undefined}>
                    <td>
                      <code className="cell-muted">{r.started_at}</code>
                    </td>
                    <td>{r.status}</td>
                    <td>{r.source_trigger}</td>
                    <td>{r.records_written}</td>
                    <td className="cell-clip">{r.error_summary ?? "—"}</td>
                    <td>
                      <button type="button" className="btn small" onClick={() => selectRun(r.id)}>
                        {r.id === runId ? "Viewing" : "View rows"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!runsQuery.isPending && (runsQuery.data?.items.length ?? 0) === 0 ? (
          <p className="status loading">No runs yet — use “Sync from GitHub” on the dashboard.</p>
        ) : null}
      </section>

      {runId ? (
        <section className="card">
          <h2>
            Raw records <code className="cell-muted">{runId}</code>
          </h2>
          {recordsQuery.isPending ? (
            <p className="status loading">Loading records…</p>
          ) : recordsQuery.isError ? (
            <p className="banner error">{(recordsQuery.error as Error).message}</p>
          ) : recordsQuery.data ? (
            <>
              <p className="meta">
                Showing {recordsQuery.data.offset + 1}–
                {Math.min(
                  recordsQuery.data.offset + recordsQuery.data.items.length,
                  recordsQuery.data.total,
                )}{" "}
                of {recordsQuery.data.total} — page {page + 1} of{" "}
                {Math.max(1, Math.ceil(recordsQuery.data.total / PAGE_SIZE))}
              </p>
              <div className="btn-row">
                <button
                  type="button"
                  className="btn secondary"
                  disabled={page <= 0}
                  onClick={() => setPage(page - 1)}
                >
                  Previous page
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  disabled={
                    recordsQuery.data.offset + recordsQuery.data.items.length >=
                    recordsQuery.data.total
                  }
                  onClick={() => setPage(page + 1)}
                >
                  Next page
                </button>
              </div>
              <div className="table-wrap">
                <table className="data-table records-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>replay_seq</th>
                      <th>resource_type</th>
                      <th>external_id</th>
                      <th>endpoint</th>
                      <th>payload (JSON)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recordsQuery.data.items.map((row, i) => (
                      <tr key={row.id}>
                        <td>{recordsQuery.data!.offset + i + 1}</td>
                        <td>
                          <code>{row.replay_sequence}</code>
                        </td>
                        <td>
                          <code>{row.resource_type}</code>
                        </td>
                        <td>
                          <code className="cell-wrap">{row.external_id}</code>
                        </td>
                        <td>
                          <code className="cell-wrap cell-muted">{row.api_endpoint}</code>
                        </td>
                        <td>
                          <pre className="payload-preview">
                            {JSON.stringify(row.payload_body, null, 2)}
                          </pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </section>
      ) : (
        <section className="card">
          <p className="meta">Select a run to load raw ingestion rows.</p>
        </section>
      )}
    </div>
  );
}

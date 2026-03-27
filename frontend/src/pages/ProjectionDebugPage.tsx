import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

const ENTITIES = [
  { id: "repositories", label: "Repositories" },
  { id: "pull_requests", label: "Pull requests" },
  { id: "issues", label: "Issues" },
  { id: "commits", label: "Commits" },
  { id: "users", label: "Users" },
] as const;

type EntityId = (typeof ENTITIES)[number]["id"];

const ENTITY_COLUMNS: Record<EntityId, readonly string[]> = {
  repositories: [
    "repository_github_id",
    "full_name",
    "owner_login",
    "private",
    "default_branch",
    "archived",
    "github_updated_at",
    "last_observed_at",
    "last_raw_record_id",
    "last_replay_sequence",
  ],
  pull_requests: [
    "repo_full_name",
    "pr_number",
    "title",
    "state",
    "author_login",
    "base_ref",
    "head_ref",
    "merged_at",
    "github_updated_at",
    "last_observed_at",
    "last_raw_record_id",
    "last_replay_sequence",
  ],
  issues: [
    "repo_full_name",
    "issue_number",
    "title",
    "state",
    "author_login",
    "github_updated_at",
    "last_observed_at",
    "last_raw_record_id",
    "last_replay_sequence",
  ],
  commits: [
    "repo_full_name",
    "commit_sha",
    "author_login",
    "author_date",
    "message",
    "last_observed_at",
    "last_raw_record_id",
    "last_replay_sequence",
  ],
  users: [
    "github_id",
    "login",
    "type",
    "avatar_url",
    "html_url",
    "last_observed_at",
    "last_raw_record_id",
    "last_replay_sequence",
  ],
};

type ProjectionRowsResponse = {
  connector: string;
  connection_id: string;
  entity: string;
  total: number;
  limit: number;
  offset: number;
  items: Record<string, unknown>[];
};

type RawRecordResponse = {
  item: {
    id: number;
    replay_sequence: number;
    resource_type: string;
    external_id: string;
    payload_body: Record<string, unknown>;
    [k: string]: unknown;
  };
};

const PAGE_SIZE = 40;

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

function displayCell(entity: EntityId, col: string, row: Record<string, unknown>): string {
  if (entity === "commits" && col === "author_login") {
    const login = row.author_login;
    const name = row.author_name;
    if (login != null && String(login).length > 0) {
      return String(login);
    }
    if (name != null && String(name).length > 0) {
      return String(name);
    }
    return "—";
  }
  const v = row[col];
  if (v == null) {
    return "—";
  }
  if (typeof v === "boolean") {
    return v ? "true" : "false";
  }
  return String(v as string | number);
}

export default function ProjectionDebugPage() {
  const { connector = "github", connectionId = "" } = useParams<{
    connector: string;
    connectionId: string;
  }>();
  const apiBase = useMemo(() => import.meta.env.VITE_API_BASE_URL.replace(/\/$/, ""), []);
  const [entity, setEntity] = useState<EntityId>("repositories");
  const [page, setPage] = useState(0);
  const [filterQ, setFilterQ] = useState("");
  const [queryInput, setQueryInput] = useState("");
  const [detailJson, setDetailJson] = useState<string | null>(null);
  const [rawModal, setRawModal] = useState<string | null>(null);

  const summaryKeys = useMemo(() => [...ENTITY_COLUMNS[entity]], [entity]);

  const rowsQuery = useQuery({
    queryKey: ["projection-rows", apiBase, connector, connectionId, entity, page, filterQ],
    queryFn: async () => {
      const q = new URLSearchParams({
        entity,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (filterQ.trim()) {
        q.set("q", filterQ.trim());
      }
      const res = await fetch(
        `${apiBase}/debug/connectors/${encodeURIComponent(connector)}/connections/${encodeURIComponent(connectionId)}/projections/rows?${q}`,
        { credentials: "include" },
      );
      if (res.status === 401) {
        throw new Error("Not signed in");
      }
      if (!res.ok) {
        throw new Error(await readErrorDetail(res));
      }
      return res.json() as Promise<ProjectionRowsResponse>;
    },
    enabled: Boolean(connectionId),
  });

  function applyFilter() {
    setPage(0);
    setFilterQ(queryInput);
  }

  async function openRawRecord(recordId: number) {
    const res = await fetch(
      `${apiBase}/debug/connectors/${encodeURIComponent(connector)}/connections/${encodeURIComponent(connectionId)}/raw-records/${recordId}`,
      { credentials: "include" },
    );
    if (!res.ok) {
      setRawModal(await readErrorDetail(res));
      return;
    }
    const data = (await res.json()) as RawRecordResponse;
    setRawModal(JSON.stringify(data.item, null, 2));
  }

  function rawRecordHref(recordId: number): string {
    const q = new URLSearchParams({
      connector,
      connection_id: connectionId,
    });
    return `/debug/ingestion/raw/${recordId}?${q.toString()}`;
  }

  return (
    <div className="app legacy-debug">
      <header className="header">
        <h1>Debug — connector projections</h1>
        <p className="subtitle">
          Step 2 materialized state for <code>{connector}</code> / connection{" "}
          <code className="cell-muted">{connectionId}</code>
        </p>
        <p className="meta">
          <Link to="/">← Dashboard</Link>
          {" · "}
          <Link to="/github/ingestion">GitHub ingestion</Link>
        </p>
      </header>

      {rowsQuery.isError ? (
        <p className="banner error">{(rowsQuery.error as Error).message}</p>
      ) : null}

      <section className="card">
        <div className="btn-row wrap" style={{ gap: "0.35rem", marginBottom: "0.75rem" }}>
          {ENTITIES.map((e) => (
            <button
              key={e.id}
              type="button"
              className={`btn small ${entity === e.id ? "" : "secondary"}`}
              onClick={() => {
                setEntity(e.id);
                setPage(0);
              }}
            >
              {e.label}
            </button>
          ))}
        </div>
        <div className="btn-row" style={{ alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
          <input
            type="search"
            className="input-guess"
            placeholder="Filter (substring)…"
            value={queryInput}
            onChange={(ev) => setQueryInput(ev.target.value)}
            onKeyDown={(ev) => {
              if (ev.key === "Enter") {
                applyFilter();
              }
            }}
            style={{
              flex: "1 1 12rem",
              padding: "0.45rem 0.6rem",
              borderRadius: 6,
              border: "1px solid #333",
              background: "#0e0f12",
              color: "#e8eaed",
            }}
          />
          <button type="button" className="btn small" onClick={applyFilter}>
            Apply filter
          </button>
        </div>
      </section>

      <section className="card">
        {rowsQuery.isPending ? (
          <p className="status loading">Loading…</p>
        ) : rowsQuery.data ? (
          <>
            <p className="meta">
              {rowsQuery.data.entity}: {rowsQuery.data.total} rows — page {page + 1} of{" "}
              {Math.max(1, Math.ceil(rowsQuery.data.total / PAGE_SIZE))}
            </p>
            <div className="btn-row">
              <button
                type="button"
                className="btn secondary small"
                disabled={page <= 0}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <button
                type="button"
                className="btn secondary small"
                disabled={(page + 1) * PAGE_SIZE >= rowsQuery.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
            <div className="table-wrap">
              <table className="data-table records-table">
                <thead>
                  <tr>
                    <th></th>
                    {summaryKeys.map((k) => (
                      <th key={k}>{k}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rowsQuery.data.items.map((row, i) => (
                    <tr key={`${page}-${i}`}>
                      <td>
                        <button
                          type="button"
                          className="btn small secondary"
                          onClick={() => setDetailJson(JSON.stringify(row, null, 2))}
                        >
                          JSON
                        </button>
                        {typeof row.last_raw_record_id === "number" ? (
                          <button
                            type="button"
                            className="btn small secondary"
                            style={{ marginTop: 4 }}
                            onClick={() => openRawRecord(row.last_raw_record_id as number)}
                          >
                            Raw
                          </button>
                        ) : null}
                      </td>
                      {summaryKeys.map((k) => (
                        <td key={k}>
                          {k === "last_raw_record_id" &&
                          typeof row.last_raw_record_id === "number" ? (
                            <Link
                              className="cell-wrap link-inline"
                              to={rawRecordHref(row.last_raw_record_id as number)}
                            >
                              {String(row.last_raw_record_id)}
                            </Link>
                          ) : (
                            <code className="cell-wrap cell-muted">
                              {displayCell(entity, k, row)}
                            </code>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </section>

      {detailJson ? (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          onClick={() => setDetailJson(null)}
          onKeyDown={(ev) => {
            if (ev.key === "Escape") {
              setDetailJson(null);
            }
          }}
        >
          <pre
            className="payload-preview"
            style={{ maxWidth: "min(90vw, 900px)", maxHeight: "80vh", overflow: "auto" }}
            onClick={(ev) => ev.stopPropagation()}
            onKeyDown={(ev) => ev.stopPropagation()}
          >
            {detailJson}
          </pre>
        </div>
      ) : null}

      {rawModal ? (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.75)",
            zIndex: 60,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem",
          }}
          onClick={() => setRawModal(null)}
          onKeyDown={(ev) => {
            if (ev.key === "Escape") {
              setRawModal(null);
            }
          }}
        >
          <pre
            className="payload-preview"
            style={{ maxWidth: "min(90vw, 900px)", maxHeight: "80vh", overflow: "auto" }}
            onClick={(ev) => ev.stopPropagation()}
            onKeyDown={(ev) => ev.stopPropagation()}
          >
            {rawModal}
          </pre>
        </div>
      ) : null}
    </div>
  );
}

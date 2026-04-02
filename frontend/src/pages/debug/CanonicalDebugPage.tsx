import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { CopyableId } from "../../components/canonical/CopyableId";
import { DebugEntityLabel } from "../../components/canonical/DebugEntityLabel";
import GraphPanel from "../../components/canonical/GraphPanel";
import { formatArtifactListLine, UI_TAB_LABELS } from "../../lib/executionModelDisplay";
import { decodeGithubExternalKey } from "../../lib/githubExternalKeyDecode";
import {
  fetchActorsPage,
  fetchArtifactsPage,
  fetchCanonicalStatus,
  fetchExternalReferencesPage,
  fetchGithubIngestionRuns,
  fetchRelationshipsPage,
  fetchSubgraphByActor,
  fetchSubgraphByArtifact,
  relationKindName,
  rebuildFromStep1Canonical,
  resetAndResyncCanonical,
  type CanonicalClient,
  type SubgraphResponse,
} from "../../lib/canonicalApi";

const PAGE_SIZE = 40;

const TABS = [
  { id: "artifacts", label: UI_TAB_LABELS.artifacts },
  { id: "actors", label: UI_TAB_LABELS.actors },
  { id: "relationships", label: UI_TAB_LABELS.relationships },
  { id: "xrefs", label: UI_TAB_LABELS.xrefs },
  { id: "graph", label: UI_TAB_LABELS.graph },
  { id: "status", label: UI_TAB_LABELS.status },
] as const;

type TabId = (typeof TABS)[number]["id"];

function clientQueryTag(c: CanonicalClient): string {
  return c.kind === "session" ? "session" : `admin:${c.tenantId}`;
}

export type CanonicalDebugPageProps = {
  client: CanonicalClient;
  /** Base path for in-app entity routes (no trailing slash). */
  entityBasePath: string;
  dashboardHref?: string;
  /** `admin` uses light chrome to match Vector Admin; `developer` keeps the dark debug HUD. */
  visualTheme?: "developer" | "admin";
};

export default function CanonicalDebugPage({
  client: canonicalClient,
  entityBasePath,
  dashboardHref = "/app",
  visualTheme = "developer",
}: CanonicalDebugPageProps) {
  const isAdminShell = visualTheme === "admin";
  const rawIngestionHref =
    canonicalClient.kind === "admin"
      ? `/admin/tenants/${canonicalClient.tenantId}/step1`
      : "/admin";
  const cqTag = useMemo(() => clientQueryTag(canonicalClient), [canonicalClient]);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab") as TabId | null;
  const tab: TabId = TABS.some((t) => t.id === tabParam) ? (tabParam as TabId) : "artifacts";

  const [page, setPage] = useState(0);
  const [filterQ, setFilterQ] = useState("");
  const [filterInput, setFilterInput] = useState("");

  const [graphAnchor, setGraphAnchor] = useState<"artifact" | "actor">("artifact");
  const [graphId, setGraphId] = useState("");
  const [graphDepth, setGraphDepth] = useState(2);
  const [graphData, setGraphData] = useState<SubgraphResponse | null>(null);
  const [graphError, setGraphError] = useState<string | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);

  const connectionFromUrl = searchParams.get("connection_id") ?? "";
  const statusConnector = searchParams.get("connector") ?? "github";

  const runsQuery = useQuery({
    queryKey: ["github-ingestion-runs", cqTag],
    queryFn: () => fetchGithubIngestionRuns(canonicalClient),
  });

  const connectionOptions = useMemo(() => {
    const items = runsQuery.data?.items ?? [];
    const seen = new Set<string>();
    const out: { id: string; label: string }[] = [];
    for (const r of items) {
      if (!seen.has(r.connection_id)) {
        seen.add(r.connection_id);
        out.push({ id: r.connection_id, label: r.connection_id.slice(0, 8) + "…" });
      }
    }
    return out;
  }, [runsQuery.data?.items]);

  const [statusConnectionId, setStatusConnectionId] = useState(connectionFromUrl);
  const [resetConfirmText, setResetConfirmText] = useState("");
  const [resetRunning, setResetRunning] = useState(false);
  const [resetMessage, setResetMessage] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);

  const [rebuildConfirmText, setRebuildConfirmText] = useState("");
  const [rebuildRunning, setRebuildRunning] = useState(false);
  const [rebuildMessage, setRebuildMessage] = useState<string | null>(null);
  const [rebuildError, setRebuildError] = useState<string | null>(null);

  useEffect(() => {
    if (connectionFromUrl) {
      setStatusConnectionId(connectionFromUrl);
    }
  }, [connectionFromUrl]);

  const statusQuery = useQuery({
    queryKey: ["canonical-status", cqTag, statusConnectionId, statusConnector],
    queryFn: () => fetchCanonicalStatus(canonicalClient, statusConnectionId, statusConnector),
    enabled: Boolean(statusConnectionId) && tab === "status",
  });

  const artifactsQuery = useQuery({
    queryKey: ["canonical-artifacts", cqTag, page, filterQ],
    queryFn: () =>
      fetchArtifactsPage(canonicalClient, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        q: filterQ || undefined,
      }),
    enabled: tab === "artifacts",
  });

  const actorsQuery = useQuery({
    queryKey: ["canonical-actors", cqTag, page, filterQ],
    queryFn: () =>
      fetchActorsPage(canonicalClient, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        q: filterQ || undefined,
      }),
    enabled: tab === "actors",
  });

  const relQuery = useQuery({
    queryKey: ["canonical-relationships", cqTag, page],
    queryFn: () =>
      fetchRelationshipsPage(canonicalClient, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        currentOnly: true,
      }),
    enabled: tab === "relationships",
  });

  const xrefQuery = useQuery({
    queryKey: ["canonical-xrefs", cqTag, page],
    queryFn: () =>
      fetchExternalReferencesPage(canonicalClient, {
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
    enabled: tab === "xrefs",
  });

  function switchTab(next: TabId) {
    setSearchParams((prev) => {
      const p = new URLSearchParams(prev);
      p.set("tab", next);
      return p;
    });
    setPage(0);
  }

  function applyFilter() {
    setPage(0);
    setFilterQ(filterInput);
  }

  async function runResetAndResync() {
    const connectionId = statusConnectionId.trim();
    if (!connectionId) {
      setResetError("Select or paste a connection_id first.");
      return;
    }
    if (resetConfirmText.trim().toUpperCase() !== "RESET") {
      setResetError("Type RESET to enable this action.");
      return;
    }
    setResetRunning(true);
    setResetError(null);
    setResetMessage(null);
    try {
      const out = await resetAndResyncCanonical(canonicalClient, connectionId);
      const msg =
        `Reset complete. Ingestion run ${out.ingestion_run_id} (${out.ingestion_status}). ` +
        `Projected ${out.projection_rows_processed} raw rows; canonical processed ${out.canonical_rows_processed}.`;
      setResetMessage(out.warning ? `${msg} ${out.warning}` : msg);
      await runsQuery.refetch();
      await statusQuery.refetch();
    } catch (e) {
      setResetError((e as Error).message);
    } finally {
      setResetRunning(false);
    }
  }

  async function runRebuildFromStep1() {
    const connectionId = statusConnectionId.trim();
    if (!connectionId) {
      setRebuildError("Select or paste a connection_id first.");
      return;
    }
    if (rebuildConfirmText.trim().toUpperCase() !== "REBUILD") {
      setRebuildError('Type REBUILD to enable this action.');
      return;
    }
    setRebuildRunning(true);
    setRebuildError(null);
    setRebuildMessage(null);
    try {
      const out = await rebuildFromStep1Canonical(canonicalClient, connectionId);
      setRebuildMessage(
        `Rebuilt from Step 1 (raw rows unchanged). Projected ${out.projection_rows_processed} raw rows; canonical processed ${out.canonical_rows_processed}.`,
      );
      await statusQuery.refetch();
    } catch (e) {
      setRebuildError((e as Error).message);
    } finally {
      setRebuildRunning(false);
    }
  }

  async function loadGraph() {
    const id = graphId.trim();
    if (!id) {
      setGraphError("Enter a UUID.");
      setGraphData(null);
      return;
    }
    setGraphLoading(true);
    setGraphError(null);
    try {
      const d =
        graphAnchor === "artifact"
          ? await fetchSubgraphByArtifact(canonicalClient, id, graphDepth)
          : await fetchSubgraphByActor(canonicalClient, id, graphDepth);
      setGraphData(d);
    } catch (e) {
      setGraphData(null);
      setGraphError((e as Error).message);
    } finally {
      setGraphLoading(false);
    }
  }

  return (
    <div className={isAdminShell ? "canonical-admin-shell" : "app legacy-debug"}>
      <header className="header">
        <h1>Execution Graph (Step 3)</h1>
        <p className="subtitle">Inspect how people and work are connected in your system.</p>
        <ul className="meta" style={{ marginTop: "0.35rem", paddingLeft: "1.25rem" }}>
          <li>People (actors)</li>
          <li>Work objects (repositories, commits, pull requests, issues)</li>
          <li>Connections between them</li>
        </ul>
        <p className="meta">
          <Link to={dashboardHref}>{isAdminShell ? "← Admin" : "← App"}</Link>
          {" · "}
          <Link to={rawIngestionHref}>Raw ingestion (admin)</Link>
        </p>
      </header>

      <section className="card nested" style={{ marginBottom: "0.75rem" }}>
        <h2 style={{ marginTop: 0, fontSize: "1rem" }}>How to read this page</h2>
        <p className="meta" style={{ marginBottom: 0 }}>
          People perform actions on work objects (repos, commits, PRs, issues). Connections record how
          those objects relate — not raw database rows.
        </p>
      </section>

      <section className="card">
        <div className="btn-row wrap" style={{ gap: "0.35rem", marginBottom: "0.75rem" }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`btn small ${tab === t.id ? "" : "secondary"}`}
              onClick={() => switchTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {(tab === "artifacts" || tab === "actors") && (
          <div className="btn-row" style={{ alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="search"
              className="input-guess"
              placeholder="Filter by name…"
              value={filterInput}
              onChange={(ev) => setFilterInput(ev.target.value)}
              onKeyDown={(ev) => {
                if (ev.key === "Enter") {
                  applyFilter();
                }
              }}
              style={
                isAdminShell
                  ? {
                      flex: "1 1 12rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                    }
                  : {
                      flex: "1 1 12rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                      border: "1px solid #333",
                      background: "#0e0f12",
                      color: "#e8eaed",
                    }
              }
            />
            <button type="button" className="btn small" onClick={applyFilter}>
              Apply filter
            </button>
          </div>
        )}
      </section>

      {tab === "artifacts" && (
        <section className="card">
          {artifactsQuery.isError ? (
            <p className="banner error">{(artifactsQuery.error as Error).message}</p>
          ) : artifactsQuery.isPending ? (
            <p className="status loading">Loading…</p>
          ) : artifactsQuery.data ? (
            <>
              <p className="meta">
                {artifactsQuery.data.total} work objects — page {page + 1} of{" "}
                {Math.max(1, Math.ceil(artifactsQuery.data.total / PAGE_SIZE))}
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
                  disabled={(page + 1) * PAGE_SIZE >= artifactsQuery.data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
              <div className="table-wrap">
                <table className="data-table records-table">
                  <thead>
                    <tr>
                      <th>Display</th>
                      <th>Last observed</th>
                      <th className="cell-muted">Internal ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {artifactsQuery.data.items.map((row) => {
                      const id = String(row.id ?? "");
                      const kindId = row.artifact_kind_id as number | undefined;
                      return (
                        <tr
                          key={id}
                          style={{ cursor: "pointer" }}
                          onClick={() => navigate(`${entityBasePath}/artifacts/${id}`)}
                          title={id}
                        >
                          <td>
                            <span className="debug-pill debug-pill--work">
                              {formatArtifactListLine({
                                artifact_kind_id: kindId,
                                title: row.title != null ? String(row.title) : null,
                                summary: row.summary != null ? String(row.summary) : null,
                              })}
                            </span>
                          </td>
                          <td>{row.last_observed_at != null ? String(row.last_observed_at) : "—"}</td>
                          <td className="cell-muted">
                            <CopyableId id={id} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </section>
      )}

      {tab === "actors" && (
        <section className="card">
          {actorsQuery.isError ? (
            <p className="banner error">{(actorsQuery.error as Error).message}</p>
          ) : actorsQuery.isPending ? (
            <p className="status loading">Loading…</p>
          ) : actorsQuery.data ? (
            <>
              <p className="meta">
                {actorsQuery.data.total} people — page {page + 1} of{" "}
                {Math.max(1, Math.ceil(actorsQuery.data.total / PAGE_SIZE))}
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
                  disabled={(page + 1) * PAGE_SIZE >= actorsQuery.data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
              <div className="table-wrap">
                <table className="data-table records-table">
                  <thead>
                    <tr>
                      <th>Person</th>
                      <th>Role</th>
                      <th className="cell-muted">Internal ID</th>
                    </tr>
                  </thead>
                  <tbody>
                    {actorsQuery.data.items.map((row) => {
                      const id = String(row.id ?? "");
                      return (
                        <tr
                          key={id}
                          style={{ cursor: "pointer" }}
                          onClick={() => navigate(`${entityBasePath}/actors/${id}`)}
                          title={id}
                        >
                          <td>
                            <span className="debug-pill debug-pill--person">
                              {row.display_name != null ? String(row.display_name) : "—"}
                            </span>
                          </td>
                          <td>{row.kind != null ? String(row.kind) : "—"}</td>
                          <td className="cell-muted">
                            <CopyableId id={id} />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </section>
      )}

      {tab === "relationships" && (
        <section className="card">
          {relQuery.isError ? (
            <p className="banner error">{(relQuery.error as Error).message}</p>
          ) : relQuery.isPending ? (
            <p className="status loading">Loading…</p>
          ) : relQuery.data ? (
            <>
              <p className="meta">
                {relQuery.data.total} connections (current) — page {page + 1} of{" "}
                {Math.max(1, Math.ceil(relQuery.data.total / PAGE_SIZE))}
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
                  disabled={(page + 1) * PAGE_SIZE >= relQuery.data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
              <div className="debug-connection-list">
                {relQuery.data.items.map((row) => {
                  const id = String(row.id ?? "");
                  const st = String(row.subject_type ?? "");
                  const sid = String(row.subject_id ?? "");
                  const ot = String(row.object_type ?? "");
                  const oid = String(row.object_id ?? "");
                  const rk = relationKindName(row.relation_kind_id as number);
                  return (
                    <div key={id} className="debug-connection-row">
                      <div className="debug-connection-line">
                        <DebugEntityLabel client={canonicalClient} linkPrefix={entityBasePath} type={st} id={sid} />
                        <span className="debug-relation-badge">{rk}</span>
                        <DebugEntityLabel client={canonicalClient} linkPrefix={entityBasePath} type={ot} id={oid} />
                      </div>
                      <div className="debug-connection-meta">
                        <span className="cell-muted">row id</span> <CopyableId id={id} />
                        {row.valid_from != null ? (
                          <span className="cell-muted"> · valid_from {String(row.valid_from)}</span>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          ) : null}
        </section>
      )}

      {tab === "xrefs" && (
        <section className="card">
          {xrefQuery.isError ? (
            <p className="banner error">{(xrefQuery.error as Error).message}</p>
          ) : xrefQuery.isPending ? (
            <p className="status loading">Loading…</p>
          ) : xrefQuery.data ? (
            <>
              <p className="meta">
                {xrefQuery.data.total} external IDs — page {page + 1} of{" "}
                {Math.max(1, Math.ceil(xrefQuery.data.total / PAGE_SIZE))}
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
                  disabled={(page + 1) * PAGE_SIZE >= xrefQuery.data.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
              <div className="debug-xref-list">
                {xrefQuery.data.items.map((row) => {
                  const id = String(row.id ?? "");
                  const raw = row.external_key != null ? String(row.external_key) : "";
                  const connector = String(row.connector ?? "").toLowerCase();
                  const decoded = connector === "github" ? decodeGithubExternalKey(raw) : null;
                  return (
                    <div key={id} className="card nested" style={{ marginBottom: "0.65rem" }}>
                      <div className="debug-xref-headline">
                        {decoded?.headline ?? "External ID"}
                      </div>
                      {decoded?.lines.map((line, i) => (
                        <div key={i} className="meta" style={{ marginBottom: "0.2rem" }}>
                          {line}
                        </div>
                      ))}
                      <div className="meta" style={{ marginTop: "0.35rem" }}>
                        connector: {row.connector != null ? String(row.connector) : "—"} · last raw{" "}
                        {row.last_raw_record_id != null ? String(row.last_raw_record_id) : "—"}
                      </div>
                      <div className="meta" style={{ marginTop: "0.25rem" }}>
                        internal <CopyableId id={id} />
                      </div>
                      <details style={{ marginTop: "0.5rem" }} className="debug-xref-raw">
                        <summary className="meta">Raw key</summary>
                        <code style={{ wordBreak: "break-all", fontSize: "0.8rem" }}>{raw || "—"}</code>
                      </details>
                    </div>
                  );
                })}
              </div>
            </>
          ) : null}
        </section>
      )}

      {tab === "graph" && (
        <section className="card">
          <p className="meta" style={{ marginBottom: "0.75rem" }}>
            Small graphs only — backend enforces max depth 5.
          </p>
          <div className="btn-row wrap" style={{ gap: "0.5rem", alignItems: "center" }}>
            <label className="meta">
              Anchor{" "}
              <select
                value={graphAnchor}
                onChange={(ev) => setGraphAnchor(ev.target.value as "artifact" | "actor")}
                style={{ marginLeft: 6, padding: "0.25rem 0.4rem" }}
              >
                <option value="artifact">Work object</option>
                <option value="actor">Person</option>
              </select>
            </label>
            <input
              className="input-guess"
              placeholder="UUID"
              value={graphId}
              onChange={(ev) => setGraphId(ev.target.value)}
              style={
                isAdminShell
                  ? {
                      flex: "1 1 16rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                    }
                  : {
                      flex: "1 1 16rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                      border: "1px solid #333",
                      background: "#0e0f12",
                      color: "#e8eaed",
                    }
              }
            />
            <label className="meta">
              depth{" "}
              <select
                value={graphDepth}
                onChange={(ev) => setGraphDepth(Number(ev.target.value))}
                style={{ marginLeft: 6 }}
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5}>5</option>
              </select>
            </label>
            <button type="button" className="btn small" onClick={() => void loadGraph()}>
              Load subgraph
            </button>
          </div>
          <GraphPanel
            data={graphData}
            error={graphError}
            loading={graphLoading}
            entityBasePath={entityBasePath}
            surface={isAdminShell ? "light" : "dark"}
          />
        </section>
      )}

      {tab === "status" && (
        <section className="card">
          <p className="meta" style={{ marginBottom: "0.75rem" }}>
            Pipeline health for Step 3 (canonical) vs Step 2 (projections), per connector
            connection. Choose a connection or paste its UUID. Deep link:{" "}
            <code className="cell-muted">
              ?connection_id=&lt;uuid&gt;&amp;tab=status&amp;connector=linear
            </code>
            .
          </p>
          <div className="btn-row wrap" style={{ gap: "0.5rem", alignItems: "center" }}>
            <label className="meta" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              Connector
              <select
                value={statusConnector}
                onChange={(ev) => {
                  const v = ev.target.value;
                  setSearchParams((prev) => {
                    const p = new URLSearchParams(prev);
                    if (v && v !== "github") {
                      p.set("connector", v);
                    } else {
                      p.delete("connector");
                    }
                    return p;
                  });
                }}
                style={{ padding: "0.35rem 0.5rem" }}
              >
                <option value="github">github</option>
                <option value="linear">linear</option>
              </select>
            </label>
            <select
              value={statusConnectionId}
              onChange={(ev) => {
                setStatusConnectionId(ev.target.value);
                setSearchParams((prev) => {
                  const p = new URLSearchParams(prev);
                  if (ev.target.value) {
                    p.set("connection_id", ev.target.value);
                  } else {
                    p.delete("connection_id");
                  }
                  return p;
                });
              }}
              style={{ minWidth: "14rem", padding: "0.35rem 0.5rem" }}
            >
              <option value="">— select connection —</option>
              {connectionOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id}
                </option>
              ))}
            </select>
            <input
              className="input-guess"
              placeholder="Or paste connection_id UUID"
              value={statusConnectionId}
              onChange={(ev) => {
                setStatusConnectionId(ev.target.value);
                setSearchParams((prev) => {
                  const p = new URLSearchParams(prev);
                  if (ev.target.value.trim()) {
                    p.set("connection_id", ev.target.value.trim());
                  } else {
                    p.delete("connection_id");
                  }
                  return p;
                });
              }}
              style={
                isAdminShell
                  ? {
                      flex: "1 1 14rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                    }
                  : {
                      flex: "1 1 14rem",
                      padding: "0.45rem 0.6rem",
                      borderRadius: 6,
                      border: "1px solid #333",
                      background: "#0e0f12",
                      color: "#e8eaed",
                    }
              }
            />
          </div>
          {runsQuery.isError ? (
            <p className="banner error">Could not load runs: {(runsQuery.error as Error).message}</p>
          ) : null}
          {statusQuery.isError ? (
            <p className="banner error">{(statusQuery.error as Error).message}</p>
          ) : statusQuery.isPending && statusConnectionId ? (
            <p className="status loading" style={{ marginTop: "0.75rem" }}>
              Loading status…
            </p>
          ) : statusQuery.data ? (
            <dl
              className="meta"
              style={{
                marginTop: "1rem",
                display: "grid",
                gridTemplateColumns: "max-content 1fr",
                gap: "0.35rem 1rem",
              }}
            >
                  <dt>step3_last_processed_replay_sequence</dt>
                  <dd>{statusQuery.data.step3_last_processed_replay_sequence}</dd>
                  <dt>step3_last_processed_id</dt>
                  <dd>{statusQuery.data.step3_last_processed_id}</dd>
                  <dt>step3_lag_rows</dt>
                  <dd>
                    {statusQuery.data.step3_lag_rows}
                    <span className="meta"> — raw rows still to process for Step 3 (0 = caught up)</span>
                  </dd>
                  <dt>step3_last_processed_timestamp</dt>
                  <dd>
                    {statusQuery.data.step3_last_processed_timestamp != null
                      ? String(statusQuery.data.step3_last_processed_timestamp)
                      : "—"}
                  </dd>
                  <dt>step2_watermark_replay_sequence</dt>
                  <dd>{statusQuery.data.step2_watermark_replay_sequence}</dd>
                  <dt>step2_watermark_id</dt>
                  <dd>{statusQuery.data.step2_watermark_id}</dd>
                </dl>
          ) : !statusConnectionId ? (
            <p className="meta" style={{ marginTop: "0.75rem" }}>
              Select a connection to load pipeline status.
            </p>
          ) : null}

          <div
            className="card nested"
            style={
              isAdminShell
                ? { marginTop: "1rem", borderColor: "#93c5fd", background: "#eff6ff" }
                : { marginTop: "1rem", borderColor: "#3d4f6b" }
            }
          >
            <h3
              style={
                isAdminShell
                  ? { marginTop: 0, fontSize: "0.95rem", color: "#1e40af" }
                  : { marginTop: 0, fontSize: "0.95rem", color: "#b6cdf0" }
              }
            >
              Rebuild from Step 1 (no GitHub pull)
            </h3>
            <p className="meta" style={{ marginTop: 0 }}>
              Keeps raw ingestion rows. Clears Step 2 for this connection only. Step 3 (canonical graph)
              is cleared for the whole tenant, then rebuilt from all raw rows — same as full reset for
              that layer. Use after mapper changes without re-syncing GitHub.
            </p>
            <div className="btn-row wrap" style={{ gap: "0.5rem", alignItems: "center" }}>
              <input
                className="input-guess"
                placeholder='Type "REBUILD"'
                value={rebuildConfirmText}
                onChange={(ev) => setRebuildConfirmText(ev.target.value)}
                style={
                  isAdminShell
                    ? { flex: "0 0 11rem", padding: "0.45rem 0.6rem", borderRadius: 6 }
                    : {
                        flex: "0 0 11rem",
                        padding: "0.45rem 0.6rem",
                        borderRadius: 6,
                        border: "1px solid #4a5f8a",
                        background: "#0f1218",
                        color: "#dde7f7",
                      }
                }
              />
              <button
                type="button"
                className="btn small secondary"
                disabled={
                  rebuildRunning ||
                  resetRunning ||
                  rebuildConfirmText.trim().toUpperCase() !== "REBUILD"
                }
                onClick={() => void runRebuildFromStep1()}
              >
                {rebuildRunning ? "Rebuilding…" : "Rebuild Step 2 + Step 3"}
              </button>
            </div>
            {rebuildError ? (
              <p className="banner error" style={{ marginTop: "0.6rem" }}>
                {rebuildError}
              </p>
            ) : null}
            {rebuildMessage ? (
              <p className="meta" style={{ marginTop: "0.6rem" }}>
                {rebuildMessage}
              </p>
            ) : null}
          </div>

          <div
            className="card nested"
            style={
              isAdminShell
                ? { marginTop: "1rem", borderColor: "#fecaca", background: "#fef2f2" }
                : { marginTop: "1rem", borderColor: "#5b2a2a" }
            }
          >
            <h3
              style={
                isAdminShell
                  ? { marginTop: 0, fontSize: "0.95rem", color: "#991b1b" }
                  : { marginTop: 0, fontSize: "0.95rem", color: "#f0b6b6" }
              }
            >
              Danger zone: reset and full reingest
            </h3>
            <p className="meta" style={{ marginTop: 0 }}>
              Deletes GitHub ingestion + projection + canonical data for this connection, then runs a
              fresh pull and rebuild.
            </p>
            <div className="btn-row wrap" style={{ gap: "0.5rem", alignItems: "center" }}>
              <input
                className="input-guess"
                placeholder='Type "RESET"'
                value={resetConfirmText}
                onChange={(ev) => setResetConfirmText(ev.target.value)}
                style={
                  isAdminShell
                    ? { flex: "0 0 11rem", padding: "0.45rem 0.6rem", borderRadius: 6 }
                    : {
                        flex: "0 0 11rem",
                        padding: "0.45rem 0.6rem",
                        borderRadius: 6,
                        border: "1px solid #6b3636",
                        background: "#140f10",
                        color: "#f2d7d7",
                      }
                }
              />
              <button
                type="button"
                className="btn small"
                disabled={
                  resetRunning ||
                  rebuildRunning ||
                  resetConfirmText.trim().toUpperCase() !== "RESET"
                }
                onClick={() => void runResetAndResync()}
                style={
                  isAdminShell
                    ? { background: "#b91c1c", border: "1px solid #991b1b" }
                    : { background: "#7d1f1f", borderColor: "#a83a3a" }
                }
              >
                {resetRunning ? "Resetting…" : "Reset + repull from scratch"}
              </button>
            </div>
            {resetError ? (
              <p className="banner error" style={{ marginTop: "0.6rem" }}>
                {resetError}
              </p>
            ) : null}
            {resetMessage ? (
              <p className="meta" style={{ marginTop: "0.6rem" }}>
                {resetMessage}
              </p>
            ) : null}
          </div>
        </section>
      )}

    </div>
  );
}

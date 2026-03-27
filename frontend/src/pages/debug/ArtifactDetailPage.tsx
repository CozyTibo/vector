import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";

import { formatArtifactListLine, workObjectTypeLabel } from "../../lib/executionModelDisplay";
import {
  adminCanonicalClient,
  fetchArtifactDetail,
  fetchMappingEventsForXref,
  sessionCanonicalClient,
  type ArtifactDetailResponse,
  type CanonicalClient,
} from "../../lib/canonicalApi";
import { getAdminPassword } from "../../lib/adminCredentials";

function TargetLink({
  ep,
  linkPrefix,
}: {
  ep: { type: string; id: string; label: string };
  linkPrefix: string;
}) {
  const text = ep.label?.trim() || ep.id.slice(0, 8) + "…";
  if (ep.type === "artifact") {
    return (
      <Link to={`${linkPrefix}/artifacts/${ep.id}`} className="link-inline" title={ep.id}>
        {text}
      </Link>
    );
  }
  if (ep.type === "actor") {
    return (
      <Link to={`${linkPrefix}/actors/${ep.id}`} className="link-inline" title={ep.id}>
        {text}
      </Link>
    );
  }
  return (
    <span title={ep.id}>
      {ep.type}: {text}
    </span>
  );
}

function splitRels(artifactId: string, rels: ArtifactDetailResponse["relationships"]) {
  const outgoing: typeof rels = [];
  const incoming: typeof rels = [];
  for (const r of rels) {
    if (r.subject.type === "artifact" && r.subject.id === artifactId) {
      outgoing.push(r);
    }
    if (r.object.type === "artifact" && r.object.id === artifactId) {
      incoming.push(r);
    }
  }
  return { outgoing, incoming };
}

function clientTag(c: CanonicalClient): string {
  return c.kind === "session" ? "session" : `admin:${c.tenantId}`;
}

export default function ArtifactDetailPage() {
  const { artifactId = "", tenantId } = useParams<{ artifactId: string; tenantId?: string }>();
  const adminPw = tenantId ? getAdminPassword() : null;
  const client = useMemo((): CanonicalClient | null => {
    if (tenantId) {
      if (!adminPw) {
        return null;
      }
      return adminCanonicalClient(tenantId, adminPw);
    }
    return sessionCanonicalClient();
  }, [tenantId, adminPw]);
  const entityBase = tenantId ? `/admin/tenants/${tenantId}/step3` : `/debug/canonical`;
  const cqTag = client ? clientTag(client) : "none";

  const detailQuery = useQuery({
    queryKey: ["canonical-artifact-detail", cqTag, artifactId],
    queryFn: () => fetchArtifactDetail(client!, artifactId),
    enabled: Boolean(artifactId) && client !== null,
  });

  const xrefs = detailQuery.data?.external_references ?? [];
  const mappingQueries = useQueries({
    queries: xrefs.map((x) => ({
      queryKey: ["canonical-mapping-events", cqTag, x.id],
      queryFn: () => fetchMappingEventsForXref(client!, x.id),
      enabled: Boolean(detailQuery.data) && xrefs.length > 0 && client !== null,
    })),
  });

  const mappingRows = useMemo(() => {
    const rows: { event_id: number; rule_version: string; effective_at: string; xref_id: string }[] =
      [];
    mappingQueries.forEach((q, i) => {
      const xrefId = xrefs[i]?.id;
      if (!q.data?.items || !xrefId) {
        return;
      }
      for (const ev of q.data.items) {
        rows.push({
          event_id: ev.id,
          rule_version: ev.rule_version,
          effective_at: ev.effective_at,
          xref_id: xrefId,
        });
      }
    });
    rows.sort((a, b) => b.effective_at.localeCompare(a.effective_at));
    return rows;
  }, [mappingQueries, xrefs]);

  const { outgoing, incoming } = useMemo(() => {
    if (!detailQuery.data) {
      return { outgoing: [], incoming: [] };
    }
    return splitRels(artifactId, detailQuery.data.relationships);
  }, [detailQuery.data, artifactId]);

  if (tenantId && !adminPw) {
    return (
      <div className="app legacy-debug">
        <p className="banner error">Admin session missing — sign in at /admin again.</p>
        <p className="meta">
          <Link to="/admin">← Admin</Link>
        </p>
      </div>
    );
  }

  const selfLine = useMemo(() => {
    if (!detailQuery.data) {
      return "";
    }
    const a = detailQuery.data.artifact;
    return formatArtifactListLine({
      artifact_kind_id: a.artifact_kind_id,
      title: a.title,
      summary: a.summary,
    });
  }, [detailQuery.data]);

  if (detailQuery.isError) {
    return (
      <div className="app legacy-debug">
        <p className="banner error">{(detailQuery.error as Error).message}</p>
        <p className="meta">
          <Link to={entityBase}>← Execution Graph</Link>
        </p>
      </div>
    );
  }

  if (detailQuery.isPending || !detailQuery.data) {
    return (
      <div className="app legacy-debug">
        <p className="status loading">Loading work object…</p>
        <p className="meta">
          <Link to={entityBase}>← Execution Graph</Link>
        </p>
      </div>
    );
  }

  const { artifact } = detailQuery.data;
  const typeLabel = workObjectTypeLabel(artifact.artifact_kind);

  return (
    <div className="app legacy-debug">
      <header className="header">
        <h1>{selfLine}</h1>
        <p className="meta">
          <Link to={entityBase}>← Execution Graph</Link>
          {" · "}
          <Link to={`${entityBase}?tab=graph`}>Graph</Link>
        </p>
      </header>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Work object</h2>
        <dl
          className="meta"
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "0.35rem 1rem",
          }}
        >
          <dt>Type</dt>
          <dd>{typeLabel}</dd>
          <dt>Name</dt>
          <dd>{selfLine}</dd>
          <dt>Internal ID</dt>
          <dd className="cell-muted">{artifact.id}</dd>
          <dt>Created at</dt>
          <dd>{artifact.created_at}</dd>
          <dt>Last observed</dt>
          <dd>{artifact.last_observed_at ?? "—"}</dd>
        </dl>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Connections FROM this work object</h2>
        <p className="meta" style={{ marginBottom: "0.75rem" }}>
          This work object is the <strong>subject</strong> of each connection below.
        </p>
        {outgoing.length === 0 ? (
          <p className="meta">None</p>
        ) : (
          <ul className="debug-connection-prose-list">
            {outgoing.map((r) => (
              <li key={r.id} className="debug-connection-prose">
                <span className="debug-bracket">[{selfLine}]</span>{" "}
                <span className="debug-relation-badge">{r.relation_kind}</span> →{" "}
                <TargetLink ep={r.object} linkPrefix={entityBase} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Connections TO this work object</h2>
        <p className="meta" style={{ marginBottom: "0.75rem" }}>
          This work object is the <strong>object</strong> of each connection below.
        </p>
        {incoming.length === 0 ? (
          <p className="meta">None</p>
        ) : (
          <ul className="debug-connection-prose-list">
            {incoming.map((r) => (
              <li key={r.id} className="debug-connection-prose">
                <TargetLink ep={r.subject} linkPrefix={entityBase} />{" "}
                <span className="debug-relation-badge">{r.relation_kind}</span> →{" "}
                <span className="debug-bracket">[{selfLine}]</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>External IDs</h2>
        <div className="table-wrap">
          <table className="data-table records-table">
            <thead>
              <tr>
                <th>connector</th>
                <th>external key</th>
                <th>last raw record</th>
              </tr>
            </thead>
            <tbody>
              {detailQuery.data.external_references.length === 0 ? (
                <tr>
                  <td colSpan={3} className="meta">
                    None
                  </td>
                </tr>
              ) : (
                detailQuery.data.external_references.map((x) => (
                  <tr key={x.id}>
                    <td>{x.connector}</td>
                    <td className="cell-muted">{x.external_key}</td>
                    <td>{x.last_raw_record_id ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Mapping history</h2>
        <p className="meta" style={{ marginBottom: "0.5rem" }}>
          Per–external-id mapping events for this work object.
        </p>
        {mappingQueries.some((q) => q.isPending) ? (
          <p className="status loading">Loading…</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table records-table">
              <thead>
                <tr>
                  <th>event_id</th>
                  <th>rule_version</th>
                  <th>effective_at</th>
                  <th className="cell-muted">external id</th>
                </tr>
              </thead>
              <tbody>
                {mappingRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="meta">
                      None
                    </td>
                  </tr>
                ) : (
                  mappingRows.map((r) => (
                    <tr key={`${r.xref_id}-${r.event_id}`}>
                      <td>{r.event_id}</td>
                      <td>{r.rule_version}</td>
                      <td>{r.effective_at}</td>
                      <td className="cell-muted">{r.xref_id.slice(0, 8)}…</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

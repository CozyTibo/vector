import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";

import { entityRoleLabel } from "../../lib/executionModelDisplay";
import {
  adminCanonicalClient,
  fetchActorDetail,
  sessionCanonicalClient,
  type ActorDetailResponse,
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
      {entityRoleLabel(ep.type)}: {text}
    </span>
  );
}

function otherEndpoint(
  actorId: string,
  r: ActorDetailResponse["relationships"][number],
): { type: string; id: string; label: string } {
  if (r.subject.type === "actor" && r.subject.id === actorId) {
    return r.object;
  }
  if (r.object.type === "actor" && r.object.id === actorId) {
    return r.subject;
  }
  return r.object;
}

function clientTag(c: CanonicalClient): string {
  return c.kind === "session" ? "session" : `admin:${c.tenantId}`;
}

export default function ActorDetailPage() {
  const { actorId = "", tenantId } = useParams<{ actorId: string; tenantId?: string }>();
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
    queryKey: ["canonical-actor-detail", cqTag, actorId],
    queryFn: () => fetchActorDetail(client!, actorId),
    enabled: Boolean(actorId) && client !== null,
  });

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
        <p className="status loading">Loading person…</p>
        <p className="meta">
          <Link to={entityBase}>← Execution Graph</Link>
        </p>
      </div>
    );
  }

  const { actor, external_identities, relationships } = detailQuery.data;
  const displayTitle = actor.display_name?.trim() || "Person";

  return (
    <div className="app legacy-debug">
      <header className="header">
        <h1>{displayTitle}</h1>
        <p className="meta">
          <Link to={`${entityBase}?tab=actors`}>← Execution Graph</Link>
        </p>
      </header>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Person</h2>
        <dl
          className="meta"
          style={{
            display: "grid",
            gridTemplateColumns: "max-content 1fr",
            gap: "0.35rem 1rem",
          }}
        >
          <dt>Internal ID</dt>
          <dd className="cell-muted">{actor.id}</dd>
          <dt>Role</dt>
          <dd>{actor.kind}</dd>
          <dt>Name</dt>
          <dd>{actor.display_name ?? "—"}</dd>
          <dt>Created at</dt>
          <dd>{actor.created_at}</dd>
        </dl>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Source identities</h2>
        <p className="meta" style={{ marginBottom: "0.5rem" }}>
          Connector accounts linked to this person.
        </p>
        <div className="table-wrap">
          <table className="data-table records-table">
            <thead>
              <tr>
                <th>connector</th>
                <th>external id</th>
                <th>last observed</th>
              </tr>
            </thead>
            <tbody>
              {external_identities.length === 0 ? (
                <tr>
                  <td colSpan={3} className="meta">
                    None
                  </td>
                </tr>
              ) : (
                external_identities.map((e) => (
                  <tr key={e.id}>
                    <td>{e.connector}</td>
                    <td className="cell-muted">{e.external_id}</td>
                    <td>{e.last_observed_at ?? "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Connections</h2>
        <div className="table-wrap">
          <table className="data-table records-table">
            <thead>
              <tr>
                <th>Relation</th>
                <th>Other</th>
                <th className="cell-muted">Kind</th>
                <th>valid_from</th>
                <th>valid_to</th>
              </tr>
            </thead>
            <tbody>
              {relationships.length === 0 ? (
                <tr>
                  <td colSpan={5} className="meta">
                    None
                  </td>
                </tr>
              ) : (
                relationships.map((r) => {
                  const other = otherEndpoint(actor.id, r);
                  return (
                    <tr key={r.id}>
                      <td>
                        <span className="debug-relation-badge">{r.relation_kind}</span>
                      </td>
                      <td>
                        <TargetLink ep={other} linkPrefix={entityBase} />
                      </td>
                      <td className="cell-muted">{entityRoleLabel(other.type)}</td>
                      <td>{r.valid_from}</td>
                      <td>{r.valid_to ?? "—"}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

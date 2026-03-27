import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import {
  fetchActorDetail,
  fetchArtifactDetail,
  type ActorDetailResponse,
  type ArtifactDetailResponse,
  type CanonicalClient,
} from "../../lib/canonicalApi";
import { formatArtifactListLine } from "../../lib/executionModelDisplay";

type Props = {
  client: CanonicalClient;
  /** Base path for React Router links (e.g. /debug/canonical). */
  linkPrefix: string;
  type: string;
  id: string;
};

function clientTag(c: CanonicalClient): string {
  return c.kind === "session" ? "session" : `admin:${c.tenantId}`;
}

/**
 * Resolves a semantic label for an artifact or actor (uses existing detail endpoints).
 * React Query dedupes identical (type, id) on the same page.
 */
export function DebugEntityLabel({ client, linkPrefix, type, id }: Props) {
  const q = useQuery({
    queryKey: ["debug-entity-label", clientTag(client), type, id],
    queryFn: async () => {
      if (type === "artifact") {
        return fetchArtifactDetail(client, id);
      }
      if (type === "actor") {
        return fetchActorDetail(client, id);
      }
      throw new Error("unsupported endpoint type");
    },
    enabled: type === "artifact" || type === "actor",
    staleTime: 60_000,
  });

  const personClass = "debug-pill debug-pill--person";
  const workClass = "debug-pill debug-pill--work";
  const artPath = `${linkPrefix}/artifacts/${id}`;
  const actPath = `${linkPrefix}/actors/${id}`;

  if (q.isPending) {
    return <span className="cell-muted">…</span>;
  }

  if (q.isError || !q.data) {
    const href = type === "artifact" ? artPath : actPath;
    const fallback = type === "artifact" ? "Work object" : "Person";
    return (
      <Link to={href} className="link-inline debug-entity-link">
        <span className={type === "actor" ? personClass : workClass}>{fallback}</span>{" "}
        <span className="debug-id-muted">({id.slice(0, 8)}…)</span>
      </Link>
    );
  }

  if (type === "actor") {
    const data = q.data as ActorDetailResponse;
    const name = data.actor.display_name?.trim() || "Person";
    return (
      <Link to={actPath} className="link-inline debug-entity-link">
        <span className={personClass}>{name}</span>
      </Link>
    );
  }

  const art = (q.data as ArtifactDetailResponse).artifact;
  const text = formatArtifactListLine({
    artifact_kind_id: art.artifact_kind_id,
    title: art.title,
    summary: art.summary,
  });

  return (
    <Link to={artPath} className="link-inline debug-entity-link">
      <span className={workClass}>{text}</span>
    </Link>
  );
}

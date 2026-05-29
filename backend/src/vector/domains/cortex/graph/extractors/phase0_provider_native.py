"""Phase 0 — provider-native edges from raw payload paths."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def _latest_raw(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity_id: uuid.UUID,
) -> tuple[CanonEntitySource, RawIngestionRecord] | None:
    row = session.execute(
        select(CanonEntitySource, RawIngestionRecord)
        .join(RawIngestionRecord, RawIngestionRecord.id == CanonEntitySource.raw_id)
        .where(
            CanonEntitySource.canon_entity_id == entity_id,
            CanonEntitySource.is_latest.is_(True),
        )
        .limit(1),
    ).first()
    if row is None:
        return None
    return row[0], row[1]


def _resolve_commit_sha(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connector: str,
    sha: str,
) -> uuid.UUID | None:
    key = derive_source_identity_key(
        connector=connector,
        resource_type="github.commit",
        external_id=sha,
    )
    entity_key = f"{tenant_id}:{key}"[:512]
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_key == entity_key,
        ),
    )


def extract_provider_native_edges(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> list[EdgeDraft]:
    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return []
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    observed_at = raw.fetched_at
    edges: list[EdgeDraft] = []

    if entity.entity_type == "pull_request":
        pr = payload.get("pull_request")
        if isinstance(pr, dict):

            def _append_pr_commit_edge(*, sha: str, kind: str, rule: str, evidence_ref: str) -> None:
                commit_id = _resolve_commit_sha(
                    session,
                    tenant_id=tenant_id,
                    connector=entity.connector,
                    sha=sha,
                )
                if commit_id is None:
                    return
                edges.append(
                    EdgeDraft(
                        relationship_kind=kind,
                        from_entity_id=entity.id,
                        to_entity_id=commit_id,
                        extractor_rule=rule,
                        evidence_kind="provider_field",
                        evidence_ref=evidence_ref,
                        evidence_snapshot={"sha": sha},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="certain",
                    ),
                )

            head = pr.get("head")
            if isinstance(head, dict):
                head_sha = head.get("sha")
                if isinstance(head_sha, str) and head_sha.strip():
                    _append_pr_commit_edge(
                        sha=head_sha.strip(),
                        kind="head_commit",
                        rule="github.pull_request.head.sha",
                        evidence_ref="pull_request.head.sha",
                    )
            merge_sha = pr.get("merge_commit_sha")
            if isinstance(merge_sha, str) and merge_sha.strip():
                _append_pr_commit_edge(
                    sha=merge_sha.strip(),
                    kind="merged_as_commit",
                    rule="github.pull_request.merge_commit_sha",
                    evidence_ref="pull_request.merge_commit_sha",
                )

    if entity.entity_type == "deployment":
        for key in ("deployment", "workflow_run"):
            segment = payload.get(key)
            if not isinstance(segment, dict):
                continue
            sha = segment.get("sha") or segment.get("head_sha")
            if not isinstance(sha, str) or not sha.strip():
                continue
            commit_id = _resolve_commit_sha(
                session,
                tenant_id=tenant_id,
                connector=entity.connector,
                sha=sha.strip(),
            )
            if commit_id is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="deploys",
                        from_entity_id=entity.id,
                        to_entity_id=commit_id,
                        extractor_rule=f"github.{key}.sha",
                        evidence_kind="provider_field",
                        evidence_ref=f"{key}.sha",
                        evidence_snapshot={"sha": sha.strip()},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
                break

    return edges

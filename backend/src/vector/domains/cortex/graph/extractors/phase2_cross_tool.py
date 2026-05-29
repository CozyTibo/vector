"""Phase 2 — cross-tool URLs, commit messages, and @mentions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.extractors.patterns import (
    GITHUB_AT_MENTION_RE,
    SLACK_ARCHIVE_URL_RE,
    SLACK_USER_MENTION_RE,
)
from vector.domains.cortex.graph.extractors.text_collect import collect_scannable_text
from vector.domains.cortex.graph.extractors.text_references import extract_reference_edges_from_text
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.domains.cortex.graph.resolve import resolve_entity_id_by_source_identity_key
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _resolve_slack_user(session: Session, *, tenant_id: uuid.UUID, slack_user_id: str) -> uuid.UUID | None:
    key = derive_source_identity_key(
        connector="slack",
        resource_type="slack.user",
        external_id=slack_user_id,
    )
    return resolve_entity_id_by_source_identity_key(session, tenant_id=tenant_id, source_identity_key=key)


def _slack_ts_from_permalink_token(p_token: str) -> str:
    """Convert Slack archive `p` token to message `ts` (channel_id:ts external_id suffix)."""
    if len(p_token) <= 10:
        return p_token
    return f"{p_token[:-6]}.{p_token[-6:]}"


def _resolve_slack_archive_message(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    channel_id: str,
    p_token: str,
) -> uuid.UUID | None:
    ts = _slack_ts_from_permalink_token(p_token)
    external_id = f"{channel_id}:{ts}"
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.connector == "slack",
            CanonEntity.entity_type == "message",
            CanonEntity.attrs_json["external_id"].astext == external_id,
        ),
    )


def _resolve_github_login(session: Session, *, tenant_id: uuid.UUID, login: str) -> uuid.UUID | None:
    key = derive_source_identity_key(
        connector="github",
        resource_type="github.user",
        external_id=login,
    )
    return resolve_entity_id_by_source_identity_key(session, tenant_id=tenant_id, source_identity_key=key)


def _extract_mentions(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    connector: str,
    field_path: str,
    text: str,
    source_raw_id: int,
    source_canon_source_id: int,
    observed_at: Any,
) -> list[EdgeDraft]:
    edges: list[EdgeDraft] = []
    if connector == "slack":
        for match in SLACK_USER_MENTION_RE.finditer(text):
            uid = match.group(1)
            actor = _resolve_slack_user(session, tenant_id=tenant_id, slack_user_id=uid)
            if actor is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="mentions",
                        from_entity_id=entity.id,
                        to_entity_id=actor,
                        extractor_rule="text.slack_user_mention",
                        evidence_kind="text_pattern",
                        evidence_ref="slack_user_mention_v1",
                        evidence_snapshot={"field": field_path, "user": uid},
                        source_raw_id=source_raw_id,
                        source_canon_source_id=source_canon_source_id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
    elif connector == "github":
        for match in GITHUB_AT_MENTION_RE.finditer(text):
            login = match.group(1)
            actor = _resolve_github_login(session, tenant_id=tenant_id, login=login)
            if actor is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="mentions",
                        from_entity_id=entity.id,
                        to_entity_id=actor,
                        extractor_rule="text.github_at_mention",
                        evidence_kind="text_pattern",
                        evidence_ref="github_at_mention_v1",
                        evidence_snapshot={"field": field_path, "login": login},
                        source_raw_id=source_raw_id,
                        source_canon_source_id=source_canon_source_id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
    return edges


def extract_cross_tool_edges(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> tuple[list[EdgeDraft], list[UnresolvedRefDraft]]:
    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return [], []
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    observed_at = raw.fetched_at
    resource_type = str(raw.resource_type or "")
    edges: list[EdgeDraft] = []
    unresolved: list[UnresolvedRefDraft] = []

    for field_path, text in collect_scannable_text(
        payload,
        entity_type=entity.entity_type,
        connector=entity.connector,
        resource_type=resource_type,
    ):
        ref_edges, ref_unresolved = extract_reference_edges_from_text(
            session,
            tenant_id=tenant_id,
            entity=entity,
            field_path=field_path,
            text=text,
            repo_fn=None,
            source_raw_id=int(raw.id),
            source_canon_source_id=source.id,
            observed_at=observed_at,
        )
        edges.extend(ref_edges)
        unresolved.extend(ref_unresolved)

        edges.extend(
            _extract_mentions(
                session,
                tenant_id=tenant_id,
                entity=entity,
                connector=entity.connector,
                field_path=field_path,
                text=text,
                source_raw_id=int(raw.id),
                source_canon_source_id=source.id,
                observed_at=observed_at,
            ),
        )

        if entity.connector == "slack":
            for match in SLACK_ARCHIVE_URL_RE.finditer(text):
                channel_id = match.group(1)
                p_token = match.group(2)
                target = _resolve_slack_archive_message(
                    session,
                    tenant_id=tenant_id,
                    channel_id=channel_id,
                    p_token=p_token,
                )
                ref = match.group(0)
                if target is not None:
                    edges.append(
                        EdgeDraft(
                            relationship_kind="references",
                            from_entity_id=entity.id,
                            to_entity_id=target,
                            extractor_rule="text.slack_archive_url",
                            evidence_kind="text_pattern",
                            evidence_ref="slack_archive_url_v1",
                            evidence_snapshot={
                                "field": field_path,
                                "matched": ref,
                                "channel_id": channel_id,
                                "permalink_ts": p_token,
                            },
                            source_raw_id=int(raw.id),
                            source_canon_source_id=source.id,
                            observed_at=observed_at,
                            confidence="high",
                        ),
                    )
                else:
                    unresolved.append(
                        UnresolvedRefDraft(
                            reference_kind="slack_archive_url",
                            reference_text=ref[:512],
                            extractor_rule="text.slack_archive_url",
                            evidence_snapshot={
                                "field": field_path,
                                "channel_id": channel_id,
                                "permalink_ts": p_token,
                            },
                        ),
                    )

    return edges, unresolved

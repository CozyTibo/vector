"""Phase 2 — cross-tool URLs, commit messages, and @mentions."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.extractors.patterns import (
    GITHUB_AT_MENTION_RE,
    MAX_TEXT_SCAN_CHARS,
    NOTION_PAGE_URL_RE,
    SLACK_USER_MENTION_RE,
)
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.domains.cortex.graph.resolve import resolve_entity_id_by_source_identity_key
from vector.domains.cortex.ingestion.live_idempotency import derive_source_identity_key
from vector.infrastructure.db.models.canon_entity import CanonEntity


def _resolve_notion_page(session: Session, *, tenant_id: uuid.UUID, page_id: str) -> uuid.UUID | None:
    needle = page_id.replace("-", "")
    rows = list(
        session.scalars(
            select(CanonEntity).where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "document",
                CanonEntity.connector == "notion",
            ),
        ).all(),
    )
    for ent in rows:
        attrs = ent.attrs_json if isinstance(ent.attrs_json, dict) else {}
        ext = str(attrs.get("external_id", "")).replace("-", "")
        if ext == needle or needle in ent.entity_key.replace("-", ""):
            return ent.id
    return None


def _resolve_slack_user(session: Session, *, tenant_id: uuid.UUID, slack_user_id: str) -> uuid.UUID | None:
    key = derive_source_identity_key(
        connector="slack",
        resource_type="slack.user",
        external_id=slack_user_id,
    )
    return resolve_entity_id_by_source_identity_key(session, tenant_id=tenant_id, source_identity_key=key)


def _resolve_github_login(session: Session, *, tenant_id: uuid.UUID, login: str) -> uuid.UUID | None:
    key = derive_source_identity_key(
        connector="github",
        resource_type="github.user",
        external_id=login,
    )
    return resolve_entity_id_by_source_identity_key(session, tenant_id=tenant_id, source_identity_key=key)


def _collect_text(payload: dict[str, Any], entity_type: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if entity_type == "message":
        msg = payload.get("message")
        if isinstance(msg, dict):
            text = msg.get("text")
            if isinstance(text, str) and text.strip():
                out.append(("message.text", text[:MAX_TEXT_SCAN_CHARS]))
    if entity_type == "commit":
        commit = payload.get("commit")
        if isinstance(commit, dict):
            message = commit.get("message")
            if isinstance(message, str) and message.strip():
                out.append(("commit.message", message[:MAX_TEXT_SCAN_CHARS]))
    return out


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
    edges: list[EdgeDraft] = []
    unresolved: list[UnresolvedRefDraft] = []

    for field_path, text in _collect_text(payload, entity.entity_type):
        for match in NOTION_PAGE_URL_RE.finditer(text):
            page_id = match.group(1)
            target = _resolve_notion_page(session, tenant_id=tenant_id, page_id=page_id)
            ref = match.group(0)
            if target is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="references",
                        from_entity_id=entity.id,
                        to_entity_id=target,
                        extractor_rule="text.notion_page_url",
                        evidence_kind="text_pattern",
                        evidence_ref="notion_page_url_v1",
                        evidence_snapshot={"field": field_path, "matched": ref},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
            else:
                unresolved.append(
                    UnresolvedRefDraft(
                        reference_kind="notion_page_url",
                        reference_text=ref[:512],
                        extractor_rule="text.notion_page_url",
                        evidence_snapshot={"field": field_path},
                    ),
                )

        if entity.connector == "slack":
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
                            source_raw_id=int(raw.id),
                            source_canon_source_id=source.id,
                            observed_at=observed_at,
                            confidence="high",
                        ),
                    )

        if entity.connector == "github":
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
                            source_raw_id=int(raw.id),
                            source_canon_source_id=source.id,
                            observed_at=observed_at,
                            confidence="high",
                        ),
                    )

    return edges, unresolved

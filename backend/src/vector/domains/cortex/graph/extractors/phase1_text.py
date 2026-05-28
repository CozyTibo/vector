"""Phase 1 — deterministic textual reference extraction."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.extractors.patterns import (
    GITHUB_HASH_NUM_RE,
    GITHUB_ISSUE_URL_RE,
    GITHUB_PR_URL_RE,
    LINEAR_IDENTIFIER_RE,
    MAX_TEXT_SCAN_CHARS,
)
from vector.domains.cortex.graph.extractors.phase0_provider_native import _latest_raw
from vector.infrastructure.db.models.canon_entity import CanonEntity


@dataclass(frozen=True)
class TextExtractResult:
    edges: list[EdgeDraft]
    unresolved: list[UnresolvedRefDraft]


def _text_blobs(payload: dict[str, Any], entity_type: str) -> list[tuple[str, str]]:
    blobs: list[tuple[str, str]] = []
    for key in ("pull_request", "issue", "comment", "message", "commit"):
        segment = payload.get(key)
        if isinstance(segment, dict):
            for field in ("body", "title", "message"):
                val = segment.get(field)
                if isinstance(val, str) and val.strip():
                    blobs.append((f"{key}.{field}", val[:MAX_TEXT_SCAN_CHARS]))
    if entity_type == "work_item":
        issue = payload.get("issue")
        if isinstance(issue, dict):
            for field in ("description", "title"):
                val = issue.get(field)
                if isinstance(val, str) and val.strip():
                    blobs.append((f"issue.{field}", val[:MAX_TEXT_SCAN_CHARS]))
    closing = payload.get("closing_issues")
    if isinstance(closing, list):
        for item in closing:
            if isinstance(item, dict):
                num = item.get("number")
                if isinstance(num, int):
                    blobs.append(("closing_issues", f"#{num}"))
    return blobs


def _resolve_repo_project_id(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    repo_full_name: str,
) -> uuid.UUID | None:
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_type == "project",
            CanonEntity.connector == "github",
            CanonEntity.attrs_json["full_name"].astext == repo_full_name,
        ),
    )


def _resolve_github_number(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    repo_full_name: str,
    number: int,
    is_pr: bool,
) -> uuid.UUID | None:
    repo_id = _resolve_repo_project_id(session, tenant_id=tenant_id, repo_full_name=repo_full_name)
    if repo_id is None:
        return None
    entity_type = "pull_request" if is_pr else "work_item"
    stmt = select(CanonEntity.id).where(
        CanonEntity.tenant_id == tenant_id,
        CanonEntity.entity_type == entity_type,
        CanonEntity.connector == "github",
        CanonEntity.attrs_json["number"].as_integer() == number,
    )
    if is_pr:
        stmt = stmt.where(CanonEntity.repository_entity_id == repo_id)
    return session.scalar(stmt.limit(1))


def _resolve_linear_identifier(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    identifier: str,
) -> uuid.UUID | None:
    ident = identifier.upper()
    return session.scalar(
        select(CanonEntity.id).where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.entity_type == "work_item",
            CanonEntity.connector == "linear",
            CanonEntity.attrs_json["identifier"].astext == ident,
        ),
    )


def extract_text_references(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
) -> TextExtractResult:
    pair = _latest_raw(session, tenant_id=tenant_id, entity_id=entity.id)
    if pair is None:
        return TextExtractResult(edges=[], unresolved=[])
    source, raw = pair
    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    observed_at = raw.fetched_at
    edges: list[EdgeDraft] = []
    unresolved: list[UnresolvedRefDraft] = []
    repo_fn: str | None = None
    if entity.repository_entity_id:
        repo_ent = session.get(CanonEntity, entity.repository_entity_id)
        if repo_ent and isinstance(repo_ent.attrs_json, dict):
            repo_fn = repo_ent.attrs_json.get("full_name")
    if not repo_fn:
        pr = payload.get("pull_request")
        if isinstance(pr, dict):
            head = pr.get("head")
            if isinstance(head, dict):
                repo = head.get("repo")
                if isinstance(repo, dict) and isinstance(repo.get("full_name"), str):
                    repo_fn = repo["full_name"]

    for field_path, text in _text_blobs(payload, entity.entity_type):
        for match in LINEAR_IDENTIFIER_RE.finditer(text):
            ident = match.group(1)
            target = _resolve_linear_identifier(session, tenant_id=tenant_id, identifier=ident)
            if target is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="references",
                        from_entity_id=entity.id,
                        to_entity_id=target,
                        extractor_rule="text.linear_identifier",
                        evidence_kind="text_pattern",
                        evidence_ref="linear_identifier_v1",
                        evidence_snapshot={"field": field_path, "matched": ident},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
            else:
                unresolved.append(
                    UnresolvedRefDraft(
                        reference_kind="linear_identifier",
                        reference_text=ident,
                        extractor_rule="text.linear_identifier",
                        evidence_snapshot={"field": field_path, "matched": ident},
                    ),
                )

        for match in GITHUB_PR_URL_RE.finditer(text):
            _owner, repo, num_s = match.groups()
            full = f"{_owner}/{repo}"
            target = _resolve_github_number(
                session,
                tenant_id=tenant_id,
                repo_full_name=full,
                number=int(num_s),
                is_pr=True,
            )
            ref_text = match.group(0)
            if target is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="references",
                        from_entity_id=entity.id,
                        to_entity_id=target,
                        extractor_rule="text.github_pr_url",
                        evidence_kind="text_pattern",
                        evidence_ref="github_pr_url_v1",
                        evidence_snapshot={"field": field_path, "matched": ref_text},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
            else:
                unresolved.append(
                    UnresolvedRefDraft(
                        reference_kind="github_pr_url",
                        reference_text=ref_text[:512],
                        extractor_rule="text.github_pr_url",
                        evidence_snapshot={"field": field_path},
                    ),
                )

        for match in GITHUB_ISSUE_URL_RE.finditer(text):
            _owner, repo, num_s = match.groups()
            full = f"{_owner}/{repo}"
            target = _resolve_github_number(
                session,
                tenant_id=tenant_id,
                repo_full_name=full,
                number=int(num_s),
                is_pr=False,
            )
            ref_text = match.group(0)
            if target is not None:
                edges.append(
                    EdgeDraft(
                        relationship_kind="references",
                        from_entity_id=entity.id,
                        to_entity_id=target,
                        extractor_rule="text.github_issue_url",
                        evidence_kind="text_pattern",
                        evidence_ref="github_issue_url_v1",
                        evidence_snapshot={"field": field_path, "matched": ref_text},
                        source_raw_id=int(raw.id),
                        source_canon_source_id=source.id,
                        observed_at=observed_at,
                        confidence="high",
                    ),
                )
            else:
                unresolved.append(
                    UnresolvedRefDraft(
                        reference_kind="github_issue_url",
                        reference_text=ref_text[:512],
                        extractor_rule="text.github_issue_url",
                        evidence_snapshot={"field": field_path},
                    ),
                )

        if repo_fn:
            for match in GITHUB_HASH_NUM_RE.finditer(text):
                num = int(match.group(1))
                is_pr = "pull request" in text.lower() or "pr " in text.lower()
                target = _resolve_github_number(
                    session,
                    tenant_id=tenant_id,
                    repo_full_name=repo_fn,
                    number=num,
                    is_pr=is_pr,
                )
                token = f"#{num}"
                if target is not None:
                    edges.append(
                        EdgeDraft(
                            relationship_kind="references",
                            from_entity_id=entity.id,
                            to_entity_id=target,
                            extractor_rule="text.github_hash_number",
                            evidence_kind="text_pattern",
                            evidence_ref="github_hash_number_v1",
                            evidence_snapshot={
                                "field": field_path,
                                "matched": token,
                                "repo": repo_fn,
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
                            reference_kind="github_hash_number",
                            reference_text=f"{repo_fn}{token}",
                            extractor_rule="text.github_hash_number",
                            evidence_snapshot={"field": field_path, "repo": repo_fn},
                        ),
                    )

    return TextExtractResult(edges=edges, unresolved=unresolved)

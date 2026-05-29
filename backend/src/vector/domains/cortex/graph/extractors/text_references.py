"""Shared text reference extraction (GitHub URLs, Linear ids, etc.)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.graph.edges import EdgeDraft, UnresolvedRefDraft
from vector.domains.cortex.graph.extractors.patterns import (
    GITHUB_HASH_NUM_RE,
    GITHUB_ISSUE_URL_RE,
    GITHUB_PR_URL_RE,
    GITHUB_SHORTHAND_RE,
    LINEAR_IDENTIFIER_RE,
    LINEAR_ISSUE_URL_RE,
    NOTION_PAGE_URL_RE,
    NOTION_SITE_URL_RE,
)
from vector.infrastructure.db.models.canon_entity import CanonEntity


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


def _normalize_notion_page_id(page_id: str) -> str:
    return page_id.replace("-", "").lower()


def _resolve_notion_page(session: Session, *, tenant_id: uuid.UUID, page_id: str) -> uuid.UUID | None:
    needle = _normalize_notion_page_id(page_id)
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
        for raw_id in (attrs.get("notion_id"), attrs.get("external_id")):
            if isinstance(raw_id, str) and _normalize_notion_page_id(raw_id) == needle:
                return ent.id
        if needle in ent.entity_key.replace("-", "").lower():
            return ent.id
    return None


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


def repo_full_name_for_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    payload: dict,
) -> str | None:
    if entity.repository_entity_id:
        repo_ent = session.get(CanonEntity, entity.repository_entity_id)
        if repo_ent and isinstance(repo_ent.attrs_json, dict):
            fn = repo_ent.attrs_json.get("full_name")
            if isinstance(fn, str) and fn:
                return fn
    pr = payload.get("pull_request")
    if isinstance(pr, dict):
        head = pr.get("head")
        if isinstance(head, dict):
            repo = head.get("repo")
            if isinstance(repo, dict) and isinstance(repo.get("full_name"), str):
                return repo["full_name"]
    return None


def _append_linear_reference(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    field_path: str,
    ident: str,
    ref_text: str,
    extractor_rule: str,
    evidence_ref: str,
    source_raw_id: int,
    source_canon_source_id: int,
    observed_at: datetime,
    seen_linear: set[str],
    edges: list[EdgeDraft],
    unresolved: list[UnresolvedRefDraft],
) -> None:
    ident_u = ident.upper()
    if ident_u in seen_linear:
        return
    seen_linear.add(ident_u)
    target = _resolve_linear_identifier(session, tenant_id=tenant_id, identifier=ident_u)
    if target is not None:
        edges.append(
            EdgeDraft(
                relationship_kind="references",
                from_entity_id=entity.id,
                to_entity_id=target,
                extractor_rule=extractor_rule,
                evidence_kind="text_pattern",
                evidence_ref=evidence_ref,
                evidence_snapshot={"field": field_path, "matched": ref_text},
                source_raw_id=source_raw_id,
                source_canon_source_id=source_canon_source_id,
                observed_at=observed_at,
                confidence="high",
            ),
        )
    else:
        unresolved.append(
            UnresolvedRefDraft(
                reference_kind="linear_issue",
                reference_text=ref_text[:512],
                extractor_rule=extractor_rule,
                evidence_snapshot={"field": field_path, "matched": ident_u},
            ),
        )


def _append_notion_reference(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    field_path: str,
    page_id: str,
    ref_text: str,
    extractor_rule: str,
    evidence_ref: str,
    source_raw_id: int,
    source_canon_source_id: int,
    observed_at: datetime,
    seen_notion: set[str],
    edges: list[EdgeDraft],
    unresolved: list[UnresolvedRefDraft],
) -> None:
    needle = _normalize_notion_page_id(page_id)
    if needle in seen_notion:
        return
    seen_notion.add(needle)
    target = _resolve_notion_page(session, tenant_id=tenant_id, page_id=page_id)
    if target is not None:
        edges.append(
            EdgeDraft(
                relationship_kind="references",
                from_entity_id=entity.id,
                to_entity_id=target,
                extractor_rule=extractor_rule,
                evidence_kind="text_pattern",
                evidence_ref=evidence_ref,
                evidence_snapshot={"field": field_path, "matched": ref_text},
                source_raw_id=source_raw_id,
                source_canon_source_id=source_canon_source_id,
                observed_at=observed_at,
                confidence="high",
            ),
        )
    else:
        unresolved.append(
            UnresolvedRefDraft(
                reference_kind="notion_page_url",
                reference_text=ref_text[:512],
                extractor_rule=extractor_rule,
                evidence_snapshot={"field": field_path, "page_id": page_id},
            ),
        )


def extract_reference_edges_from_text(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    entity: CanonEntity,
    field_path: str,
    text: str,
    repo_fn: str | None,
    source_raw_id: int,
    source_canon_source_id: int,
    observed_at: datetime,
) -> tuple[list[EdgeDraft], list[UnresolvedRefDraft]]:
    edges: list[EdgeDraft] = []
    unresolved: list[UnresolvedRefDraft] = []
    seen_linear: set[str] = set()
    seen_notion: set[str] = set()

    for match in LINEAR_IDENTIFIER_RE.finditer(text):
        _append_linear_reference(
            session=session,
            tenant_id=tenant_id,
            entity=entity,
            field_path=field_path,
            ident=match.group(1),
            ref_text=match.group(0),
            extractor_rule="text.linear_identifier",
            evidence_ref="linear_identifier_v1",
            source_raw_id=source_raw_id,
            source_canon_source_id=source_canon_source_id,
            observed_at=observed_at,
            seen_linear=seen_linear,
            edges=edges,
            unresolved=unresolved,
        )

    for match in LINEAR_ISSUE_URL_RE.finditer(text):
        _append_linear_reference(
            session=session,
            tenant_id=tenant_id,
            entity=entity,
            field_path=field_path,
            ident=match.group(1),
            ref_text=match.group(0),
            extractor_rule="text.linear_issue_url",
            evidence_ref="linear_issue_url_v1",
            source_raw_id=source_raw_id,
            source_canon_source_id=source_canon_source_id,
            observed_at=observed_at,
            seen_linear=seen_linear,
            edges=edges,
            unresolved=unresolved,
        )

    for regex, rule, ref in (
        (NOTION_PAGE_URL_RE, "text.notion_page_url", "notion_page_url_v1"),
        (NOTION_SITE_URL_RE, "text.notion_site_url", "notion_site_url_v1"),
    ):
        for match in regex.finditer(text):
            _append_notion_reference(
                session=session,
                tenant_id=tenant_id,
                entity=entity,
                field_path=field_path,
                page_id=match.group(1),
                ref_text=match.group(0),
                extractor_rule=rule,
                evidence_ref=ref,
                source_raw_id=source_raw_id,
                source_canon_source_id=source_canon_source_id,
                observed_at=observed_at,
                seen_notion=seen_notion,
                edges=edges,
                unresolved=unresolved,
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
                    source_raw_id=source_raw_id,
                    source_canon_source_id=source_canon_source_id,
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
                    source_raw_id=source_raw_id,
                    source_canon_source_id=source_canon_source_id,
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

    for match in GITHUB_SHORTHAND_RE.finditer(text):
        owner, repo, num_s = match.groups()
        full = f"{owner}/{repo}"
        is_pr = "pull request" in text.lower() or "pr " in text.lower()
        target = _resolve_github_number(
            session,
            tenant_id=tenant_id,
            repo_full_name=full,
            number=int(num_s),
            is_pr=is_pr,
        )
        ref_text = match.group(0)
        if target is not None:
            edges.append(
                EdgeDraft(
                    relationship_kind="references",
                    from_entity_id=entity.id,
                    to_entity_id=target,
                    extractor_rule="text.github_shorthand",
                    evidence_kind="text_pattern",
                    evidence_ref="github_shorthand_v1",
                    evidence_snapshot={"field": field_path, "matched": ref_text},
                    source_raw_id=source_raw_id,
                    source_canon_source_id=source_canon_source_id,
                    observed_at=observed_at,
                    confidence="high",
                ),
            )
        else:
            unresolved.append(
                UnresolvedRefDraft(
                    reference_kind="github_shorthand",
                    reference_text=ref_text[:512],
                    extractor_rule="text.github_shorthand",
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
                        source_raw_id=source_raw_id,
                        source_canon_source_id=source_canon_source_id,
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

    return edges, unresolved

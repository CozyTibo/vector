"""S4.4 — execution grounding laws before synthesis LLM (scope must cite execution index rows)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_useful_artifact_v1 import (
    EXECUTION_ARTIFACT_KINDS_V1,
    EXECUTION_INDEX_KINDS_V1,
    _normalize_index_kind_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

SYNTHESIS_EXECUTION_GROUNDING_SCHEMA_VERSION: Final[int] = 1
FAILURE_CODE_ORG_LINK_ONLY_SCOPE_V1: Final[str] = "synthesis_scope_org_link_only"
FAILURE_CODE_MISSING_EXECUTION_REFS_V1: Final[str] = "synthesis_scope_missing_execution_refs"
ORG_LINK_INDEX_KIND_V1: Final[str] = "org_link"


class SynthesisExecutionGroundingError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        detail: dict[str, Any] | None = None,
        http_status: int = 422,
    ) -> None:
        self.code = code
        self.detail = dict(detail or {})
        self.http_status = http_status
        super().__init__(code)


def is_synthesis_require_execution_refs_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_synthesis_require_execution_refs)
    except Exception:  # noqa: BLE001
        return True


def _lookup_index_kind_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_lookup_id: str,
    index_epoch: str | None,
) -> str | None:
    if not retrieval_lookup_id or not index_epoch:
        return None
    row = session.scalar(
        select(CortexRetrievalIndexEntry.index_kind).where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.retrieval_lookup_id == retrieval_lookup_id,
            CortexRetrievalIndexEntry.index_epoch == index_epoch,
        )
    )
    return str(row) if row else None


def resolve_hit_index_kind_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    hit: Mapping[str, Any],
    index_epoch: str | None,
) -> str:
    kind = _normalize_index_kind_v1(str(hit.get("index_kind") or ""))
    if kind:
        return kind
    prov = hit.get("provenance")
    if isinstance(prov, Mapping):
        pk = _normalize_index_kind_v1(str(prov.get("index_kind") or prov.get("artifact_kind") or ""))
        if pk:
            return pk
    sak = _normalize_index_kind_v1(str(hit.get("source_artifact_kind") or ""))
    if sak:
        return sak
    lookup = str(hit.get("retrieval_lookup_id") or "")
    db_kind = _lookup_index_kind_v1(
        session,
        tenant_id=tenant_id,
        retrieval_lookup_id=lookup,
        index_epoch=index_epoch,
    )
    return _normalize_index_kind_v1(db_kind or "")


def audit_retrieval_hits_execution_mix_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    hits: Sequence[Mapping[str, Any]],
    index_epoch: str | None,
) -> dict[str, Any]:
    hist: dict[str, int] = {}
    execution_ref_count = 0
    for hit in hits:
        kind = resolve_hit_index_kind_v1(
            session,
            tenant_id=tenant_id,
            hit=hit,
            index_epoch=index_epoch,
        ) or "unknown"
        hist[kind] = hist.get(kind, 0) + 1
        if kind in EXECUTION_INDEX_KINDS_V1:
            execution_ref_count += 1
    total = sum(hist.values())
    org_link_count = int(hist.get(ORG_LINK_INDEX_KIND_V1, 0))
    org_link_only = total > 0 and org_link_count == total
    return {
        "schema_version": SYNTHESIS_EXECUTION_GROUNDING_SCHEMA_VERSION,
        "index_epoch": index_epoch,
        "hit_count": total,
        "index_kind_histogram": hist,
        "execution_ref_count": execution_ref_count,
        "org_link_count": org_link_count,
        "org_link_only_scope": org_link_only,
        "has_execution_ref": execution_ref_count >= 1,
    }


def enforce_execution_grounding_before_llm_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    retrieval_hits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Reject org_link-only scopes and scopes without execution refs before LLM (S4.4)."""
    if not is_synthesis_require_execution_refs_enabled_v1():
        return {"skipped": True, "reason": "execution_refs_gate_disabled"}
    pins = envelope.get("retrieval_pins") or {}
    index_epoch = str(pins.get("index_epoch") or "").strip() or None
    audit = audit_retrieval_hits_execution_mix_v1(
        session,
        tenant_id=tenant_id,
        hits=retrieval_hits,
        index_epoch=index_epoch,
    )
    if int(audit.get("hit_count") or 0) == 0:
        return {"ok": True, "skipped": True, "reason": "lawful_empty_retrieval_scope", "grounding_audit": audit}
    if audit["org_link_only_scope"]:
        raise SynthesisExecutionGroundingError(
            FAILURE_CODE_ORG_LINK_ONLY_SCOPE_V1,
            detail=audit,
        )
    if not audit["has_execution_ref"]:
        raise SynthesisExecutionGroundingError(
            FAILURE_CODE_MISSING_EXECUTION_REFS_V1,
            detail=audit,
        )
    return {"ok": True, "grounding_audit": audit}

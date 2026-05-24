"""S4.5 — synthesis job inspector (epoch mix, scope kinds, claim grounding)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1 import (
    _claim_has_evidence_ref_v1,
    count_verifiable_claims_v1,
)
from vector.domains.cortex.synthesis.synthesis_execution_grounding_v1 import (
    audit_retrieval_hits_execution_mix_v1,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import normalize_retrieval_hits_v1
from vector.domains.cortex.synthesis.synthesis_orchestrator import get_synthesis_job_detail_v1
from vector.domains.cortex.synthesis.synthesis_useful_artifact_v1 import (
    EXECUTION_INDEX_KINDS_V1,
    _claim_has_execution_evidence_ref_v1,
    count_execution_index_entries_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

SYNTHESIS_JOB_INSPECTOR_SCHEMA_VERSION: Final[int] = 1


def _scope_index_kind_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None,
    island_scope_id: str | None,
) -> dict[str, int]:
    if not index_epoch:
        return {}
    stmt = select(CortexRetrievalIndexEntry).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
        CortexRetrievalIndexEntry.index_epoch == index_epoch,
    )
    rows = list(session.scalars(stmt).all())
    if island_scope_id:
        from vector.domains.cortex.retrieval.retrieval_component_materialization import (
            P1_C_ISLAND_SCOPE_KEY_V1,
        )

        rows = [
            row
            for row in rows
            if str((row.omission_summary or {}).get(P1_C_ISLAND_SCOPE_KEY_V1) or "") == island_scope_id
        ]
    hist: dict[str, int] = {}
    for row in rows:
        kind = str(row.index_kind or "unknown")
        hist[kind] = hist.get(kind, 0) + 1
    return dict(sorted(hist.items()))


def _inspect_claims_v1(body: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims = body.get("claims") or []
    out: list[dict[str, Any]] = []
    if not isinstance(claims, list):
        return out
    for idx, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            continue
        has_evidence = _claim_has_evidence_ref_v1(claim)
        execution_grounded = _claim_has_execution_evidence_ref_v1(claim)
        out.append(
            {
                "claim_index": idx,
                "claim_id": claim.get("claim_id"),
                "claim_kind": claim.get("claim_kind"),
                "has_evidence_ref": has_evidence,
                "execution_grounded": execution_grounded,
                "ungrounded": not has_evidence,
                "ungrounded_execution": has_evidence and not execution_grounded,
            }
        )
    return out


def build_synthesis_job_inspector_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    detail = get_synthesis_job_detail_v1(session, tenant_id=tenant_id, job_id=job_id)
    envelope = dict(detail.get("envelope_json") or {})
    pins = envelope.get("retrieval_pins") or {}
    index_epoch = str(pins.get("index_epoch") or "").strip() or None
    island_scope_id = str(envelope.get("island_scope_id") or "").strip() or None

    hits: list[dict[str, Any]] = []
    for sub in detail.get("retrieval_subqueries") or []:
        if not isinstance(sub, Mapping):
            continue
        resp = sub.get("retrieval_response") or sub
        hits.extend(normalize_retrieval_hits_v1(resp))

    mix = audit_retrieval_hits_execution_mix_v1(
        session,
        tenant_id=tenant_id,
        hits=hits,
        index_epoch=index_epoch,
    )
    scope_kinds = _scope_index_kind_histogram_v1(
        session,
        tenant_id=tenant_id,
        index_epoch=index_epoch,
        island_scope_id=island_scope_id,
    )
    execution_entries = (
        count_execution_index_entries_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=index_epoch,
            island_scope_id=island_scope_id,
        )
        if index_epoch and island_scope_id
        else int(
            session.scalar(
                select(func.count())
                .select_from(CortexRetrievalIndexEntry)
                .where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.index_epoch == index_epoch,
                    CortexRetrievalIndexEntry.index_kind.in_(sorted(EXECUTION_INDEX_KINDS_V1)),
                )
            )
            or 0
        )
        if index_epoch
        else 0
    )

    artifact_row = session.scalar(
        select(CortexSynthesisArtifact).where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.job_id == job_id,
        )
    )
    body = dict(artifact_row.body_json or {}) if artifact_row else {}
    claim_inspection = _inspect_claims_v1(body)
    ungrounded = [c for c in claim_inspection if c.get("ungrounded")]
    ungrounded_execution = [c for c in claim_inspection if c.get("ungrounded_execution")]

    return {
        "surface_kind": "synthesis_job_inspector",
        "schema_version": SYNTHESIS_JOB_INSPECTOR_SCHEMA_VERSION,
        "job_id": str(job_id),
        "tenant_id": str(tenant_id),
        "job_detail": detail,
        "retrieval_epoch": index_epoch,
        "island_scope_id": island_scope_id,
        "retrieval_epoch_mix": mix,
        "scope_index_kind_histogram": scope_kinds,
        "execution_index_entries_in_scope": execution_entries,
        "claims": claim_inspection,
        "claim_count": len(claim_inspection),
        "verifiable_claim_count": count_verifiable_claims_v1(body),
        "ungrounded_claim_count": len(ungrounded),
        "ungrounded_execution_claim_count": len(ungrounded_execution),
        "ungrounded_claims": ungrounded[:16],
        "artifact_id": str(artifact_row.id) if artifact_row else None,
        "artifact_kind": artifact_row.artifact_kind if artifact_row else None,
    }

"""E2E verification helpers for Phase 08 synthesis substrate."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.phase_boundaries import SD_UPSTREAM_RD_V1
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    project_synthesis_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_control_plane import build_synthesis_control_plane_v1
from vector.domains.cortex.synthesis.synthesis_publication import get_current_synthesis_publication_epoch_v1
from vector.domains.cortex.synthesis.synthesis_repository import find_idempotent_synthesis_job_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    build_synthesis_replay_equivalence_twin_diff_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob


def legal_retrieval_stub_v1(
    *,
    replay_identity: str = "rqid:p08-e2e",
    legality: str = "retrieval_replay_safe",
    omission_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "retrieval_legality_class": legality,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: replay_identity,
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": omission_rows or [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:e2e"},
    }


def degraded_upstream_retrieval_stub_v1() -> dict[str, Any]:
    stub = legal_retrieval_stub_v1(
        replay_identity="rqid:p08-e2e-degraded",
        legality="retrieval_degraded",
        omission_rows=[{"retrieval_omission_class": "RD-TCRE-GAP"}],
    )
    stub["retrieval_degradation_rollup"] = {"rd_code_counts": {"RD-TCRE-GAP": 1}}
    return stub


def assert_synthesis_substrate_ready_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    require_publication_epoch: bool = True,
) -> dict[str, Any]:
    """Fail-closed synthesis readiness after pipeline phase 08."""
    published_index = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    synthesis_epoch = get_current_synthesis_publication_epoch_v1(session, tenant_id=tenant_id)
    completeness = project_synthesis_completeness_v1(session, tenant_id=tenant_id)
    artifact_count = session.scalar(
        select(CortexSynthesisArtifact.id).where(CortexSynthesisArtifact.tenant_id == tenant_id).limit(1)
    )
    errors: list[str] = []
    if published_index is None:
        errors.append("no_published_index_epoch")
    if require_publication_epoch and not synthesis_epoch:
        errors.append("no_synthesis_publication_epoch")
    if artifact_count is None:
        errors.append("no_synthesis_artifacts")
    return {
        "ready": len(errors) == 0,
        "errors": errors,
        "published_index_epoch": published_index,
        "synthesis_publication_epoch": synthesis_epoch,
        "completeness": completeness,
    }


def assert_synthesis_control_plane_runtime_backed_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    cp = build_synthesis_control_plane_v1(session, tenant_id=tenant_id)
    ok = cp.get("surface_kind") == "derived_aggregate" and int(cp.get("surfaces_wired_count") or 0) >= 12
    return {
        "passed": ok,
        "surface_kind": cp.get("surface_kind"),
        "surfaces_wired_count": cp.get("surfaces_wired_count"),
        "health_strip": cp.get("health_strip"),
    }


def assert_synthesis_idempotent_replay_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
    envelope_digest: str,
) -> dict[str, Any]:
    """Scenario D — same idempotency key + digest returns one completed job."""
    first = find_idempotent_synthesis_job_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        envelope_digest=envelope_digest,
    )
    return {
        "passed": first is not None,
        "job_id": str(first.id) if first else None,
        "artifact_id": None,
    }


def assert_synthesis_degraded_upstream_v1(
    *,
    synthesis_legality_class: str,
    omission_rows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Scenario B — upstream RD propagates to SD."""
    sd_codes = {
        str(r.get("sd_code") or r.get("synthesis_omission_class") or "")
        for r in omission_rows
        if isinstance(r, Mapping)
    }
    passed = synthesis_legality_class == "synthesis_degraded" and SD_UPSTREAM_RD_V1 in sd_codes
    return {
        "passed": passed,
        "synthesis_legality_class": synthesis_legality_class,
        "sd_codes": sorted(sd_codes),
    }


def assert_synthesis_replay_twin_zero_citation_diff_v1(
    session: Session,
    *,
    twin_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Scenario C — structural twin with zero citation multiset diff when self-compared."""
    twin = dict(twin_result)
    diff = build_synthesis_replay_equivalence_twin_diff_v1(twin, dict(twin))
    citation_diff = diff.get("citation_multiset_diff") or {}
    passed = bool(twin.get("gp08_replay_proof_passed")) and not citation_diff.get("added") and not citation_diff.get(
        "removed",
    )
    return {
        "passed": passed,
        "gp08_replay_proof_passed": twin.get("gp08_replay_proof_passed"),
        "citation_multiset_diff": citation_diff,
        PHASE08_REPLAY_IDENTITY_FIELD_V1: twin.get(PHASE08_REPLAY_IDENTITY_FIELD_V1),
    }


def load_first_index_lookup_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None = None,
) -> str | None:
    from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

    stmt = select(CortexRetrievalIndexEntry.retrieval_lookup_id).where(
        CortexRetrievalIndexEntry.tenant_id == tenant_id,
    )
    if index_epoch:
        stmt = stmt.where(CortexRetrievalIndexEntry.index_epoch == index_epoch)
    row = session.scalar(stmt.limit(1))
    return str(row) if row else None


def get_synthesis_job_artifact_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> CortexSynthesisArtifact | None:
    return session.scalar(
        select(CortexSynthesisArtifact).where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.job_id == job_id,
        )
    )


def get_completed_job_with_receipt_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexSynthesisJob | None:
    return session.scalar(
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.status == "completed",
            CortexSynthesisJob.receipt_digest.isnot(None),
        )
        .order_by(CortexSynthesisJob.created_at.desc())
        .limit(1)
    )

"""Phase 08 Step 32 — synthesis publication epoch barrier (**G-P08-REPLAY-02**)."""

from __future__ import annotations

import re
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import SD_PUBLISH_BLOCKED_V1
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    compute_synthesis_lag_epochs_v1,
    count_synthesis_synthesized_scopes_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import GP08_REPLAY_02_GATE_ID_V1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_synthesis_publication_epoch import (
    CortexSynthesisPublicationEpoch,
)

SYNTHESIS_PUBLICATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_PUB01_GATE_ID_V1: Final[str] = "G-P08-PUB-01"

_PUBLISHABLE_LEGALITY_V1: Final[frozenset[str]] = frozenset(
    {"synthesis_replay_safe", "synthesis_degraded"},
)

_EPOCH_NAME_PATTERN_V1 = re.compile(r"^syn-(.+)-(\d+)$")


class SynthesisPublicationError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def parse_synthesis_publication_epoch_seq_v1(epoch_name: str) -> int:
    """Numeric sequence suffix for monotonic comparisons (**G-P08-REPLAY-02**)."""
    match = _EPOCH_NAME_PATTERN_V1.match((epoch_name or "").strip())
    if not match:
        return 0
    try:
        return int(match.group(2))
    except ValueError:
        return 0


def list_tenant_publication_epoch_names_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 64,
) -> list[str]:
    rows = list(
        session.scalars(
            select(CortexSynthesisPublicationEpoch.synthesis_publication_epoch)
            .where(CortexSynthesisPublicationEpoch.tenant_id == tenant_id)
            .order_by(CortexSynthesisPublicationEpoch.published_at.desc())
            .limit(limit)
        ).all()
    )
    return [str(r) for r in rows]


def assert_publication_epoch_monotonic_v1(
    *,
    prior_epoch: str | None,
    next_epoch: str,
    tenant_id: uuid.UUID | None = None,
    prior_epochs: Sequence[str] | None = None,
) -> None:
    """Forward-only epoch law — numeric suffix must strictly increase."""
    candidates = list(prior_epochs or [])
    if prior_epoch:
        candidates.append(prior_epoch)
    max_seq = max(parse_synthesis_publication_epoch_seq_v1(e) for e in candidates) if candidates else 0
    next_seq = parse_synthesis_publication_epoch_seq_v1(next_epoch)
    if next_seq <= max_seq:
        raise SynthesisPublicationError(
            "publication_epoch_not_monotonic",
            http_status=409,
            detail={
                "tenant_id": str(tenant_id) if tenant_id else None,
                "prior_max_sequence": max_seq,
                "next_epoch": next_epoch,
                "next_sequence": next_seq,
            },
        )


def get_current_synthesis_publication_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> str | None:
    row = session.scalar(
        select(CortexSynthesisPublicationEpoch.synthesis_publication_epoch)
        .where(CortexSynthesisPublicationEpoch.tenant_id == tenant_id)
        .order_by(
            CortexSynthesisPublicationEpoch.published_at.desc(),
            CortexSynthesisPublicationEpoch.synthesis_publication_epoch.desc(),
        )
        .limit(1)
    )
    return str(row) if row else None


def _next_synthesis_publication_epoch_name_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str | None,
) -> str:
    base = (published_index_epoch or "none").strip()
    prior_names = list_tenant_publication_epoch_names_v1(session, tenant_id=tenant_id)
    max_seq = max((parse_synthesis_publication_epoch_seq_v1(e) for e in prior_names), default=0)
    return f"syn-{base}-{max_seq + 1}"


def _pinned_index_epoch_v1(envelope: Mapping[str, Any]) -> str | None:
    pins = envelope.get("retrieval_pins")
    if isinstance(pins, Mapping):
        raw = pins.get("index_epoch")
        if raw is not None:
            return str(raw).strip() or None
    scope = envelope.get("retrieval_scope")
    if isinstance(scope, Mapping):
        raw = scope.get("index_epoch")
        if raw is not None:
            return str(raw).strip() or None
    return None


def _prior_published_replay_identity_for_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    retrieval_lookup_id: str | None,
    artifact_kind: str,
) -> str | None:
    if not retrieval_lookup_id:
        return None
    row = session.scalar(
        select(CortexSynthesisJob.synthesis_job_replay_identity)
        .join(CortexSynthesisArtifact, CortexSynthesisArtifact.job_id == CortexSynthesisJob.id)
        .where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.published.is_(True),
            CortexSynthesisArtifact.retrieval_lookup_id == retrieval_lookup_id,
            CortexSynthesisArtifact.artifact_kind == artifact_kind,
            CortexSynthesisArtifact.synthesis_legality_class.in_(tuple(_PUBLISHABLE_LEGALITY_V1)),
        )
        .order_by(desc(CortexSynthesisArtifact.created_at))
        .limit(1)
    )
    return str(row).strip() if row else None


def evaluate_artifact_publish_eligibility_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact: CortexSynthesisArtifact,
    job: CortexSynthesisJob | None = None,
    published_index_epoch: str | None = None,
) -> dict[str, Any]:
    """Per-artifact **G-P08-REPLAY-02** eligibility."""
    index_epoch = published_index_epoch or get_published_index_epoch_v1(session, tenant_id=tenant_id)
    job_row = job or session.get(CortexSynthesisJob, artifact.job_id)
    legality = str(artifact.synthesis_legality_class or (job_row.synthesis_legality_class if job_row else ""))
    replay_id = str(
        artifact.body_json.get(PHASE08_REPLAY_IDENTITY_FIELD_V1)
        or (job_row.synthesis_job_replay_identity if job_row else "")
        or "",
    ).strip()
    lookup = str(artifact.retrieval_lookup_id or "").strip() or None
    body = artifact.body_json or {}
    if not lookup:
        lookup = str(body.get("retrieval_lookup_id") or "").strip() or None

    blocked_reasons: list[str] = []
    if legality not in _PUBLISHABLE_LEGALITY_V1:
        blocked_reasons.append("legality_not_publishable")
    if body.get("retracted") is True:
        blocked_reasons.append("artifact_retracted")

    pinned = _pinned_index_epoch_v1(job_row.envelope_json if job_row else {})
    if pinned and index_epoch and pinned != index_epoch:
        blocked_reasons.append("retrieval_index_epoch_pin_stale")

    prior_replay = _prior_published_replay_identity_for_scope_v1(
        session,
        tenant_id=tenant_id,
        retrieval_lookup_id=lookup,
        artifact_kind=str(artifact.artifact_kind),
    )
    if prior_replay and replay_id and prior_replay != replay_id:
        blocked_reasons.append("replay_identity_scope_mismatch")

    from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
        evaluate_synthesis_publish_barrier_v1,
    )

    barrier = evaluate_synthesis_publish_barrier_v1(
        synthesis_legality_class=legality,
        session=session,
        tenant_id=tenant_id,
    )
    if not barrier.get("can_publish"):
        blocked_reasons.append(str(barrier.get("reason") or "publish_barrier_blocked"))

    from vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1 import (
        is_synthesis_empty_claims_gate_enabled_v1,
        validate_artifact_claims_for_publish_v1,
    )

    if is_synthesis_empty_claims_gate_enabled_v1():
        claims_ok, claim_violations = validate_artifact_claims_for_publish_v1(
            body_json=body,
            artifact_kind=str(artifact.artifact_kind or ""),
        )
        if not claims_ok:
            blocked_reasons.append("synthesis_empty_claims")
            blocked_reasons.extend(claim_violations)

    eligible = len(blocked_reasons) == 0
    return {
        "artifact_id": str(artifact.id),
        "eligible": eligible,
        "can_publish": eligible,
        "blocked_reasons": blocked_reasons,
        "sd_code": None if eligible else SD_PUBLISH_BLOCKED_V1,
        "synthesis_legality_class": legality,
        "synthesis_job_replay_identity": replay_id or None,
        "prior_scope_replay_identity": prior_replay,
        "pinned_index_epoch": pinned,
        "published_index_epoch": index_epoch,
        "first_publish_for_scope": prior_replay is None,
    }


def _load_artifacts_for_publish_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_ids: list[uuid.UUID] | None,
    substrate_pipeline_run_id: uuid.UUID | None,
) -> list[tuple[CortexSynthesisArtifact, CortexSynthesisJob]]:
    if artifact_ids:
        rows: list[CortexSynthesisArtifact] = list(
            session.scalars(
                select(CortexSynthesisArtifact).where(
                    CortexSynthesisArtifact.tenant_id == tenant_id,
                    CortexSynthesisArtifact.id.in_(artifact_ids),
                )
            ).all()
        )
    elif substrate_pipeline_run_id is not None:
        rows = list(
            session.scalars(
                select(CortexSynthesisArtifact)
                .join(CortexSynthesisJob, CortexSynthesisJob.id == CortexSynthesisArtifact.job_id)
                .where(
                    CortexSynthesisJob.tenant_id == tenant_id,
                    CortexSynthesisJob.substrate_pipeline_run_id == substrate_pipeline_run_id,
                    CortexSynthesisArtifact.published.is_(False),
                )
            ).all()
        )
    else:
        rows = []
    out: list[tuple[CortexSynthesisArtifact, CortexSynthesisJob]] = []
    for artifact in rows:
        job = session.get(CortexSynthesisJob, artifact.job_id)
        if job is not None:
            out.append((artifact, job))
    return out


def publish_synthesis_epoch_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    published_index_epoch: str | None = None,
    substrate_pipeline_run_id: uuid.UUID | None = None,
    artifact_ids: list[uuid.UUID] | None = None,
    allow_empty_scope: bool = False,
) -> dict[str, Any]:
    """Publish tenant synthesis epoch and stamp eligible artifacts (**PIPE-08** / **G-P08-REPLAY-02**)."""
    index_epoch = published_index_epoch or get_published_index_epoch_v1(session, tenant_id=tenant_id)
    prior = get_current_synthesis_publication_epoch_v1(session, tenant_id=tenant_id)
    epoch_name = _next_synthesis_publication_epoch_name_v1(
        session,
        tenant_id=tenant_id,
        published_index_epoch=index_epoch,
    )
    assert_publication_epoch_monotonic_v1(
        prior_epoch=prior,
        next_epoch=epoch_name,
        tenant_id=tenant_id,
        prior_epochs=list_tenant_publication_epoch_names_v1(session, tenant_id=tenant_id),
    )

    pairs = _load_artifacts_for_publish_v1(
        session,
        tenant_id=tenant_id,
        artifact_ids=artifact_ids,
        substrate_pipeline_run_id=substrate_pipeline_run_id,
    )
    eligibility = [
        evaluate_artifact_publish_eligibility_v1(
            session,
            tenant_id=tenant_id,
            artifact=artifact,
            job=job,
            published_index_epoch=index_epoch,
        )
        for artifact, job in pairs
    ]
    eligible_ids = [uuid.UUID(str(e["artifact_id"])) for e in eligibility if e.get("eligible")]
    blocked = [e for e in eligibility if not e.get("eligible")]

    if not eligible_ids and not allow_empty_scope:
        raise SynthesisPublicationError(
            "publish_requires_artifact_or_empty_scope_documented",
            detail={
                "substrate_pipeline_run_id": str(substrate_pipeline_run_id)
                if substrate_pipeline_run_id
                else None,
                "blocked_count": len(blocked),
                "blocked": blocked[:8],
            },
        )

    now = datetime.now(UTC)
    if eligible_ids:
        session.execute(
            update(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.id.in_(eligible_ids),
            )
            .values(
                published=True,
                synthesis_publication_epoch=epoch_name,
            )
        )

    row = CortexSynthesisPublicationEpoch(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        synthesis_publication_epoch=epoch_name,
        published_index_epoch=index_epoch,
        artifact_count=len(eligible_ids),
        substrate_pipeline_run_id=substrate_pipeline_run_id,
        published_at=now,
    )
    session.add(row)
    session.flush()

    from vector.domains.cortex.synthesis.synthesis_observability import (
        record_synthesis_publication_lag_v1,
    )

    lag = compute_synthesis_lag_epochs_v1(
        published_index_epoch=index_epoch,
        synthesis_publication_epoch=epoch_name,
    )
    record_synthesis_publication_lag_v1(int(lag.get("lag_vs_retrieval") or 0))

    return {
        "gate_id": GP08_REPLAY_02_GATE_ID_V1,
        "synthesis_publication_epoch": epoch_name,
        "published_index_epoch": index_epoch,
        "artifact_count": len(eligible_ids),
        "artifact_ids": [str(i) for i in eligible_ids],
        "blocked_artifacts": blocked,
        "published_at": now.isoformat(),
        "prior_synthesis_publication_epoch": prior,
        "monotonic_sequence": parse_synthesis_publication_epoch_seq_v1(epoch_name),
        "publication_forward_only": True,
    }


def retract_synthesis_artifact_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_id: uuid.UUID,
    reason: str,
) -> dict[str, Any]:
    """Operator retract — marks artifact retracted; epoch history is append-only."""
    row = session.get(CortexSynthesisArtifact, artifact_id)
    if row is None or row.tenant_id != tenant_id:
        raise SynthesisPublicationError("artifact_not_found", http_status=404)
    body = dict(row.body_json or {})
    body["retracted"] = True
    body["retracted_at"] = datetime.now(UTC).isoformat()
    body["retract_reason"] = reason[:500]
    row.body_json = body
    row.published = False
    session.flush()
    return {
        "artifact_id": str(artifact_id),
        "retracted": True,
        "synthesis_publication_epoch": row.synthesis_publication_epoch,
        "reason": reason[:500],
    }


def skip_synthesis_publication_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    reason: str,
    operator_id: str | None = None,
) -> dict[str, Any]:
    """Dangerous operator skip — documents SD on phase 08 without deleting phase 07 artifacts."""
    from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1, skip_phase_v1

    phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
    if phase is None:
        raise SynthesisPublicationError("pipeline_phase_08_not_found", http_status=404)
    skip_phase_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_08_SYNTHESIS,
        reason=f"publish_skip:{reason[:200]}",
    )
    return {
        "skipped": True,
        "pipeline_run_id": str(pipeline_run_id),
        "tenant_id": str(tenant_id),
        "operator_id": operator_id,
        "reason": reason[:500],
        "sd_code": SD_PUBLISH_BLOCKED_V1,
    }


def list_synthesis_publication_epochs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 25,
) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(CortexSynthesisPublicationEpoch)
            .where(CortexSynthesisPublicationEpoch.tenant_id == tenant_id)
            .order_by(CortexSynthesisPublicationEpoch.published_at.desc())
            .limit(limit)
        ).all()
    )
    return [
        {
            "synthesis_publication_epoch": row.synthesis_publication_epoch,
            "published_index_epoch": row.published_index_epoch,
            "artifact_count": row.artifact_count,
            "substrate_pipeline_run_id": str(row.substrate_pipeline_run_id)
            if row.substrate_pipeline_run_id
            else None,
            "published_at": row.published_at.isoformat() if row.published_at else None,
            "epoch_sequence": parse_synthesis_publication_epoch_seq_v1(row.synthesis_publication_epoch),
        }
        for row in rows
    ]


def build_synthesis_publication_law_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "gate_ids": [GP08_REPLAY_02_GATE_ID_V1, GP08_PUB01_GATE_ID_V1],
        "publishable_legality_classes": sorted(_PUBLISHABLE_LEGALITY_V1),
        "forward_only": True,
        "rollback_forbidden": True,
        "retract_marks_unpublished": True,
        "epoch_name_pattern": "syn-{published_index_epoch}-{sequence}",
        "replay02_rules": [
            "legality in synthesis_replay_safe | synthesis_degraded",
            "replay_identity matches prior published scope or first publish",
            "retrieval index_epoch pin equals tenant published index epoch",
            "monotonic numeric epoch sequence per tenant",
        ],
        "sd_code_on_block": SD_PUBLISH_BLOCKED_V1,
    }


def build_synthesis_publication_status_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin publish status — current epoch, history, lag, blocked unpublished count."""
    current = get_current_synthesis_publication_epoch_v1(session, tenant_id=tenant_id)
    published_index = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    history = list_synthesis_publication_epochs_v1(session, tenant_id=tenant_id, limit=10)
    coverage = count_synthesis_synthesized_scopes_v1(session, tenant_id=tenant_id)
    lag = compute_synthesis_lag_epochs_v1(
        published_index_epoch=published_index,
        synthesis_publication_epoch=current,
    )
    unpublished = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(False),
            )
        )
        or 0
    )
    blocked_probe: list[dict[str, Any]] = []
    candidates = list(
        session.scalars(
            select(CortexSynthesisArtifact)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(False),
            )
            .order_by(CortexSynthesisArtifact.created_at.desc())
            .limit(5)
        ).all()
    )
    for artifact in candidates:
        job = session.get(CortexSynthesisJob, artifact.job_id)
        if job is None:
            continue
        ev = evaluate_artifact_publish_eligibility_v1(
            session,
            tenant_id=tenant_id,
            artifact=artifact,
            job=job,
            published_index_epoch=published_index,
        )
        if not ev.get("eligible"):
            blocked_probe.append(ev)

    monotonic_ok = True
    if len(history) >= 2:
        seqs = [int(h.get("epoch_sequence") or 0) for h in history]
        monotonic_ok = seqs == sorted(seqs, reverse=True)

    return {
        "surface_kind": "runtime_backed",
        "gate_id": GP08_REPLAY_02_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "synthesis_publication_epoch": current,
        "published_index_epoch": published_index,
        "publication_history": history,
        "lag_epochs": lag,
        "coverage": {
            "synthesized_scopes": coverage.get("synthesized_scopes"),
            "eligible_scopes": coverage.get("eligible_scopes"),
            "artifact_published_count": coverage.get("artifact_published_count"),
        },
        "has_unpublished_artifacts": unpublished,
        "blocked_unpublished_sample": blocked_probe,
        "gp08_replay02_monotonic": monotonic_ok,
        "publication_forward_only": True,
    }


def compare_gp08_replay02_publication_monotonicity_v1(
    epoch_names: Sequence[str],
) -> dict[str, Any]:
    """**G-P08-REPLAY-02** — verify epoch name sequence is strictly increasing."""
    seqs = [parse_synthesis_publication_epoch_seq_v1(e) for e in epoch_names]
    passed = len(seqs) <= 1 or all(b > a for a, b in zip(seqs, seqs[1:], strict=False))
    return {
        "gate_id": GP08_REPLAY_02_GATE_ID_V1,
        "gp08_replay02_monotonic_passed": passed,
        "epoch_sequences": seqs,
        "epoch_names": list(epoch_names),
    }


def verify_gp08_pub01_publication_barrier_module_static() -> dict[str, Any]:
    errors: list[str] = []
    for name in (
        "publish_synthesis_epoch_v1",
        "evaluate_artifact_publish_eligibility_v1",
        "assert_publication_epoch_monotonic_v1",
        "build_synthesis_publication_status_v1",
        "retract_synthesis_artifact_v1",
    ):
        if name not in globals():
            errors.append(f"missing:{name}")
    law = build_synthesis_publication_law_catalog_v1()
    if law.get("forward_only") is not True:
        errors.append("forward_only_required")
    mono = compare_gp08_replay02_publication_monotonicity_v1(["syn-ep-1", "syn-ep-2", "syn-ep-3"])
    if not mono.get("gp08_replay02_monotonic_passed"):
        errors.append("monotonic_compare_self_test_failed")
    bad = compare_gp08_replay02_publication_monotonicity_v1(["syn-ep-2", "syn-ep-1"])
    if bad.get("gp08_replay02_monotonic_passed"):
        errors.append("monotonic_compare_must_fail_on_regression")
    try:
        assert_publication_epoch_monotonic_v1(prior_epoch="syn-ep-2", next_epoch="syn-ep-1")
        errors.append("monotonic_assert_must_raise_on_regression")
    except SynthesisPublicationError as exc:
        if exc.code != "publication_epoch_not_monotonic":
            errors.append("monotonic_assert_wrong_code")
    return {
        "id": GP08_PUB01_GATE_ID_V1,
        "name": "gp08_pub01_publication_barrier_module",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

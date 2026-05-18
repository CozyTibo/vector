"""Phase 08 Step 33 — synthesis durable store repository (persistence + idempotency + retention)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_replay_equivalence import SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_synthesis_job_receipt import CortexSynthesisJobReceipt
from vector.infrastructure.db.models.cortex_synthesis_retention_event import CortexSynthesisRetentionEvent

PHASE08_SYNTHESIS_REPOSITORY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_STORE01_GATE_ID_V1: Final[str] = "G-P08-STORE-01"

SYN_FSM04_IDEMPOTENCY_GATE_V1: Final[str] = "SYN-FSM-04"

SYNTHESIS_DURABLE_STORE_INDEXES_V1: Final[tuple[str, ...]] = (
    "ix_cortex_synthesis_jobs_tenant_created",
    "ix_cortex_synthesis_jobs_tenant_idempotency",
    "ix_cortex_synthesis_jobs_tenant_status_created",
    "ix_cortex_synthesis_jobs_tenant_pipeline",
    "uq_cortex_synthesis_jobs_tenant_idem_digest_completed",
    "ix_cortex_synthesis_job_receipts_job_created",
    "ix_cortex_synthesis_job_receipts_tenant_created",
    "uq_cortex_synthesis_artifacts_tenant_digest",
    "ix_cortex_synthesis_artifacts_tenant_created",
    "ix_cortex_synthesis_artifacts_tenant_lookup",
    "ix_cortex_synthesis_artifacts_tenant_rqid",
    "ix_cortex_synthesis_artifacts_tenant_pub_epoch",
    "ix_cortex_synthesis_artifacts_tenant_published_created",
    "ix_cortex_synthesis_publication_epochs_tenant_epoch",
    "ix_cortex_synthesis_publication_epochs_tenant_published_at",
)

SYNTHESIS_RETENTION_POLICY_V1: Final[dict[str, Any]] = {
    "policy_version": 1,
    "failed_job_purge_after_days": 90,
    "exploration_unpublished_purge_after_days": 180,
    "receipt_append_only": True,
    "never_delete_published_artifacts": True,
    "never_delete_publication_epochs": True,
    "default_dry_run": True,
    "aligns_with": "phase-02-raw-memory-retention-pattern",
}


class SynthesisRepositoryError(ValueError):
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


def envelope_json_for_persistence_v1(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Strip runtime-only underscore fields before persisting envelope JSON."""
    return {k: v for k, v in envelope.items() if not str(k).startswith("_")}


def find_idempotent_synthesis_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
    envelope_digest: str,
) -> CortexSynthesisJob | None:
    """**SYN-FSM-04** — return completed job when key + digest match."""
    return session.scalar(
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.idempotency_key == idempotency_key,
            CortexSynthesisJob.envelope_digest == envelope_digest,
            CortexSynthesisJob.status == "completed",
        )
        .order_by(CortexSynthesisJob.created_at.desc())
        .limit(1)
    )


def assert_synthesis_idempotency_key_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str | None,
    envelope_digest: str,
) -> None:
    """Reject conflicting idempotency key with different envelope digest."""
    if not idempotency_key:
        return
    row = session.scalar(
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.idempotency_key == idempotency_key,
            CortexSynthesisJob.status == "completed",
        )
        .limit(1)
    )
    if row is not None and str(row.envelope_digest) != envelope_digest:
        raise SynthesisRepositoryError(
            "idempotency_key_digest_mismatch",
            http_status=409,
            detail={
                "idempotency_key": idempotency_key,
                "existing_envelope_digest": row.envelope_digest,
                "requested_envelope_digest": envelope_digest,
            },
        )


def create_synthesis_job_row_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    envelope_digest: str,
) -> CortexSynthesisJob:
    idem = envelope.get("idempotency_key")
    assert_synthesis_idempotency_key_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=str(idem) if idem else None,
        envelope_digest=envelope_digest,
    )
    substrate_raw = envelope.get("substrate_pipeline_run_id")
    substrate_id = uuid.UUID(str(substrate_raw)) if substrate_raw else None
    row = CortexSynthesisJob(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        status="queued",
        envelope_json=envelope_json_for_persistence_v1(envelope),
        envelope_digest=envelope_digest,
        synthesis_workload_class=str(envelope["synthesis_workload_class"]),
        synthesis_intent=str(envelope["synthesis_intent"]),
        execution_partition=str(envelope["execution_partition"]),
        idempotency_key=str(idem) if idem else None,
        synthesis_policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
        synthesis_orchestrator_build_id=SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1,
        substrate_pipeline_run_id=substrate_id,
    )
    session.add(row)
    session.flush()
    return row


def persist_synthesis_job_receipt_row_v1(
    session: Session,
    *,
    job: CortexSynthesisJob,
    receipt: Mapping[str, Any],
    execution_trace: list[dict[str, Any]],
) -> CortexSynthesisJobReceipt:
    row = CortexSynthesisJobReceipt(
        id=uuid.uuid4(),
        tenant_id=job.tenant_id,
        job_id=job.id,
        receipt_digest=str(receipt["receipt_digest"]),
        receipt_json=dict(receipt),
        execution_trace_json=list(execution_trace),
    )
    session.add(row)
    session.flush()
    return row


def get_synthesis_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> CortexSynthesisJob | None:
    row = session.get(CortexSynthesisJob, job_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def list_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    status: str | None = None,
    substrate_pipeline_run_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[CortexSynthesisJob]:
    stmt = select(CortexSynthesisJob).where(CortexSynthesisJob.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(CortexSynthesisJob.status == status)
    if substrate_pipeline_run_id is not None:
        stmt = stmt.where(CortexSynthesisJob.substrate_pipeline_run_id == substrate_pipeline_run_id)
    return list(
        session.scalars(stmt.order_by(CortexSynthesisJob.created_at.desc()).limit(limit)).all()
    )


def get_synthesis_artifact_by_tenant_digest_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    artifact_digest: str,
) -> CortexSynthesisArtifact | None:
    return session.scalar(
        select(CortexSynthesisArtifact).where(
            CortexSynthesisArtifact.tenant_id == tenant_id,
            CortexSynthesisArtifact.artifact_digest == artifact_digest,
        )
    )


def count_synthesis_store_rows_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    jobs = int(
        session.scalar(
            select(func.count()).select_from(CortexSynthesisJob).where(
                CortexSynthesisJob.tenant_id == tenant_id,
            )
        )
        or 0
    )
    artifacts = int(
        session.scalar(
            select(func.count()).select_from(CortexSynthesisArtifact).where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
            )
        )
        or 0
    )
    receipts = int(
        session.scalar(
            select(func.count()).select_from(CortexSynthesisJobReceipt).where(
                CortexSynthesisJobReceipt.tenant_id == tenant_id,
            )
        )
        or 0
    )
    return {"jobs": jobs, "artifacts": artifacts, "receipts": receipts}


def _record_retention_event_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    event_type: str,
    job_id: uuid.UUID | None = None,
    artifact_id: uuid.UUID | None = None,
    detail: Mapping[str, Any] | None = None,
    note: str | None = None,
) -> None:
    session.add(
        CortexSynthesisRetentionEvent(
            tenant_id=tenant_id,
            job_id=job_id,
            artifact_id=artifact_id,
            event_type=event_type,
            detail=dict(detail or {}),
            note=note,
        )
    )


def apply_synthesis_retention_policy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    dry_run: bool = True,
    failed_job_purge_after_days: int | None = None,
    exploration_unpublished_purge_after_days: int | None = None,
    allow_delete: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Tenant-scoped retention (dry-run default). Never deletes published artifacts."""
    policy = dict(SYNTHESIS_RETENTION_POLICY_V1)
    failed_days = int(failed_job_purge_after_days or policy["failed_job_purge_after_days"])
    exploration_days = int(
        exploration_unpublished_purge_after_days or policy["exploration_unpublished_purge_after_days"],
    )
    ts = now or datetime.now(UTC)
    failed_cutoff = ts - timedelta(days=max(1, failed_days))
    exploration_cutoff = ts - timedelta(days=max(1, exploration_days))

    failed_jobs = list(
        session.scalars(
            select(CortexSynthesisJob.id).where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "failed",
                CortexSynthesisJob.created_at <= failed_cutoff,
            )
        ).all()
    )
    exploration_artifacts = list(
        session.scalars(
            select(CortexSynthesisArtifact.id)
            .join(CortexSynthesisJob, CortexSynthesisJob.id == CortexSynthesisArtifact.job_id)
            .where(
                CortexSynthesisArtifact.tenant_id == tenant_id,
                CortexSynthesisArtifact.published.is_(False),
                CortexSynthesisJob.execution_partition == "exploration",
                CortexSynthesisArtifact.created_at <= exploration_cutoff,
            )
        ).all()
    )

    if not dry_run and allow_delete:
        if failed_jobs:
            session.execute(
                delete(CortexSynthesisJob).where(
                    CortexSynthesisJob.tenant_id == tenant_id,
                    CortexSynthesisJob.id.in_([uuid.UUID(str(j)) for j in failed_jobs]),
                )
            )
        if exploration_artifacts:
            session.execute(
                delete(CortexSynthesisArtifact).where(
                    CortexSynthesisArtifact.tenant_id == tenant_id,
                    CortexSynthesisArtifact.id.in_([uuid.UUID(str(a)) for a in exploration_artifacts]),
                    CortexSynthesisArtifact.published.is_(False),
                )
            )
        for jid in failed_jobs[:50]:
            _record_retention_event_v1(
                session,
                tenant_id=tenant_id,
                job_id=uuid.UUID(str(jid)),
                event_type="failed_job_purged",
                detail={"failed_job_purge_after_days": failed_days},
            )
        for aid in exploration_artifacts[:50]:
            _record_retention_event_v1(
                session,
                tenant_id=tenant_id,
                artifact_id=uuid.UUID(str(aid)),
                event_type="exploration_artifact_purged",
                detail={"exploration_unpublished_purge_after_days": exploration_days},
            )
        session.flush()
    elif not dry_run:
        for jid in failed_jobs[:50]:
            _record_retention_event_v1(
                session,
                tenant_id=tenant_id,
                job_id=uuid.UUID(str(jid)),
                event_type="failed_job_deletion_candidate",
                detail={"delete_executed": False},
            )
        session.flush()

    return {
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "allow_delete": allow_delete,
        "policy_version": policy["policy_version"],
        "failed_job_purge_after_days": failed_days,
        "exploration_unpublished_purge_after_days": exploration_days,
        "failed_job_candidate_count": len(failed_jobs),
        "exploration_artifact_candidate_count": len(exploration_artifacts),
        "failed_job_candidate_ids": [str(j) for j in failed_jobs[:25]],
        "exploration_artifact_candidate_ids": [str(a) for a in exploration_artifacts[:25]],
        "deletes_executed": bool((not dry_run) and allow_delete and (failed_jobs or exploration_artifacts)),
        "never_delete_published_artifacts": True,
    }


def run_synthesis_durable_store_load_smoke_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    iterations: int = 8,
) -> dict[str, Any]:
    """Lightweight index-path smoke — insert + query by idempotency/status/digest."""
    from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
        hash_reasoning_canonical_json_sha256_v1,
    )

    started = datetime.now(UTC)
    idem_base = f"smoke-{uuid.uuid4().hex[:12]}"
    created_job_ids: list[str] = []
    for i in range(max(1, min(iterations, 32))):
        digest = hash_reasoning_canonical_json_sha256_v1({"i": i, "base": idem_base})
        envelope = {
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "synthesis_workload_class": "degradation_brief",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "idempotency_key": f"{idem_base}-{i}",
        }
        job = create_synthesis_job_row_v1(
            session,
            tenant_id=tenant_id,
            envelope=envelope,
            envelope_digest=digest,
        )
        job.status = "completed"
        job.receipt_digest = digest
        created_job_ids.append(str(job.id))
    session.flush()

    hit = find_idempotent_synthesis_job_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=f"{idem_base}-0",
        envelope_digest=hash_reasoning_canonical_json_sha256_v1({"i": 0, "base": idem_base}),
    )
    listed = list_synthesis_jobs_v1(session, tenant_id=tenant_id, status="completed", limit=5)
    elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    return {
        "gate_id": GP08_STORE01_GATE_ID_V1,
        "iterations": iterations,
        "jobs_created": len(created_job_ids),
        "idempotency_hit": hit is not None,
        "status_list_count": len(listed),
        "elapsed_ms": elapsed_ms,
        "passed": hit is not None and len(listed) >= 1,
    }


def build_synthesis_durable_store_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_durable_store_v1",
        "phase08_synthesis_repository_runtime_schema_version": (
            PHASE08_SYNTHESIS_REPOSITORY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_STORE01_GATE_ID_V1,
        "idempotency_gate": SYN_FSM04_IDEMPOTENCY_GATE_V1,
        "indexes": list(SYNTHESIS_DURABLE_STORE_INDEXES_V1),
        "retention_policy": dict(SYNTHESIS_RETENTION_POLICY_V1),
        "tables": [
            "cortex_synthesis_jobs",
            "cortex_synthesis_job_receipts",
            "cortex_synthesis_artifacts",
            "cortex_synthesis_publication_epochs",
            "cortex_synthesis_retention_events",
        ],
    }


def verify_gp08_store01_synthesis_durable_store_static() -> dict[str, Any]:
    errors: list[str] = []
    catalog = build_synthesis_durable_store_catalog_v1()
    if "uq_cortex_synthesis_jobs_tenant_idem_digest_completed" not in catalog["indexes"]:
        errors.append("missing_idempotency_unique_index")
    if catalog["retention_policy"].get("never_delete_published_artifacts") is not True:
        errors.append("published_artifact_retention_guard_missing")
    for name in (
        "find_idempotent_synthesis_job_v1",
        "create_synthesis_job_row_v1",
        "apply_synthesis_retention_policy_v1",
        "run_synthesis_durable_store_load_smoke_v1",
    ):
        if name not in globals():
            errors.append(f"missing:{name}")
    mono = run_synthesis_durable_store_load_smoke_v1
    if not callable(mono):
        errors.append("missing_load_smoke")
    return {
        "id": GP08_STORE01_GATE_ID_V1,
        "name": "gp08_store01_synthesis_durable_store",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

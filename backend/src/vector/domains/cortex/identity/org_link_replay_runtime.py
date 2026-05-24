"""Phase 04 Step 10 — org link continuity replay jobs + L-class receipts (P04-10).

Normative: `DOCS/cortex/04-identity/phase-04-continuity-replay-doctrine.md`.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Final, Literal

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.identity.candidate_generation import (
    CANDIDATE_GENERATION_ENGINE_BUILD_REF,
    compute_candidate_set_sha256,
    regenerate_link_candidates,
)
from vector.domains.cortex.identity.link_ledger import compute_authoritative_link_set_sha256
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import CortexOrgLinkReplayJobReceipt

ORG_LINK_REPLAY_SCHEMA_VERSION: Final[int] = 2
ORG_LINK_REPLAY_ENGINE_BUILD_REF: Final[str] = "phase04-step10-org-link-replay-v1"

OrgLinkJobKind = Literal[
    "authoritative_replay",
    "candidate_regen",
    "graph_projection_export",
    "identity_continuity_rebuild",
    "identity_rebuild_from_anchors",
    "lawful_edge_promotion",
]
_LINK_DRIFT_CLASSES: Final[frozenset[str]] = frozenset({f"L{i}" for i in range(8)})


class OrgLinkReplayError(ValueError):
    """Raised when org link replay parameters are invalid."""


def verify_org_link_replay_rpl01_static() -> dict[str, Any]:
    """G-P04-RPL-01 — deterministic candidate hash + L-class envelope (static)."""
    errors: list[str] = []
    rows = [
        {
            "link_type": "org.persona_belongs_to_handle",
            "source_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "rpl-s")),
            "target_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "rpl-t")),
            "evidence_raw_record_ids": [9, 8],
            "rule_id": None,
        },
        {
            "link_type": "org.fixture_rule_only",
            "source_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "rpl-t")),
            "target_entity_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "rpl-s")),
            "evidence_raw_record_ids": [],
            "rule_id": "rule.p04.rpl01",
        },
    ]
    a = compute_candidate_set_sha256(rows)
    b = compute_candidate_set_sha256(list(reversed(rows)))
    if a != b:
        errors.append("candidate_set_hash_must_be_order_invariant")
    ev_perm = [{**rows[0], "evidence_raw_record_ids": [8, 9]}, rows[1]]
    if compute_candidate_set_sha256(ev_perm) != a:
        errors.append("candidate_set_hash_must_be_evidence_order_invariant")
    for cls in ("L0", "L3", "L7"):
        if cls not in _LINK_DRIFT_CLASSES:
            errors.append(f"missing_l_class:{cls}")
    passed = len(errors) == 0
    return {
        "id": "G-P04-RPL-01",
        "name": "org_link_continuity_replay_regen_determinism",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors, "sample_candidate_set_sha256_prefix": a[:16]},
    }


def list_completed_org_link_replay_jobs_missing_receipts(
    db: Session, *, tenant_id: uuid.UUID, limit: int = 5_000
) -> list[uuid.UUID]:
    """Persisted half of G-P04-RPL-01 — completed jobs with zero receipts."""
    lim = max(1, min(limit, 50_000))
    jobs = list(
        db.scalars(
            select(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "completed",
            )
            .order_by(nullslast(CortexOrgLinkReplayJob.completed_at.desc()))
            .limit(lim)
        ).all()
    )
    missing: list[uuid.UUID] = []
    for job in jobs:
        n = db.scalar(
            select(func.count())
            .select_from(CortexOrgLinkReplayJobReceipt)
            .where(CortexOrgLinkReplayJobReceipt.job_id == job.id)
        )
        if int(n or 0) == 0:
            missing.append(job.id)
    return missing


def _append_receipt(
    db: Session,
    *,
    job_id: uuid.UUID,
    receipt_class: str,
    detail_json: dict[str, Any],
) -> None:
    rc = receipt_class.strip()
    if rc not in _LINK_DRIFT_CLASSES:
        msg = f"invalid_receipt_class:{receipt_class}"
        raise OrgLinkReplayError(msg)
    db.add(
        CortexOrgLinkReplayJobReceipt(
            job_id=job_id,
            receipt_class=rc,
            detail_json=dict(detail_json or {}),
        )
    )


def org_link_replay_job_public_dict(row: CortexOrgLinkReplayJob) -> dict[str, Any]:
    return {
        "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
        "id": row.id,
        "tenant_id": row.tenant_id,
        "job_kind": row.job_kind,
        "pinned_rule_version": row.pinned_rule_version,
        "dry_run": bool(row.dry_run),
        "status": row.status,
        "scope_json": dict(row.scope_json or {}),
        "summary_json": dict(row.summary_json or {}),
        "error_detail": row.error_detail,
        "engine_build_ref": row.engine_build_ref,
        "celery_task_id": row.celery_task_id,
        "created_at": row.created_at,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
    }


def org_link_replay_receipt_public_dict(row: CortexOrgLinkReplayJobReceipt) -> dict[str, Any]:
    return {
        "id": row.id,
        "job_id": row.job_id,
        "receipt_class": row.receipt_class,
        "detail_json": dict(row.detail_json or {}),
        "created_at": row.created_at,
    }


def _validate_org_link_replay_job_params(
    *,
    job_kind: str,
    pinned_rule_version: str | None,
    dry_run: bool,
) -> None:
    if job_kind not in (
        "authoritative_replay",
        "candidate_regen",
        "graph_projection_export",
        "identity_continuity_rebuild",
        "identity_rebuild_from_anchors",
        "lawful_edge_promotion",
    ):
        msg = (
            "job_kind must be authoritative_replay, candidate_regen, "
            "graph_projection_export, identity_continuity_rebuild, identity_rebuild_from_anchors, "
            "or lawful_edge_promotion"
        )
        raise OrgLinkReplayError(msg)
    if job_kind == "identity_continuity_rebuild":
        return
    if job_kind == "identity_rebuild_from_anchors":
        return
    if job_kind == "candidate_regen" and not dry_run:
        rv = (pinned_rule_version or "").strip()
        if not rv:
            msg = "pinned_rule_version_required_for_candidate_regen_when_not_dry_run"
            raise OrgLinkReplayError(msg)


def create_queued_org_link_replay_job(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    job_kind: OrgLinkJobKind,
    pinned_rule_version: str | None = None,
    dry_run: bool = False,
    scope_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
    job_id: uuid.UUID | None = None,
) -> CortexOrgLinkReplayJob:
    """Insert a **queued** replay/export job row (P04-19 async worker entrypoint)."""
    from vector.domains.cortex.identity.anchor_continuity_candidates import ANCHOR_CONTINUITY_RULE_SEMANTIC

    eff_pinned = pinned_rule_version
    if job_kind == "candidate_regen" and not dry_run and not (eff_pinned or "").strip():
        eff_pinned = ANCHOR_CONTINUITY_RULE_SEMANTIC
    _validate_org_link_replay_job_params(
        job_kind=job_kind, pinned_rule_version=eff_pinned, dry_run=dry_run
    )
    job = CortexOrgLinkReplayJob(
        id=job_id or uuid.uuid4(),
        tenant_id=tenant_id,
        job_kind=job_kind,
        pinned_rule_version=(eff_pinned.strip() if eff_pinned else None),
        dry_run=dry_run,
        status="queued",
        scope_json=dict(scope_json or {}),
        summary_json={},
        engine_build_ref=engine_build_ref or ORG_LINK_REPLAY_ENGINE_BUILD_REF,
    )
    db.add(job)
    db.flush()
    return job


def run_org_link_replay_job_for_row(db: Session, job: CortexOrgLinkReplayJob) -> None:
    """Execute work for a **queued** job; persists **completed** or **failed** (no raise)."""
    if job.status != "queued":
        return
    now = datetime.now(tz=UTC)
    job.status = "running"
    job.started_at = now
    db.flush()
    job_kind = job.job_kind
    try:
        if job_kind == "identity_continuity_rebuild":
            from vector.domains.cortex.identity.continuity_rebuild import run_identity_continuity_rebuild

            bundle_id = str((job.scope_json or {}).get("bundle_id") or "").strip()
            if not bundle_id:
                raise OrgLinkReplayError("scope_json.bundle_id_required_for_identity_continuity_rebuild")
            mbl = int((job.scope_json or {}).get("materialize_batch_limit") or 2000)
            alim = int((job.scope_json or {}).get("anchor_limit") or 5000)
            rdr = bool((job.scope_json or {}).get("run_determinism_repair", True))
            run_identity_continuity_rebuild(
                db,
                tenant_id=job.tenant_id,
                bundle_id=bundle_id,
                materialize_batch_limit=mbl,
                anchor_limit=alim,
                run_determinism_repair=rdr,
                dry_run=bool(job.dry_run),
                replay_job=job,
            )
            sj = dict(job.summary_json or {})
            _append_receipt(
                db,
                job_id=job.id,
                receipt_class="L0",
                detail_json={
                    "lane": "identity_continuity_rebuild",
                    "bundle_id": bundle_id,
                    "candidate_set_sha256": sj.get("candidate_set_sha256"),
                    "anchor_evidence_input_sha256": sj.get("anchor_evidence_input_sha256"),
                },
            )
        elif job_kind == "identity_rebuild_from_anchors":
            from vector.domains.cortex.identity.continuity_rebuild import (
                _run_rebuild_identities_substrate_v1,
                substrate_counts,
            )
            from vector.domains.cortex.ingestion.full_pipeline_reset import clear_derived_outputs_from_phase_v1

            scope = dict(job.scope_json or {})
            alim = int(scope.get("anchor_limit") or 5000)
            restart_downstream = bool(scope.get("restart_downstream", True))
            counts_before = substrate_counts(db, tenant_id=job.tenant_id)
            cleared_identity: dict[str, Any] | None = None
            if not scope.get("identity_already_cleared"):
                cleared_identity = clear_derived_outputs_from_phase_v1(
                    db,
                    tenant_id=job.tenant_id,
                    from_phase="IDENTITY",
                )
            downstream = _run_rebuild_identities_substrate_v1(
                db,
                tenant_id=job.tenant_id,
                anchor_limit=alim,
                restart_downstream=restart_downstream,
            )
            job.summary_json = {
                "surface_kind": "identity_rebuild_from_anchors_v1",
                "tenant_id": str(job.tenant_id),
                "counts_before": counts_before,
                "counts_after": downstream["counts_after"],
                "cleared_identity": cleared_identity,
                "substrate": downstream["substrate"],
                "cleared_downstream": downstream["cleared_downstream"],
                "restarted": downstream["restarted"],
                "anchor_limit_applied": alim,
            }
            _append_receipt(
                db,
                job_id=job.id,
                receipt_class="L0",
                detail_json={
                    "lane": "identity_rebuild_from_anchors",
                    "anchor_limit_applied": alim,
                    "restart_downstream": restart_downstream,
                },
            )
        elif job_kind == "authoritative_replay":
            sha = compute_authoritative_link_set_sha256(db, tenant_id=job.tenant_id)
            job.summary_json = {
                "authoritative_set_sha256": sha,
                "dry_run": bool(job.dry_run),
                "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
            }
            _append_receipt(
                db,
                job_id=job.id,
                receipt_class="L0",
                detail_json={"lane": "authoritative_replay", "authoritative_set_sha256": sha},
            )
        elif job_kind == "graph_projection_export":
            from vector.domains.cortex.identity.projection_export import build_org_graph_projection_export_document

            doc = build_org_graph_projection_export_document(db, tenant_id=job.tenant_id)
            job.summary_json = {
                "org_graph_projection_schema_version": doc["org_graph_projection_schema_version"],
                "stable_hash_sha256": doc["stable_hash_sha256"],
                "engine_build_ref": doc.get("engine_build_ref"),
                "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
            }
            _append_receipt(
                db,
                job_id=job.id,
                receipt_class="L0",
                detail_json={"lane": "graph_projection_export", "stable_hash_sha256": doc["stable_hash_sha256"]},
            )
        elif job_kind == "lawful_edge_promotion":
            from vector.domains.cortex.identity.org_link_replay_lane_registry import (
                run_lawful_edge_promotion_lane_v1,
            )

            run_lawful_edge_promotion_lane_v1(db, job)
        elif job_kind == "candidate_regen":
            if job.dry_run:
                empty_sha = compute_candidate_set_sha256([])
                job.summary_json = {
                    "dry_run": True,
                    "candidate_set_sha256": empty_sha,
                    "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
                }
                _append_receipt(
                    db,
                    job_id=job.id,
                    receipt_class="L0",
                    detail_json={"lane": "candidate_regen", "note": "dry_run_no_batch_write"},
                )
            else:
                from vector.domains.cortex.identity.anchor_continuity_candidates import (
                    ANCHOR_CONTINUITY_RULE_SEMANTIC,
                    run_anchor_continuity_candidate_regeneration,
                )
                from vector.domains.cortex.identity.linkage_rules import get_active_link_rule_version_by_semantic

                rv_str = (job.pinned_rule_version or "").strip()
                scope = dict(job.scope_json or {})
                use_anchor_continuity = bool(
                    scope.get("use_anchor_continuity") is True or rv_str == ANCHOR_CONTINUITY_RULE_SEMANTIC
                )
                if use_anchor_continuity:
                    out = run_anchor_continuity_candidate_regeneration(db, tenant_id=job.tenant_id)
                else:
                    ver_row = (
                        get_active_link_rule_version_by_semantic(db, tenant_id=job.tenant_id, semantic_version=rv_str)
                        if rv_str
                        else None
                    )
                    link_vid = ver_row.id if ver_row is not None else None
                    out = regenerate_link_candidates(
                        db,
                        tenant_id=job.tenant_id,
                        rule_version=rv_str,
                        engine_build_ref=CANDIDATE_GENERATION_ENGINE_BUILD_REF,
                        link_rule_version_id=link_vid,
                    )
                job.summary_json = {
                    **out,
                    "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
                    "replay_lane": "anchor_continuity" if use_anchor_continuity else "legacy_rule_rows",
                }
                _append_receipt(
                    db,
                    job_id=job.id,
                    receipt_class="L0",
                    detail_json={
                        "lane": "candidate_regen",
                        "candidate_batch_id": out.get("candidate_batch_id"),
                        "candidate_set_sha256": out.get("candidate_set_sha256"),
                        "anchor_evidence_input_sha256": out.get("anchor_evidence_input_sha256"),
                    },
                )
        else:
            raise OrgLinkReplayError(f"unsupported_job_kind:{job_kind}")
        job.status = "completed"
        job.completed_at = datetime.now(tz=UTC)
        db.flush()
    except Exception as exc:
        job.status = "failed"
        job.error_detail = str(exc)
        job.completed_at = datetime.now(tz=UTC)
        db.flush()
        from vector.domains.cortex.identity.failure_remediation import record_org_link_replay_job_failed

        record_org_link_replay_job_failed(db, job, error=str(exc))
        db.flush()


def execute_org_link_replay_job(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    job_kind: OrgLinkJobKind,
    pinned_rule_version: str | None = None,
    dry_run: bool = False,
    scope_json: dict[str, Any] | None = None,
    engine_build_ref: str | None = None,
) -> CortexOrgLinkReplayJob:
    """Create a job row, run one continuity pass, persist summary + ≥1 L0 receipt (synchronous admin path)."""
    job = create_queued_org_link_replay_job(
        db,
        tenant_id=tenant_id,
        job_kind=job_kind,
        pinned_rule_version=pinned_rule_version,
        dry_run=dry_run,
        scope_json=scope_json,
        engine_build_ref=engine_build_ref,
    )
    run_org_link_replay_job_for_row(db, job)
    if job.status == "failed":
        raise OrgLinkReplayError(job.error_detail or "org_link_replay_job_failed")
    return job


def list_org_link_replay_jobs(db: Session, *, tenant_id: uuid.UUID, limit: int = 50) -> list[CortexOrgLinkReplayJob]:
    lim = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(CortexOrgLinkReplayJob)
            .where(CortexOrgLinkReplayJob.tenant_id == tenant_id)
            .options(selectinload(CortexOrgLinkReplayJob.receipts))
            .order_by(nullslast(CortexOrgLinkReplayJob.created_at.desc()))
            .limit(lim)
        ).all()
    )


def get_org_link_replay_job(db: Session, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> CortexOrgLinkReplayJob | None:
    row = db.scalars(
        select(CortexOrgLinkReplayJob)
        .where(CortexOrgLinkReplayJob.tenant_id == tenant_id, CortexOrgLinkReplayJob.id == job_id)
        .options(selectinload(CortexOrgLinkReplayJob.receipts))
    ).first()
    return row

"""Operator-grade Phase 04 identity continuity rebuild (raw → canonical → anchors → candidates → replay).

Deterministic orchestration for stale tenants after fixture/runtime upgrades.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.transform_runtime import (
    drain_stub_materialize_backlog,
    repair_tenant_materialization_oracle_determinism_drift,
)
from vector.domains.cortex.identity.anchor_continuity_candidates import run_anchor_continuity_candidate_regeneration
from vector.domains.cortex.identity.backfill import run_anchor_handle_backfill
from vector.domains.cortex.identity.link_ledger import compute_authoritative_link_set_sha256
from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records
from vector.domains.cortex.identity.org_link_replay_runtime import ORG_LINK_REPLAY_SCHEMA_VERSION
from vector.infrastructure.db.models.cortex_canonical_identity_anchor import CortexCanonicalIdentityAnchor
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import CortexOrgLinkReplayJobReceipt
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def run_identity_handles_and_candidates_refresh(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    dry_run: bool = False,
    anchor_limit: int = 5_000,
) -> dict[str, Any]:
    """Authoritative identity substrate: anchor org-handle backfill then anchor continuity candidates.

    Used by **identity continuity rebuild** and **flush+rerun** so both paths share the same
    deterministic org-handle + candidate semantics (no drift between operator actions).
    """
    bf = run_anchor_handle_backfill(
        db,
        tenant_id=tenant_id,
        dry_run=dry_run,
        anchor_limit=anchor_limit,
        skip_candidate_regen=True,
    )
    if dry_run:
        return {**bf, "candidate_regeneration": None, "identity_continuity_substrate_pipeline": "v1"}
    db.flush()
    cand = run_anchor_continuity_candidate_regeneration(db, tenant_id=tenant_id)
    db.flush()
    return {**bf, "candidate_regeneration": cand, "identity_continuity_substrate_pipeline": "v1"}


def build_identity_substrate_projection_receipt_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    substrate: dict[str, Any],
    substrate_trigger: str,
    counts_before: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Deterministic phase-03 receipt JSON — no org-link replay job row ."""
    cand = substrate.get("candidate_regeneration") or {}
    auth_sha = compute_authoritative_link_set_sha256(db, tenant_id=tenant_id)
    after = substrate_counts(db, tenant_id=tenant_id)
    backfill_only = {
        k: v
        for k, v in substrate.items()
        if k not in ("candidate_regeneration", "identity_continuity_substrate_pipeline")
    }
    return {
        "continuity_rebuild_schema_version": CONTINUITY_REBUILD_SCHEMA_VERSION,
        "engine_build_ref": CONTINUITY_REBUILD_ENGINE_BUILD_REF,
        "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "bundle_id": bundle_id.strip(),
        "substrate_trigger": substrate_trigger,
        "counts_before_identity_substrate": dict(counts_before) if counts_before is not None else None,
        "anchor_backfill": backfill_only,
        "candidate_regeneration": cand,
        "identity_continuity_substrate_pipeline": substrate.get("identity_continuity_substrate_pipeline"),
        "authoritative_set_sha256": auth_sha,
        "ambiguity_opened_total": int(cand.get("ambiguity_opened_email_slack_multiplicity") or 0)
        + int(cand.get("ambiguity_opened_email_norm_slack_multiplicity") or 0)
        + int(cand.get("ambiguity_opened_fixture_cohort") or 0),
        "candidates_generated_count": int(cand.get("candidate_count") or 0),
        "candidate_set_sha256": cand.get("candidate_set_sha256"),
        "anchor_evidence_input_sha256": cand.get("anchor_evidence_input_sha256"),
        "replay_lane": "anchor_continuity",
        "counts_after": after,
    }


def schedule_graph_density_promotion_after_identity_substrate_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    substrate: dict[str, Any],
) -> dict[str, Any] | None:
    """Bounded lawful promotion after phase-03 identity substrate (not phase-04 sidecar)."""
    backfill_only = {
        k: v
        for k, v in substrate.items()
        if k not in ("candidate_regeneration", "identity_continuity_substrate_pipeline")
    }
    entities_upserted = int(backfill_only.get("entities_upserted") or 0)
    cand = substrate.get("candidate_regeneration") or {}
    candidate_count = int(cand.get("candidate_count") or 0)
    if entities_upserted <= 0 and candidate_count <= 0:
        return None
    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
        schedule_graph_density_pass_v1,
    )

    return schedule_graph_density_pass_v1(
        tenant_id=tenant_id,
        trigger=PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
        force=False,
        session=db,
    )


def run_identity_substrate_projection_for_pipeline_v1(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    substrate_trigger: str,
    anchor_limit: int = 5_000,
) -> dict[str, Any]:
    """Single phase-03 transform: handles/candidates refresh + inline audit receipt (no replay job)."""
    counts_before = substrate_counts(db, tenant_id=tenant_id)
    substrate = run_identity_handles_and_candidates_refresh(
        db,
        tenant_id=tenant_id,
        dry_run=False,
        anchor_limit=anchor_limit,
    )
    from vector.domains.cortex.execution.execution_event_triggers import (
        trigger_identity_promotion_after_substrate_v1,
    )

    promotion_trigger = trigger_identity_promotion_after_substrate_v1(
        db,
        tenant_id=tenant_id,
        substrate=substrate,
    )
    graph_density_promotion = promotion_trigger.get("promotion")
    audit = build_identity_substrate_projection_receipt_v1(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        substrate=substrate,
        substrate_trigger=substrate_trigger,
        counts_before=counts_before,
    )
    return {
        "identity_continuity_substrate": substrate,
        "identity_substrate_audit": audit,
        "graph_density_promotion": graph_density_promotion,
        "anchor_limit_applied": anchor_limit,
        "counts_before": counts_before,
        "counts_after": audit.get("counts_after"),
    }


def finalize_identity_substrate_operator_audit(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    substrate: dict[str, Any],
    substrate_trigger: str,
    counts_before: dict[str, int] | None = None,
) -> tuple[dict[str, Any], uuid.UUID]:
    """Admin/ingest path: same receipt plus durable org-link replay job audit row."""
    report = build_identity_substrate_projection_receipt_v1(
        db,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        substrate=substrate,
        substrate_trigger=substrate_trigger,
        counts_before=counts_before,
    )
    audit_jid = uuid.uuid4()
    report["audit_replay_job_id"] = str(audit_jid)
    _persist_standalone_audit_job(db, tenant_id=tenant_id, bundle_id=bundle_id.strip(), report=dict(report), job_id=audit_jid)
    return report, audit_jid

_LOGGER = logging.getLogger("vector.cortex.identity.continuity_rebuild")

CONTINUITY_REBUILD_ENGINE_BUILD_REF: Final[str] = "phase04-identity-continuity-rebuild-v1"
CONTINUITY_REBUILD_SCHEMA_VERSION: Final[int] = 1

_LINK_DRIFT_CLASSES: Final[frozenset[str]] = frozenset({f"L{i}" for i in range(8)})


def substrate_counts(db: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    raw_n = int(
        db.scalar(select(func.count()).select_from(RawIngestionRecord).where(RawIngestionRecord.tenant_id == tenant_id))
        or 0
    )
    anchor_n = int(
        db.scalar(
            select(func.count()).select_from(CortexCanonicalIdentityAnchor).where(CortexCanonicalIdentityAnchor.tenant_id == tenant_id)
        )
        or 0
    )
    org_n = int(
        db.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
            )
        )
        or 0
    )
    cand_n = int(
        db.scalar(select(func.count()).select_from(CortexOrgLinkCandidate).where(CortexOrgLinkCandidate.tenant_id == tenant_id)) or 0
    )
    amb_n = int(count_open_org_ambiguity_records(db, tenant_id=tenant_id))
    replay_n = int(
        db.scalar(select(func.count()).select_from(CortexOrgLinkReplayJob).where(CortexOrgLinkReplayJob.tenant_id == tenant_id)) or 0
    )
    return {
        "raw_ingestion_records": raw_n,
        "identity_anchors": anchor_n,
        "org_entities_active": org_n,
        "org_link_candidates": cand_n,
        "org_ambiguity_open": amb_n,
        "org_link_replay_jobs": replay_n,
    }


def _append_l0_receipt(db: Session, *, job_id: uuid.UUID, detail_json: dict[str, Any]) -> None:
    rc = "L0"
    if rc not in _LINK_DRIFT_CLASSES:
        msg = f"invalid_receipt_class:{rc}"
        raise ValueError(msg)
    db.add(
        CortexOrgLinkReplayJobReceipt(
            job_id=job_id,
            receipt_class=rc,
            detail_json=dict(detail_json or {}),
        )
    )


def _persist_standalone_audit_job(
    db: Session, *, tenant_id: uuid.UUID, bundle_id: str, report: dict[str, Any], job_id: uuid.UUID | None = None
) -> uuid.UUID:
    now = datetime.now(tz=UTC)
    jid = job_id or uuid.uuid4()
    scope: dict[str, Any] = {"bundle_id": bundle_id.strip()}
    trig = report.get("substrate_trigger")
    if isinstance(trig, str) and trig.strip():
        scope["substrate_trigger"] = trig.strip()
    job = CortexOrgLinkReplayJob(
        id=jid,
        tenant_id=tenant_id,
        job_kind="identity_continuity_rebuild",
        pinned_rule_version=None,
        dry_run=False,
        status="completed",
        scope_json=scope,
        summary_json=dict(report),
        error_detail=None,
        engine_build_ref=CONTINUITY_REBUILD_ENGINE_BUILD_REF,
        started_at=now,
        completed_at=now,
    )
    db.add(job)
    db.flush()
    _append_l0_receipt(
        db,
        job_id=jid,
        detail_json={
            "lane": "identity_continuity_rebuild",
            "bundle_id": bundle_id,
            "substrate_trigger": report.get("substrate_trigger"),
            "candidate_set_sha256": report.get("candidate_regeneration", {}).get("candidate_set_sha256"),
            "anchor_evidence_input_sha256": report.get("candidate_regeneration", {}).get("anchor_evidence_input_sha256"),
        },
    )
    db.flush()
    return jid


def run_identity_continuity_rebuild(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
    materialize_batch_limit: int = 2000,
    anchor_limit: int = 5_000,
    run_determinism_repair: bool = True,
    dry_run: bool = False,
    replay_job: CortexOrgLinkReplayJob | None = None,
) -> dict[str, Any]:
    """Run canonical drain → optional repair → anchor backfill (skip embedded regen) → candidate regen → auth hash.

    When ``replay_job`` is set (async worker path), summary is written onto that row; otherwise a completed audit job is inserted.
    """
    t_mono = time.monotonic()
    bid = bundle_id.strip()
    before = substrate_counts(db, tenant_id=tenant_id)
    _LOGGER.info(
        "continuity_rebuild_start tenant_id=%s bundle_id=%s dry_run=%s before=%s",
        tenant_id,
        bid,
        dry_run,
        before,
    )

    if dry_run:
        elapsed_ms = int((time.monotonic() - t_mono) * 1000)
        report = {
            "continuity_rebuild_schema_version": CONTINUITY_REBUILD_SCHEMA_VERSION,
            "engine_build_ref": CONTINUITY_REBUILD_ENGINE_BUILD_REF,
            "tenant_id": str(tenant_id),
            "bundle_id": bid,
            "dry_run": True,
            "duration_ms": elapsed_ms,
            "counts_before": before,
            "counts_after": before,
            "steps": {"note": "dry_run_no_writes"},
        }
        _LOGGER.info("continuity_rebuild_dry_run tenant_id=%s duration_ms=%s", tenant_id, elapsed_ms)
        if replay_job is not None:
            replay_job.summary_json = {**report, "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION}
        return report

    canonical = drain_stub_materialize_backlog(
        db,
        tenant_id=tenant_id,
        bundle_id=bid,
        connector=None,
        resource_type=None,
        batch_limit=materialize_batch_limit,
    )
    _LOGGER.info(
        "continuity_rebuild_canonical_drain tenant_id=%s succeeded=%s attempted=%s batches=%s failures=%s",
        tenant_id,
        canonical.get("total_succeeded"),
        canonical.get("total_attempted"),
        canonical.get("batches_run"),
        canonical.get("total_failed_rows"),
    )

    repair: dict[str, Any] | None = None
    if run_determinism_repair:
        repair_scan = min(5000, max(200, int(materialize_batch_limit) * 4))
        repair = repair_tenant_materialization_oracle_determinism_drift(
            db,
            tenant_id=tenant_id,
            bundle_id=bid,
            scan_limit=repair_scan,
            dry_run=False,
        )
        _LOGGER.info("continuity_rebuild_determinism_repair tenant_id=%s summary=%s", tenant_id, repair)

    substrate = run_identity_handles_and_candidates_refresh(
        db,
        tenant_id=tenant_id,
        dry_run=False,
        anchor_limit=anchor_limit,
    )
    backfill = {k: v for k, v in substrate.items() if k not in ("candidate_regeneration", "identity_continuity_substrate_pipeline")}
    cand = substrate.get("candidate_regeneration") or {}
    _LOGGER.info(
        "continuity_rebuild_identity_substrate tenant_id=%s anchors_scanned=%s entities_upserted=%s candidates=%s",
        tenant_id,
        backfill.get("anchors_scanned"),
        backfill.get("entities_upserted"),
        cand.get("candidate_count"),
    )
    _LOGGER.info(
        "continuity_rebuild_candidate_regen tenant_id=%s candidate_count=%s ambiguity_email_slack=%s ambiguity_email_norm_slack=%s ambiguity_fixture=%s anchor_input_sha=%s",
        tenant_id,
        cand.get("candidate_count"),
        cand.get("ambiguity_opened_email_slack_multiplicity"),
        cand.get("ambiguity_opened_email_norm_slack_multiplicity"),
        cand.get("ambiguity_opened_fixture_cohort"),
        (cand.get("anchor_evidence_input_sha256") or "")[:16],
    )

    auth_sha = compute_authoritative_link_set_sha256(db, tenant_id=tenant_id)
    elapsed_ms = int((time.monotonic() - t_mono) * 1000)

    report = {
        "continuity_rebuild_schema_version": CONTINUITY_REBUILD_SCHEMA_VERSION,
        "engine_build_ref": CONTINUITY_REBUILD_ENGINE_BUILD_REF,
        "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "bundle_id": bid,
        "dry_run": False,
        "duration_ms": elapsed_ms,
        "counts_before": before,
        "canonical_materialize_drain": canonical,
        "determinism_repair": repair,
        "anchor_backfill": backfill,
        "identity_continuity_substrate_pipeline": substrate.get("identity_continuity_substrate_pipeline"),
        "candidate_regeneration": cand,
        "authoritative_set_sha256": auth_sha,
        "ambiguity_opened_total": int(cand.get("ambiguity_opened_email_slack_multiplicity") or 0)
        + int(cand.get("ambiguity_opened_email_norm_slack_multiplicity") or 0)
        + int(cand.get("ambiguity_opened_fixture_cohort") or 0),
        "candidates_generated_count": int(cand.get("candidate_count") or 0),
    }
    report["candidate_set_sha256"] = cand.get("candidate_set_sha256")
    report["anchor_evidence_input_sha256"] = cand.get("anchor_evidence_input_sha256")
    report["replay_lane"] = "anchor_continuity"
    report["substrate_trigger"] = "continuity_rebuild"

    after = substrate_counts(db, tenant_id=tenant_id)
    report["counts_after"] = after

    if replay_job is not None:
        replay_job.summary_json = {**report, "org_link_replay_schema_version": ORG_LINK_REPLAY_SCHEMA_VERSION}
    else:
        audit_jid = uuid.uuid4()
        report["audit_replay_job_id"] = str(audit_jid)
        _persist_standalone_audit_job(db, tenant_id=tenant_id, bundle_id=bid, report=dict(report), job_id=audit_jid)

    _LOGGER.info(
        "continuity_rebuild_done tenant_id=%s duration_ms=%s after=%s candidates=%s amb_open_total=%s",
        tenant_id,
        elapsed_ms,
        after,
        report["candidates_generated_count"],
        report["ambiguity_opened_total"],
    )

    return report


def verify_continuity_fixture_pressure(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    sample_limit: int = 800,
) -> dict[str, Any]:
    """Scan raw payloads for declared ``continuity_fixture`` keys (operator proof of hostile activation)."""
    lim = max(1, min(int(sample_limit), 5000))
    rows = list(
        db.scalars(
            select(RawIngestionRecord.payload_body)
            .where(RawIngestionRecord.tenant_id == tenant_id)
            .limit(lim)
        ).all()
    )
    keys = (
        "cluster_key",
        "link_subject",
        "stable_account_key",
        "ambiguity_cohort_key",
        "family",
    )
    hits: dict[str, int] = {k: 0 for k in keys}
    rows_with_fixture = 0
    for body in rows:
        if not isinstance(body, dict):
            continue
        cf = None
        md = body.get("metadata")
        if isinstance(md, dict):
            cf = md.get("continuity_fixture")
        if not isinstance(cf, dict):
            pr = body.get("pull_request")
            if isinstance(pr, dict):
                pmd = pr.get("metadata")
                if isinstance(pmd, dict):
                    cf = pmd.get("continuity_fixture")
        if not isinstance(cf, dict):
            continue
        rows_with_fixture += 1
        for k in keys:
            if k in cf and cf.get(k) is not None and str(cf.get(k)).strip():
                hits[k] += 1

    return {
        "continuity_fixture_verify_schema_version": 1,
        "tenant_id": str(tenant_id),
        "raw_rows_sampled": len(rows),
        "raw_rows_with_continuity_fixture": rows_with_fixture,
        "fixture_field_hits": hits,
    }

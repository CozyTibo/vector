"""Phase 04 Step 17 — Execution Continuity Operator Console aggregate (P04-17).

Normative: ``phase-04-control-plane-doctrine.md`` §§5–7, §16, Appendix A (**identity_control_plane_v1**).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import and_, func, nullslast, or_, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.bundle_equivalence import list_org_links_missing_cross_bundle_equivalence
from vector.domains.cortex.identity.identity_primitive_projection import IDENTITY_PRIMITIVE_LANE
from vector.domains.cortex.identity.org_ambiguity import count_open_org_ambiguity_records
from vector.domains.cortex.identity.org_entities import OrgEntityKind
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_candidate_batch import CortexOrgLinkCandidateBatch
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.cortex_org_link_replay_job_receipt import CortexOrgLinkReplayJobReceipt
from vector.infrastructure.db.models.cortex_org_merge import CortexOrgMerge
from vector.infrastructure.db.models.cortex_org_primitive_instance import CortexOrgPrimitiveInstance
from vector.infrastructure.db.models.cortex_org_verification_run import CortexOrgVerificationRun

IDENTITY_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION: Final[int] = 5
IDENTITY_CONTROL_PLANE_CONTRACT: Final[str] = "identity_control_plane_v1"

# G-P04-18 — org replay jobs older than this vs ``computed_at`` ⇒ top-level ``freshness_label`` = ``stale``.
_ORG_REPLAY_FRESHNESS_STALE_AFTER: Final[timedelta] = timedelta(hours=24)

OPERATIONAL_REPLAY_CANONICAL_GUIDE: Final[dict[str, Any]] = {
    "schema_version": "p04.operational_replay_canonical_guide.v3_wave3",
    "archived_wave3_dead_celery": {
        "removed_task_names": [
            "vector.cortex.identity.regenerate_link_candidates",
            "vector.cortex.identity.replay_authoritative_links",
        ],
        "replacement": "mark_dirty_and_enqueue_convergence_v1 → run_identity_substrate_repair_slice_v1",
        "org_link_replay_job_retained": "vector.cortex.identity.run_org_link_replay_job (debug / narrow scopes only)",
    },
    "archived_wave3_orphan_stitch": {
        "autonomous_promotion": False,
        "note": "run_continuity_stitching_pass_v1 may classify orphans and run anchor regen only; no promotion enqueue.",
    },
    "authoritative_operator_repair": {
        "workflow": "POST .../cortex/operator/actions { action: rebuild_identities }",
        "implementation": "reset_identity_substrate_repair_state_v1 + mark_dirty_and_enqueue_convergence_v1",
        "does_not": ["enqueue identity_rebuild_from_anchors replay job", "run repair until exhausted in one HTTP request"],
    },
    "debug_full_substrate_refresh": {
        "workflow": "POST .../cortex/debug/identity/full-substrate-refresh?debug_acknowledged=true",
        "formerly": "identity_continuity_rebuild",
        "warning": "Bypasses convergence-native slice repair — forensics only",
    },
    "primary_full_substrate_refresh": {
        "workflow": "deprecated — see authoritative_operator_repair",
        "rebuilds": [],
        "does_not_by_default": [],
        "hash_semantics": {},
    },
    "narrow_candidate_regen_only": {
        "workflow": "org_link_replay_job with job_kind=candidate_regen (pinned anchor continuity semantic)",
        "rebuilds": ["CortexOrgLinkCandidate batch from current anchors + raw join"],
        "does_not": ["ingest new raw", "re-materialize anchors", "touch authoritative org links"],
    },
    "authoritative_replay": {
        "workflow": "org_link_replay_job authoritative_replay",
        "rebuilds": ["authoritative org link materialization / projection per job scope"],
        "does_not": ["regenerate anchor continuity candidates unless explicitly combined in a higher-level flow"],
    },
    "operator_rule": (
        "Use **rebuild_identities** (reset repair cursor + mark dirty). "
        "Debug full refresh only under .../cortex/debug/identity/ with acknowledgement."
    ),
}

_CARD_KEYS: Final[tuple[str, ...]] = (
    "org_handles",
    "persona_bindings",
    "authoritative_links",
    "candidate_links",
    "ambiguous_identities",
    "pending_merges",
    "replay_drift",
    "bundle_equivalence_gaps",
    "primitive_instances",
    "orphaned_references",
)


def _drill_admin(tenant_id: uuid.UUID, suffix: str) -> str:
    s = suffix.lstrip("/")
    return f"/admin/tenants/{tenant_id}/cortex/identity/{s}"


def _authoritative_valid_now_clause(now: datetime) -> Any:
    return and_(
        CortexOrgLink.link_authority == "authoritative",
        CortexOrgLink.revoked_at.is_(None),
        or_(CortexOrgLink.valid_from.is_(None), CortexOrgLink.valid_from <= now),
        or_(CortexOrgLink.valid_to.is_(None), CortexOrgLink.valid_to > now),
    )


def _last_candidate_regen_job_public(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any] | None:
    row = _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="candidate_regen")
    base = _replay_job_pointer_public(row)
    if base is None or row is None:
        return base
    sj = dict(row.summary_json or {})
    base["convergence_excerpt"] = {
        "replay_lane": sj.get("replay_lane"),
        "candidate_count": sj.get("candidate_count"),
        "candidate_set_sha256": sj.get("candidate_set_sha256"),
        "anchor_evidence_input_sha256": sj.get("anchor_evidence_input_sha256"),
        "ambiguity_opened_email_slack_multiplicity": sj.get("ambiguity_opened_email_slack_multiplicity"),
        "ambiguity_opened_email_norm_slack_multiplicity": sj.get("ambiguity_opened_email_norm_slack_multiplicity"),
        "ambiguity_opened_fixture_cohort": sj.get("ambiguity_opened_fixture_cohort"),
        "candidate_generation_overflow_accounting": sj.get("candidate_generation_overflow_accounting"),
        "continuity_pair_evidence_preview": sj.get("continuity_pair_evidence_preview"),
    }
    return base


def _replay_job_pointer_public(row: CortexOrgLinkReplayJob | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "job_kind": row.job_kind,
        "pinned_rule_version": row.pinned_rule_version,
        "dry_run": bool(row.dry_run),
        "status": row.status,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _continuity_rebuild_job_public(row: CortexOrgLinkReplayJob | None) -> dict[str, Any] | None:
    if row is None:
        return None
    sj = dict(row.summary_json or {})
    base = _replay_job_pointer_public(row) or {}
    return {
        **base,
        "replay_lane": sj.get("replay_lane"),
        "candidate_set_sha256": sj.get("candidate_set_sha256"),
        "anchor_evidence_input_sha256": sj.get("anchor_evidence_input_sha256"),
        "ambiguity_opened_total": sj.get("ambiguity_opened_total"),
        "candidates_generated_count": sj.get("candidates_generated_count"),
        "duration_ms": sj.get("duration_ms"),
    }


def _latest_completed_replay_job(
    session: Session, *, tenant_id: uuid.UUID, job_kind: str
) -> CortexOrgLinkReplayJob | None:
    return session.scalars(
        select(CortexOrgLinkReplayJob)
        .where(
            CortexOrgLinkReplayJob.tenant_id == tenant_id,
            CortexOrgLinkReplayJob.job_kind == job_kind,
            CortexOrgLinkReplayJob.status == "completed",
            CortexOrgLinkReplayJob.completed_at.is_not(None),
        )
        .order_by(nullslast(CortexOrgLinkReplayJob.completed_at.desc()))
        .limit(1)
    ).first()


def _latest_completed_continuity_rebuild(
    session: Session, *, tenant_id: uuid.UUID
) -> CortexOrgLinkReplayJob | None:
    return _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="identity_continuity_rebuild")


def _replay_receipt_histogram(session: Session, *, tenant_id: uuid.UUID, job_limit: int = 80) -> dict[str, int]:
    """Histogram of receipt classes across recent completed jobs (bounded)."""
    lim = max(1, min(job_limit, 200))
    job_ids = list(
        session.scalars(
            select(CortexOrgLinkReplayJob.id)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.status == "completed",
            )
            .order_by(nullslast(CortexOrgLinkReplayJob.completed_at.desc()))
            .limit(lim)
        ).all()
    )
    if not job_ids:
        return {}
    rows = session.execute(
        select(CortexOrgLinkReplayJobReceipt.receipt_class, func.count())
        .where(CortexOrgLinkReplayJobReceipt.job_id.in_(job_ids))
        .group_by(CortexOrgLinkReplayJobReceipt.receipt_class)
    ).all()
    out: dict[str, int] = {str(rc): int(n) for rc, n in rows}
    return dict(sorted(out.items()))


def _count_pending_merges(session: Session, *, tenant_id: uuid.UUID, scan_limit: int = 2_000) -> int:
    lim = max(1, min(scan_limit, 10_000))
    rows = list(
        session.scalars(
            select(CortexOrgMerge)
            .where(CortexOrgMerge.tenant_id == tenant_id)
            .order_by(CortexOrgMerge.created_at.desc())
            .limit(lim)
        ).all()
    )
    n = 0
    for r in rows:
        meta = dict(r.metadata_json or {})
        if meta.get("merge_queue_status") == "pending" or meta.get("proposal_status") == "pending":
            n += 1
    return n


def _compute_freshness_label(
    *,
    computed_at: datetime,
    last_auth: CortexOrgLinkReplayJob | None,
    last_cand: CortexOrgLinkReplayJob | None,
) -> str:
    stamps: list[datetime] = []
    for j in (last_auth, last_cand):
        if j is not None and j.completed_at is not None:
            stamps.append(j.completed_at)
    if not stamps:
        return "fresh"
    newest = max(stamps)
    if computed_at - newest > _ORG_REPLAY_FRESHNESS_STALE_AFTER:
        return "stale"
    return "fresh"


def _count_primitive_lane_projection(session: Session, *, tenant_id: uuid.UUID, projection_kind: str) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
                CortexOrgEntity.metadata_json["anchor_backfill_lane"].astext == IDENTITY_PRIMITIVE_LANE,
                CortexOrgEntity.metadata_json["projection_kind"].astext == projection_kind,
            )
        )
        or 0
    )


def _candidate_link_row_totals(session: Session, *, tenant_id: uuid.UUID) -> tuple[int, int, uuid.UUID | None]:
    """Return (total_retained_rows, rows_in_latest_batch, latest_batch_id_or_none).

    Regeneration is append-only (new ``CortexOrgLinkCandidateBatch`` per run); the operator
    card should reflect the **current** snapshot (latest batch), not cumulative DB rows.
    """
    total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(CortexOrgLinkCandidate.tenant_id == tenant_id)
        )
        or 0
    )
    latest_batch_id = session.scalar(
        select(CortexOrgLinkCandidateBatch.id)
        .where(CortexOrgLinkCandidateBatch.tenant_id == tenant_id)
        .order_by(nullslast(CortexOrgLinkCandidateBatch.created_at.desc()), CortexOrgLinkCandidateBatch.id.asc())
        .limit(1)
    )
    if latest_batch_id is None:
        return total, 0, None
    latest_n = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(
                CortexOrgLinkCandidate.tenant_id == tenant_id,
                CortexOrgLinkCandidate.batch_id == latest_batch_id,
            )
        )
        or 0
    )
    return total, latest_n, latest_batch_id


def _candidate_rule_histogram(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    batch_id: uuid.UUID | None = None,
    limit_rules: int = 32,
) -> dict[str, int]:
    """Rule mix for candidates; when ``batch_id`` is set, only that batch (matches latest-batch card semantics)."""
    lim = max(1, min(limit_rules, 64))
    wh = [
        CortexOrgLinkCandidate.tenant_id == tenant_id,
        CortexOrgLinkCandidate.rule_id.isnot(None),
    ]
    if batch_id is not None:
        wh.append(CortexOrgLinkCandidate.batch_id == batch_id)
    rows = session.execute(
        select(CortexOrgLinkCandidate.rule_id, func.count())
        .where(*wh)
        .group_by(CortexOrgLinkCandidate.rule_id)
        .order_by(func.count().desc())
        .limit(lim)
    ).all()
    return {str(r[0]): int(r[1]) for r in rows if r[0] is not None}


def _continuity_substrate_debug(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    candidate_row_totals: tuple[int, int, uuid.UUID | None] | None = None,
) -> dict[str, Any]:
    """Operator visibility: human vs fixture primitive handles + candidate rule mix (deterministic counts)."""
    cand_total, cand_latest, latest_batch_id = (
        candidate_row_totals
        if candidate_row_totals is not None
        else _candidate_link_row_totals(session, tenant_id=tenant_id)
    )
    from vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1 import (
        snapshot_promotion_diversity_observability_v1,
    )

    promotion_diversity = snapshot_promotion_diversity_observability_v1(session, tenant_id=tenant_id)
    human_pk = ("slack_user", "github_user", "linear_user", "email_display_identity", "email_identity")
    fixture_pk = ("cross_tool_cluster", "cross_tool_link_subject", "stable_account_identity")
    primitive_projection_counts = {pk: _count_primitive_lane_projection(session, tenant_id=tenant_id, projection_kind=pk) for pk in human_pk + fixture_pk}
    human_primitive_handles = sum(primitive_projection_counts[p] for p in human_pk)
    fixture_primitive_handles = sum(primitive_projection_counts[p] for p in fixture_pk)
    asset_context_handles = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tenant_id,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.lifecycle_state == "active",
                CortexOrgEntity.entity_kind.in_(
                    (
                        OrgEntityKind.REPOSITORY_ASSET.value,
                        OrgEntityKind.COORDINATION_THREAD.value,
                        OrgEntityKind.WORKSPACE.value,
                        OrgEntityKind.INITIATIVE.value,
                    )
                ),
            )
        )
        or 0
    )
    return {
        "human_primitive_handle_count": human_primitive_handles,
        "fixture_primitive_handle_count": fixture_primitive_handles,
        "primitive_projection_counts": primitive_projection_counts,
        "asset_context_org_handle_count": asset_context_handles,
        "candidate_link_rows_total_retained": cand_total,
        "candidate_link_rows_latest_batch": cand_latest,
        "candidate_links_by_rule_id": _candidate_rule_histogram(
            session, tenant_id=tenant_id, batch_id=latest_batch_id
        ),
        "promotion_diversity": promotion_diversity,
        "promotable_by_rule_id": promotion_diversity.get("promotable_by_rule_id") or [],
    }


def _sparse_substrate_honesty(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    from vector.domains.cortex.identity.continuity_rebuild import substrate_counts

    c = substrate_counts(session, tenant_id=tenant_id)
    return {
        "schema_version": "p04.control_plane_sparse_honesty.v1",
        "substrate_counts": c,
        "interpretation": (
            "Sparse graphs are valid when recurrence is absent. Compare raw + anchor counts vs candidates; "
            "use latest candidate regen ``candidate_generation_overflow_accounting`` on the candidate job excerpt "
            "to detect global edge-cap starvation."
        ),
    }


def build_identity_control_plane(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Bounded aggregate JSON for Identity Dashboard (**identity_control_plane_v1**)."""
    now = datetime.now(tz=UTC)
    computed_iso = now.isoformat()

    org_handles = int(
        session.scalar(
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

    persona_bindings = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.link_type == "org.persona_belongs_to_handle",
                _authoritative_valid_now_clause(now),
            )
        )
        or 0
    )

    authoritative_links = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                _authoritative_valid_now_clause(now),
            )
        )
        or 0
    )

    cand_total_retained, candidate_links, latest_cand_batch_id = _candidate_link_row_totals(session, tenant_id=tenant_id)

    ambiguous_identities = count_open_org_ambiguity_records(session, tenant_id=tenant_id)
    pending_merges = _count_pending_merges(session, tenant_id=tenant_id)
    hist = _replay_receipt_histogram(session, tenant_id=tenant_id)
    drift_total = int(sum(hist.values()))
    bundle_equivalence_gaps = len(list_org_links_missing_cross_bundle_equivalence(session, tenant_id=tenant_id))
    primitive_instances = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgPrimitiveInstance)
            .where(CortexOrgPrimitiveInstance.tenant_id == tenant_id)
        )
        or 0
    )
    # Phase 3.5 normalized-ref orphan surface is not materialized in DB yet — contract field is present (0).
    orphaned_references = 0

    last_auth = _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="authoritative_replay")
    last_cand = _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="candidate_regen")
    last_rebuild = _latest_completed_continuity_rebuild(session, tenant_id=tenant_id)
    freshness = _compute_freshness_label(computed_at=now, last_auth=last_auth, last_cand=last_cand)

    last_run_id = session.scalar(
        select(CortexOrgVerificationRun.id)
        .where(CortexOrgVerificationRun.tenant_id == tenant_id)
        .order_by(CortexOrgVerificationRun.created_at.desc())
        .limit(1)
    )

    def _card(value: Any, drill: str) -> dict[str, Any]:
        return {
            "value": value,
            "computed_at": computed_iso,
            "drilldown": _drill_admin(tenant_id, drill),
            "freshness_label": freshness,
        }

    cards: dict[str, Any] = {
        "org_handles": _card(org_handles, "handles"),
        "persona_bindings": _card(persona_bindings, "links?link_type=org.persona_belongs_to_handle"),
        "authoritative_links": _card(authoritative_links, "links"),
        "candidate_links": _card(candidate_links, "link-candidates"),
        "ambiguous_identities": _card(ambiguous_identities, "ambiguity-queue"),
        "pending_merges": _card(pending_merges, "merge-queue"),
        "replay_drift": {
            "value": drift_total,
            "histogram": hist,
            "computed_at": computed_iso,
            "drilldown": _drill_admin(tenant_id, "replay-jobs"),
            "freshness_label": freshness,
        },
        "bundle_equivalence_gaps": _card(bundle_equivalence_gaps, "bundle-equivalence"),
        "primitive_instances": _card(primitive_instances, "primitives"),
        "orphaned_references": _card(orphaned_references, "links"),
    }

    substrate = _continuity_substrate_debug(
        session,
        tenant_id=tenant_id,
        candidate_row_totals=(cand_total_retained, candidate_links, latest_cand_batch_id),
    )
    substrate["operational_replay_canonical_guide"] = dict(OPERATIONAL_REPLAY_CANONICAL_GUIDE)
    substrate["sparse_substrate_honesty"] = _sparse_substrate_honesty(session, tenant_id=tenant_id)

    return {
        "identity_control_plane_runtime_schema_version": IDENTITY_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION,
        "schema_version": IDENTITY_CONTROL_PLANE_CONTRACT,
        "tenant_id": str(tenant_id),
        "computed_at": computed_iso,
        "freshness_label": freshness,
        "cards": cards,
        "continuity_substrate": substrate,
        "last_authoritative_replay_job": _replay_job_pointer_public(last_auth),
        "last_candidate_regen_job": _last_candidate_regen_job_public(session, tenant_id=tenant_id),
        "last_continuity_rebuild_job": _continuity_rebuild_job_public(last_rebuild),
        "verification_pointer": {"last_org_verification_run_id": int(last_run_id) if last_run_id is not None else None},
    }


def verify_identity_control_plane_v1_shape(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Structural checks for **G-P04-21** (Appendix A + §16.1)."""
    errs: list[str] = []
    if payload.get("schema_version") != IDENTITY_CONTROL_PLANE_CONTRACT:
        errs.append("schema_version_not_identity_control_plane_v1")
    if not isinstance(payload.get("tenant_id"), str):
        errs.append("tenant_id_not_str")
    if not isinstance(payload.get("computed_at"), str):
        errs.append("computed_at_not_str")
    fl = payload.get("freshness_label")
    if fl not in ("fresh", "stale"):
        errs.append("freshness_label_invalid")
    cards = payload.get("cards")
    if not isinstance(cards, dict):
        errs.append("cards_not_object")
    else:
        for k in _CARD_KEYS:
            if k not in cards:
                errs.append(f"missing_card:{k}")
                continue
            c = cards[k]
            if not isinstance(c, dict):
                errs.append(f"card_not_object:{k}")
                continue
            if k == "replay_drift":
                if "histogram" not in c or not isinstance(c["histogram"], dict):
                    errs.append("replay_drift_histogram")
                if "value" not in c:
                    errs.append("replay_drift_value")
            else:
                if "value" not in c:
                    errs.append(f"card_missing_value:{k}")
            if "computed_at" not in c:
                errs.append(f"card_missing_computed_at:{k}")
            if "drilldown" not in c or not isinstance(c["drilldown"], str):
                errs.append(f"card_missing_drilldown:{k}")
    if "last_authoritative_replay_job" not in payload:
        errs.append("missing_last_authoritative_replay_job")
    if "last_candidate_regen_job" not in payload:
        errs.append("missing_last_candidate_regen_job")
    if "last_continuity_rebuild_job" not in payload:
        errs.append("missing_last_continuity_rebuild_job")
    vp = payload.get("verification_pointer")
    if not isinstance(vp, dict) or "last_org_verification_run_id" not in vp:
        errs.append("verification_pointer_shape")
    return len(errs) == 0, errs


def verify_gp04_21_identity_control_plane_aggregate(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-21 — dashboard aggregate matches **identity_control_plane_v1** contract."""
    payload = build_identity_control_plane(session, tenant_id=tenant_id)
    ok, errs = verify_identity_control_plane_v1_shape(payload)
    return {
        "id": "G-P04-21",
        "name": "identity_control_plane_aggregate_contract",
        "passed": ok,
        "severity": "hard_fail",
        "detail": {"tenant_id": str(tenant_id), "errors": errs},
    }


def verify_gp04_18_org_control_plane_replay_freshness(session: Session, *, tenant_id: uuid.UUID) -> dict[str, Any]:
    """G-P04-18 — aggregate freshness + last replay job pointers match bounded DB truth."""
    payload = build_identity_control_plane(session, tenant_id=tenant_id)
    errors: list[str] = []
    la = _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="authoritative_replay")
    lc = _latest_completed_replay_job(session, tenant_id=tenant_id, job_kind="candidate_regen")
    p_la = payload.get("last_authoritative_replay_job")
    p_lc = payload.get("last_candidate_regen_job")
    if la is None:
        if p_la is not None:
            errors.append("last_authoritative_expected_null")
    else:
        if not isinstance(p_la, dict) or p_la.get("id") != str(la.id):
            errors.append("last_authoritative_id_mismatch")
    if lc is None:
        if p_lc is not None:
            errors.append("last_candidate_expected_null")
    else:
        if not isinstance(p_lc, dict) or p_lc.get("id") != str(lc.id):
            errors.append("last_candidate_id_mismatch")
    parse_ok = True
    try:
        computed_at = datetime.fromisoformat(str(payload.get("computed_at") or "").replace("Z", "+00:00"))
    except ValueError:
        parse_ok = False
        errors.append("computed_at_parse_failed")
    if parse_ok:
        expected = _compute_freshness_label(computed_at=computed_at, last_auth=la, last_cand=lc)
        if payload.get("freshness_label") != expected:
            errors.append("freshness_label_recompute_mismatch")
    return {
        "id": "G-P04-18",
        "name": "org_identity_control_plane_replay_freshness",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"tenant_id": str(tenant_id), "errors": errors, "expected_freshness_label": expected},
    }

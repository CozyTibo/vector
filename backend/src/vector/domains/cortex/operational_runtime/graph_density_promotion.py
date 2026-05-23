"""Phase 08.5 P085-11 — lawful edge promotion automation (**G-P085-PROMO-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-graph-density-doctrine.md`` §Lawful growth.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.authoritative_writer import (
    AUTHORITATIVE_WRITER_ENGINE_BUILD_REF,
    PromotionInvariantError,
    create_promotion_policy,
    promote_candidate_to_authoritative_link,
)
from vector.domains.cortex.identity.org_link_replay_runtime import (
    ORG_LINK_REPLAY_ENGINE_BUILD_REF,
    OrgLinkReplayError,
    _append_receipt,
    create_queued_org_link_replay_job,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    GP085_GRAPH01_GATE_ID_V1,
    count_graph_candidate_count_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_candidate import CortexOrgLinkCandidate
from vector.infrastructure.db.models.cortex_org_link_promotion_policy import CortexOrgLinkPromotionPolicy
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob

PHASE085_GRAPH_PROMOTION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_GRAPH_PROMOTION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-graph-density-doctrine.md"
)

GP085_PROMO01_GATE_ID_V1: Final[str] = "G-P085-PROMO-01"

CESP_LAWFUL_PROMOTION_POLICY_REF_V1: Final[str] = "cesp.lawful_edge_promotion.v1"

ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1: Final[str] = "lawful_edge_promotion"

CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.graph_density_promotion_pass"
)

PROMOTION_TRIGGER_AFTER_PHASE_04_V1: Final[str] = "after_phase_04"
PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1: Final[str] = "backlog_threshold"
PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1: Final[str] = "convergence_slice"
PROMOTION_TRIGGER_MANUAL_V1: Final[str] = "manual"

DETAIL_KEY_GRAPH_DENSITY_PROMOTION_SCHEDULE_V1: Final[str] = "graph_density_promotion_schedule"

PROMOTION_RECEIPT_CLASS_LAWFUL_V1: Final[str] = "L0"


class GraphDensityPromotionError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_promotion_max_per_pass_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_graph_density_promotion_max_per_pass))
    except Exception:  # noqa: BLE001
        return 50


def get_promotion_backlog_threshold_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(0, int(get_settings().cortex_graph_density_promotion_backlog_threshold))
    except Exception:  # noqa: BLE001
        return 10


def get_promotion_require_replay_receipt_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_graph_density_promotion_require_replay_receipt)
    except Exception:  # noqa: BLE001
        return True


def is_graph_density_promotion_on_convergence_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_graph_density_promotion_on_convergence_enabled)
    except Exception:  # noqa: BLE001
        return True


def get_promotion_schedule_countdown_seconds_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(0, int(get_settings().cortex_graph_density_promotion_schedule_countdown_seconds))
    except Exception:  # noqa: BLE001
        return 5


def _promoted_candidate_exists_clause_v1() -> Any:
    return exists(
        select(1).where(
            CortexOrgLink.tenant_id == CortexOrgLinkCandidate.tenant_id,
            CortexOrgLink.promoted_from_candidate_id == CortexOrgLinkCandidate.id,
            CortexOrgLink.revoked_at.is_(None),
        )
    )


def count_unpromoted_link_candidates_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkCandidate)
            .where(
                CortexOrgLinkCandidate.tenant_id == tenant_id,
                ~_promoted_candidate_exists_clause_v1(),
            )
        )
        or 0
    )


def list_unpromoted_link_candidates_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
) -> list[CortexOrgLinkCandidate]:
    lim = max(1, min(int(limit), 500))
    return list(
        session.scalars(
            select(CortexOrgLinkCandidate)
            .where(
                CortexOrgLinkCandidate.tenant_id == tenant_id,
                ~_promoted_candidate_exists_clause_v1(),
            )
            .order_by(
                CortexOrgLinkCandidate.created_at.asc(),
                CortexOrgLinkCandidate.row_digest.asc(),
            )
            .limit(lim)
        ).all()
    )


def get_cesp_promotion_policy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexOrgLinkPromotionPolicy | None:
    return session.scalars(
        select(CortexOrgLinkPromotionPolicy)
        .where(
            CortexOrgLinkPromotionPolicy.tenant_id == tenant_id,
            CortexOrgLinkPromotionPolicy.policy_ref == CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
        )
        .order_by(CortexOrgLinkPromotionPolicy.created_at.asc())
        .limit(1)
    ).first()


def ensure_cesp_promotion_policy_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexOrgLinkPromotionPolicy:
    existing = get_cesp_promotion_policy_v1(session, tenant_id=tenant_id)
    if existing is not None:
        return existing
    return create_promotion_policy(
        session,
        tenant_id=tenant_id,
        policy_ref=CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
        engine_build_ref=AUTHORITATIVE_WRITER_ENGINE_BUILD_REF,
    )


def assert_lawful_promotion_candidate_v1(cand: CortexOrgLinkCandidate) -> None:
    """Deterministic governance only — no probabilistic edge invention."""
    if not (cand.link_type or "").strip():
        raise GraphDensityPromotionError("candidate_missing_link_type")
    if cand.source_entity_id is None or cand.target_entity_id is None:
        raise GraphDensityPromotionError("candidate_missing_endpoints")
    evidence = cand.evidence_raw_record_ids
    if evidence is not None and not isinstance(evidence, list):
        raise GraphDensityPromotionError("candidate_evidence_not_list")


def evaluate_promotion_backlog_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str | None = None,
) -> dict[str, Any]:
    """Whether a density promotion pass should run (backlog threshold or phase-04 hook)."""
    unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
    threshold = get_promotion_backlog_threshold_v1()
    trig = (trigger or "").strip()
    if trig == PROMOTION_TRIGGER_AFTER_PHASE_04_V1:
        should = unpromoted > 0
        reason = "after_phase_04_with_candidates" if should else "after_phase_04_no_candidates"
    elif trig in (
        PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
        PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
    ) and unpromoted > threshold:
        should = True
        reason = trig or PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1
    else:
        should = False
        reason = "backlog_below_threshold"
    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_PROMO01_GATE_ID_V1,
        "unpromoted_link_candidate_count": unpromoted,
        "backlog_threshold": threshold,
        "should_schedule": should,
        "schedule_reason": reason,
        "trigger": trig or None,
    }


def _create_lawful_promotion_replay_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str,
    pipeline_run_id: uuid.UUID | None,
    existing_job_id: uuid.UUID | None = None,
) -> CortexOrgLinkReplayJob:
    scope: dict[str, Any] = {
        "trigger": trigger,
        "promotion_policy_ref": CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
    }
    if pipeline_run_id is not None:
        scope["pipeline_run_id"] = str(pipeline_run_id)
    return create_queued_org_link_replay_job(
        session,
        tenant_id=tenant_id,
        job_kind=ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,  # type: ignore[arg-type]
        scope_json=scope,
        engine_build_ref=ORG_LINK_REPLAY_ENGINE_BUILD_REF,
        job_id=existing_job_id,
    )


def _execute_bounded_lawful_promotions_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    cap: int,
    trigger: str,
) -> tuple[CortexOrgLinkPromotionPolicy, list[str], list[dict[str, str]]]:
    policy = ensure_cesp_promotion_policy_v1(session, tenant_id=tenant_id)
    candidates = list_unpromoted_link_candidates_v1(session, tenant_id=tenant_id, limit=cap)
    promoted_ids: list[str] = []
    skipped: list[dict[str, str]] = []
    for cand in candidates:
        try:
            assert_lawful_promotion_candidate_v1(cand)
            link = promote_candidate_to_authoritative_link(
                session,
                tenant_id=tenant_id,
                candidate_id=cand.id,
                promotion_policy_id=policy.id,
                metadata_json={
                    "cesp_promotion_trigger": trigger,
                    "cesp_gate_id": GP085_PROMO01_GATE_ID_V1,
                },
            )
            promoted_ids.append(str(link.id))
        except (PromotionInvariantError, GraphDensityPromotionError) as exc:
            skipped.append({"candidate_id": str(cand.id), "error": str(exc)})
    return policy, promoted_ids, skipped


def _finalize_lawful_promotion_replay_job_v1(
    session: Session,
    *,
    job: CortexOrgLinkReplayJob,
    summary: dict[str, Any],
) -> None:
    job.summary_json = {**summary, "org_link_replay_schema_version": 2}
    _append_receipt(
        session,
        job_id=job.id,
        receipt_class=PROMOTION_RECEIPT_CLASS_LAWFUL_V1,
        detail_json={
            "lane": ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,
            "promoted_count": summary.get("promoted_count"),
            "promotion_policy_ref": CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
        },
    )
    from datetime import UTC, datetime

    job.status = "completed"
    job.completed_at = datetime.now(tz=UTC)
    session.flush()


def run_graph_density_promotion_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    max_promotions: int | None = None,
    trigger: str = PROMOTION_TRIGGER_MANUAL_V1,
    pipeline_run_id: uuid.UUID | None = None,
    org_link_replay_job_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Bounded lawful promotion of unpromoted link candidates (**G-P085-PROMO-01**)."""
    cap = max_promotions if max_promotions is not None else get_promotion_max_per_pass_v1()
    cap = max(1, min(int(cap), 500))
    require_receipt = get_promotion_require_replay_receipt_v1()

    job: CortexOrgLinkReplayJob | None = None
    if org_link_replay_job_id is not None:
        job = session.get(CortexOrgLinkReplayJob, org_link_replay_job_id)
        if job is None or job.tenant_id != tenant_id:
            raise GraphDensityPromotionError("org_link_replay_job_not_found")
    elif require_receipt:
        job = _create_lawful_promotion_replay_job_v1(
            session,
            tenant_id=tenant_id,
            trigger=trigger,
            pipeline_run_id=pipeline_run_id,
        )
        job.status = "running"
        job.started_at = job.started_at or job.created_at
        session.flush()

    policy, promoted_ids, skipped = _execute_bounded_lawful_promotions_v1(
        session,
        tenant_id=tenant_id,
        cap=cap,
        trigger=trigger,
    )

    summary: dict[str, Any] = {
        "gate_id": GP085_PROMO01_GATE_ID_V1,
        "trigger": trigger,
        "promotion_policy_ref": CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
        "promotion_policy_id": str(policy.id),
        "promoted_count": len(promoted_ids),
        "promoted_link_ids": promoted_ids,
        "skipped_count": len(skipped),
        "skipped": skipped,
        "max_promotions": cap,
        "unpromoted_remaining": count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id),
        "graph_candidate_count": count_graph_candidate_count_v1(session, tenant_id=tenant_id),
    }
    if pipeline_run_id is not None:
        summary["pipeline_run_id"] = str(pipeline_run_id)

    if summary["unpromoted_remaining"] > 0 and len(promoted_ids) >= cap:
        from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
            build_upstream_cap_omission_v1,
        )

        summary["upstream_cap_omission"] = build_upstream_cap_omission_v1(
            cap_kind="graph_promotion_max_per_pass",
            detail=f"promoted={len(promoted_ids)} cap={cap} remaining={summary['unpromoted_remaining']}",
            deferred_count=int(summary["unpromoted_remaining"]),
        )

    if job is not None:
        _finalize_lawful_promotion_replay_job_v1(session, job=job, summary=summary)
        summary["org_link_replay_job_id"] = str(job.id)
    elif require_receipt:
        raise GraphDensityPromotionError("replay_job_required_but_not_created")

    return summary


def execute_lawful_edge_promotion_replay_job_v1(
    session: Session,
    job: CortexOrgLinkReplayJob,
) -> None:
    """Org-link replay lane handler for ``lawful_edge_promotion`` jobs (job row pre-created)."""
    scope = dict(job.scope_json or {})
    trigger = str(scope.get("trigger") or PROMOTION_TRIGGER_MANUAL_V1)
    prid_raw = scope.get("pipeline_run_id")
    prid = uuid.UUID(str(prid_raw)) if prid_raw else None
    run_graph_density_promotion_pass_v1(
        session,
        tenant_id=job.tenant_id,
        trigger=trigger,
        pipeline_run_id=prid,
        org_link_replay_job_id=job.id,
    )


def public_graph_density_promotion_run_payload_v1(schedule_out: dict[str, Any]) -> dict[str, Any]:
    """Flatten inline promotion pass output for admin HTTP (G-P085-PROMO-01)."""
    if schedule_out.get("scheduled") and isinstance(schedule_out.get("pass"), dict):
        pass_out = dict(schedule_out["pass"])
        pass_out["schedule_meta"] = {k: v for k, v in schedule_out.items() if k != "pass"}
        return pass_out
    return schedule_out


def record_graph_density_promotion_schedule_on_lease_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    schedule_out: dict[str, Any],
    convergence_reason: str,
) -> dict[str, Any]:
    """Persist last inline promotion schedule outcome on execution lease (D3 observability)."""
    from datetime import UTC, datetime

    from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1

    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None:
        return {"persisted": False, "reason": "no_lease"}
    detail = dict(lease.detail_json or {})
    manifest = {
        "updated_at": datetime.now(UTC).isoformat(),
        "convergence_reason": convergence_reason,
        "scheduled": bool(schedule_out.get("scheduled")),
        "path": schedule_out.get("path"),
        "schedule_reason": (schedule_out.get("evaluation") or {}).get("schedule_reason")
        or schedule_out.get("reason"),
        "promoted_count": int((schedule_out.get("pass") or {}).get("promoted_count") or 0),
    }
    detail[DETAIL_KEY_GRAPH_DENSITY_PROMOTION_SCHEDULE_V1] = manifest
    lease.detail_json = detail
    session.flush()
    return manifest


def schedule_graph_density_promotion_on_convergence_worker_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    convergence_reason: str = "convergence_slice",
) -> dict[str, Any] | None:
    """D3: inline promotion pass on each convergence worker slice when backlog exceeds threshold."""
    if not is_graph_density_promotion_on_convergence_enabled_v1():
        return {"scheduled": False, "reason": "convergence_promotion_disabled"}
    out = schedule_graph_density_pass_v1(
        tenant_id=tenant_id,
        trigger=PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
        force=False,
        session=session,
    )
    record_graph_density_promotion_schedule_on_lease_v1(
        session,
        tenant_id=tenant_id,
        schedule_out=out,
        convergence_reason=convergence_reason,
    )
    return out


def schedule_graph_density_pass_v1(
    *,
    tenant_id: uuid.UUID,
    trigger: str = PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
    pipeline_run_id: uuid.UUID | None = None,
    countdown: int | None = None,
    force: bool = False,
    session: Session | None = None,
) -> dict[str, Any]:
    """M9: synchronous inline pass only (admin / catalog; not wired from phase 04)."""
    _ = countdown
    _ = pipeline_run_id

    def _run(sess: Session) -> dict[str, Any]:
        eval_out = evaluate_promotion_backlog_schedule_v1(
            sess,
            tenant_id=tenant_id,
            trigger=trigger,
        )
        if not force and not eval_out.get("should_schedule"):
            return {
                "scheduled": False,
                "reason": eval_out.get("schedule_reason"),
                "evaluation": eval_out,
            }
        pass_out = run_graph_density_promotion_pass_v1(sess, tenant_id=tenant_id, trigger=trigger)
        return {
            "scheduled": True,
            "path": "inline_execution_slice",
            "trigger": trigger,
            "evaluation": eval_out,
            "pass": pass_out,
        }

    if session is not None:
        return _run(session)
    from vector.infrastructure.db.session import session_scope

    with session_scope() as scoped:
        out = _run(scoped)
        scoped.commit()
        return out


def build_graph_density_promotion_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_graph_promotion_runtime_schema_version": int(
            PHASE085_GRAPH_PROMOTION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_GRAPH_PROMOTION_SPEC_REF_V1,
        "primary_gate_id": GP085_PROMO01_GATE_ID_V1,
        "related_gate_id": GP085_GRAPH01_GATE_ID_V1,
        "promotion_policy_ref": CESP_LAWFUL_PROMOTION_POLICY_REF_V1,
        "org_link_job_kind": ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,
        "celery_task_name": CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1,
        "promotion_triggers": [
            PROMOTION_TRIGGER_AFTER_PHASE_04_V1,
            PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
            PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
            PROMOTION_TRIGGER_MANUAL_V1,
        ],
        "convergence_worker_schedule_enabled": is_graph_density_promotion_on_convergence_enabled_v1(),
        "max_per_pass": get_promotion_max_per_pass_v1(),
        "backlog_threshold": get_promotion_backlog_threshold_v1(),
        "require_org_link_replay_receipt": get_promotion_require_replay_receipt_v1(),
        "schedule_countdown_seconds": get_promotion_schedule_countdown_seconds_v1(),
        "runtime_package": "vector.domains.cortex.operational_runtime.graph_density_promotion",
        "scheduler_entrypoint": "schedule_graph_density_pass_v1",
        "pass_entrypoint": "run_graph_density_promotion_pass_v1",
    }


def _register_lawful_edge_promotion_lane_v1() -> None:
    from vector.domains.cortex.identity.org_link_replay_lane_registry import (
        register_lawful_edge_promotion_runner_v1,
    )

    register_lawful_edge_promotion_runner_v1(execute_lawful_edge_promotion_replay_job_v1)


_register_lawful_edge_promotion_lane_v1()


def verify_gp085_promo01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_graph_density_promotion_catalog_v1()
    if cat["primary_gate_id"] != GP085_PROMO01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    src = inspect.getsource(run_graph_density_promotion_pass_v1)
    if "random" in src.lower():
        errors.append("probabilistic_promotion_forbidden")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    pr_src = inspect.getsource(pr.run_phase_04_graph_v1)
    if "schedule_graph_density_pass_v1" in pr_src:
        errors.append("phase_04_must_not_schedule_graph_density_sidecar_m9")

    from vector.domains.cortex.identity import org_link_replay_lane_registry as reg
    from vector.domains.cortex.identity import org_link_replay_runtime as orr

    reg_src = inspect.getsource(reg.run_lawful_edge_promotion_lane_v1)
    if "lawful_edge_promotion_runner_not_registered" not in reg_src:
        errors.append("org_link_lane_registry_missing_lawful_runner_guard")
    orr_src = inspect.getsource(orr.run_org_link_replay_job_for_row)
    if ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1 not in orr_src:
        errors.append("org_link_replay_missing_lawful_edge_promotion_lane")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_graph_density_promotion") is not None:
        errors.append("celery_graph_density_promotion_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_PROMO01_GATE_ID_V1,
        "name": "cesp_graph_density_promotion",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

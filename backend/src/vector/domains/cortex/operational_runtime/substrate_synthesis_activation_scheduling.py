"""Phase 08.5 P085-24 — synthesis activation scheduler (**G-P085-SYN-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-synthesis-activation-doctrine.md`` §Continuous activation.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Mapping

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.synthesis.phase08_activation_gate import (
    SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
    SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
    compute_min_synthesis_jobs_target_v1,
    count_recent_synthesis_forbidden_v1,
    evaluate_synthesis_activation_schedule_v1 as _evaluate_synthesis_activation_schedule_v1,
    get_synthesis_forbidden_backoff_threshold_v1,
    get_synthesis_forbidden_backoff_window_hours_v1,
    is_phase_08_pipeline_enabled_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import (
    materialize_synthesis_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE085_SYNTHESIS_ACTIVATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SYNTHESIS_ACTIVATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-synthesis-activation-doctrine.md"
)

GP085_SYN01_GATE_ID_V1: Final[str] = "G-P085-SYN-01"

CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.schedule_synthesis_activation_for_tenant"
)

class SubstrateSynthesisActivationSchedulingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def build_synthesis_forbidden_escalation_panel_v1(
    *,
    tenant_id: uuid.UUID,
    forbidden_metrics: Mapping[str, Any],
    eligibility: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Operator panel when repeated ``synthesis_forbidden`` blocks automatic activation."""
    count = int(forbidden_metrics.get("forbidden_count") or 0)
    threshold = int(forbidden_metrics.get("forbidden_backoff_threshold") or 3)
    window = int(forbidden_metrics.get("forbidden_backoff_window_hours") or 24)
    messages = [
        (
            f"Synthesis activation paused: {count} synthesis_forbidden job(s) in the last "
            f"{window}h (threshold {threshold})."
        ),
        "Resolve legality upstream (retrieval pins, policy pack, replay posture) before retrying.",
        "Use admin synthesis legality APIs or POST .../synthesis-activation-scheduling/run with force=true.",
    ]
    return {
        "panel_title": "Synthesis forbidden backoff",
        "messages": messages,
        "forbidden_metrics": dict(forbidden_metrics),
        "eligibility": dict(eligibility or {}),
        "tenant_id": str(tenant_id),
    }


def evaluate_synthesis_activation_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Admin/CI wrapper — execution slice uses ``synthesis.phase08_activation_gate`` directly."""
    out = _evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        trigger=trigger,
        force=force,
    )
    return {**out, "gate_id": GP085_SYN01_GATE_ID_V1}


def chain_synthesis_activation_after_phase07_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Chain phase 08 after phase 07 publish with **G-P085-SYN-01** activation law."""
    eval_out = evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        trigger=SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
        force=force,
    )

    if not eval_out["phase_08_enabled"]:
        from vector.domains.cortex.substrate_pipeline.repository import skip_phase_v1

        skip_phase_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_08_SYNTHESIS,
            reason="phase_08_disabled",
        )
        from vector.domains.cortex.substrate_pipeline.orchestrator import (
            finalize_pipeline_if_complete_v1,
        )

        fin = finalize_pipeline_if_complete_v1(session, pipeline_run_id=pipeline_run_id)
        return {
            "chained": False,
            "phase_08_skipped": True,
            "finalize": fin,
            "activation_evaluation": eval_out,
        }

    if not eval_out["should_activate"]:
        panel = build_synthesis_forbidden_escalation_panel_v1(
            tenant_id=tenant_id,
            forbidden_metrics=dict(eval_out["forbidden_backoff"]),
            eligibility=eval_out.get("eligibility_summary"),
        )
        return {
            "chained": False,
            "synthesis_forbidden_backoff": True,
            "activation_evaluation": eval_out,
            "synthesis_forbidden_escalation_panel": panel,
        }

    from vector.domains.cortex.substrate_pipeline.orchestrator import (
        enqueue_next_pipeline_phase_v1,
    )

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_08_SYNTHESIS,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
    return {
        "chained": True,
        "activation_evaluation": eval_out,
        "next_phase_chain": chain,
        "min_jobs_target": eval_out["min_jobs_target"],
    }


def run_synthesis_activation_schedule_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str = SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
    force: bool = False,
    execute_inline: bool = True,
) -> dict[str, Any]:
    """Run synthesis activation inline or enqueue phase 08 Celery task."""
    prid = pipeline_run_id
    if prid is None:
        running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
        if running is not None:
            prid = running.id

    eval_out = evaluate_synthesis_activation_schedule_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        published_index_epoch=published_index_epoch,
        trigger=trigger,
        force=force,
    )

    if not eval_out["should_activate"]:
        panel = None
        if eval_out["activation_reason"] == "synthesis_forbidden_backoff":
            panel = build_synthesis_forbidden_escalation_panel_v1(
                tenant_id=tenant_id,
                forbidden_metrics=dict(eval_out["forbidden_backoff"]),
            )
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": False,
            "reason": eval_out["activation_reason"],
            "evaluation": eval_out,
            "synthesis_forbidden_escalation_panel": panel,
        }

    if prid is None:
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": False,
            "reason": "no_pipeline_run_id",
            "evaluation": eval_out,
        }

    if execute_inline:
        from vector.domains.cortex.synthesis.synthesis_pipeline import (
            run_substrate_phase_08_synthesis_v1,
        )

        phase_out = run_substrate_phase_08_synthesis_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
        )
        return {
            "gate_id": GP085_SYN01_GATE_ID_V1,
            "activated": True,
            "execution_mode": "inline_phase_08",
            "evaluation": eval_out,
            "phase_08_output": phase_out,
        }

    from vector.domains.cortex.substrate_pipeline.orchestrator import (
        enqueue_next_pipeline_phase_v1,
    )

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        phase_id=PHASE_08_SYNTHESIS,
    )
    return {
        "gate_id": GP085_SYN01_GATE_ID_V1,
        "activated": True,
        "execution_mode": "celery_phase_08",
        "evaluation": eval_out,
        "next_phase_chain": chain,
    }


def run_synthesis_activation_after_phase07_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Phase 07 completion hook — evaluate + chain phase 08 (**G-P085-SYN-01**)."""
    return chain_synthesis_activation_after_phase07_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        published_index_epoch=published_index_epoch,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )


def schedule_synthesis_activation_for_tenant_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    published_index_epoch: str | None = None,
    trigger: str = SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
    countdown: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Enqueue async synthesis activation schedule pass."""
    from vector.infrastructure.db.session import session_scope

    with session_scope() as session:
        eval_out = evaluate_synthesis_activation_schedule_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            trigger=trigger,
            force=force,
        )
    if not force and not eval_out.get("should_activate"):
        return {
            "scheduled": False,
            "reason": eval_out.get("activation_reason"),
            "evaluation": eval_out,
        }

    _ = countdown
    with session_scope() as session:
        pass_out = run_synthesis_activation_schedule_pass_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            trigger=trigger,
            force=force,
        )
        session.commit()
    return {
        "scheduled": True,
        "path": "inline_execution_slice",
        "evaluation": eval_out,
        "pass": pass_out,
    }


def build_substrate_synthesis_activation_scheduling_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_synthesis_activation_runtime_schema_version": int(
            PHASE085_SYNTHESIS_ACTIVATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SYNTHESIS_ACTIVATION_SPEC_REF_V1,
        "primary_gate_id": GP085_SYN01_GATE_ID_V1,
        "phase_08_setting": "CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED",
        "max_scopes_setting": "CORTEX_SYNTHESIS_PIPELINE_MAX_SCOPES",
        "forbidden_backoff_threshold": get_synthesis_forbidden_backoff_threshold_v1(),
        "forbidden_backoff_window_hours": get_synthesis_forbidden_backoff_window_hours_v1(),
        "min_jobs_formula": "min(eligible_scopes, max_scopes_per_pass)",
        "activation_audit_table": "cortex_synthesis_activation_audits",
        "materialize_entrypoint": "materialize_synthesis_for_pipeline_v1",
        "celery_task_name": CELERY_SYNTHESIS_ACTIVATION_SCHEDULE_TASK_NAME_V1,
        "scheduler_entrypoint": "schedule_synthesis_activation_for_tenant_v1",
        "pass_entrypoint": "run_synthesis_activation_schedule_pass_v1",
        "phase08_entry_evaluation": "evaluate_synthesis_activation_schedule_v1",
        "deprecated_phase07_hook": "run_synthesis_activation_after_phase07_v1",
        "schedule_triggers": [
            SYNTHESIS_ACTIVATION_TRIGGER_AFTER_PHASE_07_V1,
            SYNTHESIS_ACTIVATION_TRIGGER_MANUAL_V1,
        ],
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling"
        ),
    }


def verify_gp085_syn01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_synthesis_activation_scheduling_catalog_v1()
    if cat["primary_gate_id"] != GP085_SYN01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    if compute_min_synthesis_jobs_target_v1(eligible_scopes=10, max_scopes=4) != 4:
        errors.append("min_jobs_target_formula")
    if compute_min_synthesis_jobs_target_v1(eligible_scopes=2, max_scopes=32) != 2:
        errors.append("min_jobs_target_eligible_smaller")

    mat_src = inspect.getsource(materialize_synthesis_for_pipeline_v1)
    if "persist_synthesis_activation_audit_v1" not in mat_src:
        errors.append("materialize_missing_activation_audit")

    pass_src = inspect.getsource(run_synthesis_activation_schedule_pass_v1)
    if "random" in pass_src.lower():
        errors.append("probabilistic_activation_forbidden")

    from vector.domains.cortex.substrate_pipeline import orchestrator as orch_mod

    pub_src = inspect.getsource(orch_mod.on_retrieval_publish_completed_for_pipeline_v1)
    if "chain_synthesis_activation_after_phase07_v1" not in pub_src:
        errors.append("orchestrator_missing_activation_chain")

    from vector.domains.cortex.substrate_pipeline import phase_runners as pr
    from vector.domains.cortex.synthesis import synthesis_pipeline as syn_mod

    p07_src = inspect.getsource(pr.run_phase_07_retrieval_v1)
    if "run_synthesis_activation_after_phase07_v1" in p07_src:
        errors.append("phase07_must_not_call_synthesis_activation")

    p08_src = inspect.getsource(syn_mod.run_substrate_phase_08_synthesis_v1)
    if "operational_runtime" in p08_src:
        errors.append("phase08_must_not_import_operational_runtime")
    if "phase08_activation_gate" not in p08_src:
        errors.append("phase08_must_import_phase08_activation_gate")
    if "evaluate_synthesis_activation_schedule_v1" not in p08_src:
        errors.append("phase08_missing_synthesis_activation_evaluation")

    from vector.domains.cortex.synthesis.phase08_activation_gate import (
        evaluate_synthesis_activation_schedule_v1 as phase08_evaluate_v1,
    )

    eval_src = inspect.getsource(phase08_evaluate_v1)
    if "synthesis_forbidden_backoff" not in eval_src:
        errors.append("evaluate_missing_forbidden_backoff")

    import importlib.util

    if importlib.util.find_spec("app.tasks.cortex_substrate_synthesis_activation_scheduling") is not None:
        errors.append("celery_synthesis_activation_module_must_be_deleted_m9")

    passed = not errors
    return {
        "id": GP085_SYN01_GATE_ID_V1,
        "name": "cesp_substrate_synthesis_activation_scheduling",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

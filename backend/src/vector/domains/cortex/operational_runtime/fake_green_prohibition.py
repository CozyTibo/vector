"""Phase 08.5 Step 02 — fake-green prohibition law (**G-P085-ANTI-IDLE-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-endgoal-doctrine.md``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1

GP085_ANTI_IDLE01_GATE_ID_V1: Final[str] = "G-P085-ANTI-IDLE-01"

PHASE085_ENDGOAL_DOCTRINE_REF_V1: Final[str] = (
    "DOCS/cortex/operational-runtime/phase-085-endgoal-doctrine.md"
)

OPERATIONAL_IDLE_HEALTHY_IDLE_V1: Final[str] = "healthy_idle"
OPERATIONAL_IDLE_STARVATION_V1: Final[str] = "operational_starvation"
OPERATIONAL_IDLE_PROGRESSING_V1: Final[str] = "progressing"
OPERATIONAL_IDLE_BLOCKED_CONTINUATION_V1: Final[str] = "blocked_by_pipeline_continuation"

SYNTHESIS_IDLE_STARVED_V1: Final[str] = "starved"
SYNTHESIS_IDLE_HEALTHY_IDLE_V1: Final[str] = "healthy_idle"
SYNTHESIS_IDLE_PROGRESSING_V1: Final[str] = "progressing"

CESP_ANTI_IDLE_STAGE_IDS_V1: Final[frozenset[str]] = frozenset(
    {"graph", "traversal", "tcre", "retrieval", "synthesis"}
)

TCRE_OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1: Final[str] = "reconstruction_not_yet_run"
RETRIEVAL_OMISSION_INDEX_EMPTY_V1: Final[str] = "retrieval_index_empty"

_PIPELINE_WAIT_STATUSES_V1: Final[frozenset[str]] = frozenset(
    {CONTINUATION_STATUS_WAITING, CONTINUATION_STATUS_STALLED}
)


class CespAntiIdleLawError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def refresh_stage_envelope_receipt_digest_v1(stage: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute ``stage_receipt_digest`` after anti-idle mutation."""
    body = dict(stage)
    payload = {k: v for k, v in body.items() if k != "stage_receipt_digest"}
    body["stage_receipt_digest"] = hash_reasoning_canonical_json_sha256_v1(payload)
    return body


def count_propagation_edges_to_stage_v1(
    stage_id: str,
    propagation_chain: Sequence[Mapping[str, Any]],
) -> int:
    return sum(1 for edge in propagation_chain if str(edge.get("to_stage")) == stage_id)


def pipeline_continuation_blocks_progress_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if running is None or not hasattr(running, "id"):
        return False
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
    if continuation is None:
        return False
    return str(continuation.continuation_status) in _PIPELINE_WAIT_STATUSES_V1


def upstream_work_exists_v1(stages_by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    graph = stages_by_id.get("graph") or {}
    graph_metrics = graph.get("metrics") or {}
    if int(graph_metrics.get("entity_count") or 0) > 0:
        return True
    tcre = stages_by_id.get("tcre") or {}
    if int(tcre.get("total_objects") or 0) > 0:
        return True
    trav = stages_by_id.get("traversal") or {}
    trav_metrics = trav.get("metrics") or {}
    if int(trav_metrics.get("graph_entity_count") or 0) > 0:
        return True
    if int(trav.get("total_objects") or 0) > 0:
        return True
    return False


def tcre_reconstruction_pending_v1(stages_by_id: Mapping[str, Mapping[str, Any]]) -> bool:
    tcre = stages_by_id.get("tcre") or {}
    omissions = tcre.get("omission_classes") or {}
    if not isinstance(omissions, dict):
        return False
    if int(omissions.get(TCRE_OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1) or 0) > 0:
        return True
    metrics = tcre.get("metrics") or {}
    return bool(metrics.get("reconstruction_never_run"))


def classify_stage_operational_idle_v1(
    *,
    stage_id: str,
    total_objects: int,
    processed_count: int,
    substrate_state: str,
    propagating_edge_count: int,
    pipeline_blocked: bool,
    upstream_starvation: bool,
) -> str:
    """INV-05 — classify idle vs starvation for admin cards."""
    if pipeline_blocked and stage_id in ("tcre", "retrieval", "synthesis"):
        return OPERATIONAL_IDLE_BLOCKED_CONTINUATION_V1
    if total_objects > 0 and processed_count == 0 and substrate_state != "critical":
        return OPERATIONAL_IDLE_STARVATION_V1
    if propagating_edge_count > 0 and processed_count == 0:
        return OPERATIONAL_IDLE_STARVATION_V1
    if upstream_starvation and total_objects == 0 and stage_id in ("retrieval", "synthesis"):
        return OPERATIONAL_IDLE_STARVATION_V1
    if total_objects == 0 and processed_count == 0 and not upstream_starvation:
        return OPERATIONAL_IDLE_HEALTHY_IDLE_V1
    return OPERATIONAL_IDLE_PROGRESSING_V1


def classify_synthesis_idle_v1(
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
    upstream_starvation: bool,
) -> str:
    """INV-05 / **G-P085-SYN-02** partial — starved vs healthy idle."""
    if eligible_scopes > 0 and synthesized_scopes == 0:
        return SYNTHESIS_IDLE_STARVED_V1
    if eligible_scopes == 0 and upstream_starvation:
        return SYNTHESIS_IDLE_STARVED_V1
    if eligible_scopes == 0:
        return SYNTHESIS_IDLE_HEALTHY_IDLE_V1
    return SYNTHESIS_IDLE_PROGRESSING_V1


def must_degrade_for_anti_idle_law_v1(
    *,
    substrate_state: str,
    operational_idle_class: str,
) -> bool:
    if substrate_state != "healthy":
        return False
    return operational_idle_class in (
        OPERATIONAL_IDLE_STARVATION_V1,
        OPERATIONAL_IDLE_BLOCKED_CONTINUATION_V1,
    )


def apply_cesp_anti_idle_law_to_stage_envelope_v1(
    stage: Mapping[str, Any],
    *,
    operational_idle_class: str,
    synthesis_idle_classification: str | None = None,
    force_degraded: bool = False,
) -> dict[str, Any]:
    """Apply **G-P085-ANTI-IDLE-01** to a single stage envelope."""
    out = dict(stage)
    metrics = dict(out.get("metrics") or {})
    metrics["operational_idle_class"] = operational_idle_class
    metrics["cesp_anti_idle_gate_id"] = GP085_ANTI_IDLE01_GATE_ID_V1
    if synthesis_idle_classification is not None:
        metrics["synthesis_idle_classification"] = synthesis_idle_classification
    out["metrics"] = metrics

    if force_degraded and out.get("substrate_state") == "healthy":
        out["substrate_state"] = "degraded"
        drift = list(out.get("drift_warnings") or [])
        drift.append(
            f"{GP085_ANTI_IDLE01_GATE_ID_V1}: {operational_idle_class} — "
            "substrate_state coerced from healthy"
        )
        out["drift_warnings"] = drift

    return refresh_stage_envelope_receipt_digest_v1(out)


def apply_cesp_anti_idle_law_to_pipeline_stages_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stages: Sequence[Mapping[str, Any]],
    propagation_chain: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Post-pass on graph/traversal/tcre/retrieval/synthesis envelopes."""
    stages_by_id = {str(s.get("stage_id")): s for s in stages}
    pipeline_blocked = pipeline_continuation_blocks_progress_v1(session, tenant_id=tenant_id)
    tcre_pending = tcre_reconstruction_pending_v1(stages_by_id)
    upstream_work = upstream_work_exists_v1(stages_by_id)
    upstream_starvation = upstream_work and (tcre_pending or pipeline_blocked)

    out_stages: list[dict[str, Any]] = []
    for stage in stages:
        stage_id = str(stage.get("stage_id"))
        if stage_id not in CESP_ANTI_IDLE_STAGE_IDS_V1:
            out_stages.append(dict(stage))
            continue

        total = int(stage.get("total_objects") or 0)
        processed = int(stage.get("processed_count") or 0)
        propagating = count_propagation_edges_to_stage_v1(stage_id, propagation_chain)

        idle_class = classify_stage_operational_idle_v1(
            stage_id=stage_id,
            total_objects=total,
            processed_count=processed,
            substrate_state=str(stage.get("substrate_state") or "healthy"),
            propagating_edge_count=propagating,
            pipeline_blocked=pipeline_blocked,
            upstream_starvation=upstream_starvation,
        )

        synth_idle: str | None = None
        if stage_id == "synthesis":
            metrics = stage.get("metrics") or {}
            synth_idle = classify_synthesis_idle_v1(
                eligible_scopes=int(metrics.get("eligible_scopes") or 0),
                synthesized_scopes=int(metrics.get("synthesized_scopes") or 0),
                upstream_starvation=upstream_starvation,
            )

        if stage_id == "retrieval" and total == 0 and upstream_starvation:
            idle_class = OPERATIONAL_IDLE_STARVATION_V1

        force = must_degrade_for_anti_idle_law_v1(
            substrate_state=str(stage.get("substrate_state") or "healthy"),
            operational_idle_class=idle_class,
        )
        if total > 0 and processed == 0 and stage.get("substrate_state") == "healthy":
            force = True
        if propagating > 0 and stage.get("substrate_state") == "healthy":
            force = True

        patched = apply_cesp_anti_idle_law_to_stage_envelope_v1(
            stage,
            operational_idle_class=idle_class,
            synthesis_idle_classification=synth_idle,
            force_degraded=force,
        )
        out_stages.append(patched)

    return out_stages


def assert_never_fake_green_healthy_v1(
    *,
    stage_id: str,
    total_objects: int,
    processed_count: int,
    substrate_state: str,
) -> None:
    """Legality assertion used by static gate + runtime checks."""
    if (
        stage_id in CESP_ANTI_IDLE_STAGE_IDS_V1
        and total_objects > 0
        and processed_count == 0
        and substrate_state == "healthy"
    ):
        raise CespAntiIdleLawError(
            "fake_green_healthy_with_unprocessed_work",
            detail={
                "stage_id": stage_id,
                "total_objects": total_objects,
                "processed_count": processed_count,
            },
        )


def verify_tenant_anti_idle_law_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Tenant-scoped **G-P085-ANTI-IDLE-01** verification over substrate completeness ledger."""
    from vector.domains.cortex.completeness.substrate_completeness_ledger import (
        build_substrate_completeness_ledger_v1,
    )

    ledger = build_substrate_completeness_ledger_v1(session, tenant_id=tenant_id)
    failures: list[str] = []
    for stage in ledger.get("pipeline_stages") or []:
        stage_id = str(stage.get("stage_id"))
        if stage_id not in CESP_ANTI_IDLE_STAGE_IDS_V1:
            continue
        total = int(stage.get("total_objects") or 0)
        processed = int(stage.get("processed_count") or 0)
        state = str(stage.get("substrate_state") or "")
        try:
            assert_never_fake_green_healthy_v1(
                stage_id=stage_id,
                total_objects=total,
                processed_count=processed,
                substrate_state=state,
            )
        except CespAntiIdleLawError:
            failures.append(f"{stage_id}:fake_green_healthy")
        metrics = stage.get("metrics") or {}
        idle = str(metrics.get("operational_idle_class") or "")
        if idle == OPERATIONAL_IDLE_STARVATION_V1 and state == "healthy":
            failures.append(f"{stage_id}:starvation_marked_healthy")
        if stage_id == "tcre":
            if bool(metrics.get("reconstruction_never_run")) and state == "healthy":
                failures.append("tcre:reconstruction_never_run_healthy")
        if stage_id == "synthesis":
            synth_idle = str(metrics.get("synthesis_idle_classification") or "")
            if synth_idle == SYNTHESIS_IDLE_STARVED_V1 and state == "healthy":
                failures.append("synthesis:starved_marked_healthy")

    passed = not failures
    return {
        "id": GP085_ANTI_IDLE01_GATE_ID_V1,
        "gate_id": GP085_ANTI_IDLE01_GATE_ID_V1,
        "passed": passed,
        "failure_codes": failures,
        "tenant_id": str(tenant_id),
        "substrate_state": ledger.get("substrate_state"),
        "spec_ref": PHASE085_ENDGOAL_DOCTRINE_REF_V1,
    }

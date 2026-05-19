"""Phase 08.5 P085-23 — retrieval completeness propagation (**G-P085-RET-PROP-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-retrieval-density-doctrine.md`` §Completeness propagation.
Closes retrieval card starved vs idle law (**P0-085-04** propagation surface).
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
    OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
    OPERATIONAL_IDLE_PROGRESSING_V1,
    OPERATIONAL_IDLE_STARVATION_V1,
    RETRIEVAL_OMISSION_INDEX_EMPTY_V1,
    TCRE_OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    compute_retrieval_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    evaluate_retrieval_starvation_v1,
    merge_retrieval_starvation_into_completeness_v1,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1,
    RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1,
    RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1,
    RETRIEVAL_STAGE_OMISSION_REPLAY_DIVERGENCE_V1,
    RETRIEVAL_STAGE_OMISSION_UPSTREAM_TCRE_GAP_V1,
    assert_retrieval_never_idle_healthy_when_eligible_v1,
    count_retrieval_eligible_artifacts_v1,
    count_retrieval_indexed_in_published_epoch_v1,
    derive_retrieval_stage_substrate_state_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    compute_index_lag_epochs_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    get_retrieval_replay_divergence_total_v1,
)

PHASE085_RETRIEVAL_PROPAGATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_RETRIEVAL_PROPAGATION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-retrieval-density-doctrine.md"
)

GP085_RET_PROP01_GATE_ID_V1: Final[str] = "G-P085-RET-PROP-01"

RETRIEVAL_PROPAGATION_LAW_VERSION_V1: Final[str] = "cesp.retrieval_completeness_propagation.v1"

RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1: Final[str] = "retrieval_operational_starvation"

RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1: Final[str] = "starved"
RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1: Final[str] = "healthy_idle"
RETRIEVAL_CARD_CLASSIFICATION_PROGRESSING_V1: Final[str] = "progressing"

RETRIEVAL_PROPAGATION_DOWNSTREAM_STAGES_V1: Final[tuple[str, ...]] = ("synthesis",)

METRIC_OPERATIONAL_STARVATION_V1: Final[str] = "operational_starvation"
METRIC_RETRIEVAL_CARD_CLASSIFICATION_V1: Final[str] = "retrieval_card_classification"
METRIC_RETRIEVAL_IDLE_CLASS_V1: Final[str] = "retrieval_idle_class"


def _pct(numerator: int, denominator: int) -> float:
    from vector.domains.cortex.completeness._completeness_common import pct

    return pct(numerator, denominator)


def classify_retrieval_card_v1(
    *,
    eligible: int,
    indexed: int,
    operational_starvation: bool,
    idle_class: str,
    upstream_tcre_pending: bool,
    upstream_work_present: bool,
) -> str:
    """**INV-05** — starved vs healthy_idle vs progressing on admin card."""
    if operational_starvation or (eligible > 0 and indexed == 0):
        return RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
    if idle_class == OPERATIONAL_IDLE_HEALTHY_IDLE_V1:
        return RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1
    if eligible == 0 and (upstream_tcre_pending or upstream_work_present):
        return RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
    if idle_class == OPERATIONAL_IDLE_STARVATION_V1:
        return RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
    return RETRIEVAL_CARD_CLASSIFICATION_PROGRESSING_V1


def derive_retrieval_completeness_substrate_state_v1(
    *,
    eligible: int,
    indexed: int,
    coverage_percent: float,
    published_epoch: str | None,
    replay_posture: str,
    pending_index_builds: int,
    upstream_tcre_pending: bool,
    upstream_work_present: bool,
    operational_starvation: bool,
    index_stale: bool,
    fake_green_blocked: bool,
) -> str:
    """Derive retrieval ``substrate_state`` with starvation + fake-green card law."""
    if fake_green_blocked or operational_starvation or index_stale:
        return "degraded"
    return derive_retrieval_stage_substrate_state_v1(
        eligible=eligible,
        indexed=indexed,
        coverage_percent=coverage_percent,
        published_epoch=published_epoch,
        replay_posture=replay_posture,
        pending_index_builds=pending_index_builds,
        upstream_tcre_pending=upstream_tcre_pending,
        upstream_work_present=upstream_work_present,
    )


def evaluate_retrieval_card_fake_green_v1(
    *,
    eligible: int,
    indexed: int,
    substrate_state: str,
    operational_starvation: bool,
    upstream_tcre_pending: bool,
) -> dict[str, Any]:
    """Detect fake-green retrieval card (**G-P085-RET-PROP-01** / **INV-05**)."""
    blocked = False
    reasons: list[str] = []
    if eligible > 0 and indexed == 0 and substrate_state == "healthy":
        blocked = True
        reasons.append("eligible_unindexed_healthy")
    if operational_starvation and substrate_state == "healthy":
        blocked = True
        reasons.append("operational_starvation_healthy")
    if eligible == 0 and upstream_tcre_pending and substrate_state == "healthy":
        blocked = True
        reasons.append("upstream_tcre_pending_idle_healthy")
    return {
        "fake_green_blocked": blocked,
        "fake_green_reasons": reasons,
    }


def build_retrieval_stage_omission_classes_v1(
    *,
    never_indexed: bool,
    published: str | None,
    indexed: int,
    stale_epochs: list[str],
    tcre_gap: int,
    divergence_total: int,
    operational_starvation: bool,
    starvation_eval: dict[str, Any],
) -> dict[str, int]:
    """Merge retrieval stage omissions for degradation propagation."""
    omissions: dict[str, int] = {}
    if never_indexed:
        omissions[RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1] = 1
    if published and indexed == 0:
        omissions[RETRIEVAL_OMISSION_INDEX_EMPTY_V1] = 1
    if stale_epochs:
        omissions[RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1] = len(stale_epochs)
    if tcre_gap > 0 and not never_indexed:
        omissions[RETRIEVAL_STAGE_OMISSION_UPSTREAM_TCRE_GAP_V1] = tcre_gap
    if divergence_total > 0:
        omissions[RETRIEVAL_STAGE_OMISSION_REPLAY_DIVERGENCE_V1] = divergence_total
    if operational_starvation:
        omissions[RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1] = 1
    freshness = dict(starvation_eval.get("index_freshness") or {})
    if freshness.get("index_stale"):
        omissions[RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1] = max(
            omissions.get(RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1, 0),
            1,
        )
    return omissions


def build_retrieval_completeness_propagation_manifest_v1(
    *,
    substrate_state: str,
    card_classification: str,
    idle_class: str,
    operational_starvation: bool,
    fake_green_evaluation: dict[str, Any],
    starvation_eval: dict[str, Any],
    density_snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "law_version": RETRIEVAL_PROPAGATION_LAW_VERSION_V1,
        "gate_id": GP085_RET_PROP01_GATE_ID_V1,
        "substrate_state": substrate_state,
        METRIC_RETRIEVAL_CARD_CLASSIFICATION_V1: card_classification,
        METRIC_RETRIEVAL_IDLE_CLASS_V1: idle_class,
        METRIC_OPERATIONAL_STARVATION_V1: operational_starvation,
        "card_total_objects_law": "eligible_artifact_count",
        "card_processed_count_law": "indexed_count",
        "fake_green_evaluation": dict(fake_green_evaluation),
        "starvation_evaluation": {
            "starvation_reasons": list(starvation_eval.get("starvation_reasons") or []),
            "healthy_idle": bool(starvation_eval.get("healthy_idle")),
            "index_freshness": dict(starvation_eval.get("index_freshness") or {}),
        },
        "latest_materialization_report_id": density_snapshot.get("latest_materialization_report_id"),
        "downstream_stages": list(RETRIEVAL_PROPAGATION_DOWNSTREAM_STAGES_V1),
    }


def propagate_retrieval_completeness_stage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Build retrieval completeness stage with density + starvation propagation law."""
    from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1
    from vector.domains.cortex.completeness.graph_completeness_projection import (
        project_graph_completeness_v1,
    )
    from vector.domains.cortex.completeness.tcre_completeness_projection import (
        project_tcre_completeness_v1,
    )
    from vector.domains.cortex.operational_runtime.fake_green_prohibition import (
        upstream_work_exists_v1,
    )

    density = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    starvation_eval = evaluate_retrieval_starvation_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])

    eligible_breakdown = {
        k: dm[k]
        for k in (
            "tcre_indexable_count",
            "walk_record_count",
            "graph_link_count",
            "eligible_artifact_count",
        )
        if k in dm
    }
    if not eligible_breakdown:
        eligible_breakdown = count_retrieval_eligible_artifacts_v1(session, tenant_id=tenant_id)

    eligible = int(
        dm.get("retrieval_eligible_artifact_count") or eligible_breakdown["eligible_artifact_count"]
    )
    index_stats = count_retrieval_indexed_in_published_epoch_v1(session, tenant_id=tenant_id)
    indexed = int(dm.get("retrieval_indexed_count") or index_stats["indexed_count"])
    replay_safe = int(index_stats["replay_safe_count"])
    published = index_stats.get("published_index_epoch")
    lag = compute_index_lag_epochs_v1(session, tenant_id=tenant_id)
    stale_epochs = list(lag.get("stale_epochs") or [])

    coverage_percent = float(
        dm.get("retrieval_density_percent") or _pct(indexed, eligible if eligible else 1)
    )
    replay_safe_percent = _pct(replay_safe, indexed if indexed else 1)
    pending_builds = int(lag.get("stale_epoch_count") or 0)
    if published is None and eligible > 0:
        pending_builds = max(pending_builds, 1)

    tcre_stage = project_tcre_completeness_v1(session, tenant_id=tenant_id)
    graph_stage = project_graph_completeness_v1(session, tenant_id=tenant_id)
    tcre_omissions = dict(tcre_stage.get("omission_classes") or {})
    upstream_tcre_pending = bool(tcre_stage.get("metrics", {}).get("reconstruction_never_run")) or int(
        tcre_omissions.get(TCRE_OMISSION_RECONSTRUCTION_NOT_YET_RUN_V1) or 0
    ) > 0
    upstream_work = upstream_work_exists_v1({"tcre": tcre_stage, "graph": graph_stage})

    operational_starvation = bool(starvation_eval.get("operational_starvation"))
    idle_class = str(starvation_eval.get("idle_class") or OPERATIONAL_IDLE_PROGRESSING_V1)
    index_stale = bool(dict(starvation_eval.get("index_freshness") or {}).get("index_stale"))

    never_indexed = eligible > 0 and indexed == 0
    tcre_gap = max(0, int(eligible_breakdown.get("tcre_indexable_count", 0)) - indexed)
    divergence_total = get_retrieval_replay_divergence_total_v1()

    omission_classes = build_retrieval_stage_omission_classes_v1(
        never_indexed=never_indexed,
        published=str(published) if published else None,
        indexed=indexed,
        stale_epochs=stale_epochs,
        tcre_gap=tcre_gap,
        divergence_total=divergence_total,
        operational_starvation=operational_starvation,
        starvation_eval=starvation_eval,
    )

    replay_posture = "stable"
    if divergence_total > 0:
        replay_posture = "unsafe"
    elif coverage_percent < RETRIEVAL_COVERAGE_THRESHOLD_PERCENT_V1 and eligible > 0:
        replay_posture = "partial"
    elif never_indexed:
        replay_posture = "unknown"

    fake_green = evaluate_retrieval_card_fake_green_v1(
        eligible=eligible,
        indexed=indexed,
        substrate_state="healthy",
        operational_starvation=operational_starvation,
        upstream_tcre_pending=upstream_tcre_pending,
    )

    substrate_state = derive_retrieval_completeness_substrate_state_v1(
        eligible=eligible,
        indexed=indexed,
        coverage_percent=coverage_percent,
        published_epoch=str(published) if published else None,
        replay_posture=replay_posture,
        pending_index_builds=pending_builds,
        upstream_tcre_pending=upstream_tcre_pending,
        upstream_work_present=upstream_work,
        operational_starvation=operational_starvation,
        index_stale=index_stale,
        fake_green_blocked=bool(fake_green["fake_green_blocked"]),
    )

    card_classification = classify_retrieval_card_v1(
        eligible=eligible,
        indexed=indexed,
        operational_starvation=operational_starvation,
        idle_class=idle_class,
        upstream_tcre_pending=upstream_tcre_pending,
        upstream_work_present=upstream_work,
    )

    if fake_green["fake_green_blocked"]:
        substrate_state = "degraded"

    stage_metrics: dict[str, Any] = {
        "eligible_artifact_count": eligible,
        "indexed_count": indexed,
        "retrieval_coverage_percent": coverage_percent,
        "replay_safe_query_percent": replay_safe_percent,
        "walk_record_count": eligible_breakdown.get("walk_record_count", 0),
        "retrieval_never_indexed": never_indexed,
        "published_index_epoch": published,
        "pending_index_build_count": pending_builds,
        "retrieval_replay_divergence_total": divergence_total,
        "retrieval_density_score": dm.get("retrieval_density_score"),
        "retrieval_maturity_class": density.get("retrieval_maturity_class"),
        "retrieval_row_acceptance_rate": dm.get("retrieval_row_acceptance_rate"),
        "retrieval_epoch_empty_rate": dm.get("retrieval_epoch_empty_rate"),
        "eligible_scope_growth_rate": dm.get("eligible_scope_growth_rate"),
        "latest_materialization_report_id": density.get("latest_materialization_report_id"),
        METRIC_RETRIEVAL_CARD_CLASSIFICATION_V1: card_classification,
        METRIC_RETRIEVAL_IDLE_CLASS_V1: idle_class,
        **eligible_breakdown,
    }
    omission_classes, stage_metrics, substrate_state = merge_retrieval_starvation_into_completeness_v1(
        omission_classes=omission_classes,
        metrics=stage_metrics,
        substrate_state=substrate_state,
        starvation_eval=starvation_eval,
    )

    propagation_manifest = build_retrieval_completeness_propagation_manifest_v1(
        substrate_state=substrate_state,
        card_classification=card_classification,
        idle_class=idle_class,
        operational_starvation=operational_starvation,
        fake_green_evaluation=fake_green,
        starvation_eval=starvation_eval,
        density_snapshot=density,
    )
    stage_metrics["retrieval_completeness_propagation"] = propagation_manifest

    degraded_count = indexed - replay_safe if indexed > replay_safe else 0
    unresolved = max(0, eligible - indexed)

    drift_warnings: list[str] = []
    if never_indexed:
        drift_warnings.append(
            "Eligible retrieval artifacts exist but no published index epoch — run index rebuild."
        )
    if stale_epochs:
        drift_warnings.append(f"stale_index_epochs={','.join(stale_epochs[:5])}")
    if fake_green.get("fake_green_blocked"):
        drift_warnings.append(
            "retrieval_fake_green_blocked:" + ",".join(fake_green.get("fake_green_reasons") or [])
        )
    if card_classification == RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1:
        drift_warnings.append(f"retrieval_card_classification={RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1}")

    assert_retrieval_never_idle_healthy_when_eligible_v1(
        eligible_artifact_count=eligible,
        indexed_count=indexed,
        substrate_state=substrate_state,
    )

    detail_route = str(
        density.get("detail_route") or f"/admin/tenants/{tenant_id}/cortex/retrieval"
    )

    return build_stage_envelope_v1(
        stage_id="retrieval",
        label="Retrieval",
        total_objects=eligible,
        processed_count=indexed,
        degraded_count=degraded_count,
        unresolved_count=unresolved,
        omitted_count=sum(omission_classes.values()),
        intentionally_excluded_count=pending_builds if pending_builds else 0,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=str(published) if published else None,
        drift_warnings=drift_warnings,
        omission_classes=omission_classes,
        detail_route=detail_route,
        metrics=stage_metrics,
    )


def build_retrieval_completeness_propagation_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_retrieval_propagation_runtime_schema_version": int(
            PHASE085_RETRIEVAL_PROPAGATION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_RETRIEVAL_PROPAGATION_SPEC_REF_V1,
        "primary_gate_id": GP085_RET_PROP01_GATE_ID_V1,
        "propagation_law_version": RETRIEVAL_PROPAGATION_LAW_VERSION_V1,
        "retrieval_stage_omission_classes": [
            RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1,
            RETRIEVAL_OMISSION_INDEX_EMPTY_V1,
            RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1,
            RETRIEVAL_STAGE_OMISSION_UPSTREAM_TCRE_GAP_V1,
            RETRIEVAL_STAGE_OMISSION_REPLAY_DIVERGENCE_V1,
            RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1,
        ],
        "card_classifications": [
            RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1,
            RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1,
            RETRIEVAL_CARD_CLASSIFICATION_PROGRESSING_V1,
        ],
        "downstream_stages": list(RETRIEVAL_PROPAGATION_DOWNSTREAM_STAGES_V1),
        "p0_gap_closed": "P0-085-04",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.retrieval_completeness_propagation"
        ),
        "propagation_entrypoint": "propagate_retrieval_completeness_stage_v1",
    }


def verify_gp085_ret_prop01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_retrieval_completeness_propagation_catalog_v1()
    if cat["primary_gate_id"] != GP085_RET_PROP01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    if (
        classify_retrieval_card_v1(
            eligible=10,
            indexed=0,
            operational_starvation=True,
            idle_class=OPERATIONAL_IDLE_STARVATION_V1,
            upstream_tcre_pending=False,
            upstream_work_present=False,
        )
        != RETRIEVAL_CARD_CLASSIFICATION_STARVED_V1
    ):
        errors.append("starved_classification")

    if (
        classify_retrieval_card_v1(
            eligible=0,
            indexed=0,
            operational_starvation=False,
            idle_class=OPERATIONAL_IDLE_HEALTHY_IDLE_V1,
            upstream_tcre_pending=False,
            upstream_work_present=False,
        )
        != RETRIEVAL_CARD_CLASSIFICATION_HEALTHY_IDLE_V1
    ):
        errors.append("healthy_idle_classification")

    state = derive_retrieval_completeness_substrate_state_v1(
        eligible=0,
        indexed=0,
        coverage_percent=0.0,
        published_epoch=None,
        replay_posture="unknown",
        pending_index_builds=0,
        upstream_tcre_pending=True,
        upstream_work_present=True,
        operational_starvation=False,
        index_stale=False,
        fake_green_blocked=False,
    )
    if state != "degraded":
        errors.append("p0_085_04_upstream_tcre_pending_must_degrade")

    fg = evaluate_retrieval_card_fake_green_v1(
        eligible=5,
        indexed=0,
        substrate_state="healthy",
        operational_starvation=False,
        upstream_tcre_pending=False,
    )
    if not fg["fake_green_blocked"]:
        errors.append("eligible_unindexed_fake_green")

    from vector.domains.cortex.retrieval import retrieval_completeness_projection as rcp

    if "propagate_retrieval_completeness_stage_v1" not in inspect.getsource(
        rcp.project_retrieval_completeness_v1
    ):
        errors.append("retrieval_completeness_projection_missing_propagation_delegate")

    from vector.domains.cortex.completeness import completeness_degradation_projection as cdp

    rules_src = inspect.getsource(cdp)
    if RETRIEVAL_STAGE_OMISSION_OPERATIONAL_STARVATION_V1 not in rules_src:
        errors.append("degradation_chain_missing_operational_starvation_rule")
    if RETRIEVAL_OMISSION_INDEX_EMPTY_V1 not in rules_src:
        errors.append("degradation_chain_missing_index_empty_rule")

    passed = not errors
    return {
        "id": GP085_RET_PROP01_GATE_ID_V1,
        "name": "cesp_retrieval_completeness_propagation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

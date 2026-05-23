"""Phase 08 P08-19 — substrate completeness + overview (synthesis stage).

Normative:
``DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md`` §Completeness,
``DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md`` §Overview integration.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1,
    RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SD_LLM_SCHEMA_V1,
    SD_PUBLISH_BLOCKED_V1,
    classify_synthesis_substrate_health_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SYNTHESIS_WORKLOAD_CLASS_METADATA_V1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

PHASE08_SYNTHESIS_COMPLETENESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_COMP01_GATE_ID_V1: Final[str] = "G-P08-COMP-01"

SYNTHESIS_COMPLETENESS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-runtime-architecture.md"
)

SYNTHESIS_SUBSTRATE_OVERVIEW_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-admin-control-plane-spec.md"
)

SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1: Final[float] = 90.0

SYNTHESIS_STAGE_OMISSION_NEVER_SYNTHESIZED_V1: Final[str] = "synthesis_never_materialized"
SYNTHESIS_STAGE_OMISSION_COVERAGE_GAP_V1: Final[str] = "synthesis_scope_coverage_gap"
SYNTHESIS_STAGE_OMISSION_PUBLICATION_LAG_V1: Final[str] = "synthesis_publication_lag"
SYNTHESIS_STAGE_OMISSION_UPSTREAM_RETRIEVAL_GAP_V1: Final[str] = "synthesis_upstream_retrieval_gap"

SYNTHESIS_SUBSTRATE_HEALTH_STATES_V1: Final[frozenset[str]] = frozenset(
    {"healthy", "degraded", "critical", "unresolved", "replay_conflicted"}
)

_CRITICAL_SD_CODES_V1: Final[frozenset[str]] = frozenset({SD_PUBLISH_BLOCKED_V1, SD_LLM_SCHEMA_V1})


class SynthesisCompletenessError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def _primary_artifact_kind_for_workload_v1(workload: str) -> str:
    meta = SYNTHESIS_WORKLOAD_CLASS_METADATA_V1.get(workload) or {}
    kind = str(meta.get("primary_artifact_kind") or workload)
    if kind in ("internal cert only", "per tenant default"):
        return workload
    return kind


def pipeline_default_workloads_v1(*, pack: Mapping[str, Any] | None = None) -> list[str]:
    body = dict(pack or load_synthesis_policy_pack_v1())
    raw = body.get("pipeline_default_workloads")
    if isinstance(raw, list) and raw:
        return [str(w) for w in raw]
    return ["pipeline_default"]


def count_synthesis_eligible_scopes_in_published_epoch_for_primary_island_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """R3: eligible scopes = in-scope island rows on published epoch × workloads."""
    from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
        count_retrieval_entries_in_scope_v1,
        resolve_primary_island_scope_id_v1,
    )

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    workloads = pipeline_default_workloads_v1(pack=pack)
    scope_id, scope_meta = resolve_primary_island_scope_id_v1(session, tenant_id=tenant_id)
    in_scope = (
        count_retrieval_entries_in_scope_v1(
            session,
            tenant_id=tenant_id,
            published_index_epoch=published or "",
            island_scope_id=scope_id,
        )
        if published and scope_id
        else 0
    )
    eligible = in_scope * len(workloads)
    return {
        "published_index_epoch": published,
        "primary_island_scope_id": scope_id,
        "island_meta": scope_meta,
        "retrieval_entries_in_scope": in_scope,
        "pipeline_default_workloads": workloads,
        "eligible_scopes": eligible,
        "scope_law": "published_epoch_primary_island_in_scope",
    }


def count_synthesis_eligible_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Eligible scopes = published index rows × default pipeline workloads."""
    try:
        from vector.settings import get_settings

        if bool(getattr(get_settings(), "cortex_synthesis_eligible_scopes_use_island_in_scope", True)):
            return count_synthesis_eligible_scopes_in_published_epoch_for_primary_island_v1(
                session, tenant_id=tenant_id, pack=pack
            )
    except Exception:  # noqa: BLE001
        pass
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    workloads = pipeline_default_workloads_v1(pack=pack)
    if published:
        index_count = int(
            session.scalar(
                select(func.count())
                .select_from(CortexRetrievalIndexEntry)
                .where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.index_epoch == published,
                )
            )
            or 0
        )
    else:
        index_count = 0
    eligible = index_count * len(workloads)
    return {
        "published_index_epoch": published,
        "index_row_count": index_count,
        "pipeline_default_workloads": workloads,
        "eligible_scopes": eligible,
    }


def _artifact_scope_keys_v1(
    artifact: CortexSynthesisArtifact,
    *,
    index_rows: Sequence[CortexRetrievalIndexEntry],
    workloads: Sequence[str],
) -> set[tuple[str, str]]:
    body = artifact.body_json or {}
    rqid = str(body.get("retrieval_query_replay_identity") or "").strip()
    lookup = str(body.get("retrieval_lookup_id") or "").strip()
    matched_rows: list[CortexRetrievalIndexEntry] = []
    if rqid:
        matched_rows = [row for row in index_rows if row.replay_identity == rqid]
    elif lookup:
        matched_rows = [row for row in index_rows if row.retrieval_lookup_id == lookup]
    if not matched_rows:
        return set()
    keys: set[tuple[str, str]] = set()
    for row in matched_rows:
        for workload in workloads:
            if artifact.artifact_kind == _primary_artifact_kind_for_workload_v1(workload):
                keys.add((row.retrieval_lookup_id, workload))
    return keys


def count_synthesis_synthesized_scopes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Artifacts matching index row replay identity + default workload artifact kind."""
    eligible_stats = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id, pack=pack)
    published = eligible_stats.get("published_index_epoch")
    workloads = list(eligible_stats.get("pipeline_default_workloads") or [])
    index_rows: list[CortexRetrievalIndexEntry] = []
    if published:
        index_rows = list(
            session.scalars(
                select(CortexRetrievalIndexEntry).where(
                    CortexRetrievalIndexEntry.tenant_id == tenant_id,
                    CortexRetrievalIndexEntry.index_epoch == published,
                )
            ).all()
        )
    artifacts = list(
        session.scalars(
            select(CortexSynthesisArtifact).where(CortexSynthesisArtifact.tenant_id == tenant_id)
        ).all()
    )
    scope_keys: set[tuple[str, str]] = set()
    for artifact in artifacts:
        scope_keys |= _artifact_scope_keys_v1(
            artifact,
            index_rows=index_rows,
            workloads=workloads,
        )
    published_artifacts = [a for a in artifacts if a.published]
    publication_epochs = [
        str(a.synthesis_publication_epoch)
        for a in published_artifacts
        if a.synthesis_publication_epoch
    ]
    synthesis_publication_epoch = max(publication_epochs) if publication_epochs else None
    return {
        **eligible_stats,
        "synthesized_scopes": len(scope_keys),
        "artifact_total": len(artifacts),
        "artifact_published_count": len(published_artifacts),
        "synthesis_publication_epoch": synthesis_publication_epoch,
        "synthesized_scope_keys_sample": sorted(scope_keys)[:8],
    }


def compute_synthesis_lag_epochs_v1(
    *,
    published_index_epoch: str | None,
    synthesis_publication_epoch: str | None,
) -> dict[str, Any]:
    """Lag when synthesis publication epoch trails published retrieval index epoch."""
    if not published_index_epoch:
        return {
            "lag_epochs": 0,
            "lag_vs_retrieval": 0,
            "publication_behind_index": False,
            "published_index_epoch": None,
            "synthesis_publication_epoch": synthesis_publication_epoch,
        }
    if not synthesis_publication_epoch:
        return {
            "lag_epochs": 1,
            "lag_vs_retrieval": 1,
            "publication_behind_index": True,
            "published_index_epoch": published_index_epoch,
            "synthesis_publication_epoch": None,
        }
    behind = synthesis_publication_epoch != published_index_epoch
    lag = 1 if behind else 0
    return {
        "lag_epochs": lag,
        "lag_vs_retrieval": lag,
        "publication_behind_index": behind,
        "published_index_epoch": published_index_epoch,
        "synthesis_publication_epoch": synthesis_publication_epoch,
    }


def count_synthesis_sd_critical_v1(
    artifacts: Sequence[CortexSynthesisArtifact],
) -> int:
    total = 0
    for artifact in artifacts:
        body = artifact.body_json or {}
        rollup = body.get("synthesis_degradation_rollup")
        if not isinstance(rollup, Mapping):
            rollup = body.get("upstream_rollup")
        hist: Mapping[str, Any] = {}
        if isinstance(rollup, Mapping):
            raw_hist = rollup.get("omission_histogram")
            if isinstance(raw_hist, Mapping):
                hist = raw_hist
        for sd in _CRITICAL_SD_CODES_V1:
            total += int(hist.get(sd) or 0)
    return total


def aggregate_synthesis_substrate_health_state_v1(
    artifacts: Sequence[CortexSynthesisArtifact],
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
    publication_behind_index: bool,
) -> str:
    """Tenant-level health for overview (worst artifact health + coverage law)."""
    if eligible_scopes > 0 and synthesized_scopes == 0:
        return "unresolved"
    health_rank = {
        "healthy": 0,
        "degraded": 1,
        "unresolved": 2,
        "replay_conflicted": 3,
        "critical": 4,
    }
    worst = "healthy"
    for artifact in artifacts:
        body = artifact.body_json or {}
        rollup = body.get("synthesis_degradation_rollup")
        health = None
        if isinstance(rollup, Mapping):
            health = rollup.get("substrate_health_state")
        if not health:
            rows = body.get("synthesis_omission_rows")
            health = classify_synthesis_substrate_health_v1(
                omissions=rows if isinstance(rows, list) else [],
                synthesis_legality_class=str(artifact.synthesis_legality_class),
                is_pipeline_default_workload=True,
            )
        health = str(health or "degraded")
        if health_rank.get(health, 1) > health_rank.get(worst, 0):
            worst = health
    if publication_behind_index and worst == "healthy":
        worst = "degraded"
    if eligible_scopes > 0:
        coverage = 100.0 * synthesized_scopes / eligible_scopes
        if coverage < SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1 and worst == "healthy":
            worst = "degraded"
    return worst


def map_synthesis_health_to_stage_substrate_state_v1(health_state: str) -> str:
    if health_state == "critical":
        return "critical"
    if health_state in ("degraded", "unresolved", "replay_conflicted"):
        return "degraded"
    return "healthy"


def derive_synthesis_stage_substrate_state_v1(
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
    coverage_percent: float,
    substrate_health_state: str,
    publication_behind_index: bool,
) -> str:
    if substrate_health_state == "critical":
        return "critical"
    if eligible_scopes > 0 and synthesized_scopes == 0:
        return "degraded"
    if publication_behind_index:
        return "degraded"
    if coverage_percent < SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1 and eligible_scopes > 0:
        return "degraded"
    return map_synthesis_health_to_stage_substrate_state_v1(substrate_health_state)


def _project_synthesis_completeness_without_classification_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """8th pipeline stage envelope for substrate completeness ledger (base, pre **G-P085-SYN-02**)."""
    from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct

    scope_stats = count_synthesis_synthesized_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope_stats["eligible_scopes"])
    synthesized = int(scope_stats["synthesized_scopes"])
    published_index = scope_stats.get("published_index_epoch")
    synthesis_epoch = scope_stats.get("synthesis_publication_epoch")
    lag = compute_synthesis_lag_epochs_v1(
        published_index_epoch=str(published_index) if published_index else None,
        synthesis_publication_epoch=str(synthesis_epoch) if synthesis_epoch else None,
    )

    artifacts = list(
        session.scalars(
            select(CortexSynthesisArtifact).where(CortexSynthesisArtifact.tenant_id == tenant_id)
        ).all()
    )
    sd_critical = count_synthesis_sd_critical_v1(artifacts)
    health_state = aggregate_synthesis_substrate_health_state_v1(
        artifacts,
        eligible_scopes=eligible,
        synthesized_scopes=synthesized,
        publication_behind_index=bool(lag.get("publication_behind_index")),
    )
    coverage_percent = pct(synthesized, eligible if eligible else max(synthesized, 1))
    substrate_state = derive_synthesis_stage_substrate_state_v1(
        eligible_scopes=eligible,
        synthesized_scopes=synthesized,
        coverage_percent=coverage_percent,
        substrate_health_state=health_state,
        publication_behind_index=bool(lag.get("publication_behind_index")),
    )

    omission_classes: dict[str, int] = {}
    if eligible > 0 and synthesized == 0:
        omission_classes[SYNTHESIS_STAGE_OMISSION_NEVER_SYNTHESIZED_V1] = 1
    gap = max(0, eligible - synthesized)
    if gap > 0 and synthesized > 0:
        omission_classes[SYNTHESIS_STAGE_OMISSION_COVERAGE_GAP_V1] = gap
    if lag.get("publication_behind_index"):
        omission_classes[SYNTHESIS_STAGE_OMISSION_PUBLICATION_LAG_V1] = int(lag.get("lag_epochs") or 1)
    if published_index is None and eligible > 0:
        omission_classes[SYNTHESIS_STAGE_OMISSION_UPSTREAM_RETRIEVAL_GAP_V1] = 1

    replay_posture = "stable"
    if health_state == "replay_conflicted":
        replay_posture = "unsafe"
    elif health_state in ("degraded", "unresolved") or gap > 0:
        replay_posture = "partial"
    elif eligible > 0 and synthesized == 0:
        replay_posture = "unknown"

    drift_warnings: list[str] = []
    if eligible > 0 and synthesized == 0:
        drift_warnings.append(
            "Eligible synthesis scopes exist but no matching artifacts — run synthesis pipeline."
        )
    if lag.get("publication_behind_index"):
        drift_warnings.append(
            f"synthesis_publication_epoch={synthesis_epoch} trails index_epoch={published_index}"
        )

    assert_synthesis_never_idle_healthy_when_eligible_v1(
        eligible_scopes=eligible,
        synthesized_scopes=synthesized,
        substrate_state=substrate_state,
    )

    degraded_count = max(0, synthesized - sum(1 for a in artifacts if a.published))
    unresolved = max(0, eligible - synthesized)

    return build_stage_envelope_v1(
        stage_id="synthesis",
        label="Synthesis",
        total_objects=eligible if eligible else synthesized,
        processed_count=synthesized,
        degraded_count=degraded_count,
        unresolved_count=unresolved,
        omitted_count=sum(omission_classes.values()),
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=str(synthesis_epoch) if synthesis_epoch else None,
        drift_warnings=drift_warnings,
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/synthesis",
        metrics={
            "eligible_scopes": eligible,
            "synthesized_scopes": synthesized,
            "synthesis_coverage_percent": coverage_percent,
            "substrate_health_state": health_state,
            "publication_epoch": synthesis_epoch,
            "published_index_epoch": published_index,
            "lag_epochs": lag.get("lag_epochs"),
            "lag_vs_retrieval": lag.get("lag_vs_retrieval"),
            "sd_critical_count": sd_critical,
            "artifact_total": scope_stats.get("artifact_total"),
            "artifact_published_count": scope_stats.get("artifact_published_count"),
            "pipeline_default_workloads": scope_stats.get("pipeline_default_workloads"),
            "index_row_count": scope_stats.get("index_row_count"),
        },
    )


def project_synthesis_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Project synthesis stage (**G-P085-SYN-02** + **G-P085-SYN-03** throughput maturity)."""
    from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
        project_synthesis_completeness_with_throughput_maturity_v1,
    )

    return project_synthesis_completeness_with_throughput_maturity_v1(session, tenant_id=tenant_id)


def build_synthesis_coverage_catalog_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin ``GET .../coverage`` — synthesis completeness metrics."""
    stage = project_synthesis_completeness_v1(session, tenant_id=tenant_id)
    metrics = dict(stage.get("metrics") or {})
    lag = compute_synthesis_lag_epochs_v1(
        published_index_epoch=(
            str(metrics["published_index_epoch"]) if metrics.get("published_index_epoch") else None
        ),
        synthesis_publication_epoch=(
            str(metrics["publication_epoch"]) if metrics.get("publication_epoch") else None
        ),
    )
    return {
        "tenant_id": str(tenant_id),
        "synthesis_completeness_runtime_schema_version": (
            PHASE08_SYNTHESIS_COMPLETENESS_RUNTIME_SCHEMA_VERSION
        ),
        "stage_id": "synthesis",
        "substrate_state": stage.get("substrate_state"),
        "replay_posture": stage.get("replay_posture"),
        "eligible_scopes": int(metrics.get("eligible_scopes", 0)),
        "synthesized_scopes": int(metrics.get("synthesized_scopes", 0)),
        "coverage_percent": float(metrics.get("synthesis_coverage_percent", 0.0)),
        "status": str(metrics.get("substrate_health_state", "healthy")),
        "publication_epoch": metrics.get("publication_epoch"),
        "lag_vs_retrieval": lag.get("lag_vs_retrieval"),
        "sd_critical_count": int(metrics.get("sd_critical_count", 0)),
        "omission_classes": dict(stage.get("omission_classes") or {}),
        "synthesis_lag_epochs": lag,
        "pipeline_default_workloads": metrics.get("pipeline_default_workloads"),
    }


def build_synthesis_overview_catalog_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Admin overview card — synthesis stage strip + drill-down routes."""
    coverage = build_synthesis_coverage_catalog_v1(session, tenant_id=tenant_id)
    stage = project_synthesis_completeness_v1(session, tenant_id=tenant_id)
    return {
        **coverage,
        "surface_kind": "runtime_backed",
        "stage_envelope": stage,
        "doctrine_anchors": [
            SYNTHESIS_COMPLETENESS_SPEC_REF_V1,
            SYNTHESIS_SUBSTRATE_OVERVIEW_SPEC_REF_V1,
        ],
        "drill_down": {
            "coverage_strip": {
                "eligible": coverage.get("eligible_scopes"),
                "synthesized": coverage.get("synthesized_scopes"),
                "coverage_percent": coverage.get("coverage_percent"),
            },
            "routes": {
                "control_plane": f"/admin/tenants/{tenant_id}/cortex/synthesis",
                "artifact_explorer": f"/admin/tenants/{tenant_id}/cortex/synthesis/artifact-explorer",
                "degradation_topology": (
                    f"/admin/tenants/{tenant_id}/cortex/synthesis/degradation-topology"
                ),
            },
        },
    }


def assert_synthesis_never_idle_healthy_when_eligible_v1(
    *,
    eligible_scopes: int,
    synthesized_scopes: int,
    substrate_state: str,
) -> None:
    if eligible_scopes > 0 and synthesized_scopes == 0 and substrate_state == "healthy":
        raise SynthesisCompletenessError(
            "synthesis_idle_healthy_with_eligible_scopes",
            detail={
                "eligible_scopes": eligible_scopes,
                "synthesized_scopes": synthesized_scopes,
            },
        )


def _comp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_COMP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_completeness_runtime_schema_version": (
                PHASE08_SYNTHESIS_COMPLETENESS_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_comp01_never_idle_healthy_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        assert_synthesis_never_idle_healthy_when_eligible_v1(
            eligible_scopes=4,
            synthesized_scopes=0,
            substrate_state="healthy",
        )
    except SynthesisCompletenessError:
        pass
    else:
        errors.append("expected_idle_healthy_rejection")
    try:
        assert_synthesis_never_idle_healthy_when_eligible_v1(
            eligible_scopes=0,
            synthesized_scopes=0,
            substrate_state="healthy",
        )
    except SynthesisCompletenessError as exc:
        errors.append(f"zero_eligible_should_pass:{exc}")
    state = derive_synthesis_stage_substrate_state_v1(
        eligible_scopes=10,
        synthesized_scopes=0,
        coverage_percent=0.0,
        substrate_health_state="unresolved",
        publication_behind_index=True,
    )
    if state != "degraded":
        errors.append(f"never_synthesized_state:{state}")
    return _comp_meta("gp08_comp01_never_idle_healthy", errors)


def verify_gp08_comp01_coverage_threshold_static() -> dict[str, Any]:
    errors: list[str] = []
    if SYNTHESIS_COVERAGE_THRESHOLD_PERCENT_V1 <= 0:
        errors.append("invalid_threshold")
    low_cov = derive_synthesis_stage_substrate_state_v1(
        eligible_scopes=100,
        synthesized_scopes=40,
        coverage_percent=40.0,
        substrate_health_state="healthy",
        publication_behind_index=False,
    )
    if low_cov != "degraded":
        errors.append("low_coverage_should_degrade")
    if RETRIEVAL_STAGE_OMISSION_INDEX_NEVER_BUILT_V1 != "retrieval_index_never_built":
        errors.append("retrieval_omission_import_drift")
    if RETRIEVAL_STAGE_OMISSION_INDEX_STALE_V1 != "retrieval_index_stale":
        errors.append("retrieval_stale_import_drift")
    return _comp_meta("gp08_comp01_coverage_threshold", errors)

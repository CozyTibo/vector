"""Phase 07 P07-07 — query legality matrix + degradation class floors.

Normative: ``DOCS/cortex/retrieval/retrieval-legality-matrix.md``,
``phase-07-query-contract-doctrine.md`` §5.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.anti_goals import verify_gp07_anti01_retrieval_package_static
from vector.domains.cortex.retrieval.query_contract import addressing_has_resolvable_ref_v1
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RETRIEVAL_LEGALITY_CLASSES_V1,
    classify_retrieval_legality_v1,
    retrieval_policy_digest_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_index_entry import CortexRetrievalIndexEntry

PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1: Final[str] = "retrieval_legality_matrix_catalog_v1"

RETRIEVAL_LEGALITY_MATRIX_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/retrieval-legality-matrix.md"
)
RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-legality-matrix.md"
)
RETRIEVAL_QUERY_CONTRACT_DOCTRINE_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-query-contract-doctrine.md"
)
RETRIEVAL_VERIFICATION_WAIVERS_YAML_FUTURE_PATH_V1: Final[str] = (
    "DOCS/cortex/retrieval/waivers/retrieval_verification_waivers.yaml"
)

RETRIEVAL_LEGALITY_MATRIX_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tenant_id}/cortex/retrieval/legality",
    "/admin/tenants/{tenant_id}/cortex/retrieval/runtime-legality-matrix",
)

GP07_LEG01_GATE_ID_V1: Final[str] = "G-P07-LEG-01"

RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1: Final[dict[str, int]] = {
    "retrieval_replay_safe": 0,
    "retrieval_degraded": 1,
    "retrieval_partial": 2,
    "retrieval_unverifiable": 3,
    "retrieval_forbidden": 4,
}

RETRIEVAL_QUERY_LEGALITY_AUTHORITATIVE_FOR_PHASE08_V1: Final[dict[str, bool]] = {
    "retrieval_replay_safe": True,
    "retrieval_degraded": True,
    "retrieval_partial": True,
    "retrieval_unverifiable": False,
    "retrieval_forbidden": False,
}

_TCRE_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_continuity",
        "chronology_window",
        "causal_chain",
        "causal_edge",
        "degradation_survey",
        "dependency_propagation",
        "replay_divergence",
        "replay_equivalence",
        "materialization_as_of",
    }
)

_WALK_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {"traversal_lineage", "replay_equivalence"}
)

_INDEX_EPOCH_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {"causal_chain", "replay_equivalence", "lineage_explorer"}
)

R_LEG_PREDICATE_FAILURE_CLASS_V1: Final[dict[str, str]] = {
    "R-LEG-01": "retrieval_forbidden",
    "R-LEG-02": "retrieval_partial",
    "R-LEG-03": "retrieval_unverifiable",
    "R-LEG-04": "retrieval_unverifiable",
    "R-LEG-05": "retrieval_degraded",
    "R-LEG-06": "retrieval_unverifiable",
    "R-LEG-07": "retrieval_degraded",
}


@dataclass(frozen=True, slots=True)
class RetrievalLegalityPredicateV1:
    predicate_id: str
    description: str
    failure_class: str


_PRED_TUPLE = tuple[RetrievalLegalityPredicateV1, ...]

RETRIEVAL_LEGALITY_PREDICATES_V1: Final[_PRED_TUPLE] = tuple(
    sorted(
        (
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-01",
                description="Anti-goals scan pass (G-P07-ANTI-01).",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-01"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-02",
                description="Addressing resolves ≥1 target OR audit intent.",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-02"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-03",
                description="tcre_policy_bundle_digest pinned when TCRE-scoped workload.",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-03"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-04",
                description="octs_engine_build_ref available when walk-scoped workload.",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-04"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-05",
                description="Index epoch published when index-scoped workload.",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-05"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-06",
                description="No upstream replay_conflicted_identity in scope.",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-06"],
            ),
            RetrievalLegalityPredicateV1(
                predicate_id="R-LEG-07",
                description="G-P07-REPLAY-01 holds on verification slice (degraded floor).",
                failure_class=R_LEG_PREDICATE_FAILURE_CLASS_V1["R-LEG-07"],
            ),
        ),
        key=lambda p: p.predicate_id,
    )
)


@dataclass(frozen=True, slots=True)
class RetrievalForbiddenDeploymentV1:
    forbidden_id: str
    description: str


_FORB_TUPLE = tuple[RetrievalForbiddenDeploymentV1, ...]

RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1: Final[_FORB_TUPLE] = (
    RetrievalForbiddenDeploymentV1(
        forbidden_id="R-FORB-01",
        description="Authoritative queries without retrieval_policy_digest pin.",
    ),
    RetrievalForbiddenDeploymentV1(
        forbidden_id="R-FORB-02",
        description="Index read before first successful publish job.",
    ),
    RetrievalForbiddenDeploymentV1(
        forbidden_id="R-FORB-03",
        description="Exploration partition feeding Phase 08 default path.",
    ),
    RetrievalForbiddenDeploymentV1(
        forbidden_id="R-FORB-04",
        description="Embedding / vector index table present.",
    ),
    RetrievalForbiddenDeploymentV1(
        forbidden_id="R-FORB-05",
        description="NL query box in admin.",
    ),
)


def list_retrieval_legality_predicate_ids_v1() -> tuple[str, ...]:
    return tuple(p.predicate_id for p in RETRIEVAL_LEGALITY_PREDICATES_V1)


def _legality_ordinal(legality_class: str) -> int:
    return RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1.get(legality_class, 99)


def max_retrieval_legality_class_v1(*classes: str) -> str:
    if not classes:
        return "retrieval_replay_safe"
    return max(classes, key=_legality_ordinal)


def run_retrieval_r_leg_precheck_v1(envelope: Mapping[str, Any]) -> dict[str, bool]:
    """R-LEG-01..07 pre-check snapshot at VALIDATE."""
    wl = str(envelope["workload_class"])
    it = str(envelope["intent"])
    addressing = envelope["addressing"]
    assert isinstance(addressing, dict)
    pins = envelope.get("replay_pins")
    replay_pins = pins if isinstance(pins, dict) else {}
    index_epoch = (
        replay_pins.get("index_epoch")
        or envelope.get("index_epoch")
        or (addressing.get("index_epoch") if isinstance(addressing, dict) else None)
    )
    anti01 = verify_gp07_anti01_retrieval_package_static()
    return {
        "R-LEG-01": bool(anti01.get("passed")),
        "R-LEG-02": addressing_has_resolvable_ref_v1(addressing) or it == "audit",
        "R-LEG-03": (wl not in _TCRE_SCOPED_WORKLOADS_V1)
        or bool(replay_pins.get("tcre_policy_bundle_digest")),
        "R-LEG-04": (wl not in _WALK_SCOPED_WORKLOADS_V1)
        or bool(replay_pins.get("octs_engine_build_ref")),
        "R-LEG-05": (wl not in _INDEX_EPOCH_WORKLOADS_V1)
        or bool(str(index_epoch or "").strip()),
        "R-LEG-06": not bool(
            (envelope.get("upstream_triggers") or {}).get("replay_conflicted_identity")
        ),
        "R-LEG-07": True,
    }


def legality_classes_from_r_leg_violations_v1(r_leg: Mapping[str, bool]) -> list[str]:
    out: list[str] = []
    for pid, ok in r_leg.items():
        if not ok:
            fc = R_LEG_PREDICATE_FAILURE_CLASS_V1.get(pid)
            if fc:
                out.append(fc)
    return out


def aggregate_query_legality_class_v1(
    *,
    r_leg: Mapping[str, bool],
    upstream_row_legality: str,
    intent: str,
    hit_evidence_legalities: Iterable[str] | None = None,
) -> str:
    """Aggregate query legality from R-LEG snapshot, upstream row, and evidence floors."""
    candidates = [upstream_row_legality, *legality_classes_from_r_leg_violations_v1(r_leg)]
    for ev in hit_evidence_legalities or ():
        if ev == "evidence_unverifiable" and intent != "audit":
            candidates.append("retrieval_unverifiable")
    return max_retrieval_legality_class_v1(*candidates)


def build_retrieval_legality_posture_v1(
    *,
    legality_class: str,
    intent: str,
    execution_partition: str,
    r_leg: Mapping[str, bool],
) -> dict[str, Any]:
    violations = [pid for pid, ok in r_leg.items() if not ok]
    authoritative = RETRIEVAL_QUERY_LEGALITY_AUTHORITATIVE_FOR_PHASE08_V1.get(
        legality_class, False
    )
    audit_only_partial = legality_class == "retrieval_partial" and intent != "audit"
    return {
        "retrieval_legality_class": legality_class,
        "ordinal": _legality_ordinal(legality_class),
        "authoritative_for_phase08": authoritative and not audit_only_partial,
        "execution_partition": execution_partition,
        "intent": intent,
        "r_leg_violations": violations,
        "replay_pins_required": legality_class == "retrieval_unverifiable",
    }


def build_retrieval_legality_matrix_catalog_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    tid = "" if tenant_id is None else str(tenant_id)
    return {
        "tenant_id": tid,
        "retrieval_legality_matrix_runtime_schema_version": (
            PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
        ),
        "retrieval_legality_matrix_contract": RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1,
        "retrieval_policy_digest": retrieval_policy_digest_v1(),
        "legality_classes": [
            {
                "class": cls,
                "ordinal": RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1[cls],
                "authoritative_for_phase08": RETRIEVAL_QUERY_LEGALITY_AUTHORITATIVE_FOR_PHASE08_V1[
                    cls
                ],
            }
            for cls in sorted(
                RETRIEVAL_LEGALITY_CLASSES_V1,
                key=lambda c: RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1[c],
            )
        ],
        "predicates": [asdict(p) for p in RETRIEVAL_LEGALITY_PREDICATES_V1],
        "forbidden_deployments": [asdict(f) for f in RETRIEVAL_FORBIDDEN_DEPLOYMENTS_V1],
        "r_leg_failure_class_map": dict(R_LEG_PREDICATE_FAILURE_CLASS_V1),
        "doctrine_anchors": [
            RETRIEVAL_LEGALITY_MATRIX_SPEC_REF_V1,
            RETRIEVAL_RUNTIME_LEGALITY_MATRIX_SPEC_REF_V1,
            RETRIEVAL_QUERY_CONTRACT_DOCTRINE_REF_V1,
        ],
        "waiver_yaml_future_path": RETRIEVAL_VERIFICATION_WAIVERS_YAML_FUTURE_PATH_V1,
    }


def build_retrieval_queries_by_legality_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Tenant legality histogram from indexed entries (proxy until query metrics ledger)."""
    rows = session.execute(
        select(
            CortexRetrievalIndexEntry.retrieval_legality_class,
            func.count(),
        )
        .where(CortexRetrievalIndexEntry.tenant_id == tenant_id)
        .group_by(CortexRetrievalIndexEntry.retrieval_legality_class)
    ).all()
    hist = {cls: 0 for cls in RETRIEVAL_LEGALITY_CLASSES_V1}
    for legality_class, count in rows:
        key = str(legality_class)
        if key in hist:
            hist[key] = int(count)
    return hist


def classify_upstream_index_legality_v1(
    *,
    replay_identity_match: bool,
    chronology_legality_class: str,
    causal_legality_class: str,
    degradation_posture: str,
    continuity_posture: str,
    traversal_degraded: bool,
) -> str:
    """Upstream row legality before R-LEG aggregate (wraps projection)."""
    return classify_retrieval_legality_v1(
        replay_identity_match=replay_identity_match,
        chronology_legality_class=chronology_legality_class,
        causal_legality_class=causal_legality_class,
        degradation_posture=degradation_posture,
        continuity_posture=continuity_posture,
        traversal_degraded=traversal_degraded,
    )


def _matrix_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_LEG01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_leg01_retrieval_legality_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    want = (
        "R-LEG-01",
        "R-LEG-02",
        "R-LEG-03",
        "R-LEG-04",
        "R-LEG-05",
        "R-LEG-06",
        "R-LEG-07",
    )
    ids = list_retrieval_legality_predicate_ids_v1()
    if ids != want:
        errors.append(f"predicate_id_tuple_mismatch:{ids!r}")
    if len(RETRIEVAL_LEGALITY_CLASSES_V1) != 5:
        errors.append("legality_class_count")
    ordinals = sorted(RETRIEVAL_QUERY_LEGALITY_CLASS_ORDINALS_V1.values())
    if ordinals != [0, 1, 2, 3, 4]:
        errors.append("ordinal_sequence")
    doc = build_retrieval_legality_matrix_catalog_v1()
    if len(doc.get("predicates", [])) != 7:
        errors.append("predicates_len")
    if len(doc.get("forbidden_deployments", [])) != 5:
        errors.append("forbidden_len")
    agg = aggregate_query_legality_class_v1(
        r_leg={"R-LEG-03": False, "R-LEG-01": True, "R-LEG-02": True},
        upstream_row_legality="retrieval_replay_safe",
        intent="inspect",
    )
    if agg != "retrieval_unverifiable":
        errors.append(f"aggregate_r_leg03:{agg}")
    return _matrix_meta("gp07_leg01_retrieval_legality_matrix", errors)

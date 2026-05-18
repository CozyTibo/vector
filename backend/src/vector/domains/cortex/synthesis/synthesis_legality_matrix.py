"""Phase 08 P08-07 — synthesis legality matrix + S-LEG aggregation.

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-law-system.md`` §Legality.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase_boundaries import (
    SD_REPLAY_TWIN_V1,
    SD_UPSTREAM_RD_V1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE08_SYNTHESIS_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_LEGALITY_MATRIX_CONTRACT_V1: Final[str] = "synthesis_legality_matrix_catalog_v1"

SYNTHESIS_LEGALITY_MATRIX_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-synthesis-law-system.md"
)

GP08_LEG01_GATE_ID_V1: Final[str] = "G-P08-LEG-01"

SYNTHESIS_LEGALITY_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "synthesis_replay_safe",
        "synthesis_degraded",
        "synthesis_partial",
        "synthesis_unverifiable",
        "synthesis_forbidden",
    },
)

SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1: Final[dict[str, int]] = {
    "synthesis_replay_safe": 0,
    "synthesis_degraded": 1,
    "synthesis_partial": 2,
    "synthesis_unverifiable": 3,
    "synthesis_forbidden": 4,
}

SYNTHESIS_LEGALITY_AUTHORITATIVE_USABLE_V1: Final[dict[str, bool]] = {
    "synthesis_replay_safe": True,
    "synthesis_degraded": True,
    "synthesis_partial": True,
    "synthesis_unverifiable": False,
    "synthesis_forbidden": False,
}

_RETRIEVAL_TO_SYNTHESIS_UPSTREAM_FLOOR_V1: Final[dict[str, str]] = {
    "retrieval_replay_safe": "synthesis_replay_safe",
    "retrieval_degraded": "synthesis_degraded",
    "retrieval_partial": "synthesis_partial",
    "retrieval_unverifiable": "synthesis_unverifiable",
    "retrieval_forbidden": "synthesis_forbidden",
}

SD_CITE_GAP_V1: Final[str] = "SD-CITE-GAP"
SD_LLM_SCHEMA_V1: Final[str] = "SD-LLM-SCHEMA"

DEFAULT_MAX_CITE_GAPS_BEFORE_PARTIAL_V1: Final[int] = 0

_UPSTREAM_RD_CRITICAL_MASS_V1: Final[int] = 1

S_LEG_PREDICATE_FAILURE_CLASS_V1: Final[dict[str, str]] = {
    "S-LEG-01": "synthesis_unverifiable",
    "S-LEG-02": "synthesis_degraded",
    "S-LEG-03": "synthesis_partial",
    "S-LEG-04": "synthesis_forbidden",
    "S-LEG-05": "synthesis_forbidden",
    "S-LEG-06": "synthesis_partial",
    "S-LEG-07": "synthesis_degraded",
}


@dataclass(frozen=True, slots=True)
class SynthesisLegalityPredicateV1:
    predicate_id: str
    description: str
    failure_class: str


SYNTHESIS_LEGALITY_PREDICATES_V1: Final[tuple[SynthesisLegalityPredicateV1, ...]] = tuple(
    sorted(
        (
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-01",
                description="Any hit evidence_legality unverifiable (non-audit intent).",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-01"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-02",
                description="SD-REPLAY-TWIN present in omission rows.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-02"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-03",
                description="SD-CITE-GAP count exceeds policy cap.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-03"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-04",
                description="SD-LLM-SCHEMA after retry.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-04"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-05",
                description="Upstream retrieval_forbidden.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-05"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-06",
                description="Exploration partition caps legality at synthesis_partial.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-06"],
            ),
            SynthesisLegalityPredicateV1(
                predicate_id="S-LEG-07",
                description="SD-UPSTREAM-RD critical mass in omission rows.",
                failure_class=S_LEG_PREDICATE_FAILURE_CLASS_V1["S-LEG-07"],
            ),
        ),
        key=lambda p: p.predicate_id,
    ),
)


class SynthesisLegalityError(ValueError):
    """Raised when synthesis legality fail-closed rules block the job."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int = 403,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def _legality_ordinal(legality_class: str) -> int:
    return SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1.get(legality_class, 99)


def max_synthesis_legality_class_v1(*classes: str) -> str:
    if not classes:
        return "synthesis_replay_safe"
    return max(classes, key=_legality_ordinal)


def map_retrieval_legality_to_synthesis_floor_v1(retrieval_legality_class: str) -> str:
    """Map Phase **07** ``retrieval_legality_class`` to synthesis upstream floor."""
    norm = retrieval_legality_class.strip().lower()
    return _RETRIEVAL_TO_SYNTHESIS_UPSTREAM_FLOOR_V1.get(norm, "synthesis_unverifiable")


def upstream_retrieval_legality_from_ingress_v1(ingress: Mapping[str, Any]) -> str:
    copy = ingress.get("retrieval_legality_copy")
    if isinstance(copy, Mapping):
        raw = copy.get("retrieval_legality_class")
        if raw:
            return str(raw)
    top = ingress.get("retrieval_legality_class")
    if top:
        return str(top)
    return "retrieval_partial"


def _sd_code_from_row(row: Mapping[str, Any]) -> str:
    for key in ("sd_code", "synthesis_omission_class", "code"):
        raw = row.get(key)
        if raw:
            return str(raw).strip().upper()
    return ""


def _count_sd_code(rows: Sequence[Mapping[str, Any]], code: str) -> int:
    target = code.upper()
    return sum(1 for row in rows if _sd_code_from_row(row) == target)


def _count_upstream_rd_rows(rows: Sequence[Mapping[str, Any]]) -> int:
    return sum(
        1
        for row in rows
        if _sd_code_from_row(row) == SD_UPSTREAM_RD_V1
        or str(row.get("upstream_rd", "")).startswith("RD-")
    )


def evaluate_synthesis_s_leg_predicates_v1(
    *,
    upstream_retrieval_legality: str,
    synthesis_intent: str,
    execution_partition: str,
    synthesis_omission_rows: Sequence[Mapping[str, Any]] | None = None,
    hit_evidence_legalities: Sequence[str] | None = None,
    llm_schema_failed: bool = False,
    max_cite_gaps_before_partial: int = DEFAULT_MAX_CITE_GAPS_BEFORE_PARTIAL_V1,
) -> dict[str, bool]:
    """Evaluate **S-LEG-01..07**; ``True`` means predicate satisfied (no failure)."""
    sd_rows = [r for r in (synthesis_omission_rows or ()) if isinstance(r, Mapping)]
    hits = list(hit_evidence_legalities or ())
    cite_gaps = _count_sd_code(sd_rows, SD_CITE_GAP_V1)
    upstream_rd_mass = _count_upstream_rd_rows(sd_rows)
    return {
        "S-LEG-01": not any(
            ev == "evidence_unverifiable" for ev in hits if synthesis_intent != "audit"
        ),
        "S-LEG-02": _count_sd_code(sd_rows, SD_REPLAY_TWIN_V1) == 0,
        "S-LEG-03": cite_gaps <= max_cite_gaps_before_partial,
        "S-LEG-04": not llm_schema_failed and _count_sd_code(sd_rows, SD_LLM_SCHEMA_V1) == 0,
        "S-LEG-05": upstream_retrieval_legality.strip().lower() != "retrieval_forbidden",
        "S-LEG-06": True,
        "S-LEG-07": upstream_rd_mass < _UPSTREAM_RD_CRITICAL_MASS_V1,
    }


def legality_classes_from_s_leg_violations_v1(s_leg: Mapping[str, bool]) -> list[str]:
    out: list[str] = []
    for pid, ok in s_leg.items():
        if not ok:
            fc = S_LEG_PREDICATE_FAILURE_CLASS_V1.get(pid)
            if fc:
                out.append(fc)
    return out


def cap_exploration_partition_legality_v1(legality_class: str) -> str:
    """**S-LEG-06** — exploration jobs cap at ``synthesis_partial``."""
    if _legality_ordinal(legality_class) > _legality_ordinal("synthesis_partial"):
        return "synthesis_partial"
    return legality_class


def aggregate_synthesis_legality_class_v1(
    *,
    upstream_retrieval_legality: str,
    synthesis_intent: str,
    execution_partition: str,
    synthesis_omission_rows: Sequence[Mapping[str, Any]] | None = None,
    hit_evidence_legalities: Sequence[str] | None = None,
    llm_schema_failed: bool = False,
    max_cite_gaps_before_partial: int = DEFAULT_MAX_CITE_GAPS_BEFORE_PARTIAL_V1,
) -> str:
    """``max(upstream_retrieval_floor, sd_code_floor, llm_schema_floor, replay_twin_floor)``."""
    s_leg = evaluate_synthesis_s_leg_predicates_v1(
        upstream_retrieval_legality=upstream_retrieval_legality,
        synthesis_intent=synthesis_intent,
        execution_partition=execution_partition,
        synthesis_omission_rows=synthesis_omission_rows,
        hit_evidence_legalities=hit_evidence_legalities,
        llm_schema_failed=llm_schema_failed,
        max_cite_gaps_before_partial=max_cite_gaps_before_partial,
    )
    candidates = [
        map_retrieval_legality_to_synthesis_floor_v1(upstream_retrieval_legality),
        *legality_classes_from_s_leg_violations_v1(s_leg),
    ]
    legality = max_synthesis_legality_class_v1(*candidates)
    if execution_partition.strip().lower() == "exploration":
        legality = cap_exploration_partition_legality_v1(legality)
    return legality


def build_synthesis_legality_posture_v1(
    *,
    legality_class: str,
    synthesis_intent: str,
    execution_partition: str,
    s_leg: Mapping[str, bool],
    upstream_retrieval_legality: str,
) -> dict[str, Any]:
    violations = [pid for pid, ok in s_leg.items() if not ok]
    authoritative_usable = SYNTHESIS_LEGALITY_AUTHORITATIVE_USABLE_V1.get(legality_class, False)
    audit_only_partial = legality_class == "synthesis_partial" and synthesis_intent != "audit"
    return {
        "synthesis_legality_class": legality_class,
        "ordinal": _legality_ordinal(legality_class),
        "authoritative_usable": authoritative_usable and not audit_only_partial,
        "execution_partition": execution_partition,
        "synthesis_intent": synthesis_intent,
        "upstream_retrieval_legality_class": upstream_retrieval_legality,
        "s_leg_violations": violations,
        "s_leg_snapshot": dict(s_leg),
    }


def classify_synthesis_legality_for_job_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_ingress: Mapping[str, Any],
    hit_evidence_legalities: Sequence[str] | None = None,
    llm_schema_failed: bool = False,
) -> tuple[str, dict[str, Any]]:
    """CLASSIFY phase — aggregate legality + posture envelope."""
    upstream = upstream_retrieval_legality_from_ingress_v1(retrieval_ingress)
    sd_rows = retrieval_ingress.get("synthesis_omission_rows")
    if not isinstance(sd_rows, list):
        sd_rows = []
    intent = str(envelope["synthesis_intent"])
    partition = str(envelope["execution_partition"])
    s_leg = evaluate_synthesis_s_leg_predicates_v1(
        upstream_retrieval_legality=upstream,
        synthesis_intent=intent,
        execution_partition=partition,
        synthesis_omission_rows=sd_rows,
        hit_evidence_legalities=hit_evidence_legalities,
        llm_schema_failed=llm_schema_failed,
    )
    legality = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality=upstream,
        synthesis_intent=intent,
        execution_partition=partition,
        synthesis_omission_rows=sd_rows,
        hit_evidence_legalities=hit_evidence_legalities,
        llm_schema_failed=llm_schema_failed,
    )
    posture = build_synthesis_legality_posture_v1(
        legality_class=legality,
        synthesis_intent=intent,
        execution_partition=partition,
        s_leg=s_leg,
        upstream_retrieval_legality=upstream,
    )
    return legality, posture


def assert_synthesis_job_lawful_v1(
    *,
    legality_class: str,
    synthesis_intent: str,
    execution_partition: str = "authoritative",
) -> None:
    """Fail-closed — mirrors Phase **07** ``assert_retrieval_query_lawful_v1``."""
    if legality_class not in SYNTHESIS_LEGALITY_CLASSES_V1:
        raise SynthesisLegalityError(
            "unknown_synthesis_legality_class",
            detail={"synthesis_legality_class": legality_class},
        )
    if legality_class == "synthesis_forbidden":
        raise SynthesisLegalityError(
            "synthesis_forbidden",
            detail={
                "synthesis_legality_class": legality_class,
                "synthesis_intent": synthesis_intent,
            },
        )
    if legality_class == "synthesis_unverifiable" and synthesis_intent != "audit":
        raise SynthesisLegalityError(
            "synthesis_fail_closed",
            detail={
                "synthesis_legality_class": legality_class,
                "synthesis_intent": synthesis_intent,
            },
        )
    if (
        execution_partition.strip().lower() == "authoritative"
        and legality_class == "synthesis_partial"
        and synthesis_intent != "audit"
    ):
        raise SynthesisLegalityError(
            "synthesis_partial_requires_audit_intent",
            detail={
                "synthesis_legality_class": legality_class,
                "synthesis_intent": synthesis_intent,
            },
        )


def build_synthesis_legality_matrix_catalog_v1(
    *,
    tenant_id: uuid.UUID | str | None = None,
) -> dict[str, Any]:
    tid = "" if tenant_id is None else str(tenant_id)
    return {
        "surface_kind": "doctrine_catalog",
        "tenant_id": tid,
        "phase08_synthesis_legality_matrix_runtime_schema_version": (
            PHASE08_SYNTHESIS_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
        ),
        "synthesis_legality_matrix_contract": SYNTHESIS_LEGALITY_MATRIX_CONTRACT_V1,
        "synthesis_policy_pack_digest": synthesis_policy_pack_digest_v1(),
        "gp08_legality_gate_id": GP08_LEG01_GATE_ID_V1,
        "legality_classes": [
            {
                "class": cls,
                "ordinal": SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1[cls],
                "authoritative_usable": SYNTHESIS_LEGALITY_AUTHORITATIVE_USABLE_V1[cls],
            }
            for cls in sorted(
                SYNTHESIS_LEGALITY_CLASSES_V1,
                key=lambda c: SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1[c],
            )
        ],
        "predicates": [asdict(p) for p in SYNTHESIS_LEGALITY_PREDICATES_V1],
        "s_leg_failure_class_map": dict(S_LEG_PREDICATE_FAILURE_CLASS_V1),
        "retrieval_to_synthesis_upstream_floor": dict(_RETRIEVAL_TO_SYNTHESIS_UPSTREAM_FLOOR_V1),
        "spec_ref": SYNTHESIS_LEGALITY_MATRIX_SPEC_REF_V1,
    }


def build_synthesis_jobs_by_legality_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Tenant synthesis job legality histogram from completed job receipts."""
    hist = {cls: 0 for cls in SYNTHESIS_LEGALITY_CLASSES_V1}
    rows = session.execute(
        select(CortexSynthesisJob.synthesis_legality_class, func.count())
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.status == "completed",
            CortexSynthesisJob.synthesis_legality_class.isnot(None),
        )
        .group_by(CortexSynthesisJob.synthesis_legality_class),
    ).all()
    for legality_class, count in rows:
        key = str(legality_class)
        if key in hist:
            hist[key] = int(count)
    return hist


def verify_gp08_leg01_synthesis_legality_matrix_static() -> dict[str, Any]:
    """``G-P08-LEG-01`` — closed classes, predicates, and aggregation law."""
    errors: list[str] = []
    want_preds = (
        "S-LEG-01",
        "S-LEG-02",
        "S-LEG-03",
        "S-LEG-04",
        "S-LEG-05",
        "S-LEG-06",
        "S-LEG-07",
    )
    pred_ids = tuple(p.predicate_id for p in SYNTHESIS_LEGALITY_PREDICATES_V1)
    if pred_ids != want_preds:
        errors.append(f"predicate_id_tuple_mismatch:{pred_ids!r}")
    if len(SYNTHESIS_LEGALITY_CLASSES_V1) != 5:
        errors.append("legality_class_count")
    ordinals = sorted(SYNTHESIS_LEGALITY_CLASS_ORDINALS_V1.values())
    if ordinals != [0, 1, 2, 3, 4]:
        errors.append("ordinal_sequence")
    agg = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality="retrieval_replay_safe",
        synthesis_intent="inspect",
        execution_partition="authoritative",
        synthesis_omission_rows=[{"sd_code": SD_REPLAY_TWIN_V1}],
    )
    if agg != "synthesis_degraded":
        errors.append(f"s_leg02_aggregate:{agg}")
    forbidden_agg = aggregate_synthesis_legality_class_v1(
        upstream_retrieval_legality="retrieval_forbidden",
        synthesis_intent="inspect",
        execution_partition="authoritative",
    )
    if forbidden_agg != "synthesis_forbidden":
        errors.append(f"s_leg05_aggregate:{forbidden_agg}")
    try:
        assert_synthesis_job_lawful_v1(
            legality_class="synthesis_unverifiable",
            synthesis_intent="inspect",
        )
    except SynthesisLegalityError as exc:
        if exc.code != "synthesis_fail_closed":
            errors.append(f"unexpected_fail_closed_code:{exc.code}")
    else:
        errors.append("expected_synthesis_fail_closed")
    cat = build_synthesis_legality_matrix_catalog_v1()
    if len(cat.get("predicates", [])) != 7:
        errors.append("catalog_predicates_len")
    return {
        "id": GP08_LEG01_GATE_ID_V1,
        "name": "synthesis_legality_matrix",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "phase08_synthesis_legality_matrix_runtime_schema_version": (
                PHASE08_SYNTHESIS_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }

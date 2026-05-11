"""Phase 03 Step 8 — confidence propagation as structured metadata (non-ranking).

Normative: `DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md` §Confidence taxonomy +
§Confidence propagation (runtime).
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_field_lineage import CortexCanonicalFieldLineage
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)

CONFIDENCE_PROPAGATION_SCHEMA_VERSION: Final[int] = 1

CONFIDENCE_NON_RANKING_SEMANTICS: Final[str] = (
    "Confidence values are opaque structured labels for downstream indexes; they MUST NOT be "
    "interpreted as ranking weights or semantic importance (Phase 03 anti-goals)."
)


class Phase03ConfidenceClass(StrEnum):
    """Allowed automatic confidence labels in Phase 03 (doctrine table + propagation rules)."""

    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    TABLE_LOOKUP = "TABLE_LOOKUP"
    PARSE_FORMAT = "PARSE_FORMAT"
    UNRESOLVED = "UNRESOLVED"
    CONTESTED = "CONTESTED"


FORBIDDEN_AUTO_CONFIDENCE_CLASSES: Final[frozenset[str]] = frozenset({"PROBABILISTIC_MODEL", "OPERATOR_POLICY"})


def validate_confidence_class(value: str) -> str:
    if value in FORBIDDEN_AUTO_CONFIDENCE_CLASSES:
        raise ValueError(f"confidence_class_forbidden_for_auto_pipeline:{value}")
    try:
        Phase03ConfidenceClass(value)
    except ValueError as exc:
        raise ValueError(f"confidence_class_unknown:{value}") from exc
    return value


def stub_lineage_confidence(*, field_path: str, rule_id: str, evidence_grade: str) -> tuple[str, dict[str, Any]]:
    """Deterministic stub mapping: lineage field → confidence class + small metadata (no scores)."""
    meta: dict[str, Any] = {
        "evidence_grade_bridge": evidence_grade,
        "stub_rule_id": rule_id,
    }
    if rule_id.endswith(".payload.channel") or rule_id.endswith(".payload.title"):
        return Phase03ConfidenceClass.PARSE_FORMAT.value, {**meta, "parse_surface": "json_field"}
    if rule_id.endswith(".column_copy"):
        return Phase03ConfidenceClass.DETERMINISTIC_RULE.value, {**meta, "derivation": "column_copy"}
    if "logical_key" in field_path:
        return Phase03ConfidenceClass.DETERMINISTIC_RULE.value, {**meta, "derivation": "logical_key_tuple"}
    return Phase03ConfidenceClass.DETERMINISTIC_RULE.value, meta


def build_confidence_taxonomy_public_section() -> dict[str, Any]:
    """Frozen operator-facing taxonomy + semantics (merged into ontology JSON)."""
    return {
        "confidence_propagation_surface_version": 1,
        "confidence_propagation_schema_version": CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
        "confidence_non_ranking_semantics": CONFIDENCE_NON_RANKING_SEMANTICS,
        "confidence_allowed_classes": [
            {
                "id": Phase03ConfidenceClass.DETERMINISTIC_RULE.value,
                "meaning": "Output follows a named mapping rule exactly",
                "allowed_phase03": True,
            },
            {
                "id": Phase03ConfidenceClass.TABLE_LOOKUP.value,
                "meaning": "Output from versioned lookup table",
                "allowed_phase03": True,
            },
            {
                "id": Phase03ConfidenceClass.PARSE_FORMAT.value,
                "meaning": "Deterministic parse produced the value (include source path refs on lineage)",
                "allowed_phase03": True,
            },
            {
                "id": Phase03ConfidenceClass.UNRESOLVED.value,
                "meaning": "Explicitly not resolved",
                "allowed_phase03": True,
            },
            {
                "id": Phase03ConfidenceClass.CONTESTED.value,
                "meaning": "Multiple evidence-backed alternatives kept",
                "allowed_phase03": True,
            },
        ],
        "confidence_forbidden_classes": [
            {"id": "PROBABILISTIC_MODEL", "reason": "Model score drives choice — not allowed in Phase 03 default"},
            {
                "id": "OPERATOR_POLICY",
                "reason": "Human override only via explicit gated operator actions outside automatic pipeline",
            },
        ],
        "confidence_summary_admin_route": "GET /admin/tenants/{tenant_id}/cortex/canonical/confidence/summary",
        "confidence_propagation_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-anti-goals-doctrine.md",
        ],
    }


def confidence_class_rollup_for_tenant(db: Session, *, tenant_id: uuid.UUID) -> tuple[int, dict[str, int]]:
    """Count field-lineage rows by confidence_class for one tenant (operator visibility)."""
    stmt = (
        select(
            CortexCanonicalFieldLineage.confidence_class,
            func.count().label("n"),
        )
        .join(
            CortexCanonicalTransformMaterialization,
            CortexCanonicalTransformMaterialization.id == CortexCanonicalFieldLineage.materialization_id,
        )
        .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        .group_by(CortexCanonicalFieldLineage.confidence_class)
    )
    rows = db.execute(stmt).all()
    by_class = {str(r[0]): int(r[1]) for r in rows}
    total = sum(by_class.values())
    return total, dict(sorted(by_class.items()))


def materialization_confidence_rollup(field_rows: list[CortexCanonicalFieldLineage]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for r in field_rows:
        cc = r.confidence_class
        counts[cc] = counts.get(cc, 0) + 1
    return {
        "by_confidence_class": dict(sorted(counts.items())),
        "semantics": "structured_metadata_non_ranking",
    }

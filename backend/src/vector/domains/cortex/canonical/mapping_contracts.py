"""Phase 03 Step 4 — deterministic mapping contracts (evidence grades, allowed/forbidden transforms).

Normative: `DOCS/cortex/03-canonical/phase-03-deterministic-canonicalization-doctrine.md`.
Specifies authoring shapes for mapping bundles (runtime engine is Step 6).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final

# Bump when evidence-grade enums, forbidden lists, or mapping-table shape fields change.
MAPPING_CONTRACT_SCHEMA_VERSION: Final[int] = 1


class EvidenceGrade(StrEnum):
    """Required posture for emitted canonical fields (`phase-03-deterministic-canonicalization-doctrine.md` §Evidence)."""

    E0 = "E0"
    E1 = "E1"


EVIDENCE_GRADE_ENTRIES: Final[tuple[dict[str, str], ...]] = (
    {
        "id": EvidenceGrade.E0.value,
        "label": "E0 — provider-explicit",
        "definition": (
            "Present as structured provider fields backing the canonical statement—no inference beyond typed copy "
            "from raw JSON."
        ),
    },
    {
        "id": EvidenceGrade.E1.value,
        "label": "E1 — deterministic-parse",
        "definition": (
            "Derived only by deterministic grammar, regex, or table rules from provider text fields; raw excerpts "
            "remain referenced where ambiguity doctrine requires—never silent fact when rules do not apply."
        ),
    },
)

DETERMINISM_CRITERIA: Final[tuple[str, ...]] = (
    "Identity keys are stable functions of declared inputs (including declared normalization tables) for a fixed "
    "Phase 02 raw substrate snapshot and configured mapping version identifiers.",
    "Ordering precedence follows temporal timeline doctrine—no random or clock-based reordering inside algorithms.",
    "No canonical field depends on randomness; processing timestamps may exist as metadata about processing but "
    "must not silently alter canonical identities.",
    "Retry and replay do not create duplicate authoritative identities for the same logical tuple per replay "
    "versioning doctrine.",
)

STRUCTURAL_EXTRACTION_DEFINITION: Final[str] = (
    "Structural extraction: copying, renaming, typing into allowed enums, partitioning, joining by explicit keys, "
    "parsing formats specified by mapping tables, and emitting explicit unknown or partial markers."
)

SEMANTIC_INFERENCE_FORBIDDEN_DEFINITION: Final[str] = (
    "Semantic inference (forbidden in Phase 03): assigning managerial meaning, interpreting natural language "
    "beyond deterministic parsing rules, or choosing among interpretive hypotheses without preserving alternatives "
    "as explicit ambiguity records."
)

ALLOWED_DETERMINISTIC_OPERATIONS: Final[tuple[dict[str, str], ...]] = (
    {
        "id": "normalize_identifier_url",
        "description": (
            "Normalize identifiers and URLs per stable rules; case folding only where explicitly allowed—preserve "
            "canonical raw pointers."
        ),
    },
    {
        "id": "map_resource_type_table",
        "description": (
            "Map provider resource types to canonical object kinds using versioned mapping tables owned by a bundle."
        ),
    },
    {
        "id": "extract_keyed_references",
        "description": (
            "Extract explicitly keyed references (IDs, URLs, mention handles) where rules are pure functions of "
            "input strings and mapping tables."
        ),
    },
    {
        "id": "normalize_timestamp_explicit_rule",
        "description": (
            "Normalize timestamps when the rule is explicit; if raw lacks timezone and a default is declared, emit "
            "ambiguity or confidence markers per ambiguity doctrine—never silent assumptions."
        ),
    },
    {
        "id": "emit_evidenced_graph_edges",
        "description": (
            "Emit canonical graph edges that mirror explicitly evidenced relationships in raw payloads (e.g. "
            "parent/child IDs present in provider JSON)."
        ),
    },
)

FORBIDDEN_OPERATIONS: Final[tuple[str, ...]] = (
    "Inferring priority, urgency, blocker, or ownership semantics not directly evidenced as structured fields.",
    "LLM classification of text unless explicitly exempted by a future closure gate (default: forbidden).",
    "Clustering or embedding similarity to merge entities (Phase 04).",
    "Best-guess entity linking across providers (Phase 04).",
    "Hidden thresholds that change mapping outcomes without surfacing as a mapping version or bundle bump.",
)

FIELD_EMISSION_POSTURE_RULES: Final[tuple[str, ...]] = (
    "Every emitted canonical scalar or structured field must declare evidence grade E0 or E1, or be omitted.",
    "Fields that cannot meet E0/E1 must be absent from authoritative canonical facts or represented under "
    "ambiguity or contestation records—not as silent truth.",
)

MAPPING_VERSIONING_RULES: Final[tuple[str, ...]] = (
    "Any change to extraction logic that can change outputs must bump canonical_mapping_version (or equivalent "
    "bundle identifier) and/or per-connector mapping micro-version.",
    "Replay equivalence tests attribute divergence to explicit version bumps—no undeclared drift.",
)

# Frozen column schema for bundle-owned mapping table rows (authoring contract; registry in Step 5).
MAPPING_TABLE_ROW_SHAPE: Final[tuple[dict[str, Any], ...]] = (
    {
        "column": "connector",
        "value_type": "string",
        "required": True,
        "description": "Connector discriminator (e.g. slack, github, linear) for routing raw rows.",
    },
    {
        "column": "provider_resource_type",
        "value_type": "string",
        "required": True,
        "description": "Raw envelope resource_type string as persisted in Phase 02.",
    },
    {
        "column": "canonical_object_kind",
        "value_type": "string",
        "required": True,
        "description": "Target structural kind id (`CanonicalObjectKind` value).",
    },
    {
        "column": "mapping_bundle_id",
        "value_type": "string",
        "required": True,
        "description": "Owning bundle identifier for remap and compatibility governance.",
    },
    {
        "column": "transform_rules_ref",
        "value_type": "string",
        "required": True,
        "description": "Stable pointer to deterministic transform rule set (tables, grammars) within the bundle.",
    },
    {
        "column": "field_projection_ref",
        "value_type": "string",
        "required": True,
        "description": "Stable pointer to field-level projections with per-field evidence grade (E0/E1) bindings.",
    },
    {
        "column": "logical_key_binding_ref",
        "value_type": "string",
        "required": True,
        "description": "Stable pointer to logical key tuple binding aligned with `logical_keys.py` for the kind.",
    },
)


def validate_mapping_contracts_internal_consistency() -> None:
    assert EVIDENCE_GRADE_ENTRIES
    assert ALLOWED_DETERMINISTIC_OPERATIONS
    assert FORBIDDEN_OPERATIONS
    assert MAPPING_TABLE_ROW_SHAPE
    ids = {x["id"] for x in EVIDENCE_GRADE_ENTRIES}
    assert EvidenceGrade.E0.value in ids and EvidenceGrade.E1.value in ids


def build_mapping_contracts_public_section() -> dict[str, Any]:
    validate_mapping_contracts_internal_consistency()
    return {
        "mapping_contract_schema_version": MAPPING_CONTRACT_SCHEMA_VERSION,
        "evidence_grades": list(EVIDENCE_GRADE_ENTRIES),
        "determinism_criteria": list(DETERMINISM_CRITERIA),
        "structural_extraction_definition": STRUCTURAL_EXTRACTION_DEFINITION,
        "semantic_inference_forbidden_definition": SEMANTIC_INFERENCE_FORBIDDEN_DEFINITION,
        "allowed_deterministic_operations": list(ALLOWED_DETERMINISTIC_OPERATIONS),
        "forbidden_operations": list(FORBIDDEN_OPERATIONS),
        "field_emission_posture_rules": list(FIELD_EMISSION_POSTURE_RULES),
        "mapping_versioning_rules": list(MAPPING_VERSIONING_RULES),
        "mapping_table_row_shape": list(MAPPING_TABLE_ROW_SHAPE),
        "mapping_contract_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-deterministic-canonicalization-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-anti-goals-doctrine.md",
        ],
    }

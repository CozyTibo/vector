"""Phase 03 Step 3 — oracle manifest inventory (pre-runtime regression vectors).

Normative: `DOCS/cortex/03-canonical/phase-03-oracle-vectors-doctrine.md`.
Vectors are structural receipts for CI/promotion — mapping execution lands in Step 6.
"""

from __future__ import annotations

import uuid
from typing import Any, Final

from vector.domains.cortex.canonical.logical_keys import logical_key_fields_for_kind
from vector.domains.cortex.canonical.ontology import CanonicalObjectKind

ORACLE_MANIFEST_SCHEMA_VERSION: Final[int] = 1

# Aligns with seeded row in `cortex_mapping_bundles` (Phase 03 Step 5 registry).
PHASE03_STEP03_MAPPING_BUNDLE_ID: Final[str] = "bundle.phase03.step03.logical_keys.v1"
PHASE03_STEP03_MAPPING_MANIFEST_HASH: Final[str] = (
    "sha256:0000000000000000000000000000000000000000000000000000000000000000"
)

# Deterministic engine identifier for oracle receipts (replace with git SHA schema in CI when wired).
ORACLE_ENGINE_BUILD_REF: Final[str] = "phase03-step03-oracle-manifest-v1"


def _lk_example(kind: CanonicalObjectKind, example_values: tuple[str, ...]) -> dict[str, Any]:
    fields = logical_key_fields_for_kind(kind)
    if len(example_values) != len(fields):
        raise AssertionError(f"{kind}: tuple length {len(example_values)} != fields {len(fields)}")
    return {
        "canonical_object_kind": kind.value,
        "tuple_field_names": list(fields),
        "example_normalized_tuple": list(example_values),
    }


# Frozen oracle vectors — expand with real Phase 02 fixture refs when corpus exists.
_ORACLE_VECTORS: tuple[dict[str, Any], ...] = (
    {
        "fixture_id": "p03_oracle_logical_key_person_github",
        "coverage_tags": ["logical_key_stability", "per_canonical_class"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_logical_key_person_github@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.PERSON,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "github",
                    "actor_node_id_12345",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_temporal_message_order",
        "coverage_tags": ["temporal_ordering", "late_arrival"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_temporal_message_order@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.MESSAGE,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "slack",
                    "C01234567",
                    "1234567890.123456",
                ),
            ),
        ],
        "expected_ordering": [
            {
                "ordering_context": "conversation_timeline",
                "sort_key_fields": ["message_provider_id"],
                "notes": "Deterministic tie-break per temporal doctrine once mapping bundle fixes normalization.",
            },
        ],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_github_pull_request_v1",
        "coverage_tags": ["github", "pull_request", "logical_key_stability"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_github_pull_request@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.PULL_REQUEST,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "github",
                    "88424",
                    "42",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_notion_page_v1",
        "coverage_tags": ["notion", "page", "logical_key_stability", "hierarchy_containment"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_notion_page@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.DOCUMENT,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "notion",
                    "7f61cf4a-81cb-4a4e-9805-2df4f1b34567",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_notion_database_row_v1",
        "coverage_tags": ["notion", "database_row", "logical_key_stability", "relation_preservation"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_notion_database_row@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.DATABASE_ROW,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "notion",
                    "db_roadmap_q3",
                    "row_launch_plan_001",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_notion_database_v1",
        "coverage_tags": ["notion", "database", "logical_key_stability", "schema_lineage"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_notion_database@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.PAGE,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "notion",
                    "db_roadmap_q3",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_notion_block_v1",
        "coverage_tags": ["notion", "block", "hierarchy_reconstruction", "logical_key_stability"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_notion_block@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.PAGE,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "notion",
                    "blk_plan_001",
                ),
            ),
        ],
        "expected_ordering": [
            {
                "ordering_context": "notion_block_siblings",
                "sort_key_fields": ["sibling_cursor_hint", "source_revision_key", "raw_record_id"],
                "notes": "Replay-safe sibling ordering uses cursor context plus global temporal tie-breaks.",
            },
        ],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_ambiguity_competing_rules",
        "coverage_tags": ["ambiguity_persistence", "competing_rules"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_ambiguity_competing_rules@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [],
        "expected_ordering": [],
        "expected_ambiguity_records": [
            {
                "ambiguity_class": "competing_mapping_rules",
                "scope": "issue.status_transition",
                "record_handle": "amb:001",
            },
        ],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_provenance_multi_source",
        "coverage_tags": ["provenance_continuity", "multi_source"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_provenance_multi_source@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.ISSUE,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "linear",
                    "linear_issue_uuid",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [
            {
                "edge_kind": "raw_to_canonical",
                "from_raw_record_ref": "raw:linear.issue:abc",
                "to_logical_key_kind": CanonicalObjectKind.ISSUE.value,
            },
        ],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_rebuild_equivalence_slice",
        "coverage_tags": ["rebuild_equivalence"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_rebuild_equivalence_slice@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [
            _lk_example(
                CanonicalObjectKind.REPOSITORY,
                (
                    "tenant_uuid",
                    PHASE03_STEP03_MAPPING_BUNDLE_ID,
                    "github",
                    "repo_node_id_999",
                ),
            ),
        ],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C0"],
    },
    {
        "fixture_id": "p03_oracle_drift_c3_raw_trust",
        "coverage_tags": ["drift_class_detector", "C3"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_drift_c3_raw_trust@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C3"],
        "injected_fault": "raw_trust_mismatch",
    },
    {
        "fixture_id": "p03_oracle_drift_c4_nondeterminism",
        "coverage_tags": ["drift_class_detector", "C4"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_drift_c4_nondeterminism@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C4"],
        "injected_fault": "unordered_iteration_simulation",
    },
    {
        "fixture_id": "p03_oracle_drift_c5_compatibility_gap",
        "coverage_tags": ["drift_class_detector", "C5"],
        "raw_snapshot_ref": "fixture://phase03/oracle/p03_oracle_drift_c5_compatibility_gap@v1",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "expected_logical_keys": [],
        "expected_ordering": [],
        "expected_ambiguity_records": [],
        "expected_provenance_edges": [],
        "allowed_divergence_classes": ["C5"],
        "injected_fault": "undeclared_bundle_jump",
    },
)

_REQUIRED_VECTOR_KEYS: frozenset[str] = frozenset(
    {
        "fixture_id",
        "coverage_tags",
        "raw_snapshot_ref",
        "mapping_bundle_id",
        "mapping_manifest_hash",
        "engine_build_ref",
        "expected_logical_keys",
        "expected_ordering",
        "expected_ambiguity_records",
        "expected_provenance_edges",
        "allowed_divergence_classes",
    },
)


def validate_oracle_manifest_internal_consistency() -> None:
    for vec in _ORACLE_VECTORS:
        keys = set(vec.keys())
        missing = _REQUIRED_VECTOR_KEYS - keys
        assert not missing, missing
        for lk in vec["expected_logical_keys"]:
            k = CanonicalObjectKind(lk["canonical_object_kind"])
            assert lk["tuple_field_names"] == list(logical_key_fields_for_kind(k))


def oracle_vectors() -> tuple[dict[str, Any], ...]:
    return _ORACLE_VECTORS


def build_oracle_manifest_public_document(*, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
    validate_oracle_manifest_internal_consistency()
    out: dict[str, Any] = {
        "oracle_manifest_schema_version": ORACLE_MANIFEST_SCHEMA_VERSION,
        "phase": "03",
        "implementation_step": 3,
        "completed_implementation_steps": [1, 2, 3],
        "name": "phase03_step03_oracle_manifest",
        "mapping_bundle_id": PHASE03_STEP03_MAPPING_BUNDLE_ID,
        "mapping_manifest_hash": PHASE03_STEP03_MAPPING_MANIFEST_HASH,
        "engine_build_ref": ORACLE_ENGINE_BUILD_REF,
        "oracle_manifest_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-oracle-vectors-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-logical-key-doctrine.md",
        ],
        "coverage_categories_documented": [
            "per_canonical_class logical-key stability",
            "temporal ordering",
            "ambiguity persistence",
            "provenance continuity",
            "rebuild equivalence",
            "drift-class detectors (C3/C4/C5)",
        ],
        "vectors": [dict(v) for v in _ORACLE_VECTORS],
    }
    if tenant_id is not None:
        out["tenant_id"] = str(tenant_id)
    return out

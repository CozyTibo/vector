"""Cortex Phase 03 — canonicalization (deterministic structural projection from raw memory)."""

from vector.domains.cortex.canonical.ambiguity_metadata import (
    AMBIGUITY_RUNTIME_SURFACE_VERSION,
    build_ambiguity_runtime_pointer_section,
)
from vector.domains.cortex.canonical.ambiguity_runtime import (
    AMBIGUITY_ENGINE_BUILD_REF,
    AMBIGUITY_RUNTIME_SCHEMA_VERSION,
    AmbiguityClass,
    AmbiguityError,
    AmbiguityStatus,
    ambiguity_record_public_dict,
    build_ambiguity_aggregates,
    get_ambiguity_record,
    list_ambiguity_records,
    open_ambiguity_record,
    transition_ambiguity_record,
)
from vector.domains.cortex.canonical.confidence_runtime import (
    CONFIDENCE_NON_RANKING_SEMANTICS,
    CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
    FORBIDDEN_AUTO_CONFIDENCE_CLASSES,
    Phase03ConfidenceClass,
    build_confidence_taxonomy_public_section,
    confidence_class_rollup_for_tenant,
    materialization_confidence_rollup,
    stub_lineage_confidence,
    validate_confidence_class,
)
from vector.domains.cortex.canonical.identity_metadata import (
    IDENTITY_RUNTIME_SURFACE_VERSION,
    build_identity_runtime_pointer_section,
)
from vector.domains.cortex.canonical.identity_runtime import (
    DEFAULT_PHASE04_BOUNDARY,
    IDENTITY_ENGINE_BUILD_REF,
    IDENTITY_RUNTIME_SCHEMA_VERSION,
    PHASE03_CANONICAL_ENTITY_NAMESPACE,
    canonical_entity_id_for_materialization,
    deterministic_canonical_entity_id,
    get_identity_anchor,
    identity_anchor_public_dict,
    list_identity_anchors,
    provider_identity_from_logical_key,
    upsert_identity_anchor_for_materialization,
)
from vector.domains.cortex.canonical.logical_keys import (
    LOGICAL_KEY_PROFILE_VERSION,
    build_logical_keys_public_section,
    logical_key_fields_for_kind,
    validate_logical_key_profile_internal_consistency,
)
from vector.domains.cortex.canonical.mapping_bundle_registry import (
    REGISTRY_RUNTIME_SCHEMA_VERSION,
    build_tenant_mapping_registry_public_document,
)
from vector.domains.cortex.canonical.mapping_contracts import (
    MAPPING_CONTRACT_SCHEMA_VERSION,
    EvidenceGrade,
    build_mapping_contracts_public_section,
    validate_mapping_contracts_internal_consistency,
)
from vector.domains.cortex.canonical.mapping_registry_metadata import (
    MAPPING_REGISTRY_SURFACE_VERSION,
    build_mapping_registry_pointer_section,
)
from vector.domains.cortex.canonical.ontology import (
    ONTOLOGY_SCHEMA_VERSION,
    build_phase03_step01_ontology_public_document,
)
from vector.domains.cortex.canonical.oracle_manifest import (
    ORACLE_MANIFEST_SCHEMA_VERSION,
    build_oracle_manifest_public_document,
    oracle_vectors,
    validate_oracle_manifest_internal_consistency,
)
from vector.domains.cortex.canonical.provenance_metadata import (
    PROVENANCE_RUNTIME_SURFACE_VERSION,
    build_provenance_runtime_pointer_section,
)
from vector.domains.cortex.canonical.provenance_runtime import (
    PROVENANCE_RUNTIME_SCHEMA_VERSION,
    get_provenance_for_materialization,
    list_provenance_for_raw_record,
    provenance_public_dict,
    upsert_provenance_for_materialization,
)
from vector.domains.cortex.canonical.replay_metadata import (
    REPLAY_RUNTIME_SURFACE_VERSION,
    build_replay_runtime_pointer_section,
)
from vector.domains.cortex.canonical.replay_runtime import (
    REPLAY_RUNTIME_SCHEMA_VERSION,
    ReplayJobError,
)
from vector.domains.cortex.canonical.taxonomy import (
    CanonicalStructuralRole,
    build_taxonomy_public_section,
    structural_examples_for_kind,
    structural_role_for_kind,
    validate_taxonomy_internal_consistency,
)
from vector.domains.cortex.canonical.canonical_query_runtime import (
    CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION,
    CanonicalQueryError,
    execute_canonical_query,
)
from vector.domains.cortex.canonical.query_metadata import (
    CANONICAL_QUERY_SURFACE_VERSION,
    build_canonical_query_pointer_section,
)
from vector.domains.cortex.canonical.temporal_metadata import (
    TEMPORAL_RUNTIME_SURFACE_VERSION,
    build_temporal_runtime_pointer_section,
)
from vector.domains.cortex.canonical.temporal_runtime import (
    TEMPORAL_RUNTIME_SCHEMA_VERSION,
    build_temporal_ordering_key,
    list_temporal_supersessions,
)
from vector.domains.cortex.canonical.transform_runtime import (
    ENGINE_BUILD_REF,
    TRANSFORM_RUNTIME_SCHEMA_VERSION,
    MaterializeError,
    canonical_json_hash,
    list_recent_materializations,
    materialization_public_dict,
    materialize_raw_record,
    resolve_materialization_input,
)
from vector.domains.cortex.canonical.transform_runtime_metadata import (
    TRANSFORM_RUNTIME_SURFACE_VERSION,
    build_transform_runtime_pointer_section,
)

__all__ = [
    "CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION",
    "CANONICAL_QUERY_SURFACE_VERSION",
    "CanonicalQueryError",
    "TEMPORAL_RUNTIME_SCHEMA_VERSION",
    "TEMPORAL_RUNTIME_SURFACE_VERSION",
    "PROVENANCE_RUNTIME_SCHEMA_VERSION",
    "PROVENANCE_RUNTIME_SURFACE_VERSION",
    "REPLAY_RUNTIME_SCHEMA_VERSION",
    "REPLAY_RUNTIME_SURFACE_VERSION",
    "ReplayJobError",
    "DEFAULT_PHASE04_BOUNDARY",
    "IDENTITY_ENGINE_BUILD_REF",
    "IDENTITY_RUNTIME_SCHEMA_VERSION",
    "IDENTITY_RUNTIME_SURFACE_VERSION",
    "PHASE03_CANONICAL_ENTITY_NAMESPACE",
    "CONFIDENCE_NON_RANKING_SEMANTICS",
    "CONFIDENCE_PROPAGATION_SCHEMA_VERSION",
    "FORBIDDEN_AUTO_CONFIDENCE_CLASSES",
    "Phase03ConfidenceClass",
    "AMBIGUITY_ENGINE_BUILD_REF",
    "AMBIGUITY_RUNTIME_SCHEMA_VERSION",
    "AMBIGUITY_RUNTIME_SURFACE_VERSION",
    "AmbiguityClass",
    "AmbiguityError",
    "AmbiguityStatus",
    "ENGINE_BUILD_REF",
    "EvidenceGrade",
    "LOGICAL_KEY_PROFILE_VERSION",
    "MAPPING_CONTRACT_SCHEMA_VERSION",
    "MAPPING_REGISTRY_SURFACE_VERSION",
    "REGISTRY_RUNTIME_SCHEMA_VERSION",
    "ORACLE_MANIFEST_SCHEMA_VERSION",
    "ONTOLOGY_SCHEMA_VERSION",
    "TRANSFORM_RUNTIME_SCHEMA_VERSION",
    "TRANSFORM_RUNTIME_SURFACE_VERSION",
    "build_logical_keys_public_section",
    "build_mapping_contracts_public_section",
    "build_mapping_registry_pointer_section",
    "build_oracle_manifest_public_document",
    "build_tenant_mapping_registry_public_document",
    "build_ambiguity_aggregates",
    "build_ambiguity_runtime_pointer_section",
    "build_confidence_taxonomy_public_section",
    "build_identity_runtime_pointer_section",
    "build_provenance_runtime_pointer_section",
    "build_replay_runtime_pointer_section",
    "build_canonical_query_pointer_section",
    "build_temporal_ordering_key",
    "build_temporal_runtime_pointer_section",
    "build_phase03_step01_ontology_public_document",
    "build_taxonomy_public_section",
    "build_transform_runtime_pointer_section",
    "ambiguity_record_public_dict",
    "confidence_class_rollup_for_tenant",
    "canonical_entity_id_for_materialization",
    "deterministic_canonical_entity_id",
    "execute_canonical_query",
    "canonical_json_hash",
    "logical_key_fields_for_kind",
    "materialization_confidence_rollup",
    "materialization_public_dict",
    "materialize_raw_record",
    "resolve_materialization_input",
    "oracle_vectors",
    "MaterializeError",
    "CanonicalStructuralRole",
    "structural_examples_for_kind",
    "structural_role_for_kind",
    "validate_logical_key_profile_internal_consistency",
    "validate_mapping_contracts_internal_consistency",
    "validate_oracle_manifest_internal_consistency",
    "validate_taxonomy_internal_consistency",
    "get_identity_anchor",
    "get_ambiguity_record",
    "identity_anchor_public_dict",
    "provenance_public_dict",
    "get_provenance_for_materialization",
    "list_identity_anchors",
    "list_provenance_for_raw_record",
    "list_temporal_supersessions",
    "list_ambiguity_records",
    "list_recent_materializations",
    "provider_identity_from_logical_key",
    "open_ambiguity_record",
    "stub_lineage_confidence",
    "upsert_identity_anchor_for_materialization",
    "upsert_provenance_for_materialization",
    "transition_ambiguity_record",
    "validate_confidence_class",
]

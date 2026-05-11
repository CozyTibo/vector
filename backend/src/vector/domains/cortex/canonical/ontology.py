"""Phase 03 Steps 1–18 — ontology + taxonomy + logical keys + contracts + registry + transform + ambiguity + confidence + identity + replay + provenance + temporal ordering + canonical query + failure/remediation + verification engine + operator control plane + stabilization proof + closure certification pack.

Normative sources: `DOCS/cortex/03-canonical/phase-03-canonical-model-doctrine.md`,
`phase-03-anti-goals-doctrine.md`, `phase-03-logical-key-doctrine.md`,
`phase-03-deterministic-canonicalization-doctrine.md`, bundle registry doctrines. Runtime authority for structural
kinds and frozen contracts; changes require `ONTOLOGY_SCHEMA_VERSION` bump and tracker note.
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import Any, Final

# Bump when ontology graph, taxonomy, logical keys, mapping-contract, registry, transform, ambiguity, confidence, identity, replay, provenance, temporal ordering, canonical query, failure/remediation, verification engine, control-plane, stabilization-proof, certification-pack, or Phase 04 org-entity / link-ledger / merge-governance / link-temporal / bundle-equivalence / graph-projection / org-ambiguity / org-identity-verification / org-failure-remediation admin metadata shape changes.
ONTOLOGY_SCHEMA_VERSION: Final[int] = 41


class CanonicalLayerKind(StrEnum):
    """Non-interpretive layer discriminant (taxonomy shell)."""

    ENTITY = "entity"
    ARTIFACT = "artifact"
    EVENT = "event"
    RELATIONSHIP = "relationship"
    REFERENCE = "reference"
    SNAPSHOT = "snapshot"


class CanonicalObjectKind(StrEnum):
    """Frozen v1 structural object kinds (snake_case stable ids)."""

    # Structural entities (provider-scoped identity bearers)
    PERSON = "person"
    ACCOUNT_INSTALLATION = "account_installation"
    WORKSPACE = "workspace"
    TEAM = "team"
    CHANNEL = "channel"
    CONVERSATION = "conversation"
    REPOSITORY = "repository"
    PROJECT = "project"
    INITIATIVE = "initiative"
    CYCLE = "cycle"
    # Structural artifacts
    DOCUMENT = "document"
    PAGE = "page"
    DATABASE_ROW = "database_row"
    PULL_REQUEST = "pull_request"
    ISSUE = "issue"
    THREAD = "thread"
    MESSAGE = "message"
    MEETING = "meeting"
    EXECUTION_CHECK = "execution_check"
    WORKFLOW_RUN = "workflow_run"
    DEPLOYMENT = "deployment"
    TRANSCRIPT = "transcript"
    RECORDING = "recording"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    # Events
    CANONICAL_EVENT = "canonical_event"
    TIMELINE_MUTATION = "timeline_mutation"
    # Relationships & pointers
    RELATIONSHIP_EDGE = "relationship_edge"
    CANONICAL_REFERENCE = "canonical_reference"
    # Snapshots (sparse use)
    STATE_SNAPSHOT = "state_snapshot"


_OBJECT_LAYER: dict[CanonicalObjectKind, CanonicalLayerKind] = {
    CanonicalObjectKind.PERSON: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.ACCOUNT_INSTALLATION: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.WORKSPACE: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.TEAM: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.CHANNEL: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.CONVERSATION: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.REPOSITORY: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.PROJECT: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.INITIATIVE: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.CYCLE: CanonicalLayerKind.ENTITY,
    CanonicalObjectKind.DOCUMENT: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.PAGE: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.DATABASE_ROW: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.PULL_REQUEST: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.ISSUE: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.THREAD: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.MESSAGE: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.MEETING: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.EXECUTION_CHECK: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.WORKFLOW_RUN: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.DEPLOYMENT: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.TRANSCRIPT: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.RECORDING: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: CanonicalLayerKind.ARTIFACT,
    CanonicalObjectKind.CANONICAL_EVENT: CanonicalLayerKind.EVENT,
    CanonicalObjectKind.TIMELINE_MUTATION: CanonicalLayerKind.EVENT,
    CanonicalObjectKind.RELATIONSHIP_EDGE: CanonicalLayerKind.RELATIONSHIP,
    CanonicalObjectKind.CANONICAL_REFERENCE: CanonicalLayerKind.REFERENCE,
    CanonicalObjectKind.STATE_SNAPSHOT: CanonicalLayerKind.SNAPSHOT,
}


class CanonicalStructuralEdgeKind(StrEnum):
    """Structural edge labels (evidenced links only in runtime mapping layers)."""

    MEMBERSHIP = "membership"
    PARENT_CHILD = "parent_child"
    CONTAINED_IN = "contained_in"
    AUTHORED_BY = "authored_by"
    MENTION = "mention"
    BLOCKS = "blocks"
    REFERENCES = "references"
    SUPERSEDES = "supersedes"
    RELATES_TO = "relates_to"


# Directed structural arcs: (source kind, edge label, target kind).
# Conservative v1 graph: encodes allowed *categories* of projection linkage, not semantic claims.
_STRUCTURAL_ARCS: tuple[tuple[CanonicalObjectKind, CanonicalStructuralEdgeKind, CanonicalObjectKind], ...] = (
    (CanonicalObjectKind.PERSON, CanonicalStructuralEdgeKind.MEMBERSHIP, CanonicalObjectKind.TEAM),
    (CanonicalObjectKind.PERSON, CanonicalStructuralEdgeKind.MEMBERSHIP, CanonicalObjectKind.CHANNEL),
    (CanonicalObjectKind.PERSON, CanonicalStructuralEdgeKind.MEMBERSHIP, CanonicalObjectKind.CONVERSATION),
    (CanonicalObjectKind.MESSAGE, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.CONVERSATION),
    (CanonicalObjectKind.MESSAGE, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.THREAD),
    (CanonicalObjectKind.MESSAGE, CanonicalStructuralEdgeKind.AUTHORED_BY, CanonicalObjectKind.PERSON),
    (CanonicalObjectKind.THREAD, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.CHANNEL),
    (CanonicalObjectKind.THREAD, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.CONVERSATION),
    (CanonicalObjectKind.ISSUE, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.REPOSITORY),
    (CanonicalObjectKind.ISSUE, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.PROJECT),
    (CanonicalObjectKind.PULL_REQUEST, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.REPOSITORY),
    (
        CanonicalObjectKind.EXECUTION_CHECK,
        CanonicalStructuralEdgeKind.CONTAINED_IN,
        CanonicalObjectKind.REPOSITORY,
    ),
    (
        CanonicalObjectKind.WORKFLOW_RUN,
        CanonicalStructuralEdgeKind.CONTAINED_IN,
        CanonicalObjectKind.REPOSITORY,
    ),
    (
        CanonicalObjectKind.DEPLOYMENT,
        CanonicalStructuralEdgeKind.CONTAINED_IN,
        CanonicalObjectKind.REPOSITORY,
    ),
    (
        CanonicalObjectKind.TRANSCRIPT_SEGMENT,
        CanonicalStructuralEdgeKind.CONTAINED_IN,
        CanonicalObjectKind.TRANSCRIPT,
    ),
    (CanonicalObjectKind.DOCUMENT, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.WORKSPACE),
    (CanonicalObjectKind.PAGE, CanonicalStructuralEdgeKind.CONTAINED_IN, CanonicalObjectKind.WORKSPACE),
    (CanonicalObjectKind.CANONICAL_EVENT, CanonicalStructuralEdgeKind.REFERENCES, CanonicalObjectKind.MESSAGE),
    (CanonicalObjectKind.CANONICAL_EVENT, CanonicalStructuralEdgeKind.REFERENCES, CanonicalObjectKind.ISSUE),
    (CanonicalObjectKind.RELATIONSHIP_EDGE, CanonicalStructuralEdgeKind.RELATES_TO, CanonicalObjectKind.PERSON),
    (CanonicalObjectKind.RELATIONSHIP_EDGE, CanonicalStructuralEdgeKind.RELATES_TO, CanonicalObjectKind.ISSUE),
    (CanonicalObjectKind.STATE_SNAPSHOT, CanonicalStructuralEdgeKind.SUPERSEDES, CanonicalObjectKind.STATE_SNAPSHOT),
)


_KIND_DESCRIPTIONS: dict[CanonicalObjectKind, str] = {
    CanonicalObjectKind.PERSON: "Provider-scoped actor object when evidenced in raw payloads.",
    CanonicalObjectKind.ACCOUNT_INSTALLATION: "Installation or OAuth installation boundary when evidenced.",
    CanonicalObjectKind.WORKSPACE: "Tenant/workspace container when evidenced.",
    CanonicalObjectKind.TEAM: "Collaboration group container when evidenced.",
    CanonicalObjectKind.CHANNEL: "Named channel or equivalent container when evidenced.",
    CanonicalObjectKind.CONVERSATION: "Conversation/DM/thread container when evidenced.",
    CanonicalObjectKind.REPOSITORY: "SCM repository object when evidenced.",
    CanonicalObjectKind.PROJECT: "Planning container (e.g. board/project) when evidenced.",
    CanonicalObjectKind.INITIATIVE: "Initiative/cycle planning object when evidenced.",
    CanonicalObjectKind.CYCLE: "Timeboxed planning cycle when evidenced.",
    CanonicalObjectKind.DOCUMENT: "Durable document artifact with stable provider id.",
    CanonicalObjectKind.PAGE: "Page-like artifact when evidenced.",
    CanonicalObjectKind.DATABASE_ROW: "Structured row artifact when evidenced.",
    CanonicalObjectKind.PULL_REQUEST: "PR/review unit when evidenced.",
    CanonicalObjectKind.ISSUE: "Issue/work item when evidenced.",
    CanonicalObjectKind.THREAD: "Thread unit under a conversation/channel when evidenced.",
    CanonicalObjectKind.MESSAGE: "Discrete message unit when evidenced.",
    CanonicalObjectKind.MEETING: "Meeting object when evidenced.",
    CanonicalObjectKind.EXECUTION_CHECK: (
        "Execution check lifecycle object (queued/in_progress/completed) with deterministic run identity."
    ),
    CanonicalObjectKind.WORKFLOW_RUN: "Workflow run lifecycle object when evidenced.",
    CanonicalObjectKind.DEPLOYMENT: "Deployment lifecycle object when evidenced.",
    CanonicalObjectKind.TRANSCRIPT: "Meeting transcript object when evidenced.",
    CanonicalObjectKind.RECORDING: "Recording attachment object when evidenced.",
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: "Transcript segment object when evidenced.",
    CanonicalObjectKind.CANONICAL_EVENT: "Occurred or observed event anchored to evidence (timeline doctrine).",
    CanonicalObjectKind.TIMELINE_MUTATION: "Structured lifecycle transition when evidenced as fields.",
    CanonicalObjectKind.RELATIONSHIP_EDGE: "Evidenced labeled link between canonical identities.",
    CanonicalObjectKind.CANONICAL_REFERENCE: "Deterministic pointer {kind, provider, stable_key, raw_record_ref}.",
    CanonicalObjectKind.STATE_SNAPSHOT: "Explicit structured state projection; sparse use (canonical model doctrine).",
}


def all_object_kinds() -> tuple[CanonicalObjectKind, ...]:
    return tuple(CanonicalObjectKind)


def layer_for_kind(kind: CanonicalObjectKind) -> CanonicalLayerKind:
    return _OBJECT_LAYER[kind]


def is_known_object_kind(value: str) -> bool:
    try:
        CanonicalObjectKind(value)
    except ValueError:
        return False
    return True


def build_phase03_step01_ontology_public_document(*, tenant_id: uuid.UUID | None = None) -> dict[str, Any]:
    """Operator-facing JSON document: ontology through Phase 03 Step 18 (incl. certification pack pointers)."""
    from vector.domains.cortex.canonical import taxonomy as canon_taxonomy
    from vector.domains.cortex.canonical.logical_keys import build_logical_keys_public_section
    from vector.domains.cortex.canonical.mapping_contracts import build_mapping_contracts_public_section
    from vector.domains.cortex.canonical.mapping_registry_metadata import build_mapping_registry_pointer_section
    from vector.domains.cortex.canonical.ambiguity_metadata import build_ambiguity_runtime_pointer_section
    from vector.domains.cortex.canonical.confidence_runtime import build_confidence_taxonomy_public_section
    from vector.domains.cortex.canonical.failure_remediation_metadata import build_failure_remediation_pointer_section
    from vector.domains.cortex.canonical.control_plane_metadata import build_control_plane_pointer_section
    from vector.domains.cortex.canonical.certification_pack_metadata import (
        build_certification_pack_pointer_section,
    )
    from vector.domains.cortex.canonical.stabilization_proof_metadata import (
        build_stabilization_proof_pointer_section,
    )
    from vector.domains.cortex.canonical.verification_engine_metadata import build_verification_engine_pointer_section
    from vector.domains.cortex.canonical.identity_metadata import build_identity_runtime_pointer_section
    from vector.domains.cortex.identity.bundle_equivalence_metadata import build_bundle_equivalence_pointer_section
    from vector.domains.cortex.identity.org_link_replay_metadata import build_org_link_replay_pointer_section
    from vector.domains.cortex.identity.link_rule_version_metadata import build_link_rule_version_pointer_section
    from vector.domains.cortex.identity.execution_primitive_persistence_metadata import (
        build_execution_primitive_persistence_pointer_section,
    )
    from vector.domains.cortex.identity.graph_projection_export_metadata import (
        build_org_graph_projection_export_pointer_section,
    )
    from vector.domains.cortex.identity.org_ambiguity_metadata import build_org_ambiguity_runtime_pointer_section
    from vector.domains.cortex.identity.org_failure_remediation_metadata import (
        build_org_failure_remediation_pointer_section,
    )
    from vector.domains.cortex.identity.identity_control_plane_metadata import (
        build_identity_control_plane_pointer_section,
    )
    from vector.domains.cortex.identity.readiness_economics_metadata import (
        build_identity_readiness_economics_pointer_section,
    )
    from vector.domains.cortex.identity.org_identity_certification_pack_metadata import (
        build_org_identity_certification_pack_pointer_section,
    )
    from vector.domains.cortex.identity.backfill_metadata import build_org_identity_backfill_pointer_section
    from vector.domains.cortex.identity.org_verification_metadata import build_org_identity_verification_pointer_section
    from vector.domains.cortex.identity.link_ledger_metadata import build_link_ledger_pointer_section
    from vector.domains.cortex.identity.merge_governance_metadata import build_merge_governance_pointer_section
    from vector.domains.cortex.identity.org_entity_metadata import build_org_entity_pointer_section
    from vector.domains.cortex.canonical.provenance_metadata import build_provenance_runtime_pointer_section
    from vector.domains.cortex.canonical.query_metadata import build_canonical_query_pointer_section
    from vector.domains.cortex.canonical.replay_metadata import build_replay_runtime_pointer_section
    from vector.domains.cortex.canonical.temporal_metadata import build_temporal_runtime_pointer_section
    from vector.domains.cortex.canonical.transform_runtime_metadata import build_transform_runtime_pointer_section

    taxonomy_section = canon_taxonomy.build_taxonomy_public_section()
    logical_keys_section = build_logical_keys_public_section()
    mapping_contracts_section = build_mapping_contracts_public_section()
    registry_pointer_section = build_mapping_registry_pointer_section()
    transform_pointer_section = build_transform_runtime_pointer_section()
    ambiguity_pointer_section = build_ambiguity_runtime_pointer_section()
    confidence_section = build_confidence_taxonomy_public_section()
    identity_pointer_section = build_identity_runtime_pointer_section()
    org_entity_pointer_section = build_org_entity_pointer_section()
    link_ledger_pointer_section = build_link_ledger_pointer_section()
    bundle_equivalence_pointer_section = build_bundle_equivalence_pointer_section()
    org_link_replay_pointer_section = build_org_link_replay_pointer_section()
    link_rule_version_pointer_section = build_link_rule_version_pointer_section()
    execution_primitive_persistence_pointer_section = build_execution_primitive_persistence_pointer_section()
    org_graph_projection_export_pointer_section = build_org_graph_projection_export_pointer_section()
    org_ambiguity_runtime_pointer_section = build_org_ambiguity_runtime_pointer_section()
    org_identity_verification_pointer_section = build_org_identity_verification_pointer_section()
    org_identity_backfill_pointer_section = build_org_identity_backfill_pointer_section()
    org_failure_remediation_pointer_section = build_org_failure_remediation_pointer_section()
    identity_control_plane_pointer_section = build_identity_control_plane_pointer_section()
    identity_readiness_economics_pointer_section = build_identity_readiness_economics_pointer_section()
    org_identity_certification_pack_pointer_section = build_org_identity_certification_pack_pointer_section()
    merge_governance_pointer_section = build_merge_governance_pointer_section()
    replay_pointer_section = build_replay_runtime_pointer_section()
    provenance_pointer_section = build_provenance_runtime_pointer_section()
    temporal_pointer_section = build_temporal_runtime_pointer_section()
    canonical_query_pointer_section = build_canonical_query_pointer_section()
    failure_remediation_pointer_section = build_failure_remediation_pointer_section()
    verification_engine_pointer_section = build_verification_engine_pointer_section()
    control_plane_pointer_section = build_control_plane_pointer_section()
    stabilization_proof_pointer_section = build_stabilization_proof_pointer_section()
    certification_pack_pointer_section = build_certification_pack_pointer_section()

    kinds_out: list[dict[str, Any]] = []
    for k in sorted(CanonicalObjectKind, key=lambda x: x.value):
        lyr = layer_for_kind(k)
        kinds_out.append(
            {
                "id": k.value,
                "layer": lyr.value,
                "taxonomy_family": lyr.value,
                "structural_role": canon_taxonomy.structural_role_for_kind(k).value,
                "structural_examples": list(canon_taxonomy.structural_examples_for_kind(k)),
                "description": _KIND_DESCRIPTIONS[k],
            }
        )
    arcs_out: list[dict[str, str]] = []
    for src, edge, dst in _STRUCTURAL_ARCS:
        arcs_out.append(
            {
                "from_kind": src.value,
                "edge_kind": edge.value,
                "to_kind": dst.value,
            }
        )
    out: dict[str, Any] = {
        "ontology_schema_version": ONTOLOGY_SCHEMA_VERSION,
        "phase": "03",
        "implementation_step": 22,
        "completed_implementation_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
        "name": "phase03_step18_certification_pack",
        "layers": [x.value for x in sorted(CanonicalLayerKind, key=lambda z: z.value)],
        "object_kinds": kinds_out,
        "structural_arcs": arcs_out,
        **taxonomy_section,
        **logical_keys_section,
        **mapping_contracts_section,
        **registry_pointer_section,
        **transform_pointer_section,
        **ambiguity_pointer_section,
        **confidence_section,
        **identity_pointer_section,
        **org_entity_pointer_section,
        **link_ledger_pointer_section,
        **bundle_equivalence_pointer_section,
        **org_link_replay_pointer_section,
        **link_rule_version_pointer_section,
        **execution_primitive_persistence_pointer_section,
        **org_graph_projection_export_pointer_section,
        **org_ambiguity_runtime_pointer_section,
        **org_identity_verification_pointer_section,
        **org_identity_backfill_pointer_section,
        **org_failure_remediation_pointer_section,
        **identity_control_plane_pointer_section,
        **identity_readiness_economics_pointer_section,
        **org_identity_certification_pack_pointer_section,
        **merge_governance_pointer_section,
        **replay_pointer_section,
        **provenance_pointer_section,
        **temporal_pointer_section,
        **canonical_query_pointer_section,
        **failure_remediation_pointer_section,
        **verification_engine_pointer_section,
        **control_plane_pointer_section,
        **stabilization_proof_pointer_section,
        **certification_pack_pointer_section,
        "doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-canonical-model-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-anti-goals-doctrine.md",
            "DOCS/cortex/03-canonical/implementation-plan.md",
            "DOCS/cortex/03-canonical/phase-03-logical-key-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-oracle-vectors-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-deterministic-canonicalization-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-mapping-bundle-registry.md",
            "DOCS/cortex/03-canonical/phase-03-mapping-system-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-transform-lineage-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-ambiguity-confidence-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-identity-continuity-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-replay-versioning-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-provenance-traceability-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-temporal-timeline-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-canonical-query-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-failure-degradation-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-remediation-recovery-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-verification-engine-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-closure-gates-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-canonical-control-plane-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-implementation-readiness-audit.md",
            "DOCS/cortex/04-identity/phase-04-link-ledger-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-candidate-vs-authoritative-linkage-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-merge-governance-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-hint-and-prohibited-link-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-verification-gates-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-failure-remediation-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-control-plane-doctrine.md",
            "DOCS/cortex/04-identity/phase-04-readiness-audit.md",
            "DOCS/cortex/04-identity/phase-04-closure-gates-doctrine.md",
        ],
    }
    if tenant_id is not None:
        out["tenant_id"] = str(tenant_id)
    return out

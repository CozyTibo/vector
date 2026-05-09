"""Phase 03 Step 2 — canonical object taxonomy (family boundaries + structural roles).

Normative: `DOCS/cortex/03-canonical/phase-03-canonical-model-doctrine.md` §Canonical object classes,
§Boundary rules. Structural only — no semantic classification.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final

from vector.domains.cortex.canonical.ontology import CanonicalLayerKind, CanonicalObjectKind, layer_for_kind


class CanonicalStructuralRole(StrEnum):
    """How a kind participates in deterministic projection (non-semantic workflow role)."""

    ACTOR = "actor"
    IDENTITY_CONTAINER = "identity_container"
    DISCRETE_UNIT = "discrete_unit"
    OCCURRENCE = "occurrence"
    LINKAGE = "linkage"
    POINTER = "pointer"
    PROJECTION = "projection"


TAXONOMY_FAMILY_DEFINITIONS: Final[dict[CanonicalLayerKind, str]] = {
    CanonicalLayerKind.ENTITY: (
        "Enduring identity bearer or collaboration/installation container evidenced in raw payloads "
        "(person, team, repo, channel, …). Not managerial interpretation—stable keys only."
    ),
    CanonicalLayerKind.ARTIFACT: (
        "Content-bearing or discrete communication/review unit with stable provider identifiers "
        "(document, issue, message, PR, …)."
    ),
    CanonicalLayerKind.EVENT: (
        "Something that occurred or was observed at a time; anchored to evidence and timeline doctrine "
        "(canonical_event, timeline_mutation)."
    ),
    CanonicalLayerKind.RELATIONSHIP: (
        "Linkage record between two or more canonical identities when evidenced "
        "(membership, parent/child, blocks, mentions)—never invented from free text."
    ),
    CanonicalLayerKind.REFERENCE: (
        "Deterministic pointer object {kind, provider, stable_key, raw_record_ref}; "
        "no cross-provider identity merge semantics (Phase 04)."
    ),
    CanonicalLayerKind.SNAPSHOT: (
        "Sparse explicit structured state projection at a revision; prefer events + supersession where possible."
    ),
}

_STRUCTURAL_ROLE: dict[CanonicalObjectKind, CanonicalStructuralRole] = {
    CanonicalObjectKind.PERSON: CanonicalStructuralRole.ACTOR,
    CanonicalObjectKind.ACCOUNT_INSTALLATION: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.WORKSPACE: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.TEAM: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.CHANNEL: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.CONVERSATION: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.REPOSITORY: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.PROJECT: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.INITIATIVE: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.CYCLE: CanonicalStructuralRole.IDENTITY_CONTAINER,
    CanonicalObjectKind.DOCUMENT: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.PAGE: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.DATABASE_ROW: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.PULL_REQUEST: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.ISSUE: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.THREAD: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.MESSAGE: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.MEETING: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.EXECUTION_CHECK: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.WORKFLOW_RUN: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.DEPLOYMENT: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.TRANSCRIPT: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.RECORDING: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: CanonicalStructuralRole.DISCRETE_UNIT,
    CanonicalObjectKind.CANONICAL_EVENT: CanonicalStructuralRole.OCCURRENCE,
    CanonicalObjectKind.TIMELINE_MUTATION: CanonicalStructuralRole.OCCURRENCE,
    CanonicalObjectKind.RELATIONSHIP_EDGE: CanonicalStructuralRole.LINKAGE,
    CanonicalObjectKind.CANONICAL_REFERENCE: CanonicalStructuralRole.POINTER,
    CanonicalObjectKind.STATE_SNAPSHOT: CanonicalStructuralRole.PROJECTION,
}

# Doctrine-aligned exemplars: provider-shaped **structural** examples ( identifiers only — not NL semantics).
_KIND_STRUCTURAL_EXAMPLES: dict[CanonicalObjectKind, tuple[str, ...]] = {
    CanonicalObjectKind.PERSON: ("slack_user_object", "github_user_object", "linear_user_object"),
    CanonicalObjectKind.ACCOUNT_INSTALLATION: ("oauth_installation_boundary",),
    CanonicalObjectKind.WORKSPACE: ("tenant_workspace_container",),
    CanonicalObjectKind.TEAM: ("slack_team", "linear_team"),
    CanonicalObjectKind.CHANNEL: ("slack_channel",),
    CanonicalObjectKind.CONVERSATION: ("slack_conversation", "dm_thread_container"),
    CanonicalObjectKind.REPOSITORY: ("github_repository",),
    CanonicalObjectKind.PROJECT: ("linear_project", "github_project_board"),
    CanonicalObjectKind.INITIATIVE: ("linear_initiative",),
    CanonicalObjectKind.CYCLE: ("linear_cycle",),
    CanonicalObjectKind.DOCUMENT: ("notion_page_document", "provider_file_object"),
    CanonicalObjectKind.PAGE: ("notion_page",),
    CanonicalObjectKind.DATABASE_ROW: ("notion_database_row",),
    CanonicalObjectKind.PULL_REQUEST: ("github_pull_request",),
    CanonicalObjectKind.ISSUE: ("linear_issue", "github_issue"),
    CanonicalObjectKind.THREAD: ("slack_thread", "message_thread"),
    CanonicalObjectKind.MESSAGE: ("slack_message", "linear_comment"),
    CanonicalObjectKind.MEETING: ("calls_meeting",),
    CanonicalObjectKind.EXECUTION_CHECK: ("github_check_run",),
    CanonicalObjectKind.WORKFLOW_RUN: ("github_workflow_run",),
    CanonicalObjectKind.DEPLOYMENT: ("github_deployment",),
    CanonicalObjectKind.TRANSCRIPT: ("calls_transcript",),
    CanonicalObjectKind.RECORDING: ("calls_recording",),
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: ("calls_transcript_segment",),
    CanonicalObjectKind.CANONICAL_EVENT: ("observed_lifecycle_event",),
    CanonicalObjectKind.TIMELINE_MUTATION: ("structured_status_transition",),
    CanonicalObjectKind.RELATIONSHIP_EDGE: ("membership_edge", "blocks_edge", "mentions_edge"),
    CanonicalObjectKind.CANONICAL_REFERENCE: ("deterministic_external_pointer",),
    CanonicalObjectKind.STATE_SNAPSHOT: ("explicit_field_projection_snapshot",),
}

TAXONOMY_HARD_RULES: Final[tuple[str, ...]] = (
    "Relationship edges require evidenced endpoints; Phase 03 does not infer edges from unstructured text.",
    "Canonical reference records carry deterministic keys only—no implicit cross-provider identity merge.",
    "State snapshots are sparse; prefer events plus supersession when mapping tables allow.",
    "Raw-only rows (pings, connectivity-only) remain non-canonical per Phase 01/02 classification.",
)


def structural_role_for_kind(kind: CanonicalObjectKind) -> CanonicalStructuralRole:
    return _STRUCTURAL_ROLE[kind]


def structural_examples_for_kind(kind: CanonicalObjectKind) -> tuple[str, ...]:
    return _KIND_STRUCTURAL_EXAMPLES[kind]


def validate_taxonomy_internal_consistency() -> None:
    """Assert Step 2 invariants; raises AssertionError if violated."""
    for k in CanonicalObjectKind:
        layer = layer_for_kind(k)
        assert k in _STRUCTURAL_ROLE
        role = _STRUCTURAL_ROLE[k]
        if layer == CanonicalLayerKind.RELATIONSHIP:
            assert role == CanonicalStructuralRole.LINKAGE
        if layer == CanonicalLayerKind.REFERENCE:
            assert role == CanonicalStructuralRole.POINTER
        if layer == CanonicalLayerKind.SNAPSHOT:
            assert role == CanonicalStructuralRole.PROJECTION


def build_taxonomy_public_section() -> dict[str, Any]:
    validate_taxonomy_internal_consistency()
    families: list[dict[str, Any]] = []
    for layer in sorted(CanonicalLayerKind, key=lambda x: x.value):
        families.append(
            {
                "id": layer.value,
                "boundary_definition": TAXONOMY_FAMILY_DEFINITIONS[layer],
            }
        )
    kind_rows: list[dict[str, Any]] = []
    for k in sorted(CanonicalObjectKind, key=lambda x: x.value):
        layer = layer_for_kind(k)
        kind_rows.append(
            {
                "object_kind_id": k.value,
                "taxonomy_family": layer.value,
                "structural_role": _STRUCTURAL_ROLE[k].value,
                "structural_examples": list(_KIND_STRUCTURAL_EXAMPLES[k]),
            }
        )
    return {
        "taxonomy_families": families,
        "kind_taxonomy": kind_rows,
        "taxonomy_hard_rules": list(TAXONOMY_HARD_RULES),
    }

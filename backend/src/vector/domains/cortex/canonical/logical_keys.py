"""Phase 03 Step 3 — canonical logical key profile (ordered idempotency tuple fields per kind).

Normative: `DOCS/cortex/03-canonical/phase-03-logical-key-doctrine.md`.
Structural specification only — no mapping execution (Step 6).
"""

from __future__ import annotations

from typing import Any, Final

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind

# Bump when any per-kind tuple field list or tie-break semantics change.
LOGICAL_KEY_PROFILE_VERSION: Final[int] = 1

LOGICAL_KEY_GLOBAL_RULES: Final[tuple[str, ...]] = (
    "Every logical key starts from tenant scope and includes mapping_bundle_id (or an explicit key_profile_version "
    "sub-id when multiple key shapes are allowed under governance).",
    "Include connector plus provider-stable resource identifiers present in raw payloads — never guessed display "
    "names or NL-derived labels.",
    "Add structural discriminants for fan-out (mention index, segment ordinal, thread reply sequence, …) when the "
    "provider yields 1→N projections.",
    "Use raw_record_id (or equivalent stable ingest pointer) as tie-break only where the provider lacks a stable "
    "discriminant — document per class.",
    "Forbidden in keys: timestamps as primary identity, random UUIDs, worker hostnames, now(), or hashes of "
    "free-text without a deterministic normalization table.",
)

# Ordered idempotency tuple field names (canonical column ids). Values are derived at mapping time from raw +
# bundle profile — this module fixes order and membership only.
_LOGICAL_KEY_FIELDS: dict[CanonicalObjectKind, tuple[str, ...]] = {
    CanonicalObjectKind.PERSON: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "provider_actor_id",
    ),
    CanonicalObjectKind.ACCOUNT_INSTALLATION: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "installation_id",
    ),
    CanonicalObjectKind.WORKSPACE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "workspace_provider_id",
    ),
    CanonicalObjectKind.TEAM: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "team_provider_id",
    ),
    CanonicalObjectKind.CHANNEL: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "channel_provider_id",
    ),
    CanonicalObjectKind.CONVERSATION: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "conversation_provider_id",
    ),
    CanonicalObjectKind.REPOSITORY: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "repository_provider_id",
    ),
    CanonicalObjectKind.PROJECT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "project_provider_id",
    ),
    CanonicalObjectKind.INITIATIVE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "initiative_provider_id",
    ),
    CanonicalObjectKind.CYCLE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "cycle_provider_id",
    ),
    CanonicalObjectKind.DOCUMENT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "document_provider_id",
    ),
    CanonicalObjectKind.PAGE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "page_provider_id",
    ),
    CanonicalObjectKind.DATABASE_ROW: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "database_provider_id",
        "row_provider_id",
    ),
    CanonicalObjectKind.PULL_REQUEST: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "repository_provider_id",
        "pull_request_discriminant",
    ),
    CanonicalObjectKind.ISSUE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "issue_provider_id",
    ),
    CanonicalObjectKind.THREAD: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "thread_provider_id",
    ),
    CanonicalObjectKind.MESSAGE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "conversation_provider_id",
        "message_provider_id",
    ),
    CanonicalObjectKind.MEETING: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "meeting_provider_id",
    ),
    CanonicalObjectKind.EXECUTION_CHECK: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "repository_provider_id",
        "check_run_provider_id",
    ),
    CanonicalObjectKind.WORKFLOW_RUN: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "repository_provider_id",
        "workflow_run_provider_id",
    ),
    CanonicalObjectKind.DEPLOYMENT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "repository_provider_id",
        "deployment_provider_id",
    ),
    CanonicalObjectKind.TRANSCRIPT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "meeting_provider_id",
        "transcript_provider_id",
    ),
    CanonicalObjectKind.RECORDING: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "meeting_provider_id",
        "recording_provider_id",
    ),
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "meeting_provider_id",
        "segment_ordinal",
    ),
    CanonicalObjectKind.CANONICAL_EVENT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "event_discriminant",
        "source_raw_record_id",
    ),
    CanonicalObjectKind.TIMELINE_MUTATION: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "target_object_ref",
        "mutation_revision",
    ),
    CanonicalObjectKind.RELATIONSHIP_EDGE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "structural_edge_kind",
        "from_endpoint_ref",
        "to_endpoint_ref",
    ),
    CanonicalObjectKind.CANONICAL_REFERENCE: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "referenced_object_kind",
        "stable_key",
        "raw_record_ref",
    ),
    CanonicalObjectKind.STATE_SNAPSHOT: (
        "tenant_id",
        "mapping_bundle_id",
        "connector",
        "snapshot_subject_ref",
        "snapshot_revision_token",
    ),
}

_TIE_BREAK_NOTES: dict[CanonicalObjectKind, str] = {
    CanonicalObjectKind.CANONICAL_EVENT: (
        "event_discriminant SHOULD be derived from evidenced fields; source_raw_record_id is the tie-break when "
        "the provider duplicates lifecycle signals without a finer stable key."
    ),
    CanonicalObjectKind.TRANSCRIPT_SEGMENT: (
        "segment_ordinal MUST be stable for the same meeting transcript ordering contract (mapping bundle defines "
        "normalization)."
    ),
    CanonicalObjectKind.MESSAGE: (
        "message_provider_id MUST be the provider-native message key (not display text); conversation_provider_id "
        "scopes DM vs channel fan-out."
    ),
}


def logical_key_fields_for_kind(kind: CanonicalObjectKind) -> tuple[str, ...]:
    return _LOGICAL_KEY_FIELDS[kind]


def tie_break_note_for_kind(kind: CanonicalObjectKind) -> str | None:
    return _TIE_BREAK_NOTES.get(kind)


def validate_logical_key_profile_internal_consistency() -> None:
    """Every ontology kind has a non-empty ordered field list."""
    for k in CanonicalObjectKind:
        fields = _LOGICAL_KEY_FIELDS[k]
        assert fields, k
        assert fields[0] == "tenant_id", k
        assert "mapping_bundle_id" in fields, k


def build_logical_keys_public_section() -> dict[str, Any]:
    validate_logical_key_profile_internal_consistency()
    rows: list[dict[str, Any]] = []
    for k in sorted(CanonicalObjectKind, key=lambda x: x.value):
        row: dict[str, Any] = {
            "canonical_object_kind": k.value,
            "idempotency_tuple_fields": list(_LOGICAL_KEY_FIELDS[k]),
        }
        note = tie_break_note_for_kind(k)
        if note is not None:
            row["tie_break_notes"] = note
        rows.append(row)
    return {
        "logical_key_profile_version": LOGICAL_KEY_PROFILE_VERSION,
        "logical_key_global_rules": list(LOGICAL_KEY_GLOBAL_RULES),
        "logical_keys_by_kind": rows,
        "logical_key_doctrine_anchors": [
            "DOCS/cortex/03-canonical/phase-03-logical-key-doctrine.md",
            "DOCS/cortex/03-canonical/phase-03-oracle-vectors-doctrine.md",
        ],
    }

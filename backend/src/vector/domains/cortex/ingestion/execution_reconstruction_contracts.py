"""Schema-first execution reconstruction contracts (Phases 01–03 substrate).

These types support **deterministic** coordination evidence --- connector fields, explicit
rules (``extraction_contract_id``), temporal ordering, and cross-system references.
They are **not** semantic-agent outputs, not embedding-derived truth, and not
probabilistic graph cognition.

``NormalizedReference`` payloads (Phase 3.5) may be embedded by reference; keep
``source_raw_record_ids`` non-empty wherever evidence is asserted.
"""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal, TypedDict

from vector.domains.cortex.continuity.reference_schema import NormalizedReference

EXECUTION_RECONSTRUCTION_CONTRACT_VERSION: int = 1


class ExecutionReconstructionContractViolation(ValueError):
    """Structural or determinism contract violation for execution reconstruction payloads."""


# ---------------------------------------------------------------------------
# 1) Conversational coordination extraction (schema-first kinds)
# ---------------------------------------------------------------------------


class ExecutionCoordinationKind(StrEnum):
    COMMITMENT = "commitment"
    ACKNOWLEDGMENT = "acknowledgment"
    BLOCKER = "blocker"
    ESCALATION = "escalation"
    OWNERSHIP_CLAIM = "ownership_claim"
    DEPENDENCY_REFERENCE = "dependency_reference"
    DELIVERY_PROMISE = "delivery_promise"
    FOLLOW_UP = "follow_up"
    RETRY = "retry"
    UNCERTAINTY = "uncertainty"
    DECISION = "decision"
    REQUEST = "request"
    COORDINATION_GAP = "coordination_gap"
    UNRESOLVED_ASK = "unresolved_ask"
    EXECUTION_HANDOFF = "execution_handoff"
    STATUS_CONFIRMATION = "status_confirmation"
    EXECUTION_RISK_SIGNAL = "execution_risk_signal"


class DeterministicConfidenceSource(StrEnum):
    """Non-ML confidence: where the label came from."""

    CONNECTOR_NATIVE_FIELD = "connector_native_field"
    EXPLICIT_RULE_ID = "explicit_rule_id"
    PATTERN_ID = "pattern_id"
    TEMPORAL_DERIVATION = "temporal_derivation"
    CROSS_REFERENCE = "cross_reference"
    UNRESOLVED = "unresolved"


class EvidenceLineageHop(TypedDict, total=False):
    """Single hop in deterministic evidence lineage."""

    hop_kind: Literal["raw_record", "normalized_reference", "derived_window", "cross_link"]
    raw_record_id: int
    reference: NormalizedReference
    rule_id: str


class ConversationExecutionEvent(TypedDict, total=False):
    """Coordination-level event extracted under a frozen extraction contract."""

    execution_reconstruction_contract_version: int
    event_id: str
    """SHA-256 hex from ``derive_conversation_execution_event_id``; optional until derived."""
    extraction_contract_id: str
    """Stable id of the deterministic extractor / rule pack (not a model name)."""
    coordination_kind: str
    source_raw_record_ids: list[int]
    observed_at_iso: str
    connector_origin: str
    connection_id: str
    source_thread_key: str
    source_message_keys: list[str]
    participant_handles: list[dict[str, str]]
    """Each item: provider + external_id (opaque strings)."""
    confidence_source: str
    evidence_lineage: list[EvidenceLineageHop]
    normalized_references: list[NormalizedReference]


CoordinationEdgeKind = Literal[
    "temporal_successor",
    "escalation_of",
    "blocks",
    "depends_on",
    "handoff",
    "same_thread",
]


class ExecutionCoordinationEdge(TypedDict, total=False):
    """Directed coordination link between events or canonical anchors."""

    execution_reconstruction_contract_version: int
    edge_id: str
    source_event_id: str
    target_event_id: str
    edge_kind: CoordinationEdgeKind
    derivation_rule_id: str
    evidence_lineage: list[EvidenceLineageHop]


class ExecutionThreadState(TypedDict, total=False):
    """Aggregate state for one coordination thread (deterministic reducer output)."""

    execution_reconstruction_contract_version: int
    thread_key: str
    open_asks: list[str]
    unresolved_blockers: list[str]
    stale_coordination: list[str]
    escalation_chain_event_ids: list[str]
    acknowledgment_state: Literal["none", "partial", "complete", "contradicted"]
    ownership_continuity_ok: bool
    latest_execution_state: str
    last_meaningful_interaction_iso: str | None
    silence_duration_seconds: int | None
    retry_count: int


ExecutionWindowKind = Literal[
    "coordination",
    "escalation",
    "silence",
    "dependency_response",
    "handoff",
    "ack_sla",
]


class ExecutionInteractionWindow(TypedDict, total=False):
    """Half-open or closed interaction interval in ingestion-time coordinates."""

    execution_reconstruction_contract_version: int
    window_id: str
    thread_key: str
    start_iso: str
    end_iso: str | None
    window_kind: ExecutionWindowKind


# ---------------------------------------------------------------------------
# 2) Temporal reconstruction
# ---------------------------------------------------------------------------


class TemporalAnchor(TypedDict, total=False):
    """Single anchor in a cross-system chain."""

    anchor_id: str
    connector_origin: str
    observed_at_iso: str
    monotonic_cursor: str | None
    """Opaque monotonic key when available (e.g. export sequence)."""
    raw_record_id: int | None


class TemporalAnchorChain(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    chain_id: str
    anchors: list[TemporalAnchor]
    replay_safe_ordering: Literal["strict", "partial", "unresolved"]


class ExecutionChronologyWindow(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    window_id: str
    label: str
    start_iso: str
    end_iso: str
    cross_source_merge_rule_id: str


class CrossSourceTemporalReference(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    reference_id: str
    left_anchor_id: str
    right_anchor_id: str
    skew_detected: bool
    late_arrival: bool


class ExecutionLatencyEnvelope(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    envelope_id: str
    p50_ms: int | None
    p95_ms: int | None
    max_ms: int | None
    sample_count: int
    derivation_rule_id: str


# ---------------------------------------------------------------------------
# 3) Commitment lifecycle
# ---------------------------------------------------------------------------


class CommitmentLifecycleState(StrEnum):
    PROPOSED = "proposed"
    ACKNOWLEDGED = "acknowledged"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    STALLED = "stalled"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    DRIFTED = "drifted"
    SUPERSEDED = "superseded"


class ExecutionCommitment(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    commitment_id: str
    committed_by_handle: dict[str, str]
    commitment_subject_refs: list[NormalizedReference]
    dependency_assumption_refs: list[NormalizedReference]
    acknowledgement_event_ids: list[str]
    expected_completion_iso: str | None
    follow_through_event_ids: list[str]
    lifecycle_state: str
    evidence_lineage: list[EvidenceLineageHop]


class CommitmentLifecycle(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    commitment_id: str
    state_history: list[dict[str, Any]]
    """Each entry: {at_iso, state, rule_id} --- reducer-emitted, deterministic order."""
    current_state: str


class CommitmentDriftSignal(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    signal_id: str
    commitment_id: str
    drift_kind: Literal["scope", "owner", "schedule", "dependency", "ack", "supersession"]
    rule_id: str
    evidence_lineage: list[EvidenceLineageHop]


class CommitmentResolutionState(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    commitment_id: str
    resolution: Literal["open", "resolved", "abandoned", "superseded", "unverifiable"]
    resolved_at_iso: str | None


# ---------------------------------------------------------------------------
# 4) Negative coordination signals
# ---------------------------------------------------------------------------


class NegativeSignalKind(StrEnum):
    UNANSWERED_REQUEST = "unanswered_request"
    IGNORED_ESCALATION = "ignored_escalation"
    STALE_BLOCKER = "stale_blocker"
    OWNERSHIP_VACUUM = "ownership_vacuum"
    ABANDONED_COORDINATION_THREAD = "abandoned_coordination_thread"
    MISSING_ACKNOWLEDGMENT = "missing_acknowledgment"
    REPEATED_FOLLOW_UP = "repeated_follow_up"
    DEPENDENCY_WITHOUT_OWNER = "dependency_without_owner"
    PR_WITHOUT_SOCIAL_RESPONSE = "pr_without_social_response"
    SILENT_DELIVERY_DRIFT = "silent_delivery_drift"
    UNRESOLVED_COMMITMENT = "unresolved_commitment"
    ESCALATION_WITHOUT_RESOLUTION = "escalation_without_resolution"


SeverityDerivation = Literal["rule_severity_v1", "rule_severity_v2", "connector_native"]


class NegativeExecutionSignal(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    signal_id: str
    signal_kind: str
    causal_event_ids: list[str]
    affected_entity_refs: list[NormalizedReference]
    duration_seconds: int | None
    severity_derivation: SeverityDerivation
    evidence_lineage: list[EvidenceLineageHop]


class CoordinationFailurePattern(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    pattern_id: str
    member_signal_ids: list[str]
    derivation_rule_id: str


class ExecutionSilenceWindow(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    silence_id: str
    thread_key: str
    start_iso: str
    end_iso: str
    silence_kind: Literal["thread", "cross_system", "dependency_wait"]


class FollowThroughGap(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    gap_id: str
    commitment_id: str
    expected_by_iso: str
    last_evidence_iso: str | None
    gap_seconds: int | None


# ---------------------------------------------------------------------------
# 5) Identity continuity (deterministic joins only)
# ---------------------------------------------------------------------------


class IdentityLinkDerivation(StrEnum):
    EXPLICIT_LINKAGE = "explicit_linkage"
    TEMPORAL_OVERLAP = "temporal_overlap"
    SHARED_EXECUTION_REFERENCE = "shared_execution_reference"
    STABLE_ORGANIZATIONAL_ANCHOR = "stable_organizational_anchor"


class IdentityContinuityRecord(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    record_id: str
    left_handle: dict[str, str]
    right_handle: dict[str, str]
    derivation: str
    rule_id: str
    evidence_lineage: list[EvidenceLineageHop]


class ExecutionDomainIdentity(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    domain_identity_id: str
    anchor_refs: list[NormalizedReference]
    continuity_record_ids: list[str]


class CanonicalWorkstream(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    workstream_id: str
    title_token: str
    """Deterministic token or hash of stable title fields --- not free-form NL summary."""
    owning_domain_identity_id: str | None
    reference_members: list[NormalizedReference]


class OwnershipContinuityLedger(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    ledger_id: str
    entries: list[dict[str, Any]]
    """Each entry: {at_iso, owner_handle, subject_ref, rule_id} in deterministic sort order."""


# ---------------------------------------------------------------------------
# 6) Canonical execution entities (durable ids + lineage hooks)
# ---------------------------------------------------------------------------


class CanonicalExecutionEntityKind(StrEnum):
    BLOCKER = "blocker"
    DEPENDENCY = "dependency"
    ESCALATION = "escalation"
    EXECUTION_GOAL = "execution_goal"
    DELIVERABLE = "deliverable"
    INCIDENT = "incident"
    OWNERSHIP_DOMAIN = "ownership_domain"
    WORKSTREAM = "workstream"
    EXECUTION_RISK = "execution_risk"
    DECISION = "decision"
    COORDINATION_THREAD = "coordination_thread"


class CanonicalExecutionEntity(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    entity_id: str
    kind: str
    state: str
    temporal_valid_from_iso: str
    temporal_valid_to_iso: str | None
    provenance_lineage: list[EvidenceLineageHop]
    cross_system_refs: list[NormalizedReference]
    causality_parent_entity_ids: list[str]


# ---------------------------------------------------------------------------
# 7) Reliability memory (system-level, not employee scoring)
# ---------------------------------------------------------------------------


class ExecutionReliabilityProfile(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    profile_id: str
    scope_ref: NormalizedReference
    window_start_iso: str
    window_end_iso: str
    coordination_responsiveness_p50_ms: int | None
    commitment_completion_rate_bps: int | None
    """Basis points 0-10000 --- deterministic ratio from counts, not a model."""
    escalation_resolution_rate_bps: int | None
    dependency_volatility_score: int | None
    """Integer score from fixed rubric id ``score_rule_id`` --- not ML."""
    score_rule_id: str


class CoordinationReliabilityVector(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    vector_id: str
    axes: dict[str, int | None]
    """Fixed-axis coordination reliability vector (counts / rubric scores only)."""
    derivation_rule_id: str


class DependencyStabilityLedger(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    ledger_id: str
    entries: list[dict[str, Any]]


class ExecutionVolatilityWindow(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    window_id: str
    start_iso: str
    end_iso: str
    volatility_class: Literal["low", "medium", "high"]
    rule_id: str


# ---------------------------------------------------------------------------
# 8) Ingestion / reconstruction quality diagnostics
# ---------------------------------------------------------------------------


class IngestionQualityDiagnostics(TypedDict, total=False):
    execution_reconstruction_contract_version: int
    diagnostics_id: str
    missing_chronology_count: int
    weak_provenance_count: int
    unresolved_identities_count: int
    orphan_execution_entities: list[str]
    dangling_commitment_ids: list[str]
    continuity_gap_refs: list[NormalizedReference]
    unresolved_coordination_chains: list[str]
    low_certainty_reconstruction_count: int
    connector_drift_flags: list[str]
    replay_instability_origins: list[str]


# ---------------------------------------------------------------------------
# Deterministic identifiers + structural validation
# ---------------------------------------------------------------------------


def _canonical_json_blob(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def derive_deterministic_id(*, namespace: str, parts: dict[str, Any]) -> str:
    """SHA-256 hex digest over namespace + canonical JSON of sorted parts."""
    body = {"namespace": namespace, "parts": {k: parts[k] for k in sorted(parts.keys())}}
    raw = _canonical_json_blob(body)
    return hashlib.sha256(raw).hexdigest()


def derive_conversation_execution_event_id(
    *, extraction_contract_id: str, parts: dict[str, Any]
) -> str:
    merged = {"extraction_contract_id": extraction_contract_id, **parts}
    return derive_deterministic_id(namespace="conversation_execution_event_v1", parts=merged)


def _is_non_empty_str(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _is_positive_int_list(v: object) -> bool:
    if not isinstance(v, list) or len(v) == 0:
        return False
    return all(type(x) is int and x > 0 for x in v)


def validate_conversation_execution_event(body: dict[str, Any]) -> list[str]:
    """Return human-readable contract violations (empty list = ok)."""
    errs: list[str] = []
    ver = body.get(
        "execution_reconstruction_contract_version",
        EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
    )
    if ver != EXECUTION_RECONSTRUCTION_CONTRACT_VERSION:
        errs.append("execution_reconstruction_contract_version_must_be_1")
    if not _is_non_empty_str(body.get("extraction_contract_id")):
        errs.append("extraction_contract_id_required")
    ck = body.get("coordination_kind")
    if not _is_non_empty_str(ck):
        errs.append("coordination_kind_required")
    else:
        try:
            ExecutionCoordinationKind(str(ck))
        except ValueError:
            errs.append("coordination_kind_unknown")
    if not _is_non_empty_str(body.get("observed_at_iso")):
        errs.append("observed_at_iso_required")
    if not _is_non_empty_str(body.get("connector_origin")):
        errs.append("connector_origin_required")
    if not _is_non_empty_str(body.get("connection_id")):
        errs.append("connection_id_required")
    if not _is_positive_int_list(body.get("source_raw_record_ids")):
        errs.append("source_raw_record_ids_required_nonempty_positive_ints")
    cs = body.get("confidence_source")
    if not _is_non_empty_str(cs):
        errs.append("confidence_source_required")
    else:
        try:
            DeterministicConfidenceSource(str(cs))
        except ValueError:
            errs.append("confidence_source_unknown")
    ph = body.get("participant_handles")
    if ph is not None:
        if not isinstance(ph, list):
            errs.append("participant_handles_must_be_list")
        else:
            for i, item in enumerate(ph):
                if not isinstance(item, dict):
                    errs.append(f"participant_handles_{i}_not_object")
                    continue
                prov_ok = _is_non_empty_str(item.get("provider"))
                ext_ok = _is_non_empty_str(item.get("external_id"))
                if not prov_ok or not ext_ok:
                    errs.append(f"participant_handles_{i}_missing_provider_or_external_id")
    return errs


def assert_conversation_execution_event(body: dict[str, Any]) -> None:
    """Raise ``ExecutionReconstructionContractViolation`` on first validation error batch."""
    errs = validate_conversation_execution_event(body)
    if errs:
        raise ExecutionReconstructionContractViolation("; ".join(errs))


def validate_execution_commitment(body: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if body.get("execution_reconstruction_contract_version", 1) != 1:
        errs.append("execution_reconstruction_contract_version_must_be_1")
    if not _is_non_empty_str(body.get("commitment_id")):
        errs.append("commitment_id_required")
    ls = body.get("lifecycle_state")
    if not _is_non_empty_str(ls):
        errs.append("lifecycle_state_required")
    else:
        try:
            CommitmentLifecycleState(str(ls))
        except ValueError:
            errs.append("lifecycle_state_unknown")
    el = body.get("evidence_lineage")
    if el is not None and not isinstance(el, list):
        errs.append("evidence_lineage_must_be_list")
    return errs


def validate_negative_execution_signal(body: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if body.get("execution_reconstruction_contract_version", 1) != 1:
        errs.append("execution_reconstruction_contract_version_must_be_1")
    if not _is_non_empty_str(body.get("signal_id")):
        errs.append("signal_id_required")
    sk = body.get("signal_kind")
    if not _is_non_empty_str(sk):
        errs.append("signal_kind_required")
    else:
        try:
            NegativeSignalKind(str(sk))
        except ValueError:
            errs.append("signal_kind_unknown")
    if not isinstance(body.get("causal_event_ids"), list):
        errs.append("causal_event_ids_required_list")
    return errs


def validate_identity_continuity_record(body: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not _is_non_empty_str(body.get("record_id")):
        errs.append("record_id_required")
    der = body.get("derivation")
    if not _is_non_empty_str(der):
        errs.append("derivation_required")
    else:
        try:
            IdentityLinkDerivation(str(der))
        except ValueError:
            errs.append("derivation_unknown")
    left_ok = isinstance(body.get("left_handle"), dict)
    right_ok = isinstance(body.get("right_handle"), dict)
    if not left_ok or not right_ok:
        errs.append("left_and_right_handle_objects_required")
    return errs


def build_minimal_conversation_execution_event(
    *,
    extraction_contract_id: str,
    coordination_kind: ExecutionCoordinationKind,
    observed_at_iso: str,
    connector_origin: str,
    connection_id: str,
    source_raw_record_ids: list[int],
    confidence_source: DeterministicConfidenceSource,
    thread_key: str,
    message_key: str,
) -> ConversationExecutionEvent:
    """Construct a minimal valid envelope and attach a derived ``event_id``."""
    parts = {
        "coordination_kind": coordination_kind.value,
        "observed_at_iso": observed_at_iso,
        "connector_origin": connector_origin,
        "connection_id": connection_id,
        "source_raw_record_ids": sorted(source_raw_record_ids),
        "confidence_source": confidence_source.value,
        "source_thread_key": thread_key,
        "source_message_keys": [message_key],
    }
    eid = derive_conversation_execution_event_id(
        extraction_contract_id=extraction_contract_id,
        parts=parts,
    )
    return {
        "execution_reconstruction_contract_version": EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
        "event_id": eid,
        "extraction_contract_id": extraction_contract_id,
        "coordination_kind": coordination_kind.value,
        "source_raw_record_ids": sorted(source_raw_record_ids),
        "observed_at_iso": observed_at_iso,
        "connector_origin": connector_origin,
        "connection_id": connection_id,
        "source_thread_key": thread_key,
        "source_message_keys": [message_key],
        "confidence_source": confidence_source.value,
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": source_raw_record_ids[0]}],
        "normalized_references": [],
    }


__all__ = [
    "EXECUTION_RECONSTRUCTION_CONTRACT_VERSION",
    "CanonicalExecutionEntity",
    "CanonicalExecutionEntityKind",
    "CommitmentDriftSignal",
    "CommitmentLifecycle",
    "CommitmentLifecycleState",
    "CommitmentResolutionState",
    "CanonicalWorkstream",
    "ConversationExecutionEvent",
    "CoordinationFailurePattern",
    "CoordinationReliabilityVector",
    "CrossSourceTemporalReference",
    "DependencyStabilityLedger",
    "DeterministicConfidenceSource",
    "EvidenceLineageHop",
    "ExecutionChronologyWindow",
    "ExecutionCommitment",
    "ExecutionCoordinationEdge",
    "ExecutionCoordinationKind",
    "ExecutionDomainIdentity",
    "ExecutionInteractionWindow",
    "ExecutionLatencyEnvelope",
    "ExecutionReconstructionContractViolation",
    "ExecutionReliabilityProfile",
    "ExecutionSilenceWindow",
    "ExecutionThreadState",
    "ExecutionVolatilityWindow",
    "FollowThroughGap",
    "IdentityContinuityRecord",
    "IdentityLinkDerivation",
    "IngestionQualityDiagnostics",
    "NegativeExecutionSignal",
    "NegativeSignalKind",
    "OwnershipContinuityLedger",
    "TemporalAnchor",
    "TemporalAnchorChain",
    "assert_conversation_execution_event",
    "build_minimal_conversation_execution_event",
    "derive_conversation_execution_event_id",
    "derive_deterministic_id",
    "validate_conversation_execution_event",
    "validate_execution_commitment",
    "validate_identity_continuity_record",
    "validate_negative_execution_signal",
]

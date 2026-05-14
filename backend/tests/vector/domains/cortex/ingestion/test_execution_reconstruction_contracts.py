"""Tests for schema-first execution reconstruction contracts."""

from __future__ import annotations

import pytest

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import (
    EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
    CommitmentLifecycleState,
    DeterministicConfidenceSource,
    ExecutionCoordinationKind,
    ExecutionReconstructionContractViolation,
    NegativeSignalKind,
    assert_conversation_execution_event,
    build_minimal_conversation_execution_event,
    derive_conversation_execution_event_id,
    derive_deterministic_id,
    validate_conversation_execution_event,
    validate_execution_commitment,
    validate_identity_continuity_record,
    validate_negative_execution_signal,
)


def test_derive_deterministic_id_stable() -> None:
    a = derive_deterministic_id(namespace="ns", parts={"b": 2, "a": 1})
    b = derive_deterministic_id(namespace="ns", parts={"a": 1, "b": 2})
    assert a == b
    assert len(a) == 64


def test_derive_event_id_includes_extraction_contract() -> None:
    parts = {"x": 1}
    i1 = derive_conversation_execution_event_id(extraction_contract_id="rule-a", parts=parts)
    i2 = derive_conversation_execution_event_id(extraction_contract_id="rule-b", parts=parts)
    assert i1 != i2


def test_validate_conversation_execution_event_ok() -> None:
    ev = build_minimal_conversation_execution_event(
        extraction_contract_id="slack:coord:v1",
        coordination_kind=ExecutionCoordinationKind.COMMITMENT,
        observed_at_iso="2026-05-13T12:00:00Z",
        connector_origin="slack",
        connection_id="00000000-0000-4000-8000-000000000001",
        source_raw_record_ids=[101, 102],
        confidence_source=DeterministicConfidenceSource.EXPLICIT_RULE_ID,
        thread_key="C12345",
        message_key="m-1",
    )
    assert validate_conversation_execution_event(dict(ev)) == []


def test_validate_conversation_execution_event_errors() -> None:
    assert "extraction_contract_id_required" in validate_conversation_execution_event({})


def test_assert_conversation_execution_event_raises() -> None:
    with pytest.raises(ExecutionReconstructionContractViolation):
        assert_conversation_execution_event({"coordination_kind": "commitment"})


def test_validate_execution_commitment() -> None:
    body = {
        "execution_reconstruction_contract_version": EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
        "commitment_id": "cmt-1",
        "lifecycle_state": CommitmentLifecycleState.PROPOSED.value,
        "evidence_lineage": [],
    }
    assert validate_execution_commitment(body) == []


def test_validate_negative_signal() -> None:
    body = {
        "execution_reconstruction_contract_version": EXECUTION_RECONSTRUCTION_CONTRACT_VERSION,
        "signal_id": "neg-1",
        "signal_kind": NegativeSignalKind.STALE_BLOCKER.value,
        "causal_event_ids": ["e1"],
    }
    assert validate_negative_execution_signal(body) == []


def test_validate_identity_continuity_record() -> None:
    body = {
        "record_id": "idr-1",
        "derivation": "explicit_linkage",
        "left_handle": {"provider": "slack", "external_id": "U1"},
        "right_handle": {"provider": "github", "external_id": "u-one"},
    }
    assert validate_identity_continuity_record(body) == []

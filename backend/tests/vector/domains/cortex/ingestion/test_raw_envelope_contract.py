"""Phase 01 Step 4 — raw envelope persistence contract."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.ingestion.raw_envelope_contract import (
    EnvelopeContractViolation,
    core_envelope_fields,
    validate_raw_payload_for_persistence,
)


def test_valid_minimal_payload() -> None:
    cid = uuid.uuid4()
    body = {
        **core_envelope_fields(
            connector="slack",
            connection_id=cid,
            source_object_type="slack.connector_health",
            source_object_id=str(cid),
        ),
    }
    validate_raw_payload_for_persistence(connector="slack", connection_id=cid, body=body)


def test_rejects_connector_type_mismatch() -> None:
    cid = uuid.uuid4()
    body = {
        **core_envelope_fields(
            connector="slack",
            connection_id=cid,
            source_object_type="slack.connector_health",
            source_object_id=str(cid),
        ),
    }
    body["connector_type"] = "github"
    with pytest.raises(EnvelopeContractViolation, match="does not match"):
        validate_raw_payload_for_persistence(connector="slack", connection_id=cid, body=body)


def test_rejects_bad_schema_version() -> None:
    cid = uuid.uuid4()
    body = {
        **core_envelope_fields(
            connector="slack",
            connection_id=cid,
            source_object_type="slack.connector_health",
            source_object_id=str(cid),
        ),
    }
    body["schema_version"] = 99
    with pytest.raises(EnvelopeContractViolation, match="schema_version"):
        validate_raw_payload_for_persistence(connector="slack", connection_id=cid, body=body)


def test_rejects_bad_replay_metadata() -> None:
    cid = uuid.uuid4()
    body = {
        **core_envelope_fields(
            connector="slack",
            connection_id=cid,
            source_object_type="slack.connector_health",
            source_object_id=str(cid),
        ),
        "cortex_replay_metadata": {
            "replay_job_id": "not-a-uuid",
            "replay_version": 1,
            "sync_mode": "replay",
        },
    }
    with pytest.raises(EnvelopeContractViolation, match="UUID"):
        validate_raw_payload_for_persistence(connector="slack", connection_id=cid, body=body)

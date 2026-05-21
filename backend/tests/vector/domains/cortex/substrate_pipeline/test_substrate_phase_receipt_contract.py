"""Substrate phase receipt contract (TRUE P0A)."""

from __future__ import annotations

import uuid

from vector.domains.cortex.execution.scheduling import verify_substrate_phase_receipt_contract_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED,
    build_substrate_phase_receipt_v1,
    compute_substrate_phase_receipt_hash_v1,
    read_phase_receipt_from_output,
)


def test_verify_substrate_phase_receipt_contract() -> None:
    assert verify_substrate_phase_receipt_contract_v1() == []


def test_receipt_hash_stable_for_same_inputs() -> None:
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    detail = {"bundle_id": "b1", "candidate_set_sha256": "abc"}
    h1 = compute_substrate_phase_receipt_hash_v1(
        phase_id=PHASE_03_IDENTITY,
        tenant_id=tid,
        pipeline_run_id=prid,
        outcome=PHASE_OUTCOME_COMPLETED,
        processed_count=2,
        blocked_reason=None,
        input_epoch="b1",
        output_epoch=None,
        detail=detail,
    )
    h2 = compute_substrate_phase_receipt_hash_v1(
        phase_id=PHASE_03_IDENTITY,
        tenant_id=tid,
        pipeline_run_id=prid,
        outcome=PHASE_OUTCOME_COMPLETED,
        processed_count=2,
        blocked_reason=None,
        input_epoch="b1",
        output_epoch=None,
        detail=detail,
    )
    assert h1 == h2


def test_build_receipt_merges_into_output_envelope() -> None:
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    raw = {"counts_after": {"org_link_edges": 3}}
    rec = build_substrate_phase_receipt_v1(
        phase_id=PHASE_03_IDENTITY,
        tenant_id=tid,
        pipeline_run_id=prid,
        outcome=PHASE_OUTCOME_COMPLETED,
        raw_output=raw,
        started_at="2026-05-21T00:00:00+00:00",
        completed_at="2026-05-21T00:00:01+00:00",
    )
    env = rec.to_output_envelope()
    assert env["receipt_hash"] == rec.receipt_hash
    assert env["outcome"] == PHASE_OUTCOME_COMPLETED
    parsed = read_phase_receipt_from_output(env)
    assert parsed is not None
    assert parsed["schema_version"] == 1

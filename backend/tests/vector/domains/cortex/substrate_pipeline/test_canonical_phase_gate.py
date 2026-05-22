"""M1 — canonical→identity gate shared by convergence and legacy Celery."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
    canonical_identity_may_proceed_despite_topology_v1,
    canonical_may_advance_to_identity_v1,
    canonical_needs_more_work_v1,
    evaluate_legacy_canonical_chain_gate_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_STATUS_FAILED,
    PHASE_STATUS_WAITING,
)

_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def test_canonical_needs_more_work_topology_wait_when_drainable() -> None:
    session = MagicMock()
    summary = {"canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT, "bundle_id": _BUNDLE}
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate._resolve_gate_bundle_id",
            return_value=_BUNDLE,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.untreated_routable_drainable_exists_v1",
            return_value=True,
        ),
    ):
        assert (
            canonical_needs_more_work_v1(
                session, canonical_summary=summary, tenant_id=uuid.uuid4(), bundle_id=_BUNDLE
            )
            is True
        )


def test_canonical_needs_more_work_topology_wait_when_not_drainable() -> None:
    session = MagicMock()
    summary = {
        "canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT,
        "bundle_id": _BUNDLE,
        "candidate_more_remain": False,
    }
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate._resolve_gate_bundle_id",
            return_value=_BUNDLE,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.untreated_routable_drainable_exists_v1",
            return_value=False,
        ),
    ):
        assert (
            canonical_needs_more_work_v1(
                session, canonical_summary=summary, tenant_id=uuid.uuid4(), bundle_id=_BUNDLE
            )
            is False
        )


def test_canonical_needs_more_work_skipped_bundle() -> None:
    session = MagicMock()
    assert (
        canonical_needs_more_work_v1(
            session,
            canonical_summary={"skipped": True},
            tenant_id=uuid.uuid4(),
        )
        is False
    )


def test_canonical_may_advance_blocks_waiting_zero_progress() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_run = MagicMock(status=PHASE_STATUS_WAITING)
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.get_phase_run_v1",
            return_value=phase_run,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate._resolve_gate_bundle_id",
            return_value=_BUNDLE,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.canonical_identity_may_proceed_despite_topology_v1",
            return_value=False,
        ),
    ):
        may, reason = canonical_may_advance_to_identity_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            phase_output={
                "bundle_id": _BUNDLE,
                "canonical_summary": {
                    "canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT,
                    "total_succeeded": 0,
                },
            },
        )
    assert may is False
    assert reason == "canonical_topology_wait_zero_progress"


def test_canonical_may_advance_allows_waiting_when_no_drainable_rows() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_run = MagicMock(status=PHASE_STATUS_WAITING)
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.get_phase_run_v1",
            return_value=phase_run,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate._resolve_gate_bundle_id",
            return_value=_BUNDLE,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.canonical_identity_may_proceed_despite_topology_v1",
            return_value=True,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.canonical_needs_more_work_v1",
            return_value=False,
        ),
    ):
        may, reason = canonical_may_advance_to_identity_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            phase_output={
                "bundle_id": _BUNDLE,
                "canonical_summary": {
                    "canonical_outcome": CANONICAL_OUTCOME_TOPOLOGY_WAIT,
                    "total_succeeded": 0,
                },
            },
        )
    assert may is True
    assert reason is None


def test_canonical_may_advance_blocks_failed_zero_progress() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    prid = uuid.uuid4()
    phase_run = MagicMock(status=PHASE_STATUS_FAILED)
    with patch(
        "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.get_phase_run_v1",
        return_value=phase_run,
    ):
        may, reason = canonical_may_advance_to_identity_v1(
            session,
            tenant_id=tid,
            pipeline_run_id=prid,
            phase_output={
                "canonical_summary": {"canonical_outcome": "failed", "total_succeeded": 0},
            },
        )
    assert may is False
    assert reason == "canonical_materialization_failed_zero_progress"


def test_evaluate_legacy_gate_disabled_always_chains() -> None:
    session = MagicMock()
    out = evaluate_legacy_canonical_chain_gate_v1(
        session,
        tenant_id=uuid.uuid4(),
        pipeline_run_id=uuid.uuid4(),
        phase_output={},
        gate_enabled=False,
    )
    assert out["may_chain"] is True
    assert out["gate_enabled"] is False


def test_canonical_needs_more_work_partial_progress_respects_drainable() -> None:
    session = MagicMock()
    summary = {"canonical_outcome": CANONICAL_OUTCOME_PARTIAL_PROGRESS, "bundle_id": _BUNDLE}
    with (
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate._resolve_gate_bundle_id",
            return_value=_BUNDLE,
        ),
        patch(
            "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.untreated_routable_drainable_exists_v1",
            return_value=False,
        ),
    ):
        assert (
            canonical_needs_more_work_v1(
                session, canonical_summary=summary, tenant_id=uuid.uuid4(), bundle_id=_BUNDLE
            )
            is False
        )


def test_canonical_identity_may_proceed_despite_topology() -> None:
    session = MagicMock()
    with patch(
        "vector.domains.cortex.substrate_pipeline.canonical_phase_gate.untreated_routable_drainable_exists_v1",
        return_value=False,
    ):
        assert (
            canonical_identity_may_proceed_despite_topology_v1(
                session, tenant_id=uuid.uuid4(), bundle_id=_BUNDLE
            )
            is True
        )

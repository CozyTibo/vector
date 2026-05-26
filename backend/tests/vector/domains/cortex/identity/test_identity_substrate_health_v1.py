"""Identity substrate health laws and phase-03 outcome honesty."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

from vector.domains.cortex.execution.dual_lane_worker import resolve_execution_lane_entry_phase_v1
from vector.domains.cortex.identity.identity_substrate_health_v1 import (
    evaluate_identity_substrate_health_v1,
    execution_downstream_blocked_by_identity_v1,
    identity_substrate_repair_owed_v1,
)
from vector.domains.cortex.identity.identity_substrate_phase_helpers_v1 import (
    resolve_phase_03_outcome_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_03_IDENTITY,
    PHASE_07_RETRIEVAL,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED,
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
)


def test_broken_when_anchors_without_human_actors() -> None:
    session = MagicMock()
    with (
        patch(
            "vector.domains.cortex.identity.identity_substrate_health_v1.count_identity_anchors_v1",
            return_value=100,
        ),
        patch(
            "vector.domains.cortex.identity.identity_substrate_health_v1.count_active_human_actors_v1",
            return_value=0,
        ),
        patch(
            "vector.domains.cortex.identity.identity_substrate_health_v1.count_distinct_authoritative_promotion_rules_v1",
            return_value=0,
        ),
        patch(
            "vector.domains.cortex.identity.identity_substrate_health_v1.count_authoritative_links_v1",
            return_value=0,
        ),
    ):
        health = evaluate_identity_substrate_health_v1(session, tenant_id=uuid.uuid4())
    assert health["status"] == "broken"
    assert "anchors_without_human_actors" in health["reasons"]
    assert identity_substrate_repair_owed_v1(health)
    assert execution_downstream_blocked_by_identity_v1(health)


def test_phase_03_never_completed_empty_when_broken() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    raw = {
        "identity_substrate_health_after": {"status": "broken", "reasons": ["anchors_without_human_actors"]},
        "identity_continuity_substrate": {
            "identity_substrate_repair": {"anchor_backfill_exhausted": False},
        },
        "identity_substrate_audit": {"counts_after": {"org_entities_active": 0}},
    }
    outcome, _ = resolve_phase_03_outcome_v1(session, tenant_id=tid, raw_output=raw)
    assert outcome != PHASE_OUTCOME_COMPLETED_EMPTY


def test_phase_03_failed_when_broken_exhausted_no_entities() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    raw = {
        "identity_substrate_health_after": {"status": "broken"},
        "identity_continuity_substrate": {
            "identity_substrate_repair": {"anchor_backfill_exhausted": True},
        },
        "identity_substrate_audit": {"counts_after": {"org_entities_active": 0}},
    }
    outcome, reason = resolve_phase_03_outcome_v1(session, tenant_id=tid, raw_output=raw)
    assert outcome == PHASE_OUTCOME_FAILED
    assert reason == "identity_substrate_broken_unrecoverable"


def test_execution_lane_rewinds_to_phase_03_when_broken() -> None:
    lease = MagicMock()
    lease.phase_cursor = PHASE_07_RETRIEVAL
    session = MagicMock()
    with patch(
        "vector.domains.cortex.identity.identity_substrate_health_v1.evaluate_identity_substrate_health_v1",
        return_value={"status": "broken", "reasons": []},
    ):
        phase = resolve_execution_lane_entry_phase_v1(session, tenant_id=uuid.uuid4(), lease=lease)
    assert phase == PHASE_03_IDENTITY


def test_healthy_idle_can_complete_empty() -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    raw = {
        "identity_substrate_health_after": {"status": "healthy", "reasons": []},
        "identity_substrate_audit": {
            "anchor_backfill": {"entities_upserted": 0},
            "distinct_candidate_pairs_delta": 0,
        },
    }
    with patch(
        "vector.domains.cortex.identity.identity_substrate_phase_helpers_v1.evaluate_identity_substrate_health_v1",
        return_value={"status": "healthy", "reasons": []},
    ):
        outcome, _ = resolve_phase_03_outcome_v1(session, tenant_id=tid, raw_output=raw)
    assert outcome == PHASE_OUTCOME_COMPLETED_EMPTY

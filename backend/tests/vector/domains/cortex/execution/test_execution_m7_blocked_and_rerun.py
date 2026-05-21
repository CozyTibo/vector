"""M7 — retrieval BLOCKED policy and admin rerun."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from vector.domains.cortex.execution.blocked import apply_post_phase07_retrieval_policy_v1
from vector.domains.cortex.execution.progression_status import (
    MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1,
)


def test_apply_post_phase07_healthy_idle_continues() -> None:
    session = MagicMock()
    run = MagicMock()
    run.summary_json = {}
    session.get.return_value = run
    with patch(
        "vector.domains.cortex.execution.blocked.count_synthesis_eligible_scopes_v1",
        return_value={"index_row_count": 0},
    ):
        out = apply_post_phase07_retrieval_policy_v1(
            session,
            tenant_id=uuid.uuid4(),
            pipeline_run_id=uuid.uuid4(),
            phase07_output={"retrieval_card_classification": "healthy_idle"},
        )
    assert out == "continue_08"


def test_apply_post_phase07_starvation_retries_until_blocked() -> None:
    session = MagicMock()
    run = MagicMock()
    run.summary_json = {
        "progression": {"retrieval_materialization_retries": MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1}
    }
    session.get.return_value = run
    with (
        patch(
            "vector.domains.cortex.execution.blocked.count_synthesis_eligible_scopes_v1",
            return_value={"index_row_count": 0},
        ),
        patch(
            "vector.domains.cortex.execution.blocked.mark_tenant_execution_blocked_v1",
            return_value={"fsm_state": "BLOCKED"},
        ) as block_mock,
    ):
        out = apply_post_phase07_retrieval_policy_v1(
            session,
            tenant_id=uuid.uuid4(),
            pipeline_run_id=uuid.uuid4(),
            phase07_output={"retrieval_card_classification": "operational_starvation"},
        )
    assert out == "blocked"
    block_mock.assert_called_once()


def test_apply_post_phase07_starvation_increments_retry() -> None:
    session = MagicMock()
    run = MagicMock()
    run.summary_json = {}
    session.get.return_value = run
    with patch(
        "vector.domains.cortex.execution.blocked.count_synthesis_eligible_scopes_v1",
        return_value={"index_row_count": 0},
    ):
        out = apply_post_phase07_retrieval_policy_v1(
            session,
            tenant_id=uuid.uuid4(),
            pipeline_run_id=uuid.uuid4(),
            phase07_output={"retrieval_card_classification": "operational_starvation"},
        )
    assert out == "retry_07"

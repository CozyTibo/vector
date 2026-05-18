"""E2E Scenario D — synthesis job idempotency."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.testing import run_synthesis_e2e_scenario_d_v1


@pytest.mark.integration
def test_scenario_d_pipeline_idempotency(db_session: Session, synthesis_e2e_tenant_id: uuid.UUID) -> None:
    result = run_synthesis_e2e_scenario_d_v1(db_session, tenant_id=synthesis_e2e_tenant_id)
    assert result["scenario"] == "D"
    assert result["passed"] is True, result
    assert result["job_id_a"] == result["job_id_b"]
    assert result["artifact_id"]

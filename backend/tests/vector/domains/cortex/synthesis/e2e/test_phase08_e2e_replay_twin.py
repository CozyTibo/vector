"""E2E Scenario C — replay equivalence structural twin."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.testing import run_synthesis_e2e_scenario_c_v1


@pytest.mark.integration
def test_scenario_c_replay_twin(db_session: Session, synthesis_e2e_tenant_id: uuid.UUID) -> None:
    result = run_synthesis_e2e_scenario_c_v1(db_session, tenant_id=synthesis_e2e_tenant_id)
    assert result["scenario"] == "C"
    assert result["passed"] is True, result
    assert result.get("gp08_replay_proof_passed") is True

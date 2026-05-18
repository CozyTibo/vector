"""E2E Scenario B — upstream degradation (RD-TCRE-GAP → SD-UPSTREAM-RD)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase_boundaries import SD_UPSTREAM_RD_V1
from vector.domains.cortex.synthesis.testing import run_synthesis_e2e_scenario_b_v1


@pytest.mark.integration
def test_scenario_b_degraded_upstream(db_session: Session, synthesis_e2e_tenant_id: uuid.UUID) -> None:
    result = run_synthesis_e2e_scenario_b_v1(db_session, tenant_id=synthesis_e2e_tenant_id)
    assert result["scenario"] == "B"
    assert result["passed"] is True, result
    assert result["synthesis_legality_class"] == "synthesis_degraded"
    assert SD_UPSTREAM_RD_V1 in (result.get("degradation_check") or {}).get("sd_codes", [])

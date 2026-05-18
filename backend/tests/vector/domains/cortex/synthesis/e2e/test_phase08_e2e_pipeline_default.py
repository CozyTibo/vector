"""E2E Scenario A — pipeline default happy path (phase 02–08)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.testing import (
    run_synthesis_e2e_scenario_a_v1,
    verify_gp08_e2e01_operational_certification_static,
)


def test_e2e_static_gate() -> None:
    assert verify_gp08_e2e01_operational_certification_static()["passed"] is True


@pytest.mark.integration
def test_scenario_a_pipeline_default_happy_path(
    db_session: Session,
    synthesis_e2e_tenant_id: uuid.UUID,
    synthesis_e2e_bundle_id: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED", "true")
    from vector.settings import get_settings

    get_settings.cache_clear()

    if not synthesis_e2e_bundle_id:
        pytest.skip("no_transformable_bundle_for_e2e_tenant")

    result = run_synthesis_e2e_scenario_a_v1(
        db_session,
        tenant_id=synthesis_e2e_tenant_id,
        bundle_id=synthesis_e2e_bundle_id,
    )
    if result.get("skipped"):
        pytest.skip(str(result.get("reason")))
    assert result["scenario"] == "A"
    assert result["passed"] is True, result
    assert result.get("pipeline", {}).get("synthesis_publication_epoch")

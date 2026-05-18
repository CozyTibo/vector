"""E2E certification bundle — scenarios A–D aggregate."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.testing import (
    GP08_E2E01_GATE_ID_V1,
    run_synthesis_e2e_certification_bundle_v1,
)


@pytest.mark.integration
def test_synthesis_e2e_certification_bundle(
    db_session: Session,
    synthesis_e2e_tenant_id: uuid.UUID,
    synthesis_e2e_bundle_id: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CORTEX_SUBSTRATE_PIPELINE_PHASE_08_ENABLED", "true")
    from vector.settings import get_settings

    get_settings.cache_clear()

    bundle = run_synthesis_e2e_certification_bundle_v1(
        db_session,
        tenant_id=synthesis_e2e_tenant_id,
        bundle_id=synthesis_e2e_bundle_id,
    )
    assert bundle["gate_id"] == GP08_E2E01_GATE_ID_V1
    scenarios = bundle["scenarios"]
    assert scenarios["B"]["passed"] is True
    assert scenarios["C"]["passed"] is True
    assert scenarios["D"]["passed"] is True
    if scenarios["A"].get("skipped"):
        pytest.skip(f"scenario_a_skipped:{scenarios['A'].get('reason')}")
    assert scenarios["A"]["passed"] is True
    assert bundle["all_passed"] is True

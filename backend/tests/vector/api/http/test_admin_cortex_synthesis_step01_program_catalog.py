"""Phase 08 Step 01 — admin synthesis program doctrine catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.normative import PHASE08_PROGRAM_FREEZE_VERSION

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_synthesis_program_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/synthesis/program",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    assert body["normative_program"]["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    assert body["replay_law"]["gate_ids"] == ["G-P08-REPLAY-01", "G-P08-REPLAY-02"]
    assert body["degradation_registry"]["code_prefix"] == "SD-"

"""Phase 08.5 Step 01 — admin operational-runtime program doctrine catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.operational_runtime.cesp_program_freeze import GP085_CESP01_GATE_ID_V1
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_PROGRAM_FREEZE_VERSION,
    PHASE085_PROGRAM_ID_V1,
)

pytestmark = pytest.mark.integration


def test_admin_catalog_cortex_operational_runtime_program_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/operational-runtime/program",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["program_id"] == PHASE085_PROGRAM_ID_V1
    assert body["phase085_program_freeze_version"] == PHASE085_PROGRAM_FREEZE_VERSION
    assert body["normative_program"]["phase085_program_freeze_version"] == PHASE085_PROGRAM_FREEZE_VERSION
    assert body["continuity_law"]["continuation_nonce_field"] == "continuation_nonce"
    assert body["density_law"]["skip_code_prefix"] == "RET-SKIP-"
    assert GP085_CESP01_GATE_ID_V1 in body["gate_ids"]

"""Admin HTTP — Phase 08.5 Step 36 certification + closure."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_certification_pack(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(db_session, note="admin cert pack test")
    db_session.commit()
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/certification-pack",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cesp_cert_pack_format"] == "CESP-CERT-PACK-1"
    assert body["closure_passed"] is True


def test_admin_program_closure_gate(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    from vector.domains.cortex.operational_runtime.substrate_phase09_readiness import (
        record_phase09_soak_signoff_v1,
    )

    record_phase09_soak_signoff_v1(db_session, note="admin closure test")
    db_session.commit()
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/program-closure",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True
    assert r.json()["id"] == "G-P085-CLOSE-01"


def test_admin_constitutional_freeze(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/constitutional-freeze",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["constitutional_freeze_bundle"] == "P085-FINAL-FREEZE-2026-05-18"

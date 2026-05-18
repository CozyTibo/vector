"""Phase 08 Step 27 — admin synthesis golden vectors catalog HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def test_admin_catalog_synthesis_golden_vectors_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/golden-vectors",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["corpus_id"] == "synthesis_golden_v1"
    assert body["golden_corpus_case_count"] == 4
    assert len(body["policy_pack_fixture_digest_sha256"]) == 64
    assert body["policy_pack_fixture_present"] is True
    assert len(body["cases"]) == 4

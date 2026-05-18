"""Phase 08 Step 04 — admin synthesis ingress law + inspector HTTP surfaces."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1

pytestmark = pytest.mark.integration


def _legal_retrieval_body() -> dict[str, object]:
    return {
        "retrieval_response": {
            "retrieval_legality_class": "retrieval_replay_safe",
            PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:admin",
            "retrieval_evidence_hits": [],
            "retrieval_omission_rows": [],
            "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        },
        "job_envelope": {
            "execution_partition": "authoritative",
        },
    }


def test_admin_catalog_cortex_synthesis_ingress_law_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.get(
        "/admin/catalog/cortex/synthesis/ingress-law",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert "SYN-INGRESS-REP-01" in body["gate_ids"]
    assert body["gp08_ingress_gate_id"] == "G-P08-INGRESS-01"


def test_admin_catalog_cortex_synthesis_ingress_validate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")

    r = client.post(
        "/admin/catalog/cortex/synthesis/ingress/validate",
        json=_legal_retrieval_body(),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ingress_passed"] is True
    assert body["retrieval_evidence_ingress"]["retrieval_ingress_digest"]


def test_admin_catalog_cortex_synthesis_ingress_validate_rejects_exploration(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    payload = _legal_retrieval_body()
    assert isinstance(payload["retrieval_response"], dict)
    payload["retrieval_response"]["non_authoritative"] = True

    r = client.post(
        "/admin/catalog/cortex/synthesis/ingress/validate",
        json=payload,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ingress_passed"] is False
    assert body["surface_kind"] == "verification_probe"

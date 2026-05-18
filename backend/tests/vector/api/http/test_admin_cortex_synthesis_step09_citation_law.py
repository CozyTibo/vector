"""Phase 08 Step 09 — admin synthesis citation law HTTP surface."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    GP08_CITE01_GATE_ID_V1,
    SYN_LAW_09_RULE_ID_V1,
)

pytestmark = pytest.mark.integration


def test_admin_get_synthesis_citation_law_catalog_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/citation-law",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == GP08_CITE01_GATE_ID_V1
    assert body["syn_law_rule"] == SYN_LAW_09_RULE_ID_V1
    assert "temporal_fact" in body["claim_kinds"]


def test_admin_post_synthesis_citations_bind_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/synthesis/citations/bind",
        auth=("admin", "integration-admin-password"),
        json={
            "retrieval_response": {
                "retrieval_evidence_hits": [
                    {
                        "retrieval_lookup_id": "sha256:" + "a" * 64,
                        "upstream_digest": "b" * 64,
                        "evidence_legality_class": "verified",
                    },
                ],
                PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:admin-bind",
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_citation_binding_inspector"
    assert body["gate_id"] == GP08_CITE01_GATE_ID_V1
    assert body["binding"]["evidence_scope_summary"]["citation_count"] == 1
    assert len(body["binding"]["claims"]) == 1


def test_admin_post_citations_bind_omits_uncited_claim(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.post(
        "/admin/catalog/cortex/synthesis/citations/bind",
        auth=("admin", "integration-admin-password"),
        json={
            "retrieval_hits": [
                {
                    "retrieval_lookup_id": "sha256:" + "c" * 64,
                    "upstream_digest": "d" * 64,
                    "evidence_legality_class": "verified",
                },
            ],
            "claim_plan": [
                {
                    "claim_id": "clm-0001",
                    "claim_kind": "temporal_fact",
                    "text": "cited",
                    "citations": ["cite-0000"],
                },
                {
                    "claim_id": "clm-0002",
                    "claim_kind": "causal_link",
                    "text": "uncited",
                    "citations": [],
                },
            ],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["binding"]["evidence_scope_summary"]["omitted_claim_count"] == 1
    assert body["passed"] is False

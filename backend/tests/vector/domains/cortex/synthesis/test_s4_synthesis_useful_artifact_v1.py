"""S4.3 — useful synthesis artifact definition."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_useful_artifact_v1 import (
    FIZZER_V1_PIPELINE_WORKLOAD_V1,
    FIZZER_V1_PRODUCT_WORKLOAD_V1,
    artifact_is_useful_v1,
    count_useful_execution_claims_v1,
    fizzer_v1_pipeline_workloads_v1,
)


def test_fizzer_v1_workload_definition() -> None:
    assert FIZZER_V1_PRODUCT_WORKLOAD_V1 == "execution_continuity_brief"
    assert FIZZER_V1_PIPELINE_WORKLOAD_V1 == "continuity_assessment"
    assert fizzer_v1_pipeline_workloads_v1() == ["continuity_assessment"]


def test_useful_artifact_requires_execution_grounded_claim() -> None:
    body = {
        "artifact_kind": "continuity_assessment",
        "claims": [
            {
                "claim_id": "clm-0001",
                "synthesis_citations": [
                    {
                        "retrieval_lookup_id": "sha256:" + "a" * 64,
                        "source_artifact_kind": "materialization",
                    }
                ],
            }
        ],
    }
    assert count_useful_execution_claims_v1(body) == 1
    assert artifact_is_useful_v1(body_json=body, artifact_kind="continuity_assessment") is True


def test_org_link_only_claim_is_not_useful() -> None:
    body = {
        "artifact_kind": "continuity_assessment",
        "claims": [
            {
                "claim_id": "clm-0002",
                "synthesis_citations": [
                    {
                        "retrieval_lookup_id": "sha256:" + "b" * 64,
                        "source_artifact_kind": "org_link",
                    }
                ],
            }
        ],
    }
    assert count_useful_execution_claims_v1(body) == 0
    assert artifact_is_useful_v1(body_json=body, artifact_kind="continuity_assessment") is False

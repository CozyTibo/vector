"""Wave S3 — retrieval semantic mix gates and orchestration contracts."""

from __future__ import annotations

import inspect

from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
    EXECUTION_INDEX_PCT_MIN_V1,
    ORG_LINK_PCT_MAX_V1,
    validate_retrieval_semantic_mix_v1,
)
def test_validate_mix_passes_execution_heavy_epoch() -> None:
    mix = {
        "entry_count": 100,
        "org_link_pct": 20.0,
        "org_entity_pct": 5.0,
        "execution_index_pct": 75.0,
        "execution_index_count": 75,
        "duplicate_retrieval_lookup_ids": 0,
    }
    ok, violations = validate_retrieval_semantic_mix_v1(mix)
    assert ok is True
    assert violations == []


def test_validate_mix_fails_org_link_heavy() -> None:
    mix = {
        "entry_count": 100,
        "org_link_pct": 90.0,
        "org_entity_pct": 0.0,
        "execution_index_pct": 10.0,
        "execution_index_count": 10,
        "duplicate_retrieval_lookup_ids": 0,
    }
    ok, violations = validate_retrieval_semantic_mix_v1(mix)
    assert ok is False
    assert any("org_link_pct" in v for v in violations)


def test_phase07_runner_handles_semantic_mix_violation() -> None:
    from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
        FAILURE_CODE_SEMANTIC_MIX_V1,
    )
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr

    src = inspect.getsource(pr.run_phase_07_retrieval_v1)
    assert "RetrievalSemanticMixError" in src
    assert FAILURE_CODE_SEMANTIC_MIX_V1 in src or "FAILURE_CODE_SEMANTIC_MIX_V1" in src


def test_finalize_publish_contract_enforces_mix() -> None:
    from vector.domains.cortex.retrieval import retrieval_publish_contract as rpc

    src = inspect.getsource(rpc.finalize_pipeline_retrieval_index_build_v1)
    assert "enforce_retrieval_semantic_mix_before_publish_v1" in src


def test_mix_threshold_constants_match_plan() -> None:
    assert ORG_LINK_PCT_MAX_V1 == 30.0
    assert EXECUTION_INDEX_PCT_MIN_V1 == 60.0

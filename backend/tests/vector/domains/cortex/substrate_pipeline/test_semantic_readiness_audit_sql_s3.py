"""Phase S3.5 — audit SQL schema drift fixes."""

from __future__ import annotations

import inspect


def test_retrieval_epoch_query_uses_build_state_not_published_at_only() -> None:
    from vector.domains.cortex.substrate_pipeline import semantic_readiness_v1 as sr

    src = inspect.getsource(sr._query_retrieval_product_v1)
    assert "build_state = 'PUBLISHED'" in src
    assert "ORDER BY created_at DESC" in src


def test_synthesis_claims_7d_uses_created_at_not_published_at() -> None:
    from vector.domains.cortex.substrate_pipeline import semantic_readiness_v1 as sr

    src = inspect.getsource(sr._query_synthesis_truth_v1)
    assert "published IS TRUE" in src
    assert "created_at >= NOW()" in src
    assert "published_at >=" not in src

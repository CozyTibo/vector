"""Wave S3 step 12 — phase-07 materialization order contract."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_semantic_orchestration_v1 import (
    WAVE_S3_MATERIALIZATION_ORDER_V1,
)


def test_wave_s3_materialization_order_walks_before_org_link() -> None:
    assert WAVE_S3_MATERIALIZATION_ORDER_V1.index("walk") < WAVE_S3_MATERIALIZATION_ORDER_V1.index(
        "org_link"
    )
    assert WAVE_S3_MATERIALIZATION_ORDER_V1.index("canonical_materialization") < (
        WAVE_S3_MATERIALIZATION_ORDER_V1.index("org_link")
    )

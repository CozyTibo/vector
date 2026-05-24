"""S4.4 — execution grounding laws."""

from __future__ import annotations

import pytest

from vector.domains.cortex.synthesis.synthesis_execution_grounding_v1 import (
    FAILURE_CODE_MISSING_EXECUTION_REFS_V1,
    FAILURE_CODE_ORG_LINK_ONLY_SCOPE_V1,
    SynthesisExecutionGroundingError,
    audit_retrieval_hits_execution_mix_v1,
    enforce_execution_grounding_before_llm_v1,
)


class _SessionStub:
    pass


def test_org_link_only_scope_rejected() -> None:
    hits = [
        {"retrieval_lookup_id": "sha256:" + "a" * 64, "source_artifact_kind": "org_link"},
        {"retrieval_lookup_id": "sha256:" + "b" * 64, "index_kind": "org_link"},
    ]
    mix = audit_retrieval_hits_execution_mix_v1(
        _SessionStub(),
        tenant_id=__import__("uuid").uuid4(),
        hits=hits,
        index_epoch="epoch-1",
    )
    assert mix["org_link_only_scope"] is True
    assert mix["has_execution_ref"] is False

    with pytest.raises(SynthesisExecutionGroundingError) as exc:
        enforce_execution_grounding_before_llm_v1(
            _SessionStub(),
            tenant_id=__import__("uuid").uuid4(),
            envelope={"retrieval_pins": {"index_epoch": "epoch-1"}},
            retrieval_hits=hits,
        )
    assert exc.value.code == FAILURE_CODE_ORG_LINK_ONLY_SCOPE_V1


def test_execution_ref_required() -> None:
    hits = [
        {"retrieval_lookup_id": "sha256:" + "c" * 64, "source_artifact_kind": "materialization"},
    ]
    out = enforce_execution_grounding_before_llm_v1(
        _SessionStub(),
        tenant_id=__import__("uuid").uuid4(),
        envelope={"retrieval_pins": {"index_epoch": "epoch-1"}},
        retrieval_hits=hits,
    )
    assert out["ok"] is True


def test_unknown_scope_without_execution_ref_fails() -> None:
    hits = [{"retrieval_lookup_id": "sha256:" + "d" * 64, "index_kind": "discourse_only"}]
    with pytest.raises(SynthesisExecutionGroundingError) as exc:
        enforce_execution_grounding_before_llm_v1(
            _SessionStub(),
            tenant_id=__import__("uuid").uuid4(),
            envelope={"retrieval_pins": {"index_epoch": "epoch-1"}},
            retrieval_hits=hits,
        )
    assert exc.value.code == FAILURE_CODE_MISSING_EXECUTION_REFS_V1

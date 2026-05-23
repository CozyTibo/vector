"""Wave S4 step 19 — synthesis empty-claims gate."""

from __future__ import annotations

import pytest

from vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1 import (
    FAILURE_CODE_EMPTY_CLAIMS_V1,
    SynthesisEmptyClaimsError,
    enforce_empty_claims_before_publish_v1,
    validate_artifact_claims_for_publish_v1,
)


def test_validate_rejects_empty_claims() -> None:
    ok, violations = validate_artifact_claims_for_publish_v1(
        body_json={"claims": []},
        artifact_kind="execution_brief",
    )
    assert ok is False
    assert "claims_empty" in violations


def test_validate_accepts_claim_with_retrieval_lookup() -> None:
    ok, violations = validate_artifact_claims_for_publish_v1(
        body_json={
            "claims": [
                {
                    "claim_text": "Walk completed",
                    "synthesis_citations": [{"retrieval_lookup_id": "sha256:" + "a" * 64}],
                }
            ]
        },
        artifact_kind="execution_brief",
    )
    assert ok is True
    assert violations == []


def test_enforce_raises_when_gate_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.synthesis.synthesis_empty_claims_gate_v1.is_synthesis_empty_claims_gate_enabled_v1",
        lambda: True,
    )
    with pytest.raises(SynthesisEmptyClaimsError) as exc:
        enforce_empty_claims_before_publish_v1(body_json={"claims": []})
    assert exc.value.code == FAILURE_CODE_EMPTY_CLAIMS_V1

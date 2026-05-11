"""Phase 02 Step 11 — progressive trust enforcement semantics."""

from __future__ import annotations

from vector.domains.cortex.ingestion.raw_memory_enforcement import (
    build_enforcement_summary,
    evaluate_progressive_enforcement,
    verify_phase02_step11_progressive_enforcement,
)


def test_progressive_blocks_only_catastrophic() -> None:
    trust = {"trust_state": "corrupted", "state_reason_codes": ["payload_mutation_corruption"]}
    closure = {"summary": {"hard_fails": ["G7"]}}
    out = evaluate_progressive_enforcement(
        trust_annotation=trust,
        phase_closure=closure,
        mode="progressive",
        operation="replay_trigger",
    )
    assert out["risk_tier"] == "catastrophic"
    assert out["blocked"] is True
    assert out["allowed"] is False


def test_progressive_unverifiable_is_warning_not_block() -> None:
    trust = {"trust_state": "unverifiable", "state_reason_codes": ["insufficient_evidence"]}
    out = evaluate_progressive_enforcement(
        trust_annotation=trust,
        phase_closure={},
        mode="progressive",
        operation="memory_query",
    )
    assert out["blocked"] is False
    assert out["would_block"] is True
    assert out["allowed"] is True


def test_step11_verifier_contract_and_determinism() -> None:
    trust = {"trust_state": "healthy", "state_reason_codes": []}
    rep = verify_phase02_step11_progressive_enforcement(
        trust_annotation=trust,
        phase_closure={"summary": {"hard_fails": []}},
        enforcement_mode="progressive",
    )
    assert rep["passed"] is True
    assert rep["summary"]["mode"] == "progressive"
    assert "replay_trigger" in rep["summary"]["decisions"]


def test_enforcement_summary_exposes_would_block_and_readiness() -> None:
    out = build_enforcement_summary(
        trust_annotation={
            "trust_state": "lineage-incomplete",
            "state_reason_codes": ["lineage_gap_detected"],
        },
        phase_closure={"summary": {"hard_fails": []}},
        mode="progressive",
    )
    assert "would_block_operations" in out
    assert "enforcement_readiness" in out
    assert out["enforcement_readiness"]["has_block_paths"] is True

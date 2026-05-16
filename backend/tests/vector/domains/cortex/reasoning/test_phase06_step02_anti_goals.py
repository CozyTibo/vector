"""P06-02 — Anti-goals + forbidden cognition (``reasoning.anti_goals``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.anti_goals import (
    PHASE06_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
    ReasoningCognitionLeakageError,
    list_reasoning_forbidden_cognition_key_violations,
    list_reasoning_package_banned_import_violations,
    validate_reasoning_canonical_json_mapping_no_cognition_leakage,
    verify_gp06_anti01_reasoning_package_static,
    verify_gp06_json_cognition_keys_static,
)


def _repo_root_containing_phase06_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "reasoning" / "phase-06-anti-goals-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/reasoning/ from test file parents.")


def test_phase06_anti_goals_runtime_schema_version() -> None:
    assert PHASE06_ANTI_GOALS_RUNTIME_SCHEMA_VERSION >= 1


def test_rejects_chain_of_thought_key() -> None:
    with pytest.raises(ReasoningCognitionLeakageError, match="chain_of_thought"):
        validate_reasoning_canonical_json_mapping_no_cognition_leakage(
            {"chain_of_thought": "evidence"}
        )


def test_rejects_insight_key_via_octs_union() -> None:
    with pytest.raises(ReasoningCognitionLeakageError, match="insight"):
        validate_reasoning_canonical_json_mapping_no_cognition_leakage({"insight": "x"})


def test_rejects_autonomous_agent_key() -> None:
    with pytest.raises(ReasoningCognitionLeakageError, match="autonomous_agent"):
        validate_reasoning_canonical_json_mapping_no_cognition_leakage({"autonomous_agent": {}})


def test_accepts_legal_reasoning_stub() -> None:
    body = {
        "tcre_policy_pack_id": "ReasoningPolicyPackV1_Default",
        "causal_chain_id": "sha256:aa",
        "chronology_legality_class": "chronology_strict",
    }
    validate_reasoning_canonical_json_mapping_no_cognition_leakage(body)


def test_list_violations_nested_chain_of_thought() -> None:
    bad = {"receipts": {"debug": {"chain_of_thought": "no"}}}
    v = list_reasoning_forbidden_cognition_key_violations(bad)
    assert any("chain_of_thought" in x for x in v)


def test_verify_gp06_anti01_package_scan_passes() -> None:
    out = verify_gp06_anti01_reasoning_package_static()
    assert out["id"] == "G-P06-ANTI-01"
    assert out["passed"] is True
    assert out["detail"]["import_violations"] == []


def test_verify_gp06_json_cognition_static_passes() -> None:
    out = verify_gp06_json_cognition_keys_static()
    assert out["passed"] is True


def test_list_reasoning_package_banned_import_violations_empty_on_clean_tree() -> None:
    assert list_reasoning_package_banned_import_violations() == []


def test_phase06_anti_goals_doctrine_contract_sections() -> None:
    root = _repo_root_containing_phase06_docs()
    text = (root / "DOCS" / "cortex" / "reasoning" / "phase-06-anti-goals-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "## Forbidden capabilities" in text
    assert "## Allowed substrate stance" in text
    assert "## Constitutional boundary" in text
    assert "derivable structure already implicit in evidence" in text

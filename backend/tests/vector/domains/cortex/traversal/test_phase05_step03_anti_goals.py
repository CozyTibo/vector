"""P05-03 — anti-goals / cognition leakage (anti_goals module)."""

from __future__ import annotations

import pytest

from vector.domains.cortex.traversal.anti_goals import (
    ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
    CognitionLeakageError,
    list_forbidden_cognition_key_violations,
    validate_octs_canonical_json_mapping_no_cognition_leakage,
    verify_gp05_anti01_forbidden_cognition_keys_static,
    verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static,
)


def test_anti_goals_runtime_schema_version() -> None:
    assert ANTI_GOALS_RUNTIME_SCHEMA_VERSION >= 1


def test_rejects_insight_key() -> None:
    with pytest.raises(CognitionLeakageError, match="insight"):
        validate_octs_canonical_json_mapping_no_cognition_leakage({"insight": "x"})


def test_rejects_ext_dynamic_key() -> None:
    with pytest.raises(CognitionLeakageError, match="ext_"):
        validate_octs_canonical_json_mapping_no_cognition_leakage({"ext_custom": 1})


def test_rejects_policy_recommendation_smuggling() -> None:
    with pytest.raises(CognitionLeakageError, match="recommendation"):
        validate_octs_canonical_json_mapping_no_cognition_leakage(
            {"policy_recommendation_hint": []}
        )


def test_accepts_legal_diagnostics_shape() -> None:
    body = {
        "diagnostics": {"termination_reason": "budget_exhausted", "edges_visited": 3},
        "hop_receipts": [],
    }
    validate_octs_canonical_json_mapping_no_cognition_leakage(body)


def test_list_violations_nested_path() -> None:
    bad = {"a": {"b": {"summary": "no"}}}
    v = list_forbidden_cognition_key_violations(bad)
    assert any("summary" in x for x in v)


def test_verify_gp05_anti01_static_passes() -> None:
    out = verify_gp05_anti01_forbidden_cognition_keys_static()
    assert out["id"] == "G-P05-ANTI-01"
    assert out["passed"] is True


def test_verify_gp05_anti02_static_passes() -> None:
    out = verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static()
    assert out["id"] == "G-P05-ANTI-02"
    assert out["passed"] is True

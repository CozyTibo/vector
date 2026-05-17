"""P07-02 — Anti-goals + forbidden cognition (``retrieval.anti_goals``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.anti_goals import (
    PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
    RetrievalAntiGoalViolationError,
    RetrievalCognitionLeakageError,
    enforce_retrieval_query_envelope_anti_goals_v1,
    list_retrieval_forbidden_cognition_key_violations,
    list_retrieval_package_banned_import_violations,
    list_retrieval_query_envelope_ingress_violations,
    retrieval_query_envelope_schema_path_v1,
    validate_retrieval_authoritative_output_algebra_v1,
    validate_retrieval_canonical_json_mapping_no_cognition_leakage,
    verify_gp07_anti01_retrieval_package_static,
    verify_gp07_anti02_retrieval_ingress_token_rejection_static,
    verify_gp07_retrieval_json_cognition_keys_static,
    verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static,
    verify_gp07_schema01_schema_file_present_static,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-anti-goals-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_anti_goals_runtime_schema_version() -> None:
    assert PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION >= 1


def test_rejects_embedding_key() -> None:
    with pytest.raises(RetrievalCognitionLeakageError, match=RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1):
        validate_retrieval_canonical_json_mapping_no_cognition_leakage({"embedding": [0.1]})


def test_rejects_summary_key_via_octs_union() -> None:
    with pytest.raises(RetrievalCognitionLeakageError) as exc:
        validate_retrieval_canonical_json_mapping_no_cognition_leakage({"summary": "x"})
    assert exc.value.code == RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1
    assert any("summary" in v for v in exc.value.detail.get("violations", []))


def test_rejects_semantic_search_key() -> None:
    with pytest.raises(RetrievalCognitionLeakageError) as exc:
        validate_retrieval_canonical_json_mapping_no_cognition_leakage({"semantic_search": True})
    assert exc.value.code == RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1
    assert any("semantic_search" in v for v in exc.value.detail.get("violations", []))


def test_accepts_legal_retrieval_stub() -> None:
    body = {
        "retrieval_lookup_id": "sha256:00",
        "retrieval_legality_class": "retrieval_replay_safe",
        "hits": [],
    }
    validate_retrieval_canonical_json_mapping_no_cognition_leakage(body)


def test_enforce_rejects_nl_query_text() -> None:
    with pytest.raises(RetrievalAntiGoalViolationError, match=RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1):
        enforce_retrieval_query_envelope_anti_goals_v1(
            {"query_text": "run a semantic search across teams"}
        )


def test_enforce_accepts_lookup_only_body() -> None:
    enforce_retrieval_query_envelope_anti_goals_v1(
        {"retrieval_lookup_id": "sha256:00", "expected_replay_identity": "rid1"}
    )


def test_authoritative_output_algebra_rejects_smuggled_key() -> None:
    with pytest.raises(RetrievalAntiGoalViolationError, match=RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1):
        validate_retrieval_authoritative_output_algebra_v1(
            {"retrieval_lookup_id": "x", "insight": "forbidden"}
        )


def test_authoritative_output_algebra_allows_engine_shape() -> None:
    validate_retrieval_authoritative_output_algebra_v1(
        {
            "retrieval_lookup_id": "sha256:00",
            "retrieval_legality_class": "retrieval_replay_safe",
            "lineage": {},
            "degradation_envelope": {},
        }
    )


def test_verify_gp07_anti01_package_scan_passes() -> None:
    out = verify_gp07_anti01_retrieval_package_static()
    assert out["id"] == "G-P07-ANTI-01"
    assert out["passed"] is True
    assert out["detail"]["import_violations"] == []


def test_verify_gp07_anti02_ingress_static_passes() -> None:
    out = verify_gp07_anti02_retrieval_ingress_token_rejection_static()
    assert out["passed"] is True


def test_verify_gp07_schema01_forbidden_keys_static_passes() -> None:
    out = verify_gp07_schema01_retrieval_query_envelope_forbidden_keys_static()
    assert out["passed"] is True


def test_verify_gp07_json_cognition_static_passes() -> None:
    out = verify_gp07_retrieval_json_cognition_keys_static()
    assert out["passed"] is True


def test_verify_gp07_schema01_schema_file_present() -> None:
    out = verify_gp07_schema01_schema_file_present_static()
    assert out["passed"] is True
    assert retrieval_query_envelope_schema_path_v1().is_file()


def test_list_retrieval_package_banned_import_violations_empty_on_clean_tree() -> None:
    assert list_retrieval_package_banned_import_violations() == []


def test_list_violations_nested_recommendation() -> None:
    bad = {"selection_policy": {"recommendation": "no"}}
    v = list_retrieval_forbidden_cognition_key_violations(bad)
    assert any("recommendation" in x for x in v)


def test_ingress_violations_embedding_on_envelope() -> None:
    v = list_retrieval_query_envelope_ingress_violations({"embedding": [0.1, 0.2]})
    assert v


def test_phase07_anti_goals_doctrine_contract_sections() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-anti-goals-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "## Constitutional boundary" in text
    assert "## Allowed retrieval outputs" in text
    assert "G‑P07‑ANTI‑01" in text
    assert "G‑P07‑ANTI‑02" in text
    assert "retrieval-query-envelope-v1.schema.json" in text

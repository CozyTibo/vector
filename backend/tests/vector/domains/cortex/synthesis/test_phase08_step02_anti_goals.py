"""P08-02 — Anti-goals + forbidden cognition (``synthesis.anti_goals``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.synthesis.anti_goals import (
    PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1,
    SynthesisAntiGoalViolationError,
    SynthesisCognitionLeakageError,
    enforce_synthesis_job_envelope_anti_goals_v1,
    list_synthesis_forbidden_cognition_key_violations,
    list_synthesis_job_envelope_ingress_violations,
    list_synthesis_package_banned_import_violations,
    synthesis_job_envelope_schema_path_v1,
    validate_synthesis_authoritative_artifact_algebra_v1,
    validate_synthesis_authoritative_job_envelope_algebra_v1,
    validate_synthesis_canonical_json_mapping_no_cognition_leakage,
    verify_gp08_anti01_synthesis_package_static,
    verify_gp08_anti02_synthesis_ingress_token_rejection_static,
    verify_gp08_schema01_schema_file_present_static,
    verify_gp08_schema01_synthesis_job_envelope_forbidden_keys_static,
    verify_gp08_synthesis_json_cognition_keys_static,
)


def _repo_root_containing_phase08_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-anti-goals-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def test_phase08_anti_goals_runtime_schema_version() -> None:
    assert PHASE08_ANTI_GOALS_RUNTIME_SCHEMA_VERSION >= 1


def test_rejects_embedding_key() -> None:
    with pytest.raises(SynthesisCognitionLeakageError, match=SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1):
        validate_synthesis_canonical_json_mapping_no_cognition_leakage({"embedding": [0.1]})


def test_rejects_chat_key() -> None:
    with pytest.raises(SynthesisCognitionLeakageError) as exc:
        validate_synthesis_canonical_json_mapping_no_cognition_leakage({"chat": True})
    assert exc.value.code == SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1
    assert any("chat" in v for v in exc.value.detail.get("violations", []))


def test_rejects_hidden_reasoning_key() -> None:
    with pytest.raises(SynthesisCognitionLeakageError) as exc:
        validate_synthesis_canonical_json_mapping_no_cognition_leakage(
            {"hidden_reasoning": "secret"}
        )
    assert exc.value.code == SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1


def test_accepts_legal_synthesis_stub() -> None:
    body = {
        "artifact_id": "00000000-0000-4000-8000-000000000001",
        "synthesis_legality_class": "synthesis_replay_safe",
        "claims": [],
        "non_authoritative": False,
    }
    validate_synthesis_canonical_json_mapping_no_cognition_leakage(body)


def test_enforce_rejects_nl_query_text() -> None:
    with pytest.raises(SynthesisAntiGoalViolationError, match=SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1):
        enforce_synthesis_job_envelope_anti_goals_v1(
            {"query_text": "run a semantic search across teams"}
        )


def test_enforce_rejects_raw_prompt_override() -> None:
    with pytest.raises(SynthesisAntiGoalViolationError, match=SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1):
        enforce_synthesis_job_envelope_anti_goals_v1(
            {
                "synthesis_prompt_overrides": {
                    "exec_brief_v1": "You are an assistant.\nWrite a summary.",
                }
            }
        )


def test_enforce_accepts_template_variant_override() -> None:
    enforce_synthesis_job_envelope_anti_goals_v1(
        {
            "schema_version": 1,
            "synthesis_workload_class": "pipeline_default",
            "synthesis_intent": "inspect",
            "execution_partition": "authoritative",
            "synthesis_prompt_overrides": {"exec_brief_v1": "variant_pin_a"},
            "retrieval_pins": {"retrieval_lookup_id": "sha256:00"},
        }
    )


def test_authoritative_job_algebra_rejects_smuggled_key() -> None:
    with pytest.raises(SynthesisAntiGoalViolationError, match=SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1):
        validate_synthesis_authoritative_job_envelope_algebra_v1(
            {
                "schema_version": 1,
                "synthesis_workload_class": "pipeline_default",
                "insight": "forbidden",
            }
        )


def test_authoritative_artifact_algebra_rejects_answer_key() -> None:
    with pytest.raises(SynthesisAntiGoalViolationError, match=SYNTHESIS_FORBIDDEN_LEGALITY_CLASS_V1):
        validate_synthesis_authoritative_artifact_algebra_v1(
            {
                "artifact_id": "00000000-0000-4000-8000-000000000001",
                "answer": "forbidden",
            }
        )


def test_authoritative_artifact_algebra_allows_engine_shape() -> None:
    validate_synthesis_authoritative_artifact_algebra_v1(
        {
            "artifact_id": "00000000-0000-4000-8000-000000000001",
            "synthesis_legality_class": "synthesis_replay_safe",
            "claims": [],
            "narrative_blocks": [],
            "non_authoritative": False,
        }
    )


def test_verify_gp08_anti01_package_scan_passes() -> None:
    out = verify_gp08_anti01_synthesis_package_static()
    assert out["id"] == "G-P08-ANTI-01"
    assert out["passed"] is True
    assert out["detail"]["import_violations"] == []


def test_verify_gp08_anti02_ingress_static_passes() -> None:
    out = verify_gp08_anti02_synthesis_ingress_token_rejection_static()
    assert out["passed"] is True


def test_verify_gp08_schema01_forbidden_keys_static_passes() -> None:
    out = verify_gp08_schema01_synthesis_job_envelope_forbidden_keys_static()
    assert out["passed"] is True


def test_verify_gp08_json_cognition_static_passes() -> None:
    out = verify_gp08_synthesis_json_cognition_keys_static()
    assert out["passed"] is True


def test_verify_gp08_schema01_schema_file_present() -> None:
    out = verify_gp08_schema01_schema_file_present_static()
    assert out["passed"] is True
    assert synthesis_job_envelope_schema_path_v1().is_file()


def test_list_synthesis_package_banned_import_violations_empty_on_clean_tree() -> None:
    assert list_synthesis_package_banned_import_violations() == []


def test_ingress_violations_rag_on_envelope() -> None:
    v = list_synthesis_job_envelope_ingress_violations({"rag": True})
    assert v


def test_list_violations_nested_recommendation() -> None:
    bad = {"selection_policy": {"recommendation": "no"}}
    v = list_synthesis_forbidden_cognition_key_violations(bad)
    assert any("recommendation" in x for x in v)


def test_phase08_anti_goals_doctrine_contract_sections() -> None:
    root = _repo_root_containing_phase08_docs()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-anti-goals-doctrine.md").read_text(
        encoding="utf-8",
    )
    assert "## Constitutional anti-goals" in text
    assert "## Forbidden envelope keys" in text
    assert "G-P08-ANTI-01" in text
    assert "G-P08-ANTI-02" in text
    assert "synthesis-job-envelope-v1.schema.json" in text or "Forbidden envelope keys" in text

"""P08-05 — Synthesis workload classes + intent taxonomy (``synthesis.synthesis_job_contract``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
    GP08_SCHEMA01_WORKLOAD_INTENT_GATE_ID_V1,
    PHASE08_SYNTHESIS_JOB_CONTRACT_RUNTIME_SCHEMA_VERSION,
    SYNTHESIS_INTENT_CLASSES_V1,
    SYNTHESIS_WORKLOAD_CLASSES_V1,
    SynthesisJobContractError,
    build_synthesis_job_contract_catalog_v1,
    build_synthesis_job_replay_identity_scope_v1,
    enforce_synthesis_job_workload_and_intent_v1,
    resolve_synthesis_workload_and_intent_v1,
    selection_policy_caps_for_synthesis_workload_v1,
    validate_synthesis_intent_v1,
    validate_synthesis_workload_class_v1,
    verify_gp08_schema01_synthesis_workload_intent_registry_static,
)


def _repo_root_containing_phase08_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-data-contracts.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def test_phase08_synthesis_job_contract_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_JOB_CONTRACT_RUNTIME_SCHEMA_VERSION >= 1


def test_workload_registry_has_eight_classes() -> None:
    assert len(SYNTHESIS_WORKLOAD_CLASSES_V1) == 8
    assert "execution_understanding" in SYNTHESIS_WORKLOAD_CLASSES_V1
    assert "pipeline_default" in SYNTHESIS_WORKLOAD_CLASSES_V1


def test_intent_registry_has_five_intents() -> None:
    assert len(SYNTHESIS_INTENT_CLASSES_V1) == 5
    assert "inspect" in SYNTHESIS_INTENT_CLASSES_V1
    assert "diff" in SYNTHESIS_INTENT_CLASSES_V1


def test_rejects_unknown_workload() -> None:
    with pytest.raises(SynthesisJobContractError, match="unknown_synthesis_workload_class"):
        validate_synthesis_workload_class_v1("chat_summary")


def test_rejects_unknown_intent() -> None:
    with pytest.raises(SynthesisJobContractError, match="unknown_synthesis_intent"):
        validate_synthesis_intent_v1("ask_anything")


def test_replay_equivalence_synthesis_rejects_enumerate_intent() -> None:
    with pytest.raises(SynthesisJobContractError, match="intent_not_allowed_for_synthesis_workload"):
        enforce_synthesis_job_workload_and_intent_v1(
            {
                "synthesis_workload_class": "replay_equivalence_synthesis",
                "synthesis_intent": "enumerate",
            },
        )


def test_execution_understanding_inspect_allowed() -> None:
    wl, it = enforce_synthesis_job_workload_and_intent_v1(
        {
            "synthesis_workload_class": "execution_understanding",
            "synthesis_intent": "inspect",
        },
    )
    assert wl == "execution_understanding"
    assert it == "inspect"


def test_resolve_defaults_for_minimal_admin_body() -> None:
    wl, it = resolve_synthesis_workload_and_intent_v1({})
    assert wl == "pipeline_default"
    assert it == "inspect"


def test_selection_policy_caps_for_degradation_brief() -> None:
    caps = selection_policy_caps_for_synthesis_workload_v1("degradation_brief")
    assert caps["max_claims"] == 64
    assert caps["max_retrieval_subqueries"] == 8


def test_replay_identity_scope_pins_workload_and_intent() -> None:
    scope = build_synthesis_job_replay_identity_scope_v1(
        synthesis_workload_class="operational_synthesis",
        synthesis_intent="audit",
    )
    assert scope["synthesis_workload_class"] == "operational_synthesis"
    assert scope["synthesis_intent"] == "audit"
    assert PHASE08_REPLAY_IDENTITY_FIELD_V1 in scope


def test_job_contract_catalog_rows() -> None:
    cat = build_synthesis_job_contract_catalog_v1()
    assert len(cat["synthesis_workload_classes"]) == 8
    assert len(cat["synthesis_intent_classes"]) == 5
    assert cat["default_synthesis_policy_pack_id"] == DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1


def test_verify_gp08_schema01_static_passes() -> None:
    out = verify_gp08_schema01_synthesis_workload_intent_registry_static()
    assert out["id"] == GP08_SCHEMA01_WORKLOAD_INTENT_GATE_ID_V1
    assert out["passed"] is True


def test_schema_enums_match_runtime_registry() -> None:
    root = _repo_root_containing_phase08_docs()
    schema_path = (
        root / "DOCS" / "cortex" / "synthesis" / "schemas" / "synthesis-job-envelope-v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    wl_enum = set(schema["properties"]["synthesis_workload_class"]["enum"])
    it_enum = set(schema["properties"]["synthesis_intent"]["enum"])
    assert wl_enum == set(SYNTHESIS_WORKLOAD_CLASSES_V1)
    assert it_enum == set(SYNTHESIS_INTENT_CLASSES_V1)

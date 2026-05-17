"""P07-05 — Query workload classes + intent taxonomy (``retrieval.query_contract``)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.query_contract import (
    GP07_QC01_GATE_ID_V1,
    PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_INTENT_CLASSES_V1,
    RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
    RETRIEVAL_WORKLOAD_CLASSES_V1,
    RetrievalQueryContractError,
    build_retrieval_query_contract_catalog_v1,
    build_retrieval_query_replay_identity_scope_v1,
    enforce_retrieval_query_workload_and_intent_v1,
    resolve_retrieval_workload_and_intent_v1,
    selection_policy_caps_for_workload_v1,
    validate_retrieval_intent_v1,
    validate_retrieval_workload_class_v1,
    verify_gp07_qc01_workload_intent_registry_static,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_query_contract_runtime_schema_version() -> None:
    assert PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION >= 1


def test_workload_registry_has_fourteen_classes() -> None:
    assert len(RETRIEVAL_WORKLOAD_CLASSES_V1) == 14
    assert "causal_chain" in RETRIEVAL_WORKLOAD_CLASSES_V1
    assert "materialization_as_of" in RETRIEVAL_WORKLOAD_CLASSES_V1


def test_intent_registry_has_five_intents() -> None:
    assert len(RETRIEVAL_INTENT_CLASSES_V1) == 5
    assert "inspect" in RETRIEVAL_INTENT_CLASSES_V1
    assert "diff" in RETRIEVAL_INTENT_CLASSES_V1


def test_rejects_unknown_workload() -> None:
    with pytest.raises(RetrievalQueryContractError, match="unknown_workload_class"):
        validate_retrieval_workload_class_v1("semantic_search")


def test_rejects_unknown_intent() -> None:
    with pytest.raises(RetrievalQueryContractError, match="unknown_intent"):
        validate_retrieval_intent_v1("ask_anything")


def test_replay_equivalence_rejects_enumerate_intent() -> None:
    with pytest.raises(RetrievalQueryContractError, match="intent_not_allowed_for_workload"):
        enforce_retrieval_query_workload_and_intent_v1(
            {"workload_class": "replay_equivalence", "intent": "enumerate"}
        )


def test_causal_chain_inspect_allowed() -> None:
    wl, it = enforce_retrieval_query_workload_and_intent_v1(
        {"workload_class": "causal_chain", "intent": "inspect"}
    )
    assert wl == "causal_chain"
    assert it == "inspect"


def test_resolve_defaults_for_minimal_admin_body() -> None:
    wl, it = resolve_retrieval_workload_and_intent_v1({})
    assert wl == "causal_chain"
    assert it == "inspect"


def test_selection_policy_caps_for_inspect_workload() -> None:
    caps = selection_policy_caps_for_workload_v1("causal_edge")
    assert caps["max_hits"] == 1


def test_replay_identity_scope_pins_workload_and_intent() -> None:
    scope = build_retrieval_query_replay_identity_scope_v1(
        workload_class="chronology_window",
        intent="audit",
    )
    assert scope["workload_class"] == "chronology_window"
    assert scope["intent"] == "audit"
    assert "retrieval_query_replay_identity" in scope


def test_query_contract_catalog_rows() -> None:
    cat = build_retrieval_query_contract_catalog_v1()
    assert len(cat["workload_classes"]) == 14
    assert len(cat["intent_classes"]) == 5
    assert cat["rd_addressing_unresolved"] == RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1


def test_verify_gp07_qc01_static_passes() -> None:
    out = verify_gp07_qc01_workload_intent_registry_static()
    assert out["id"] == GP07_QC01_GATE_ID_V1
    assert out["passed"] is True


def test_schema_enums_match_runtime_registry() -> None:
    root = _repo_root_containing_phase07_docs()
    schema_path = root / "DOCS" / "cortex" / "retrieval" / "schemas" / "retrieval-query-envelope-v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    wl_enum = set(schema["properties"]["workload_class"]["enum"])
    it_enum = set(schema["properties"]["intent"]["enum"])
    assert wl_enum == set(RETRIEVAL_WORKLOAD_CLASSES_V1)
    assert it_enum == set(RETRIEVAL_INTENT_CLASSES_V1)


def test_doctrine_lists_all_workload_classes() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "## §1 Query workload classes" in text
    assert "## §2 Retrieval intent classes" in text
    assert "G‑P07‑QC‑01" in text or "G-P07-QC-01" in text
    for wl in (
        "execution_continuity",
        "chronology_window",
        "causal_chain",
        "lineage_explorer",
        "materialization_as_of",
    ):
        assert f"`{wl}`" in text

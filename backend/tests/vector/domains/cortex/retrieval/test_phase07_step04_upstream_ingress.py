"""P07-04 — Upstream ingress law (``retrieval.retrieval_ingress``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.retrieval_ingress import (
    PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
    RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1,
    RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1,
    RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1,
    RETRIEVAL_RD_INDEX_STALE_V1,
    RetrievalIngressError,
    build_retrieval_ingress_law_catalog_v1,
    build_retrieval_provenance_inspector_fields_v1,
    classify_retrieval_artifact_kind_provenance_v1,
    enforce_retrieval_ingress_scope_v1,
    validate_retrieval_derived_index_read_v1,
    validate_retrieval_graph_edge_ingress_v1,
    validate_retrieval_index_entry_derived_read_v1,
    validate_retrieval_ingress_artifact_kind_v1,
    verify_gp07_ingress01_observed_derived_partition_static,
    verify_gp07_ingress02_forbidden_artifact_kinds_static,
    verify_gp07_ingress03_derived_index_epoch_static,
    verify_gp07_ingress04_candidate_link_authority_static,
    verify_gp07_ingress_catalog_static,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_ingress_runtime_schema_version() -> None:
    assert PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION >= 1


def test_classify_observed_and_derived_kinds() -> None:
    assert (
        classify_retrieval_artifact_kind_provenance_v1("canonical_materialization")
        == RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1
    )
    assert (
        classify_retrieval_artifact_kind_provenance_v1("retrieval_index")
        == RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1
    )
    assert (
        classify_retrieval_artifact_kind_provenance_v1("llm_cache")
        == RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1
    )


def test_rejects_forbidden_artifact_kind() -> None:
    with pytest.raises(RetrievalIngressError, match="retrieval_ingress_forbidden_artifact"):
        validate_retrieval_ingress_artifact_kind_v1("synthesis_output")


def test_derived_read_requires_index_epoch() -> None:
    with pytest.raises(RetrievalIngressError) as exc:
        validate_retrieval_derived_index_read_v1(
            artifact_kind="retrieval_index", index_epoch=None
        )
    assert exc.value.code == RETRIEVAL_RD_INDEX_STALE_V1


def test_index_row_requires_published_epoch() -> None:
    with pytest.raises(RetrievalIngressError) as exc:
        validate_retrieval_index_entry_derived_read_v1(index_epoch_on_row=None)
    assert exc.value.code == RETRIEVAL_RD_INDEX_STALE_V1


def test_index_row_epoch_mismatch() -> None:
    with pytest.raises(RetrievalIngressError) as exc:
        validate_retrieval_index_entry_derived_read_v1(
            index_epoch_on_row="epoch-a",
            pinned_index_epoch="epoch-b",
        )
    assert exc.value.code == RETRIEVAL_RD_INDEX_STALE_V1


def test_candidate_link_rejected_in_authoritative_partition() -> None:
    with pytest.raises(RetrievalIngressError) as exc:
        validate_retrieval_graph_edge_ingress_v1(
            {"link_authority": "candidate"},
            execution_partition="authoritative",
        )
    assert exc.value.code == RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1


def test_enforce_ingress_scope_rejects_forbidden_read() -> None:
    with pytest.raises(RetrievalIngressError):
        enforce_retrieval_ingress_scope_v1(
            {
                "artifact_reads": [{"artifact_kind": "embedding_table"}],
            }
        )


def test_enforce_ingress_scope_requires_epoch_for_derived() -> None:
    with pytest.raises(RetrievalIngressError) as exc:
        enforce_retrieval_ingress_scope_v1(
            {
                "artifact_reads": [{"artifact_kind": "retrieval_index"}],
            }
        )
    assert exc.value.code == RETRIEVAL_RD_INDEX_STALE_V1


def test_enforce_ingress_scope_accepts_observed_read() -> None:
    enforce_retrieval_ingress_scope_v1(
        {
            "artifact_reads": [{"artifact_kind": "causal_chain"}],
        }
    )


def test_ingress_law_catalog_complete() -> None:
    cat = build_retrieval_ingress_law_catalog_v1()
    assert "raw_record" in cat["observed_artifact_kinds"]
    assert "retrieval_index" in cat["derived_artifact_kinds"]
    assert "llm_cache" in cat["forbidden_artifact_kinds"]
    assert cat["rd_index_stale_code"] == RETRIEVAL_RD_INDEX_STALE_V1
    assert len(cat["ingress_reject_metrics"]) >= 3


def test_provenance_inspector_fields_present() -> None:
    fields = build_retrieval_provenance_inspector_fields_v1()
    assert "artifact_kind" in fields
    assert "index_epoch" in fields
    assert "evidence_legality" in fields


def test_verify_gp07_ingress_static_gates_pass() -> None:
    assert verify_gp07_ingress01_observed_derived_partition_static()["passed"] is True
    assert verify_gp07_ingress02_forbidden_artifact_kinds_static()["passed"] is True
    assert verify_gp07_ingress03_derived_index_epoch_static()["passed"] is True
    assert verify_gp07_ingress04_candidate_link_authority_static()["passed"] is True
    assert verify_gp07_ingress_catalog_static()["passed"] is True


def test_query_contract_doctrine_ingress_section() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "## §Ingress" in text
    assert "Observed:" in text
    assert "Derived:" in text
    assert "LLM caches" in text

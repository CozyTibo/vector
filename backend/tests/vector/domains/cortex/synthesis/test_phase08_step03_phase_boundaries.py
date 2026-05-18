"""P08-03 — Phase boundaries vs Phase 07 / 09 / 10 (``synthesis.phase_boundaries``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.phase_boundaries import (
    PHASE08_BOUNDARIES_RUNTIME_SCHEMA_VERSION,
    SD_PIPELINE_GAP_V1,
    SD_UPSTREAM_LEG_V1,
    SD_UPSTREAM_RD_V1,
    SYN_BND_RULE_IDS_V1,
    SynthesisPhaseBoundaryError,
    build_retrieval_evidence_ingress_v1,
    build_synthesis_phase_boundary_catalog_v1,
    enforce_synthesis_job_retrieval_boundary_v1,
    list_retrieval_package_backward_synthesis_import_violations_v1,
    list_synthesis_package_forward_product_import_violations_v1,
    list_synthesis_package_retrieval_bypass_import_violations_v1,
    map_rd_code_to_sd_code_v1,
    propagate_retrieval_omissions_to_sd_rows_v1,
    validate_synthesis_ingress_from_retrieval_v1,
    validate_synthesis_response_no_phase09_fields_v1,
    verify_gp08_bnd07_retrieval_ingress_static,
    verify_gp08_bnd09_products_boundary_static,
    verify_gp08_bnd_acyclic_dependency_static,
    verify_gp08_bnd_catalog_static,
)


def _repo_root_containing_phase08_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-phase-boundaries-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:test",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


def test_phase08_boundaries_runtime_schema_version() -> None:
    assert PHASE08_BOUNDARIES_RUNTIME_SCHEMA_VERSION >= 1


def test_boundary_catalog_lists_all_syn_bnd_rules() -> None:
    cat = build_synthesis_phase_boundary_catalog_v1()
    assert set(cat["rule_ids"]) == set(SYN_BND_RULE_IDS_V1)
    assert cat["surface_kind"] == "doctrine_catalog"
    assert "SYN-BND-07-01" in cat["rule_ids"]
    assert "SYN-BND-09-01" in cat["rule_ids"]


def test_map_rd_codes_to_sd() -> None:
    assert map_rd_code_to_sd_code_v1("RD-TCRE-GAP") == SD_UPSTREAM_RD_V1
    assert map_rd_code_to_sd_code_v1("RD-REPLAY-UNSAFE") == SD_UPSTREAM_LEG_V1
    assert map_rd_code_to_sd_code_v1("RD-INDEX-STALE") == SD_PIPELINE_GAP_V1
    assert map_rd_code_to_sd_code_v1("RD-CAP-HITS") == SD_UPSTREAM_RD_V1


def test_propagate_retrieval_omissions_to_sd_rows() -> None:
    rows = propagate_retrieval_omissions_to_sd_rows_v1(
        [{"retrieval_omission_class": "RD-TCRE-GAP", "detail": {"x": 1}}],
    )
    assert rows[0]["synthesis_omission_class"] == SD_UPSTREAM_RD_V1
    assert rows[0]["upstream_rd"] == "RD-TCRE-GAP"


def test_job_envelope_rejects_retrieval_bypass_key() -> None:
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        enforce_synthesis_job_retrieval_boundary_v1({"bypass_retrieval_executor": True})
    assert exc.value.rule_id == "SYN-BND-07-01"


def test_ingress_rejects_exploration_retrieval_for_authoritative_job() -> None:
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        validate_synthesis_ingress_from_retrieval_v1(
            {**_legal_retrieval_stub(), "non_authoritative": True},
            job_execution_partition="authoritative",
        )
    assert exc.value.rule_id == "SYN-INGRESS-PAR-01"


def test_ingress_accepts_exploration_pairing() -> None:
    ingress = validate_synthesis_ingress_from_retrieval_v1(
        {**_legal_retrieval_stub(), "non_authoritative": True},
        job_execution_partition="exploration",
        block_authoritative_on_critical_rd=False,
    )
    assert ingress["retrieval_ingress_digest"]


def test_ingress_requires_replay_identity() -> None:
    bad = dict(_legal_retrieval_stub())
    bad.pop(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        validate_synthesis_ingress_from_retrieval_v1(bad)
    assert exc.value.rule_id == "SYN-INGRESS-REP-01"


def test_ingress_requires_hits_array() -> None:
    bad = dict(_legal_retrieval_stub())
    bad.pop("retrieval_evidence_hits")
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        validate_synthesis_ingress_from_retrieval_v1(bad)
    assert exc.value.rule_id == "SYN-INGRESS-HIT-01"


def test_ingress_builds_digest_and_sd_rows() -> None:
    ingress = validate_synthesis_ingress_from_retrieval_v1(
        {
            **_legal_retrieval_stub(),
            "retrieval_omission_rows": [{"retrieval_omission_class": "RD-TCRE-GAP"}],
        },
        block_authoritative_on_critical_rd=False,
    )
    assert len(ingress["retrieval_ingress_digest"]) == 64
    assert ingress["synthesis_omission_rows"][0]["synthesis_omission_class"] == SD_UPSTREAM_RD_V1


def test_ingress_blocks_authoritative_on_critical_sd() -> None:
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        validate_synthesis_ingress_from_retrieval_v1(
            {
                **_legal_retrieval_stub(),
                "retrieval_omission_rows": [{"retrieval_omission_class": "RD-REPLAY-UNSAFE"}],
            },
            job_execution_partition="authoritative",
            block_authoritative_on_critical_rd=True,
        )
    assert exc.value.rule_id == "SYN-BND-07-05"


def test_rejects_phase09_product_fields() -> None:
    with pytest.raises(SynthesisPhaseBoundaryError) as exc:
        validate_synthesis_response_no_phase09_fields_v1({"product_workflow": "wf1"})
    assert exc.value.rule_id == "SYN-BND-09-02"


def test_build_retrieval_evidence_ingress_shape() -> None:
    ingress = build_retrieval_evidence_ingress_v1(_legal_retrieval_stub())
    assert ingress["schema_version"] == 1
    assert "retrieval_legality_copy" in ingress


def test_verify_gp08_bnd07_static_passes() -> None:
    assert verify_gp08_bnd07_retrieval_ingress_static()["passed"] is True


def test_verify_gp08_bnd09_static_passes() -> None:
    assert verify_gp08_bnd09_products_boundary_static()["passed"] is True


def test_verify_gp08_bnd_acyclic_static_passes() -> None:
    assert verify_gp08_bnd_acyclic_dependency_static()["passed"] is True


def test_verify_gp08_bnd_catalog_static_passes() -> None:
    assert verify_gp08_bnd_catalog_static()["passed"] is True


def test_import_acyclic_clean() -> None:
    assert list_synthesis_package_retrieval_bypass_import_violations_v1() == []
    assert list_synthesis_package_forward_product_import_violations_v1() == []
    assert list_retrieval_package_backward_synthesis_import_violations_v1() == []


def test_phase08_boundaries_doctrine_contract_sections() -> None:
    root = _repo_root_containing_phase08_docs()
    text = (
        root / "DOCS" / "cortex" / "synthesis" / "phase-08-phase-boundaries-doctrine.md"
    ).read_text(encoding="utf-8")
    assert "## Phase 08 OWNS" in text
    assert "## Phase 08 DOES NOT OWN" in text
    assert "SYN-BND-07-01" in text
    assert "SYN-BND-09-01" in text
    assert "SYN-BND-10-02" in text

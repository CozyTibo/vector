"""P08-04 — Retrieval evidence ingress law (``synthesis.synthesis_ingress``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.phase_boundaries import SD_UPSTREAM_LEG_V1
from vector.domains.cortex.synthesis.synthesis_ingress import (
    GP08_INGRESS01_GATE_ID_V1,
    PHASE08_INGRESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION,
    SYN_INGRESS_ALG01_V1,
    SYN_INGRESS_HIT01_V1,
    SYN_INGRESS_LEG01_V1,
    SYN_INGRESS_PAR01_V1,
    SYN_INGRESS_POL01_V1,
    SYN_INGRESS_REP01_V1,
    SynthesisIngressError,
    build_retrieval_evidence_ingress_v1,
    build_synthesis_ingress_inspector_v1,
    build_synthesis_ingress_law_catalog_v1,
    collect_synthesis_ingress_gate_results_v1,
    compute_retrieval_ingress_digest_v1,
    enforce_retrieval_evidence_ingress_v1,
    list_synthesis_ingress_algebra_violations_v1,
    list_synthesis_ingress_policy_digest_violations_v1,
    validate_retrieval_evidence_ingress_v1,
    verify_gp08_ingress01_retrieval_evidence_ingress_static,
)


def _repo_root_containing_phase08_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-data-contracts.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/synthesis/ from test file parents.")


def _legal_retrieval_stub() -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:test",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }


def test_phase08_ingress_runtime_schema_version() -> None:
    assert PHASE08_INGRESS_RUNTIME_SCHEMA_VERSION >= 1
    assert RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION == 1


def test_ingress_catalog_lists_all_gates() -> None:
    cat = build_synthesis_ingress_law_catalog_v1()
    assert cat["surface_kind"] == "doctrine_catalog"
    assert cat["gp08_ingress_gate_id"] == GP08_INGRESS01_GATE_ID_V1
    assert SYN_INGRESS_REP01_V1 in cat["gate_ids"]


def test_validate_accepts_legal_retrieval_response() -> None:
    ingress = validate_retrieval_evidence_ingress_v1(_legal_retrieval_stub())
    assert ingress["schema_version"] == RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION
    assert len(ingress["retrieval_ingress_digest"]) == 64


def test_rejects_missing_replay_identity() -> None:
    bad = dict(_legal_retrieval_stub())
    bad.pop(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(bad)
    assert exc.value.gate_id == SYN_INGRESS_REP01_V1


def test_rejects_exploration_for_authoritative_job() -> None:
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(
            {**_legal_retrieval_stub(), "non_authoritative": True},
            job_execution_partition="authoritative",
        )
    assert exc.value.gate_id == SYN_INGRESS_PAR01_V1


def test_rejects_missing_hits_array() -> None:
    bad = dict(_legal_retrieval_stub())
    bad.pop("retrieval_evidence_hits")
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(bad)
    assert exc.value.gate_id == SYN_INGRESS_HIT01_V1


def test_rejects_unverifiable_for_authoritative() -> None:
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(
            {**_legal_retrieval_stub(), "retrieval_legality_class": "retrieval_unverifiable"},
            job_execution_partition="authoritative",
        )
    assert exc.value.gate_id == SYN_INGRESS_LEG01_V1


def test_rejects_algebra_smuggled_key() -> None:
    bad = {**_legal_retrieval_stub(), "insight": "forbidden"}
    v = list_synthesis_ingress_algebra_violations_v1(bad)
    assert v
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(bad)
    assert exc.value.gate_id == SYN_INGRESS_ALG01_V1


def test_policy_digest_mismatch() -> None:
    job = {
        "execution_partition": "authoritative",
        "retrieval_pins": {"retrieval_policy_pack_digest": "sha256:deadbeef"},
    }
    v = list_synthesis_ingress_policy_digest_violations_v1(_legal_retrieval_stub(), job_envelope=job)
    assert v
    with pytest.raises(SynthesisIngressError) as exc:
        validate_retrieval_evidence_ingress_v1(_legal_retrieval_stub(), job_envelope=job)
    assert exc.value.gate_id == SYN_INGRESS_POL01_V1


def test_propagates_rd_to_sd_on_ingress_build() -> None:
    ingress = build_retrieval_evidence_ingress_v1(
        {
            **_legal_retrieval_stub(),
            "retrieval_omission_rows": [{"retrieval_omission_class": "RD-REPLAY-UNSAFE"}],
        },
    )
    assert ingress["synthesis_omission_rows"][0]["synthesis_omission_class"] == SD_UPSTREAM_LEG_V1
    assert ingress["upstream_sd_legality_floor"] == SD_UPSTREAM_LEG_V1


def test_compute_digest_is_stable_for_same_body() -> None:
    ingress = build_retrieval_evidence_ingress_v1(_legal_retrieval_stub())
    d1 = compute_retrieval_ingress_digest_v1(ingress)
    d2 = compute_retrieval_ingress_digest_v1(ingress)
    assert d1 == d2


def test_enforce_is_alias_for_validate() -> None:
    ingress = enforce_retrieval_evidence_ingress_v1(_legal_retrieval_stub())
    assert ingress["retrieval_evidence_hit_count"] == 0


def test_inspector_pass_and_fail() -> None:
    ok = build_synthesis_ingress_inspector_v1(_legal_retrieval_stub())
    assert ok["ingress_passed"] is True
    assert ok["retrieval_evidence_ingress"] is not None

    bad = build_synthesis_ingress_inspector_v1(
        {**_legal_retrieval_stub(), "non_authoritative": True},
        job_execution_partition="authoritative",
    )
    assert bad["ingress_passed"] is False
    assert bad["surface_kind"] == "verification_probe"


def test_collect_gate_results_all_pass_on_legal() -> None:
    _, violations = collect_synthesis_ingress_gate_results_v1(_legal_retrieval_stub())
    assert violations == []


def test_verify_gp08_ingress01_static_passes() -> None:
    out = verify_gp08_ingress01_retrieval_evidence_ingress_static()
    assert out["id"] == GP08_INGRESS01_GATE_ID_V1
    assert out["passed"] is True


def test_phase08_data_contracts_ingress_section() -> None:
    root = _repo_root_containing_phase08_docs()
    text = (root / "DOCS" / "cortex" / "synthesis" / "phase-08-data-contracts.md").read_text(
        encoding="utf-8",
    )
    assert "## §Ingress — RetrievalEvidenceIngressV1" in text
    assert "SYN-INGRESS-LEG-01" in text
    assert "SYN-INGRESS-POL-01" in text

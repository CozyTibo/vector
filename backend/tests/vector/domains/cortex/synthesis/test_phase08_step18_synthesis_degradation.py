"""Phase 08 Step 18 — synthesis degradation taxonomy propagation."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
from vector.domains.cortex.synthesis.phase_boundaries import SD_UPSTREAM_RD_V1
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SD_CITE_GAP_V1,
    SD_REPLAY_TWIN_V1,
    SYNTHESIS_SD_CODES_REGISTRY_V1,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    GP08_DEG02_GATE_ID_V1,
    PHASE08_SYNTHESIS_DEGRADATION_RUNTIME_SCHEMA_VERSION,
    SynthesisDegradationError,
    apply_synthesis_degradation_taxonomy_v1,
    apply_synthesis_degradation_to_artifact_v1,
    build_rd_to_sd_propagation_matrix_v1,
    build_synthesis_degradation_topology_catalog_v1,
    build_synthesis_sd_rollup_v1,
    map_rd_to_sd_via_matrix_v1,
    propagate_rd_omissions_via_matrix_v1,
    validate_synthesis_sd_multiset_monotonic_extension_v1,
    verify_gp08_deg02_artifact_taxonomy_apply_static,
    verify_gp08_deg02_rd_to_sd_matrix_static,
    verify_gp08_deg02_sd_multiset_monotonic_static,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-failure-degradation-taxonomy.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    user = User(email=f"p8deg18-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Deg18")
    tenant = Tenant(
        company_name="P8DEG18",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8deg18-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _retrieval_stub(*, rd_rows: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "retrieval_legality_class": "retrieval_degraded",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid-deg18",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": rd_rows or [{"retrieval_omission_class": "RD-TCRE-GAP"}],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_degradation_rollup": {"rd_code_counts": {"RD-TCRE-GAP": 1}},
    }


@pytest.mark.parametrize(
    "verifier",
    [
        verify_gp08_deg02_rd_to_sd_matrix_static,
        verify_gp08_deg02_sd_multiset_monotonic_static,
        verify_gp08_deg02_artifact_taxonomy_apply_static,
    ],
)
def test_gp08_deg02_static_gates(verifier: Callable[[], dict[str, Any]]) -> None:
    out = verifier()
    assert out["passed"] is True
    assert out["id"] == GP08_DEG02_GATE_ID_V1


def test_runtime_schema_version() -> None:
    assert PHASE08_SYNTHESIS_DEGRADATION_RUNTIME_SCHEMA_VERSION >= 1


def test_propagation_matrix_covers_doctrine_pairs() -> None:
    matrix = build_rd_to_sd_propagation_matrix_v1()
    by_rd = {row["rd_code"]: row["sd_code"] for row in matrix}
    assert by_rd["RD-REPLAY-TWIN"] == SD_REPLAY_TWIN_V1
    assert by_rd["RD-TCRE-GAP"] == SD_UPSTREAM_RD_V1
    for sd in by_rd.values():
        assert sd in SYNTHESIS_SD_CODES_REGISTRY_V1


def test_propagate_rd_rows_to_sd() -> None:
    rows = propagate_rd_omissions_via_matrix_v1(
        [
            {"retrieval_omission_class": "RD-REPLAY-UNSAFE"},
            {"retrieval_omission_class": "RD-INDEX-STALE"},
        ],
    )
    codes = {r["synthesis_omission_class"] for r in rows}
    assert "SD-UPSTREAM-LEG" in codes
    assert "SD-PIPELINE-GAP" in codes


def test_map_rd_to_sd_via_matrix() -> None:
    assert map_rd_to_sd_via_matrix_v1("RD-REPLAY-TWIN") == SD_REPLAY_TWIN_V1
    assert map_rd_to_sd_via_matrix_v1("RD-UNKNOWN") == SD_UPSTREAM_RD_V1


def test_sd_multiset_monotonicity() -> None:
    before = [{"sd_code": SD_CITE_GAP_V1}]
    after = before + [{"sd_code": SD_UPSTREAM_RD_V1}]
    validate_synthesis_sd_multiset_monotonic_extension_v1(before, after)
    with pytest.raises(SynthesisDegradationError, match="sd_multiset_regression"):
        validate_synthesis_sd_multiset_monotonic_extension_v1(after, before)


def test_sd_rollup_shape() -> None:
    rollup = build_synthesis_sd_rollup_v1(
        [{"sd_code": SD_CITE_GAP_V1}, {"sd_code": SD_CITE_GAP_V1}],
    )
    assert rollup["sd_code_counts"][SD_CITE_GAP_V1] == 2
    assert rollup["synthesis_degradation_posture"] == "degraded"


def test_topology_catalog() -> None:
    cat = build_synthesis_degradation_topology_catalog_v1(tenant_id="t1")
    assert cat["surface_kind"] == "synthesis_degradation_topology"
    assert cat["tenant_id"] == "t1"
    assert len(cat["rd_to_sd_propagation_matrix"]) >= 4


def test_doctrine_present() -> None:
    text = (_repo_root() / "DOCS/cortex/synthesis/phase-08-failure-degradation-taxonomy.md").read_text(
        encoding="utf-8",
    )
    assert "apply_synthesis_degradation_taxonomy_v1" in text
    assert "SD-UPSTREAM-RD" in text


@pytest.mark.integration
def test_orchestrator_artifact_persists_degradation_rollup(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "retrieval_pins": {},
        "pinned_retrieval_receipt": {"retrieval_response": _retrieval_stub()},
    }
    out = execute_synthesis_job_envelope_v1(db_session, tenant_id=tenant_id, body=body)
    art = db_session.get(CortexSynthesisArtifact, uuid.UUID(str(out["artifact_id"])))
    assert art is not None
    rollup = art.body_json.get("synthesis_degradation_rollup")
    assert isinstance(rollup, dict)
    assert SD_UPSTREAM_RD_V1 in (rollup.get("sd_codes_sorted") or [])
    assert rollup.get("synthesis_degradation_posture") in {"degraded", "critical", "unresolved"}


def test_apply_taxonomy_merges_upstream_rollup() -> None:
    tax = apply_synthesis_degradation_taxonomy_v1(
        synthesis_omission_rows=[{"sd_code": SD_CITE_GAP_V1}],
        retrieval_ingress=_retrieval_stub(),
        synthesis_legality_class="synthesis_degraded",
        synthesis_workload_class="degradation_brief",
    )
    assert tax["upstream_rollup"].get("rd_code_counts")
    assert SD_UPSTREAM_RD_V1 in tax["sd_codes_sorted"]


def test_apply_to_artifact_preserves_claims_with_omitted_reason() -> None:
    artifact = {
        "synthesis_legality_class": "synthesis_degraded",
        "synthesis_omission_rows": [],
        "claims": [
            {
                "claim_kind": "observation",
                "omitted_reason": SD_CITE_GAP_V1,
            },
        ],
    }
    out = apply_synthesis_degradation_to_artifact_v1(
        artifact,
        retrieval_ingress=_retrieval_stub(rd_rows=[{"retrieval_omission_class": "RD-REPLAY-TWIN"}]),
    )
    codes = {r["synthesis_omission_class"] for r in out["synthesis_omission_rows"]}
    assert SD_REPLAY_TWIN_V1 in codes
    assert out["claims"][0].get("omitted_reason") == SD_CITE_GAP_V1

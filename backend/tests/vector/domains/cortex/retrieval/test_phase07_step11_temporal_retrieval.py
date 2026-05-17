"""P07-11 — Temporal retrieval model (``retrieval.retrieval_temporal``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_temporal import (
    GP07_TEMP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1,
    RETRIEVAL_RD_TEMPORAL_FUTURE_V1,
    RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1,
    RetrievalTemporalError,
    apply_retrieval_temporal_law_to_query_v1,
    apply_skew_copy_through_to_hits_v1,
    artifact_valid_at_t_as_of_v1,
    assess_temporal_legality_envelope_v1,
    build_retrieval_temporal_explorer_catalog_v1,
    list_ret_temp02_pin_violations_v1,
    list_ret_temp03_future_materialization_omissions_v1,
    normalize_retrieval_temporal_scope_v1,
    validate_retrieval_temporal_scope_v1,
    verify_gp07_temp01_temporal_scope_schema_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-temporal-retrieval-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_temporal_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION >= 1


def test_normalize_temporal_scope_sorted_and_versioned() -> None:
    scope = normalize_retrieval_temporal_scope_v1(
        {"replay_epoch": "e1", "t_as_of_unix_ns": 100}
    )
    assert scope["schema_version"] == 1
    assert scope["t_as_of_unix_ns"] == 100
    assert scope["replay_epoch"] == "e1"


def test_invalid_window_raises() -> None:
    scope = normalize_retrieval_temporal_scope_v1(
        {"window_start_ns": 50, "window_end_ns": 10}
    )
    with pytest.raises(RetrievalTemporalError, match="temporal_scope_invalid_window"):
        validate_retrieval_temporal_scope_v1(scope, workload_class="causal_chain")


def test_chronology_window_requires_window() -> None:
    scope = normalize_retrieval_temporal_scope_v1({})
    with pytest.raises(RetrievalTemporalError, match="temporal_scope_missing_window"):
        validate_retrieval_temporal_scope_v1(scope, workload_class="chronology_window")


def test_ret_temp03_future_omission() -> None:
    rows = list_ret_temp03_future_materialization_omissions_v1(
        temporal_scope={"t_as_of_unix_ns": 100},
        artifact_ref={"materialization_observed_at_unix_ns": 200},
    )
    assert len(rows) == 1
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_TEMPORAL_FUTURE_V1
    assert rows[0]["omission_semantics"] == RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1


def test_ret_temp01_valid_at_selection() -> None:
    assert artifact_valid_at_t_as_of_v1(t_as_of_unix_ns=100, artifact_observed_at_unix_ns=50)
    assert not artifact_valid_at_t_as_of_v1(t_as_of_unix_ns=100, artifact_observed_at_unix_ns=150)


def test_ret_temp02_pin_violation() -> None:
    rows = list_ret_temp02_pin_violations_v1(
        {},
        workload_class="causal_chain",
        temporal_scope={"t_as_of_unix_ns": 1},
    )
    assert len(rows) == 1


def test_skew_copy_through() -> None:
    hits = apply_skew_copy_through_to_hits_v1(
        [{"provenance": {"evidence_legality_class": "evidence_authoritative"}}],
        skew_flags=["clock_skew_detected"],
    )
    assert hits[0]["provenance"]["skew_flags"] == ["clock_skew_detected"]
    assert hits[0]["provenance"]["skew_copy_through"] is True


def test_temporal_legality_envelope() -> None:
    env = assess_temporal_legality_envelope_v1(
        chronology_legality_classes=["strict"],
        replay_conflict=False,
    )
    assert env["temporal_legality_floor"] == "retrieval_replay_safe"
    degraded = assess_temporal_legality_envelope_v1(
        chronology_legality_classes=["chronology_degraded"],
    )
    assert degraded["temporal_legality_floor"] == "retrieval_degraded"


def test_gp07_temp01_static_gate() -> None:
    out = verify_gp07_temp01_temporal_scope_schema_static()
    assert out["passed"] is True
    assert out["id"] == GP07_TEMP01_GATE_ID_V1


def test_temporal_explorer_catalog() -> None:
    cat = build_retrieval_temporal_explorer_catalog_v1()
    assert cat["gate_id"] == GP07_TEMP01_GATE_ID_V1
    assert set(cat["temporal_scope_fields"]) == set(RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1)


def test_doctrine_file_present() -> None:
    text = (
        _repo_root() / "DOCS" / "cortex" / "retrieval" / "phase-07-temporal-retrieval-doctrine.md"
    ).read_text(encoding="utf-8")
    assert "RET-TEMP-01" in text or "RET‑TEMP‑01" in text
    assert "temporal_scope_v1" in text


def test_apply_temporal_law_on_row_stub() -> None:
    class _Row:
        chronology_legality_class = "strict"
        causal_legality_class = "verified"
        artifact_ref_json = {
            "causal_chain_id": "c1",
            "materialization_observed_at_unix_ns": 999,
        }
        omission_summary = {"skew_flags": ["export_skew"]}

    result = apply_retrieval_temporal_law_to_query_v1(
        envelope={"workload_class": "causal_chain", "upstream_triggers": {}},
        temporal_scope=normalize_retrieval_temporal_scope_v1({"t_as_of_unix_ns": 100}),
        row=_Row(),
        hits=[{"provenance": {}}],
        omissions=[],
        replay_pins={"tcre_policy_bundle_digest": "sha256:policy"},
    )
    assert result["temporal_skew_audit"]["skew_flags"] == ["export_skew"]
    assert any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_TEMPORAL_FUTURE_V1
        for o in result["omissions"]
    )


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7temp-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Temp")
    tenant = Tenant(
        company_name="P7TEMP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7temp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_execution_emits_temporal_envelope(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain = f"chain-{uuid.uuid4().hex[:8]}"
    index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain,
        replay_identity=replay,
        traversal_epoch="epoch-1",
        artifact_ref={
            "causal_chain_id": chain,
            "materialization_observed_at_unix_ns": 999_999,
        },
        omission_summary={"skew_flags": ["anchor_skew"]},
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "addressing": {"causal_chain_id": chain},
            "temporal_scope": {"t_as_of_unix_ns": 100},
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": "epoch-1",
                "tcre_policy_bundle_digest": "sha256:policy",
            },
        },
    )
    assert "temporal_legality_envelope" in out
    assert "temporal_skew_audit" in out
    assert out["temporal_scope"]["t_as_of_unix_ns"] == 100
    assert out["temporal_skew_audit"]["skew_flags"] == ["anchor_skew"]
    future_rows = [
        o
        for o in out.get("retrieval_omission_rows") or out.get("omissions") or []
        if o.get("retrieval_omission_class") == RETRIEVAL_RD_TEMPORAL_FUTURE_V1
    ]
    assert len(future_rows) >= 1

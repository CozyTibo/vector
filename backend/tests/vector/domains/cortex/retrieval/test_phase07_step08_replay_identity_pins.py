"""P07-08 — Query replay identity + pins (``retrieval.retrieval_replay_equivalence``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_legality_projection import retrieval_policy_digest_v1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    GP07_REPLAY_01_GATE_ID_V1,
    PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_POLICY_MISMATCH_V1,
    RetrievalReplayEquivalenceError,
    build_retrieval_query_replay_pins_v1,
    build_retrieval_replay_equivalence_twin_diff_v1,
    build_retrieval_replay_inspector_catalog_v1,
    compare_gp07_replay_01_double_run_v1,
    compute_retrieval_query_replay_identity_v1,
    enforce_retrieval_replay_pins_authoritative_v1,
    hash_retrieval_query_replay_identity_v1,
    list_retrieval_replay_pin_violations_v1,
    normalize_retrieval_omission_multiset_v1,
    verify_gp07_replay_01_canonical_identity_stable_static,
    verify_gp07_replay_01_double_run_match_static,
    verify_gp07_replay_01_policy_pin_mismatch_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-replay-equivalence-retrieval-spec.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def test_phase07_replay_equivalence_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION >= 1


def test_replay_identity_is_deterministic_sha256() -> None:
    digest = retrieval_policy_digest_v1()
    env = {
        "schema_version": 1,
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"retrieval_lookup_id": "sha256:01"},
    }
    hits = [{"retrieval_lookup_id": "sha256:01", "upstream_digest": "a" * 64}]
    id_a = compute_retrieval_query_replay_identity_v1(
        envelope=env,
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=[],
    )
    id_b = compute_retrieval_query_replay_identity_v1(
        envelope=env,
        retrieval_policy_digest=digest,
        hits=hits,
        omissions=[],
    )
    assert id_a == id_b
    assert len(id_a) == 64


def test_policy_pin_mismatch_emits_rd_code() -> None:
    actual = retrieval_policy_digest_v1()
    rows = list_retrieval_replay_pin_violations_v1(
        {"retrieval_policy_digest": "f" * 64},
        actual_policy_digest=actual,
        execution_partition="authoritative",
    )
    assert len(rows) == 1
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_POLICY_MISMATCH_V1


def test_enforce_policy_pin_raises() -> None:
    with pytest.raises(RetrievalReplayEquivalenceError, match=RETRIEVAL_RD_POLICY_MISMATCH_V1):
        enforce_retrieval_replay_pins_authoritative_v1(
            {"retrieval_policy_digest": "f" * 64},
            actual_policy_digest=retrieval_policy_digest_v1(),
            execution_partition="authoritative",
        )


def test_gp07_replay_01_double_run_compare() -> None:
    identity = hash_retrieval_query_replay_identity_v1({"x": 1})
    base = {
        PHASE07_REPLAY_IDENTITY_FIELD_V1: identity,
        "retrieval_query_receipt": {"receipt_digest": "b" * 64},
        "hits": [],
        "omissions": [],
    }
    compare_gp07_replay_01_double_run_v1(base, dict(base))


def test_twin_diff_detects_mismatch() -> None:
    a = {
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "a" * 64,
        "retrieval_query_receipt": {"receipt_digest": "b" * 64},
        "hits": [{"retrieval_lookup_id": "x", "upstream_digest": "c" * 64}],
        "omissions": [],
    }
    b = dict(a)
    b[PHASE07_REPLAY_IDENTITY_FIELD_V1] = "d" * 64
    diff = build_retrieval_replay_equivalence_twin_diff_v1(a, b)
    assert diff["gp07_replay_01_passed"] is False
    assert diff["receipt_digest_a"] == "b" * 64


def test_replay_pins_builder_includes_required_fields() -> None:
    pins = build_retrieval_query_replay_pins_v1(
        workload_class="causal_chain",
        intent="prove",
        tenant_id="00000000-0000-0000-0000-000000000001",
        replay_pins={"index_epoch": "e1"},
    )
    assert "replay_pins" in pins
    assert "required_pin_fields" in pins


def test_verify_gp07_replay_01_static_gates_pass() -> None:
    for fn in (
        verify_gp07_replay_01_canonical_identity_stable_static,
        verify_gp07_replay_01_double_run_match_static,
        verify_gp07_replay_01_policy_pin_mismatch_static,
    ):
        out = fn()
        assert out["id"] == GP07_REPLAY_01_GATE_ID_V1
        assert out["passed"] is True


def test_doctrine_replay_spec_present() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (
        root / "DOCS" / "cortex" / "retrieval" / "phase-07-replay-equivalence-retrieval-spec.md"
    ).read_text(encoding="utf-8")
    assert "retrieval_query_replay_identity" in text
    assert "G-P07-REPLAY-01" in text or "G‑P07‑REPLAY‑01" in text


def test_inspector_catalog_shape() -> None:
    cat = build_retrieval_replay_inspector_catalog_v1(tenant_id="t1")
    assert cat["gate_id"] == GP07_REPLAY_01_GATE_ID_V1
    assert cat["replay_identity_field"] == PHASE07_REPLAY_IDENTITY_FIELD_V1
    assert "retrieval_replay_divergence_total" in cat


def test_omission_multiset_sort_stable() -> None:
    rows = [
        {"retrieval_omission_class": "RD-B", "upstream_trigger": "z"},
        {"retrieval_omission_class": "RD-A", "upstream_trigger": "a"},
    ]
    assert normalize_retrieval_omission_multiset_v1(rows) == [["RD-A", "a"], ["RD-B", "z"]]


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7rep-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Rep User")
    tenant = Tenant(
        company_name="P7REP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7rep-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_query_response_includes_replay_identity(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-published",
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        retrieval_lookup_id=row.retrieval_lookup_id,
        expected_replay_identity=replay,
        envelope_body={
            "replay_pins": {
                "index_epoch": "epoch-published",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
            },
        },
    )
    assert PHASE07_REPLAY_IDENTITY_FIELD_V1 in out
    assert len(str(out[PHASE07_REPLAY_IDENTITY_FIELD_V1])) == 64
    receipt = out["retrieval_query_receipt"]
    assert receipt["receipt_body"].get(PHASE07_REPLAY_IDENTITY_FIELD_V1) == out[
        PHASE07_REPLAY_IDENTITY_FIELD_V1
    ]


@pytest.mark.integration
def test_replay_equivalence_twin_workload(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-twin",
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "replay_equivalence",
            "intent": "prove",
            "addressing": {"retrieval_lookup_id": row.retrieval_lookup_id},
            "replay_pins": {
                "index_epoch": "epoch-twin",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
        },
    )
    twin = out.get("replay_equivalence_twin")
    assert isinstance(twin, dict)
    assert twin.get("gp07_replay_01_passed") is True
    assert twin.get("hit_count_mismatch") is False

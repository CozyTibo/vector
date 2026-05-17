"""P07-06 — Lawful query envelope + execution FSM (``retrieval.query_execution``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.query_contract import (
    RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
    RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
)
from vector.domains.cortex.retrieval.query_execution import (
    PHASE07_QUERY_EXECUTION_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1,
    RETRIEVAL_QUERY_EXECUTION_PHASES_V1,
    RETRIEVAL_QUERY_RECEIPT_SCHEMA_VERSION_V1,
    RetrievalQueryExecutionError,
    addressing_has_resolvable_ref_v1,
    build_retrieval_query_receipt_v1,
    coerce_body_to_retrieval_query_envelope_v1,
    execute_retrieval_query_envelope_v1,
    normalize_retrieval_query_envelope_v1,
    resolve_retrieval_lookup_id_from_addressing_v1,
    run_retrieval_r_leg_precheck_v1,
    verify_gp07_qc02_addressing_resolution_static,
    verify_gp07_qc03_fsm_phase_order_static,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root_containing_phase07_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md"
        if marker.is_file():
            return root
    pytest.fail("Could not locate DOCS/cortex/retrieval/ from test file parents.")


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7qe-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 QE User")
    tenant = Tenant(
        company_name="P7QE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7qe-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_phase07_query_execution_runtime_schema_version() -> None:
    assert PHASE07_QUERY_EXECUTION_RUNTIME_SCHEMA_VERSION >= 1


def test_fsm_phases_match_doctrine_order() -> None:
    assert RETRIEVAL_QUERY_EXECUTION_PHASES_V1 == (
        "VALIDATE",
        "RESOLVE",
        "BOUND",
        "PROVENANCE",
        "CLASSIFY",
        "RECEIPT",
    )


def test_addressing_unresolved_rejects_empty_addressing() -> None:
    tid = uuid.UUID(int=0)
    with pytest.raises(RetrievalQueryExecutionError) as exc:
        normalize_retrieval_query_envelope_v1(
            {
                "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
                "tenant_id": str(tid),
                "workload_class": "causal_chain",
                "intent": "inspect",
                "addressing": {},
            },
            tenant_id=tid,
        )
    assert exc.value.code == RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1
    assert exc.value.detail.get("rd_code") == RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1


def test_audit_intent_allows_unresolved_addressing() -> None:
    tid = uuid.UUID(int=0)
    env = normalize_retrieval_query_envelope_v1(
        {
            "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
            "tenant_id": str(tid),
            "workload_class": "causal_chain",
            "intent": "audit",
            "addressing": {},
        },
        tenant_id=tid,
    )
    assert env["intent"] == "audit"
    assert not addressing_has_resolvable_ref_v1(env["addressing"])


def test_resolve_lookup_from_addressing() -> None:
    tid = uuid.UUID(int=0)
    env = normalize_retrieval_query_envelope_v1(
        {
            "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
            "tenant_id": str(tid),
            "workload_class": "causal_chain",
            "intent": "inspect",
            "addressing": {"retrieval_lookup_id": "sha256:deadbeef"},
        },
        tenant_id=tid,
    )
    assert resolve_retrieval_lookup_id_from_addressing_v1(env) == "sha256:deadbeef"


def test_coerce_minimal_admin_body() -> None:
    tid = uuid.UUID(int=1)
    env = coerce_body_to_retrieval_query_envelope_v1(
        {"retrieval_lookup_id": "sha256:00"},
        tenant_id=tid,
    )
    assert env["workload_class"] == "causal_chain"
    assert env["intent"] == "inspect"
    assert env["addressing"]["retrieval_lookup_id"] == "sha256:00"


def test_r_leg_precheck_snapshot_keys() -> None:
    env = {
        "workload_class": "causal_chain",
        "intent": "inspect",
        "addressing": {"retrieval_lookup_id": "x"},
        "replay_pins": {},
        "upstream_triggers": {},
    }
    snap = run_retrieval_r_leg_precheck_v1(env)
    assert set(snap) == {
        "R-LEG-01",
        "R-LEG-02",
        "R-LEG-03",
        "R-LEG-04",
        "R-LEG-05",
        "R-LEG-06",
        "R-LEG-07",
    }
    assert snap["R-LEG-01"] is True


def test_receipt_digest_stable() -> None:
    tid = uuid.UUID(int=2)
    env = {
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
    }
    trace = [{"phase": p} for p in RETRIEVAL_QUERY_EXECUTION_PHASES_V1[:-1]]
    r1 = build_retrieval_query_receipt_v1(
        tenant_id=tid,
        envelope=env,
        retrieval_lookup_id="sha256:aa",
        retrieval_legality_class="retrieval_replay_safe",
        execution_trace=trace,
        replay_posture="stable",
    )
    r2 = build_retrieval_query_receipt_v1(
        tenant_id=tid,
        envelope=env,
        retrieval_lookup_id="sha256:aa",
        retrieval_legality_class="retrieval_replay_safe",
        execution_trace=trace,
        replay_posture="stable",
    )
    assert r1["receipt_digest"] == r2["receipt_digest"]
    assert r1["schema_version"] == RETRIEVAL_QUERY_RECEIPT_SCHEMA_VERSION_V1


def test_verify_gp07_qc02_static_passes() -> None:
    out = verify_gp07_qc02_addressing_resolution_static()
    assert out["id"] == "G-P07-QC-02"
    assert out["passed"] is True


def test_verify_gp07_qc03_static_passes() -> None:
    out = verify_gp07_qc03_fsm_phase_order_static()
    assert out["id"] == "G-P07-QC-03"
    assert out["passed"] is True


def test_doctrine_documents_envelope_and_fsm() -> None:
    root = _repo_root_containing_phase07_docs()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-query-contract-doctrine.md").read_text(
        encoding="utf-8"
    )
    assert "## §3 Lawful query envelope" in text
    assert "## §4 Query execution contract" in text
    assert "RET‑QC‑02" in text or "RET-QC-02" in text
    assert "VALIDATE" in text
    assert "RECEIPT" in text


@pytest.mark.integration
def test_execute_envelope_e2e_minimal_body(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain_id,
        replay_identity=replay,
        traversal_epoch="epoch-published-1",
    )
    db_session.commit()

    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        retrieval_lookup_id=row.retrieval_lookup_id,
        expected_replay_identity=replay,
        envelope_body={
            "replay_pins": {
                "index_epoch": "epoch-published-1",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
            },
        },
    )
    phases = [t["phase"] for t in out["execution_trace"]]
    assert phases == list(RETRIEVAL_QUERY_EXECUTION_PHASES_V1)
    assert out["retrieval_lookup_id"] == row.retrieval_lookup_id
    assert "retrieval_query_receipt" in out
    assert out["retrieval_query_receipt"]["receipt_digest"]
    assert out["r_leg_precheck"]["R-LEG-01"] is True
    assert out["ingress_provenance"]["artifact_kind"] == "retrieval_index"


@pytest.mark.integration
def test_execute_envelope_full_body(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    chain_id = f"chain-{uuid.uuid4().hex[:8]}"
    lookup_id = derive_retrieval_lookup_id_v1(
        index_kind="causal_chain",
        index_key=f"causal_chain:{chain_id}",
        replay_identity=replay,
    )
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=chain_id,
        replay_identity=replay,
        traversal_epoch="epoch-published-2",
    )
    assert row.retrieval_lookup_id == lookup_id
    db_session.commit()

    body = {
        "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "workload_class": "causal_chain",
        "intent": "inspect",
        "execution_partition": "authoritative",
        "addressing": {"retrieval_lookup_id": lookup_id},
        "replay_pins": {
            "index_epoch": "epoch-published-2",
            "tcre_policy_bundle_digest": "sha256:policy-stub",
        },
    }
    out = execute_retrieval_query_envelope_v1(
        db_session,
        tenant_id=tenant_id,
        body=body,
        expected_replay_identity=replay,
    )
    assert out["workload_class"] == "causal_chain"
    assert out["execution_trace"][-1]["phase"] == "RECEIPT"

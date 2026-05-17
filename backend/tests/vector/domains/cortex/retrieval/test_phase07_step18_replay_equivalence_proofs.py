"""P07-18 — Retrieval replay equivalence proofs harness (**G-P07-REPLAY-01/02**)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_CODES_REGISTRY_V1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import GP07_REPLAY_01_GATE_ID_V1
from vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs import (
    GP07_REPLAY02_GATE_ID_V1,
    PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_REPLAY_TWIN_V1,
    build_retrieval_replay_inspector_catalog_v1,
    load_retrieval_golden_case_v1,
    retrieval_replay_omissions_from_twin_diff_v1,
    run_retrieval_golden_replay_equivalence_case_v1,
    run_retrieval_gp07_pr_blocking_static_stages_v1,
    run_retrieval_gp07_stage_c_replay_gates_v1,
    verify_gp07_replay18_golden_double_run_corpus_static,
    verify_gp07_replay18_twin_failure_emits_rd_replay_twin_static,
    verify_gp07_replay18_wired_runner_ids_match_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-replay-equivalence-retrieval-spec.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION >= 1


def test_rd_replay_twin_in_registry() -> None:
    assert RETRIEVAL_RD_REPLAY_TWIN_V1 in RETRIEVAL_RD_CODES_REGISTRY_V1


def test_static_harness_gates() -> None:
    assert verify_gp07_replay18_golden_double_run_corpus_static()["passed"] is True
    assert verify_gp07_replay18_twin_failure_emits_rd_replay_twin_static()["passed"] is True
    assert verify_gp07_replay18_wired_runner_ids_match_static()["passed"] is True


def test_stage_c_replay_harness_passes() -> None:
    out = run_retrieval_gp07_stage_c_replay_gates_v1()
    assert out["passed"] is True
    assert out["stage"] == "C"
    ids = [r["id"] for r in out["results"]]
    assert GP07_REPLAY_01_GATE_ID_V1 in ids
    assert GP07_REPLAY02_GATE_ID_V1 in ids


def test_pr_blocking_stages_abc_pass() -> None:
    out = run_retrieval_gp07_pr_blocking_static_stages_v1()
    assert out["passed"] is True
    assert out["stages"] == ["A", "B", "C"]


def test_golden_replay_equivalence_case() -> None:
    case = load_retrieval_golden_case_v1("query/replay_equivalence_double_run_v1")
    result = run_retrieval_golden_replay_equivalence_case_v1(case)
    assert result["gp07_replay_01_passed"] is True


def test_twin_omissions_on_failure() -> None:
    rows = retrieval_replay_omissions_from_twin_diff_v1(
        {"gp07_replay_01_passed": False, "ordering_divergence": True}
    )
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_REPLAY_TWIN_V1


def test_inspector_catalog_includes_harness() -> None:
    cat = build_retrieval_replay_inspector_catalog_v1(tenant_id="t1")
    assert cat["gp07_replay02_gate_id"] == GP07_REPLAY02_GATE_ID_V1
    assert "harness" in cat
    assert cat["harness"]["golden_case_id"] == "query/replay_equivalence_double_run_v1"
    assert "twin_diff_fields" in cat


def test_doctrine_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-replay-equivalence-retrieval-spec.md").read_text(
        encoding="utf-8"
    )
    assert "retrieval_query_replay_identity" in text
    assert "replay_equivalence" in text


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7rep18-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Rep18")
    tenant = Tenant(
        company_name="P7REP18",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7rep18-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_replay_equivalence_twin_workload_degraded_on_forced_divergence(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Twin failure propagates ``RD-REPLAY-TWIN`` and ``retrieval_degraded``."""
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-rep18",
    )
    db_session.commit()

    call_count = {"n": 0}
    real_build = __import__(
        "vector.domains.cortex.retrieval.retrieval_replay_equivalence",
        fromlist=["build_retrieval_replay_equivalence_twin_diff_v1"],
    ).build_retrieval_replay_equivalence_twin_diff_v1

    def _patched_twin(a, b):
        diff = real_build(a, b)
        call_count["n"] += 1
        if call_count["n"] == 1:
            diff = dict(diff)
            diff["gp07_replay_01_passed"] = False
            diff["hit_count_mismatch"] = True
        return diff

    monkeypatch.setattr(
        "vector.domains.cortex.retrieval.query_execution.build_retrieval_replay_equivalence_twin_diff_v1",
        _patched_twin,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.retrieval.query_execution.compare_gp07_replay_01_double_run_v1",
        lambda _a, _b: (_ for _ in ()).throw(
            __import__(
                "vector.domains.cortex.retrieval.retrieval_replay_equivalence",
                fromlist=["RetrievalReplayEquivalenceError"],
            ).RetrievalReplayEquivalenceError("forced")
        ),
    )

    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "replay_equivalence",
            "intent": "prove",
            "addressing": {"retrieval_lookup_id": row.retrieval_lookup_id},
            "replay_pins": {
                "index_epoch": "epoch-rep18",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {"max_hits": 50},
        },
    )
    twin = out.get("replay_equivalence_twin")
    assert isinstance(twin, dict)
    assert twin.get("gp07_replay_01_passed") is False
    assert out.get("retrieval_legality_class") == "retrieval_degraded"
    omissions = out.get("omissions") or []
    assert any(
        isinstance(o, dict) and o.get("retrieval_omission_class") == RETRIEVAL_RD_REPLAY_TWIN_V1
        for o in omissions
    )


@pytest.mark.integration
def test_replay_equivalence_twin_workload_happy_path(db_session: Session) -> None:
    tenant_id = _tenant_with_owner(db_session)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    row = index_tcre_chain_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        causal_chain_id=f"chain-{uuid.uuid4().hex[:8]}",
        replay_identity=replay,
        traversal_epoch="epoch-rep18-ok",
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
                "index_epoch": "epoch-rep18-ok",
                "tcre_policy_bundle_digest": "sha256:policy-stub",
                "octs_engine_build_ref": "build-stub",
            },
            "expected_replay_identity": replay,
            "selection_policy": {"max_hits": 50},
        },
    )
    twin = out.get("replay_equivalence_twin")
    assert isinstance(twin, dict)
    assert twin.get("gp07_replay_01_passed") is True
    assert PHASE07_REPLAY_IDENTITY_FIELD_V1 in out

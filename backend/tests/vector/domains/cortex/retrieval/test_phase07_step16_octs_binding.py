"""P07-16 — OCTS walk + traversal bindings (``retrieval.retrieval_octs_binding``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
    RETRIEVAL_RD_TRAVERSAL_IDLE_V1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_walk_for_retrieval_v1,
)
from vector.domains.cortex.retrieval.retrieval_octs_binding import (
    GP07_OCTS01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION,
    assert_walk_exploration_partition_matches_v1,
    build_retrieval_walk_ref_v1,
    build_retrieval_traversal_binding_catalog_v1,
    list_traversal_idle_omissions_v1,
    map_walk_to_retrieval_lookup_id_v1,
    query_walk_scope_v1,
    verify_gp07_octs01_walk_ref_and_scope_queries_static,
)
from vector.domains.cortex.traversal.runtime.durable_walk_store import OctsWalkApiDurableStore
from vector.domains.cortex.traversal.walk_api_contract import (
    OCTS_STUB_ENGINE_BUILD_ID,
    build_stub_completed_walk_payload_v1,
)


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_octs_binding_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION >= 1


def test_gp07_octs01_static_gate() -> None:
    out = verify_gp07_octs01_walk_ref_and_scope_queries_static()
    assert out["passed"] is True
    assert out["id"] == GP07_OCTS01_GATE_ID_V1


def test_retrieval_walk_ref_shape() -> None:
    ref = build_retrieval_walk_ref_v1(
        walk_id="00000000-0000-4000-8000-000000000099",
        walk_result_hash="sha256:" + "b" * 64,
        traversal_epoch="epoch-walk-1",
    )
    assert ref["walk_id"] == "00000000-0000-4000-8000-000000000099"
    assert ref["walk_result_hash"].startswith("sha256:")
    assert ref["traversal_epoch"] == "epoch-walk-1"


def test_walk_lookup_id_deterministic() -> None:
    replay = "replay-walk-deterministic"
    wid = "00000000-0000-4000-8000-000000000088"
    a = map_walk_to_retrieval_lookup_id_v1(walk_id=wid, replay_identity=replay)
    b = map_walk_to_retrieval_lookup_id_v1(walk_id=wid, replay_identity=replay)
    assert a == b


def test_graph_eligible_idle_rd_traversal() -> None:
    rows = list_traversal_idle_omissions_v1(
        upstream_triggers=None,
        graph_eligible=True,
        walk_count=0,
        bind_required=True,
    )
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_TRAVERSAL_IDLE_V1


def test_exploration_partition_match() -> None:
    req = {"exploration_mode": True}
    assert assert_walk_exploration_partition_matches_v1(
        execution_partition="exploration", walk_request_body=req
    )
    assert not assert_walk_exploration_partition_matches_v1(
        execution_partition="authoritative", walk_request_body=req
    )


def test_traversal_binding_catalog() -> None:
    cat = build_retrieval_traversal_binding_catalog_v1()
    assert cat["gate_id"] == GP07_OCTS01_GATE_ID_V1
    assert "walk_by_id" in cat["walk_scope_query_kinds"]


def test_doctrine_and_golden_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "OCTS" in text
    golden = (
        Path(__file__).parent
        / "retrieval_golden_vectors"
        / "v1"
        / "cases"
        / "octs"
        / "walk_ref_scope_v1"
        / "case.json"
    )
    assert golden.is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7octs-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 OCTS")
    tenant = Tenant(
        company_name="P7OCTS",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7octs-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _walk_request_body(tenant_id: uuid.UUID) -> dict:
    return {
        "temporal_anchor": {
            "tenant_id": str(tenant_id),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "cc" * 32,
            "snapshot_unix_ns": {"unix_ns": 42},
            "graph_as_of_unix_ns": {"unix_ns": 42},
        },
        "walk_policy": {
            "max_hops": 4,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
    }


def _seed_completed_walk(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
) -> tuple[dict, str]:
    body = _walk_request_body(tenant_id)
    payload = build_stub_completed_walk_payload_v1(body, tenant_id=tenant_id)
    OctsWalkApiDurableStore(db_session).insert_completed_sync(
        tenant_id=tenant_id,
        walk_id=walk_id,
        request_body=body,
        walk_payload=payload,
        idempotency_key=None,
    )
    walk_hash = str((payload.get("walk_result") or {}).get("walk_result_hash") or "")
    db_session.flush()
    return payload, walk_hash


@pytest.mark.integration
def test_walk_scope_queries_and_binding(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    walk_id = uuid.uuid4()
    _payload, walk_hash = _seed_completed_walk(db_session, tenant_id=tenant_id, walk_id=walk_id)
    scope = query_walk_scope_v1(
        db_session,
        tenant_id=tenant_id,
        scope_kind="walk_by_id",
        walk_id=str(walk_id),
    )
    assert scope["walk_count"] == 1
    inventory = query_walk_scope_v1(
        db_session,
        tenant_id=tenant_id,
        scope_kind="tenant_completed_walk_inventory",
    )
    assert inventory["walk_count"] >= 1
    db_session.commit()


@pytest.mark.integration
def test_index_walk_and_query_with_pins(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    walk_id = uuid.uuid4()
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    _payload, walk_hash = _seed_completed_walk(db_session, tenant_id=tenant_id, walk_id=walk_id)
    index_walk_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        walk_id=walk_id,
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "traversal_lineage",
            "addressing": {
                "retrieval_walk_ref": {
                    "walk_id": str(walk_id),
                    "walk_result_hash": walk_hash,
                    "traversal_epoch": epoch,
                }
            },
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "walk_result_hash": walk_hash,
                "tcre_policy_bundle_digest": "sha256:policy",
                "octs_engine_build_ref": OCTS_STUB_ENGINE_BUILD_ID,
            },
        },
    )
    assert out.get("traversal_binding_envelope", {}).get("bind_state") == "bound"
    assert out.get("retrieval_walk_ref", {}).get("walk_id") == str(walk_id)
    assert not any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1
        for o in (out.get("omissions") or [])
        if isinstance(o, dict)
    )


@pytest.mark.integration
def test_exploration_mismatch_emits_rd_traversal_blocked(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    walk_id = uuid.uuid4()
    body = _walk_request_body(tenant_id)
    body["exploration_mode"] = True
    payload = build_stub_completed_walk_payload_v1(body, tenant_id=tenant_id)
    walk_hash = str((payload.get("walk_result") or {}).get("walk_result_hash") or "")
    OctsWalkApiDurableStore(db_session).insert_completed_sync(
        tenant_id=tenant_id,
        walk_id=walk_id,
        request_body=body,
        walk_payload=payload,
        idempotency_key=None,
    )
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    index_walk_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        walk_id=walk_id,
        replay_identity=replay,
        traversal_epoch=epoch,
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "traversal_lineage",
            "execution_partition": "authoritative",
            "addressing": {
                "retrieval_walk_ref": {
                    "walk_id": str(walk_id),
                    "walk_result_hash": walk_hash,
                    "traversal_epoch": epoch,
                }
            },
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "walk_result_hash": walk_hash,
                "octs_engine_build_ref": OCTS_STUB_ENGINE_BUILD_ID,
            },
        },
    )
    assert any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1
        for o in (out.get("omissions") or [])
        if isinstance(o, dict)
    )

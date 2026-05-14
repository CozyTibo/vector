"""P05-17 / **P05-20** / **P05-21** / **P05-24** / **P05-25** — admin OCTS traversal HTTP routes (integration)."""

from __future__ import annotations

import json
import uuid
from unittest import mock

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.traversal.walk_api_contract import (
    API_WALK_CONTRACT_SCHEMA_VERSION,
    canonical_octs_walk_api_json_utf8_len_v1,
)
from vector.domains.cortex.traversal.derived_index_contract import octs_derived_index_fixture_dir
from vector.domains.cortex.traversal.walk_policy import SYNC_MAX_REQUEST_JSON_BYTES

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"octs-{uuid.uuid4().hex[:10]}@example.com", full_name="OCTS User")
    tenant = Tenant(
        company_name="OCTSCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"octs-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id, user.id


def _minimal_walk_body(tenant_id: uuid.UUID) -> dict:
    return {
        "temporal_anchor": {
            "tenant_id": str(tenant_id),
            "export_id": "00000000-0000-4000-8000-000000000002",
            "export_sequence": 0,
            "projection_content_hash": "sha256:" + "aa" * 32,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "walk_policy": {
            "max_hops": 8,
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
        "exploration_mode": False,
    }


def test_admin_octs_walk_post_get_sync_completed(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert "walk_result" in data
    assert data["walk_result"]["walk_result_hash"].startswith("sha256:")

    wid = data["walk_id"]
    r2 = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/walks/{wid}",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json()["walk_id"] == wid


def test_admin_octs_walk_async_returns_202(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks?async=1",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 202
    j = r.json()
    assert j["job_id"]
    assert j["status"] == "running"


def test_admin_octs_walk_oversize_sync_request_json_413(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    nid = "00000000-0000-0000-0000-000000000003"
    ids = list(body["start_node_ids"])
    while canonical_octs_walk_api_json_utf8_len_v1({**body, "start_node_ids": ids}) <= SYNC_MAX_REQUEST_JSON_BYTES:
        ids.append(nid)
    body["start_node_ids"] = ids

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 413
    err = r.json()
    assert err["error_code"] == "walk_too_large"
    assert "sync_request_json_bytes" in err["details"]["violations"]


def test_admin_octs_walk_oversize_sync_response_json_413(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    fat = "x" * 400_000

    def _fat_completed(wid: uuid.UUID, pl: dict) -> dict:
        return {
            "octs_walk_api_version": API_WALK_CONTRACT_SCHEMA_VERSION,
            "walk_id": str(wid),
            "status": "completed",
            "walk_result": pl["walk_result"],
            "telemetry": pl.get("telemetry", {}),
            "padding": fat,
        }

    with mock.patch(
        "vector.api.http.routes.admin_octs_walks.completed_sync_walk_api_public_document_v1",
        side_effect=_fat_completed,
    ):
        r = client.post(
            f"/admin/tenants/{tid}/cortex/traversal/walks",
            json=body,
            auth=("admin", "integration-admin-password"),
        )
    assert r.status_code == 413
    err = r.json()
    assert err["error_code"] == "walk_too_large"
    assert "sync_response_json_bytes" in err["details"]["violations"]


def test_admin_octs_walk_sync_cap_413(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    body["walk_policy"]["max_hops"] = 99
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 413
    err = r.json()
    assert err["error_code"] == "walk_too_large"
    assert "violations" in err["details"]


def test_admin_octs_walk_tenant_mismatch_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    body["temporal_anchor"]["tenant_id"] = str(uuid.uuid4())
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "tenant_mismatch"


def _inherit_child_body(tenant_id: uuid.UUID, parent_walk_id: str) -> dict:
    base = _minimal_walk_body(tenant_id)
    out = {k: v for k, v in base.items() if k != "temporal_anchor"}
    out["inherit_walk_id"] = parent_walk_id
    return out


def test_admin_octs_walk_inherit_replay_sync_matches_parent(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r1 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r1.status_code == 200
    parent = r1.json()
    h1 = parent["walk_result"]["walk_result_hash"]

    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_inherit_child_body(tid, parent["walk_id"]),
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    child = r2.json()
    assert child["walk_result"]["walk_result_hash"] == h1
    tel = child.get("telemetry") or {}
    assert tel.get("replay_of_walk_id") == parent["walk_id"]
    assert tel.get("original_walk_result_hash") == h1
    assert tel.get("engine_build_id")


def test_admin_octs_walk_inherit_source_not_found_404(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_inherit_child_body(tid, str(uuid.uuid4())),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404
    assert r.json()["error_code"] == "source_walk_not_found"


def test_admin_octs_walk_inherit_expected_hash_mismatch_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r1 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r1.status_code == 200
    body = _inherit_child_body(tid, r1.json()["walk_id"])
    body["expected_walk_result_hash"] = "sha256:" + "bb" * 32
    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 400
    assert r2.json()["error_code"] == "replay_hash_mismatch"


def test_admin_octs_walk_requires_auth(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
    )
    assert r.status_code == 401


def test_admin_octs_walk_cancel_async(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks?async=1",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 202
    wid = r.json()["walk_id"]

    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks/{wid}/cancel",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "cancelled"


def test_admin_octs_walk_cannot_cancel_completed(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    wid = r.json()["walk_id"]

    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks/{wid}/cancel",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 400
    assert r2.json()["error_code"] == "cannot_cancel_terminal"


def test_admin_octs_walk_idempotency_returns_same_walk(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    body = _minimal_walk_body(tid)
    key = f"idem-{uuid.uuid4()}"
    r1 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        headers={"Idempotency-Key": key},
        auth=("admin", "integration-admin-password"),
    )
    r2 = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        headers={"Idempotency-Key": key},
        auth=("admin", "integration-admin-password"),
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["walk_id"] == r2.json()["walk_id"]


def _good_derived_artifact() -> dict:
    d = octs_derived_index_fixture_dir()
    return json.loads((d / "derived_index_artifact_good_v1.json").read_text(encoding="utf-8"))


def test_admin_octs_derived_index_replay_verify_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    art = _good_derived_artifact()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify",
        json={"artifact": art},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["double_run_equal"] is True
    assert body["index_content_hash"].startswith("sha256:")
    assert body["octs_index_replay_api_version"] >= 1


def test_admin_octs_derived_index_replay_verify_expected_mismatch_409(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    art = _good_derived_artifact()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify",
        json={
            "artifact": art,
            "expected_index_content_hash": "sha256:" + "bb" * 32,
        },
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 409
    err = r.json()
    assert err["error_code"] == "index_replay_hash_mismatch"


def test_admin_octs_derived_index_replay_verify_schema_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify",
        json={"artifact": {}, "bogus": 1},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "index_replay_verify_schema"


def test_admin_octs_engine_identity_get_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    for k in (
        "VECTOR_OCTS_ENGINE_BUILD_ID",
        "VECTOR_OCTS_EMBEDDED_GIT_SHA",
        "OCTS_DEV_ENGINE_ID",
    ):
        monkeypatch.delenv(k, raising=False)
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/engine-identity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["engine_identity_available"] is False
    assert j["engine_build_id"] is None
    assert j["error_code"] == "engine_identity_unavailable"


def test_admin_octs_engine_identity_get_available_when_pinned(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("VECTOR_OCTS_ENGINE_BUILD_ID", "git:" + "ab" * 20)
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/engine-identity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["engine_identity_available"] is True
    assert j["engine_build_id"] == "git:" + "ab" * 20


def test_admin_octs_walk_enforce_engine_identity_503_without_pin(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY", "1")
    for k in ("VECTOR_OCTS_ENGINE_BUILD_ID", "OCTS_DEV_ENGINE_ID"):
        monkeypatch.delenv(k, raising=False)
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 503
    assert r.json()["error_code"] == "engine_identity_unavailable"


def test_admin_octs_walk_enforce_engine_identity_ok_with_git_pin(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY", "1")
    monkeypatch.setenv("VECTOR_OCTS_ENGINE_BUILD_ID", "git:" + "cd" * 20)
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200


def test_admin_octs_walk_async_bypasses_engine_enforce(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    monkeypatch.setenv("VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY", "1")
    for k in ("VECTOR_OCTS_ENGINE_BUILD_ID", "OCTS_DEV_ENGINE_ID"):
        monkeypatch.delenv(k, raising=False)
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks?async=1",
        json=_minimal_walk_body(tid),
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 202


def test_admin_octs_traversal_control_plane_get_200_empty(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["traversal_queue"] == []
    assert j["abort_classes"] == {}
    assert j["budget_histogram"] == {}
    assert "computed_at_utc" in j


def test_admin_octs_traversal_control_plane_bad_include_exploration_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/control-plane?include_exploration=maybe",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "control_plane_bad_include_exploration"


def test_admin_octs_traversal_control_plane_lists_completed_walk(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    body = _minimal_walk_body(tid)
    r = client.post(
        f"/admin/tenants/{tid}/cortex/traversal/walks",
        json=body,
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    wid = r.json()["walk_id"]
    r2 = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/control-plane?include_exploration=1",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    rows = r2.json()["traversal_queue"]
    assert any(row["walk_id"] == wid for row in rows)


def test_admin_octs_traversal_readiness_economics_get_200_clean(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/readiness-economics",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    j = r.json()
    assert j["probe_profile"] == "clean"
    assert j["economics_violations"] == []
    assert j["economics_receipt_hash"].startswith("sha256:")
    assert "octs_economics_threshold_table_version" in j


def test_admin_octs_traversal_readiness_economics_bad_profile_400(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/readiness-economics?probe_profile=nope",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "readiness_economics_bad_probe_profile"


def test_admin_octs_traversal_readiness_economics_hostile_has_violations(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid, _ = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/traversal/readiness-economics?probe_profile=hostile",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    v = r.json()["economics_violations"]
    assert "P05_ECO_MAX_OUT_DEGREE" in v
    assert "P05_ECO_WALK_WALL_BUDGET" in v

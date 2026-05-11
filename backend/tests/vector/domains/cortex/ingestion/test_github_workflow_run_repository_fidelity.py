"""github.workflow_run raw payload must carry repository identity for canonical materialization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.ontology import CanonicalObjectKind
from vector.domains.cortex.canonical.replay_topology import build_replay_dependency_topology
from vector.domains.cortex.canonical.transform_runtime import _build_lineage_specs, materialize_raw_record
from vector.domains.cortex.ingestion.sync_executor import ensure_github_workflow_run_repository_metadata
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User

_STUB_BUNDLE = "bundle.phase03.step03.logical_keys.v1"


def test_ensure_github_workflow_run_repository_metadata_fills_from_installation_repo() -> None:
    """List-style workflow run rows (id only) gain repository truth from the sync-scoped installation record."""
    inst = {
        "id": 88424,
        "full_name": "acme/widget",
        "name": "widget",
        "owner": {"login": "acme", "id": 1},
    }
    run = {"id": 40001, "status": "completed", "conclusion": "success", "head_sha": "abc"}
    out = ensure_github_workflow_run_repository_metadata(
        run,
        installation_repository=inst,
        repository_full_name="acme/widget",
    )
    repo = out["repository"]
    assert repo["id"] == 88424
    assert repo["full_name"] == "acme/widget"
    assert repo["name"] == "widget"
    assert repo["owner"]["login"] == "acme"


def test_ensure_github_workflow_run_repository_metadata_preserves_api_nested_object() -> None:
    """When GitHub already returns a complete repository block, keep it (do not strip)."""
    run = {
        "id": 1,
        "repository": {"id": 99, "full_name": "acme/preserved", "name": "preserved", "owner": {"login": "acme"}},
    }
    out = ensure_github_workflow_run_repository_metadata(
        run,
        installation_repository={"id": 1, "full_name": "other/other", "name": "x", "owner": {"login": "x"}},
        repository_full_name="acme/sync-context",
    )
    assert out["repository"]["id"] == 99
    assert out["repository"]["full_name"] == "acme/preserved"


def test_workflow_run_transform_uses_head_repository_when_repository_empty() -> None:
    """Fork / sparse list payloads may omit ``repository`` but include ``head_repository`` (GitHub REST)."""
    tenant = uuid.uuid4()
    raw = SimpleNamespace(
        connector="github",
        resource_type="github.workflow_run",
        external_id="acme/upstream:workflow_run:77",
        source_identity_key="si",
        source_revision_key="sr",
        payload_body={
            "workflow_run": {
                "id": 77,
                "status": "completed",
                "head_repository": {"id": 333, "full_name": "contrib/fork", "name": "fork"},
            }
        },
    )
    lk, _emitted, _specs = _build_lineage_specs(
        raw=raw,
        bundle_id=_STUB_BUNDLE,
        tenant_uuid=tenant,
        kind=CanonicalObjectKind.WORKFLOW_RUN,
        rule_base="rule.registry.github.github.workflow_run",
    )
    assert lk["repository_provider_id"] == "333"
    assert lk["workflow_run_provider_id"] == "77"


def test_mock_github_workflow_run_still_materializes_after_hydration_pass() -> None:
    """Dataset rows already include repository; hydration must remain idempotent."""
    from mock_connectors.github_mock import dataset_generator as gh_gen

    gh = {
        "repos": [{"full_name": "acme/vector", "id": 42, "name": "vector", "owner": {"login": "acme"}}],
        "commits": [
            {
                "_repo": "acme/vector",
                "sha": "cafef00d",
                "commit": {
                    "author": {"date": "2026-01-01T00:00:00Z"},
                    "committer": {"date": "2026-01-01T00:00:01Z"},
                },
            }
        ],
    }
    rows, _ = gh_gen.workflow_runs_for_repo_with_total(gh, "acme", "vector", page=1, per_page=5)
    raw_run = rows[0]
    inst = gh["repos"][0]
    merged = ensure_github_workflow_run_repository_metadata(
        raw_run,
        installation_repository=inst,
        repository_full_name="acme/vector",
    )
    assert merged["repository"]["id"] == 42
    assert merged["repository"]["full_name"] == "acme/vector"


@pytest.mark.integration
def test_github_workflow_run_materialization_after_repository_hydration(db_session: Session) -> None:
    """End-to-end: hydrated raw row → transform materialization row."""
    user = User(email=f"wfrepo-{uuid.uuid4().hex[:8]}@example.com", full_name="WF Repo User")
    tenant = Tenant(
        company_name="WF Repo Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"wfrepo-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="github",
        status="active",
        connected_by_user_id=user.id,
    )
    db_session.add(conn)
    db_session.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(UTC),
    )
    db_session.add(run)
    db_session.flush()
    wf = ensure_github_workflow_run_repository_metadata(
        {"id": 91001, "status": "completed", "conclusion": "success", "head_sha": "deadbeef"},
        installation_repository={
            "id": 5001,
            "full_name": "acme/widget",
            "name": "widget",
            "owner": {"login": "acme"},
        },
        repository_full_name="acme/widget",
    )
    raw = RawIngestionRecord(
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="github",
        resource_type="github.workflow_run",
        external_id="acme/widget:workflow_run:91001",
        api_endpoint="https://api.github.com/repos/acme/widget/actions/runs",
        query_params={"page": 1},
        payload_body={"workflow_run": wf},
        payload_hash="hash-wf-repo",
        http_status=200,
        fetched_at=datetime.now(UTC),
        run_id=run.id,
        source_trigger="manual_admin",
        idempotency_key="idem-wf-repo-1",
        source_identity_key="github:github.workflow_run:acme/widget:workflow_run:91001",
        source_revision_key="rev-wf-1",
    )
    db_session.add(raw)
    db_session.flush()

    mat = materialize_raw_record(
        db_session,
        tenant_id=tenant.id,
        bundle_id=_STUB_BUNDLE,
        raw_record_id=int(raw.id),
        commit=False,
    )
    assert mat.canonical_object_kind == "workflow_run"
    assert mat.logical_key_json["workflow_run_provider_id"] == "91001"
    assert mat.logical_key_json["repository_provider_id"] == "5001"


def test_replay_topology_workflow_run_rows_order_deterministically() -> None:
    """No inter-run edges: topology preserves temporal ordering keys for staging."""
    r1 = SimpleNamespace(
        id=10,
        connector="github",
        resource_type="github.workflow_run",
        external_id="a/b:workflow_run:100",
        payload_body={
            "workflow_run": {"id": 100, "repository": {"id": 1, "full_name": "a/b"}},
        },
    )
    r2 = SimpleNamespace(
        id=11,
        connector="github",
        resource_type="github.workflow_run",
        external_id="a/b:workflow_run:101",
        payload_body={
            "workflow_run": {"id": 101, "repository": {"id": 1, "full_name": "a/b"}},
        },
    )
    keys = {10: "0000000010", 11: "0000000011"}
    topo = build_replay_dependency_topology([r1, r2], temporal_key_by_id=keys)
    assert topo.get("orphan_refs") == []
    assert not topo.get("dependency_edges")

"""P07-17 — graph / identity / canonical bindings (``retrieval.retrieval_graph_binding``)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.org_entities import upsert_org_entity
from vector.domains.cortex.retrieval.retrieval_bounded_caps import RETRIEVAL_RD_GRAPH_ORPHAN_V1
from vector.domains.cortex.retrieval.retrieval_ingress import RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_graph_ref_for_retrieval_v1,
)
from vector.domains.cortex.retrieval.retrieval_graph_binding import (
    GP07_GRAPH01_GATE_ID_V1,
    PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION,
    apply_candidate_link_legality_to_hits_v1,
    list_graph_orphan_omissions_v1,
    map_graph_ref_to_retrieval_lookup_id_v1,
    query_graph_scope_v1,
    verify_gp07_graph01_entity_link_addressing_static,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    classify_org_link_authority_for_retrieval_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink


def _repo_root() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md"
        if marker.is_file():
            return root
    pytest.fail("repo root not found")


def test_phase07_graph_binding_runtime_schema_version() -> None:
    assert PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION >= 1


def test_gp07_graph01_static_gate() -> None:
    out = verify_gp07_graph01_entity_link_addressing_static()
    assert out["passed"] is True
    assert out["id"] == GP07_GRAPH01_GATE_ID_V1


def test_entity_link_lookup_ids_differ() -> None:
    replay = "replay-graph-deterministic"
    eid = str(uuid.uuid4())
    lid = str(uuid.uuid4())
    le = map_graph_ref_to_retrieval_lookup_id_v1(
        ref_kind="org_entity_id", ref_value=eid, replay_identity=replay
    )
    ll = map_graph_ref_to_retrieval_lookup_id_v1(
        ref_kind="org_link_id", ref_value=lid, replay_identity=replay
    )
    assert le != ll
    assert le.startswith("sha256:")


def test_candidate_link_authoritative_partition() -> None:
    leg = classify_org_link_authority_for_retrieval_v1(
        "candidate", execution_partition="authoritative"
    )
    assert leg == RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1


def test_orphan_upstream_trigger() -> None:
    rows = list_graph_orphan_omissions_v1(
        upstream_triggers={"orphan_artifacts": True},
        entity_orphan=False,
        link_orphan=False,
        bind_required=False,
    )
    assert rows[0]["retrieval_omission_class"] == RETRIEVAL_RD_GRAPH_ORPHAN_V1


def test_candidate_hits_legality() -> None:
    hits = apply_candidate_link_legality_to_hits_v1(
        [{"provenance": {}}],
        evidence_legality_class=RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
    )
    assert hits[0]["evidence_legality_class"] == RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1


def test_graph_binding_catalog() -> None:
    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        build_retrieval_graph_binding_catalog_v1,
    )

    cat = build_retrieval_graph_binding_catalog_v1()
    assert cat["gate_id"] == GP07_GRAPH01_GATE_ID_V1
    assert "entity_by_id" in cat["graph_scope_query_kinds"]


def test_doctrine_and_golden_present() -> None:
    root = _repo_root()
    text = (root / "DOCS" / "cortex" / "retrieval" / "phase-07-retrieval-runtime-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "Graph" in text
    golden = (
        Path(__file__).parent
        / "retrieval_golden_vectors"
        / "v1"
        / "cases"
        / "graph"
        / "entity_link_addressing_v1"
        / "case.json"
    )
    assert golden.is_file()


def _tenant(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7graph-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 Graph")
    tenant = Tenant(
        company_name="P7GRAPH",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7graph-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def _seed_entity_link(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    src = upsert_org_entity(
        db_session,
        tenant_id=tenant_id,
        entity_kind="human_actor",
        identity_material={"email": f"actor-{uuid.uuid4().hex[:6]}@example.com"},
    )
    tgt = upsert_org_entity(
        db_session,
        tenant_id=tenant_id,
        entity_kind="team",
        identity_material={"name": f"team-{uuid.uuid4().hex[:6]}"},
    )
    link_id = uuid.uuid4()
    db_session.add(
        CortexOrgLink(
            id=link_id,
            tenant_id=tenant_id,
            link_type="org.persona_belongs_to_handle",
            source_entity_id=src.id,
            target_entity_id=tgt.id,
            evidence_raw_record_ids=[1],
            rule_id=None,
            confidence_class="phase03_confidence_stub",
            link_authority="authoritative",
            link_class="authoritative",
            metadata_json={},
            engine_build_ref="test-graph-binding",
        )
    )
    db_session.flush()
    return src.id, link_id


@pytest.mark.integration
def test_graph_scope_queries(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    eid, lid = _seed_entity_link(db_session, tenant_id=tenant_id)
    ent_scope = query_graph_scope_v1(
        db_session,
        tenant_id=tenant_id,
        scope_kind="entity_by_id",
        org_entity_id=str(eid),
    )
    assert ent_scope["entity_found"] is True
    assert ent_scope["orphan"] is False
    link_scope = query_graph_scope_v1(
        db_session,
        tenant_id=tenant_id,
        scope_kind="link_by_id",
        org_link_id=str(lid),
    )
    assert link_scope["link_found"] is True
    db_session.commit()


@pytest.mark.integration
def test_index_entity_and_query_with_export_pin(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    eid, _lid = _seed_entity_link(db_session, tenant_id=tenant_id)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    index_graph_ref_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        ref_kind="org_entity_id",
        ref_value=str(eid),
        replay_identity=replay,
        index_epoch=epoch,
    )
    db_session.commit()
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "ownership_continuity",
            "addressing": {"org_entity_id": str(eid)},
            "temporal_scope": {"t_as_of_unix_ns": 100, "export_sequence": 42},
            "selection_policy": {
                "max_hits": 50,
                "max_chronology_rows": 50,
                "max_edges": 50,
                "max_lineage_hops": 32,
            },
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "export_sequence": 42,
                "tcre_policy_bundle_digest": "sha256:policy",
            },
        },
    )
    assert out.get("graph_binding_envelope", {}).get("bind_state") == "bound"
    assert out.get("graph_scope", {}).get("entity_kind") == "human_actor"


@pytest.mark.integration
def test_missing_entity_emits_rd_graph_orphan(db_session: Session) -> None:
    tenant_id = _tenant(db_session)
    eid, _ = _seed_entity_link(db_session, tenant_id=tenant_id)
    replay = f"replay-{uuid.uuid4().hex[:8]}"
    epoch = f"epoch-{uuid.uuid4().hex[:8]}"
    missing_id = str(uuid.uuid4())
    index_graph_ref_for_retrieval_v1(
        db_session,
        tenant_id=tenant_id,
        ref_kind="org_entity_id",
        ref_value=str(eid),
        replay_identity=replay,
        index_epoch=epoch,
    )
    db_session.commit()
    lookup_id = map_graph_ref_to_retrieval_lookup_id_v1(
        ref_kind="org_entity_id", ref_value=str(eid), replay_identity=replay
    )
    out = execute_retrieval_query_v1(
        db_session,
        tenant_id=tenant_id,
        envelope_body={
            "workload_class": "ownership_continuity",
            "addressing": {
                "retrieval_lookup_id": lookup_id,
                "org_entity_id": missing_id,
            },
            "temporal_scope": {"t_as_of_unix_ns": 100, "export_sequence": 1},
            "selection_policy": {
                "max_hits": 50,
                "max_chronology_rows": 50,
                "max_edges": 50,
                "max_lineage_hops": 32,
            },
            "replay_pins": {
                "replay_identity": replay,
                "index_epoch": epoch,
                "export_sequence": 1,
            },
        },
    )
    assert any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_GRAPH_ORPHAN_V1
        for o in (out.get("omissions") or [])
        if isinstance(o, dict)
    )

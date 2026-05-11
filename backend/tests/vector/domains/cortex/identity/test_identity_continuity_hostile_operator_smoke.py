"""Operator continuity rebuild smoke — hostile-style payloads → candidates + ambiguities + audit job."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.continuity_rebuild import run_identity_continuity_rebuild, substrate_counts
from vector.domains.cortex.identity.org_entities import OrgEntityKind
from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant_connection import TenantConnection


def _seed_tenant_bundle(db: Session) -> tuple[uuid.UUID, str, uuid.UUID, uuid.UUID]:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p04sm-{uuid.uuid4().hex[:8]}@example.com", full_name="P04SM")
    tenant = Tenant(
        company_name="P04SM Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p04sm-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    bundle_id = f"bundle.p04sm.{uuid.uuid4().hex[:8]}"
    db.add(
        CortexMappingBundle(
            bundle_id=bundle_id,
            lifecycle_state="approved",
            manifest_hash="sha256:" + "c" * 64,
            owner_team="cortex-platform",
            title="P04SM bundle",
            notes=None,
        )
    )
    conn = TenantConnection(
        tenant_id=tenant.id,
        provider="slack",
        status="active",
        connected_by_user_id=user.id,
    )
    db.add(conn)
    db.flush()
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        connection_id=conn.id,
        connector="slack",
        source_trigger="manual_admin",
        sync_mode="incremental",
        replay_mode=False,
        replay_version=1,
        status="COMPLETED",
        started_at=datetime.now(tz=UTC),
    )
    db.add(run)
    db.flush()
    return tenant.id, bundle_id, run.id, conn.id


def _insert_slack_raws(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    run_id: uuid.UUID,
    n_cluster: int,
) -> None:
    cohort = "p04_smoke_hostile_cohort"
    cluster = "p04_smoke_dense_cluster"
    shared_email = "shared.inbox@nexora.test"
    shared_dn = "shared support"
    for i in range(n_cluster):
        uid = f"USMOKE{i % 4:02d}"
        ext = f"smoke-{i}-{uuid.uuid4().hex[:6]}"
        db.add(
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector="slack",
                resource_type="slack.message",
                external_id=ext,
                api_endpoint="https://slack.com/api/test",
                query_params={},
                payload_body={
                    "channel": "#smoke",
                    "ts": f"2025-03-{(i % 28) + 1:02d}T10:{i % 60:02d}:00Z",
                    "user_id": uid,
                    "user_email": f"user{i}@nexora.test",
                    "display_name": f"smoke user {i % 4}",
                    "metadata": {
                        "continuity_fixture": {
                            "cluster_key": cluster,
                            "link_subject": "p04:smoke:cross_tool_fracture",
                            "stable_account_key": "p04_smoke_stable_acct",
                            "family": "P04MD-H01",
                        }
                    },
                },
                payload_hash="ph-" + ext,
                http_status=200,
                fetched_at=datetime.now(tz=UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-" + ext,
                source_identity_key=f"slack:slack.message:{ext}",
                source_revision_key="rev-1",
            )
        )
    for j, sid in enumerate(("UINBOX01", "UINBOX02")):
        ext = f"smoke-inbox-{j}"
        db.add(
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector="slack",
                resource_type="slack.message",
                external_id=ext,
                api_endpoint="https://slack.com/api/test",
                query_params={},
                payload_body={
                    "channel": "#support",
                    "ts": f"2025-04-0{j + 1}T12:00:00Z",
                    "user_id": sid,
                    "user_email": shared_email,
                    "display_name": shared_dn,
                    "metadata": {
                        "continuity_fixture": {
                            "ambiguity_cohort_key": cohort,
                            "org_ambiguity_class": "multiple_persona_unresolved",
                            "family": "P04MD-H04",
                        }
                    },
                },
                payload_hash="ph-" + ext,
                http_status=200,
                fetched_at=datetime.now(tz=UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-" + ext,
                source_identity_key=f"slack:slack.message:{ext}",
                source_revision_key="rev-1",
            )
        )
    for m in range(2):
        ext = f"smoke-extra-{m}"
        db.add(
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector="slack",
                resource_type="slack.message",
                external_id=ext,
                api_endpoint="https://slack.com/api/test",
                query_params={},
                payload_body={
                    "channel": "#extra",
                    "ts": f"2025-06-0{m + 1}T15:00:00Z",
                    "user_id": f"UEXTRA{m}",
                    "user_email": f"extra{m}@nexora.test",
                    "display_name": "extra operator",
                    "metadata": {
                        "continuity_fixture": {
                            "ambiguity_cohort_key": "p04_smoke_extra_cohort",
                            "org_ambiguity_class": "cross_bundle_persona_gap",
                            "family": "P04MD-H09",
                        }
                    },
                },
                payload_hash="ph-" + ext,
                http_status=200,
                fetched_at=datetime.now(tz=UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-" + ext,
                source_identity_key=f"slack:slack.message:{ext}",
                source_revision_key="rev-1",
            )
        )
    for k in range(2):
        ext = f"smoke-alex-{k}"
        db.add(
            RawIngestionRecord(
                tenant_id=tenant_id,
                connection_id=connection_id,
                connector="slack",
                resource_type="slack.message",
                external_id=ext,
                api_endpoint="https://slack.com/api/test",
                query_params={},
                payload_body={
                    "channel": "#people",
                    "ts": f"2025-05-0{k + 1}T09:00:00Z",
                    "user_id": f"UALEX{k:02d}",
                    "user_email": f"alex{k}@nexora.test",
                    "display_name": "alex",
                    "metadata": {
                        "continuity_fixture": {
                            "ambiguity_cohort_key": "p04_smoke_two_alex",
                            "org_ambiguity_class": "handle_collision_unresolved",
                            "family": "P04MD-H06",
                        }
                    },
                },
                payload_hash="ph-" + ext,
                http_status=200,
                fetched_at=datetime.now(tz=UTC),
                run_id=run_id,
                source_trigger="manual_admin",
                idempotency_key="idem-" + ext,
                source_identity_key=f"slack:slack.message:{ext}",
                source_revision_key="rev-1",
            )
        )
    db.flush()


@pytest.mark.parametrize("scenario", ["nexora_p04_hostile_baseline"])
def test_hostile_scenario_rebuild_meets_operator_minimums(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    scenario: str,
) -> None:
    monkeypatch.setenv("P04_CONTINUITY_SCENARIO", scenario)
    tid, bundle_id, run_id, conn_id = _seed_tenant_bundle(db_session)
    _insert_slack_raws(db_session, tenant_id=tid, connection_id=conn_id, run_id=run_id, n_cluster=46)
    db_session.commit()

    from vector.domains.cortex.canonical.transform_runtime import drain_stub_materialize_backlog

    drain_stub_materialize_backlog(
        db_session,
        tenant_id=tid,
        bundle_id=bundle_id,
        batch_limit=2000,
    )
    db_session.commit()

    report = run_identity_continuity_rebuild(
        db_session,
        tenant_id=tid,
        bundle_id=bundle_id,
        materialize_batch_limit=2000,
        anchor_limit=10_000,
        run_determinism_repair=False,
        dry_run=False,
        replay_job=None,
    )
    db_session.commit()

    assert int(report.get("candidates_generated_count") or 0) > 20
    assert int(report.get("ambiguity_opened_total") or 0) >= 4
    assert report.get("candidate_set_sha256")
    assert report.get("anchor_evidence_input_sha256")
    assert report.get("replay_lane") == "anchor_continuity"

    n_jobs = int(
        db_session.scalar(
            select(func.count()).select_from(CortexOrgLinkReplayJob).where(CortexOrgLinkReplayJob.tenant_id == tid)
        )
        or 0
    )
    assert n_jobs > 0

    n_rebuild = int(
        db_session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tid,
                CortexOrgLinkReplayJob.job_kind == "identity_continuity_rebuild",
            )
        )
        or 0
    )
    assert n_rebuild > 0

    snap = substrate_counts(db_session, tenant_id=tid)
    assert snap["org_link_candidates"] > 20
    assert snap["org_ambiguity_open"] >= 4

    non_ph = int(
        db_session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(
                CortexOrgEntity.tenant_id == tid,
                CortexOrgEntity.tombstoned_at.is_(None),
                CortexOrgEntity.entity_kind != OrgEntityKind.UNKNOWN_PLACEHOLDER.value,
            )
        )
        or 0
    )
    assert non_ph > 0

    from vector.domains.cortex.identity.continuity_evidence_inspector import (
        build_continuity_evidence_inspection_for_tenant,
    )

    insp = build_continuity_evidence_inspection_for_tenant(db_session, tenant_id=tid, anchor_scan_limit=5000)
    assert insp["substrate_counters"]["anchors_with_continuity_fixture_dict"] > 0
    assert insp["substrate_counters"]["anchors_with_fixture_cluster_key"] > 0
    assert insp["substrate_counters"]["anchors_continuity_rule_eligible"] > 0
    assert insp["current_engine_candidate_row_count"] > 20
    assert insp["fixture_survival_sample"]
    surv0 = insp["fixture_survival_sample"][0]
    assert surv0["raw_has_continuity_fixture"] is True
    assert surv0["canonical_emitted_has_continuity_fixture"] is False
    trace = insp["hostile_continuity_dry_run_trace"]
    assert isinstance(trace, dict)
    assert "raw" in trace
    assert trace["rules_evaluated_summary"]["candidate_rows_referencing_this_raw_id"] > 0

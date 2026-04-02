"""Internal admin API — HTTP Basic (ADMIN_PASSWORD). Cross-tenant inspection."""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from vector.api.http.admin_deps import require_admin_basic
from vector.api.http.deps import get_db, settings_dep
from vector.api.http.serialization import orm_to_dict
from vector.contracts.admin import (
    AdminConnectionsResponse,
    AdminStep1RawResetRequest,
    AdminStep1RawResetResponse,
    OnboardingAdminSnapshot,
    OnboardingChatMessageItem,
    RawIngestionAdminDetail,
    RawIngestionAdminDetailResponse,
    RawIngestionAdminItem,
    RawIngestionAdminPage,
    TenantAdminDetailResponse,
    TenantConnectionAdminItem,
    TenantListItem,
    TenantListResponse,
)
from vector.contracts.connectors import GithubIngestionRunListItem, GithubIngestionRunsListResponse
from vector.contracts.debug_canonical import (
    CanonicalStatusResponse,
    PaginatedResponse,
    SubgraphAnchor,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResponse,
)
from vector.contracts.debug_projections import ProjectionRowsResponse
from vector.domains.canonical.worker import count_canonical_lag, drain_github_canonical
from vector.domains.connectors.runtime import runtime_by_id
from vector.domains.debug.github_pipeline_wipe import (
    rebuild_derived_from_step1_github,
    reset_github_pipeline_state,
)
from vector.application.services import connector_sync
from vector.domains.ingestion.github_poll_sync import run_github_poll_ingestion_for_tenant
from vector.domains.ingestion.http_fetch import FetchFatalError
from vector.domains.ingestion.linear_graphql_sync import run_linear_graphql_ingestion_for_tenant
from vector.domains.ingestion.mock_preflight import preflight_mock_connectors_reachable
from vector.domains.ingestion.step1_reset import (
    STEP1_RAW_RESET_CONFIRMATION_PHRASE,
    wipe_step1_raw_for_tenant,
)
from vector.domains.projections.github.worker import drain_github_projections
from vector.infrastructure.db.models.canonical import Step3CanonicalCursor
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories import canonical_debug_queries as cq
from vector.infrastructure.db.repositories import ingestion_queries as ing_queries
from vector.infrastructure.db.repositories import onboarding as onboarding_repo
from vector.infrastructure.db.repositories import projection_debug_queries as dbg
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, RUN_STATUS_SUCCEEDED
from vector.settings import Settings

GITHUB_ENTITIES = frozenset({"repositories", "pull_requests", "issues", "commits", "users"})


def _tools_interest(ans: dict[str, object]) -> list[str]:
    raw = ans.get("tools_interest")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if x is not None]


def _company_domain(ans: dict[str, object]) -> str | None:
    raw = ans.get("company_domain")
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s or None


def _tools_stack(ans: dict[str, object]) -> dict[str, Any] | None:
    raw = ans.get("tools_stack")
    if not isinstance(raw, dict):
        return None
    return dict(raw)


def _profile_phase(ans: dict[str, object]) -> str | None:
    raw = ans.get("profile_phase")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _profile_role(ans: dict[str, object]) -> str | None:
    prof = ans.get("profile")
    if isinstance(prof, dict):
        r = prof.get("role")
        if isinstance(r, str) and r.strip():
            return r.strip()
    return None


def _company_size(ans: dict[str, object]) -> str | None:
    comp = ans.get("company")
    if isinstance(comp, dict):
        s = comp.get("size")
        if isinstance(s, str) and s.strip():
            return s.strip()
    return None


def _company_website(ans: dict[str, object]) -> str | None:
    comp = ans.get("company")
    if isinstance(comp, dict):
        w = comp.get("website")
        if isinstance(w, str) and w.strip():
            return w.strip()
    return _company_domain(ans)


def _tools_category(ans: dict[str, object], key: str) -> list[str]:
    raw = ans.get("tools")
    if not isinstance(raw, dict):
        return []
    v = raw.get(key)
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if isinstance(x, str)]


def _snapshot_from_onboarding(
    session: Session, row: OnboardingState | None
) -> OnboardingAdminSnapshot | None:
    if row is None:
        return None
    ans = dict(row.answers_json or {})
    msgs: list[OnboardingChatMessageItem] = []
    if onboarding_repo.onboarding_messages_table_exists(session):
        raw_rows = onboarding_repo.list_recent_onboarding_messages(session, row.tenant_id, limit=50)
        for m in sorted(raw_rows, key=lambda x: x.created_at):
            msgs.append(
                OnboardingChatMessageItem(role=m.role, content=m.content, created_at=m.created_at)
            )
    return OnboardingAdminSnapshot(
        status=row.status,
        current_step=row.current_step,
        started_at=row.started_at,
        completed_at=row.completed_at,
        abandoned_at=row.abandoned_at,
        profile_phase=_profile_phase(ans),
        tools_interest=_tools_interest(ans),
        company_domain=_company_domain(ans),
        company_website=_company_website(ans),
        company_size=_company_size(ans),
        user_role=_profile_role(ans),
        tools_engineering=_tools_category(ans, "engineering"),
        tools_pm=_tools_category(ans, "pm"),
        tools_communication=_tools_category(ans, "communication"),
        tools_docs=_tools_category(ans, "docs"),
        tools_stack=_tools_stack(ans),
        chat_messages=msgs,
    )


def _assert_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    if tenancy_repo.get_tenant_by_id(session, tenant_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None


def build_admin_router() -> APIRouter:
    r = APIRouter(
        prefix="/admin",
        tags=["admin"],
        dependencies=[Depends(require_admin_basic)],
    )

    @r.get("/tenants", response_model=TenantListResponse)
    def list_tenants(
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ) -> TenantListResponse:
        rows = tenancy_repo.list_all_tenants(db, limit=limit)
        t_ids = [t.id for t in rows]
        ob_map = onboarding_repo.list_onboarding_for_tenants(db, t_ids)
        items: list[TenantListItem] = []
        for t in rows:
            ob = ob_map.get(t.id)
            conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=t.id)
            items.append(
                TenantListItem(
                    id=t.id,
                    company_name=t.company_name,
                    created_at=t.created_at,
                    onboarding_status=ob.status if ob else None,
                    onboarding_current_step=ob.current_step if ob else None,
                    connected_connectors=[c.provider for c in conns],
                ),
            )
        return TenantListResponse(items=items)

    @r.get("/tenants/{tenant_id}", response_model=TenantAdminDetailResponse)
    def get_tenant(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            connected_connectors=[c.provider for c in conns],
        )

    @r.get("/tenants/{tenant_id}/connections", response_model=AdminConnectionsResponse)
    def list_connections(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminConnectionsResponse:
        _assert_tenant(db, tenant_id)
        rows = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
        return AdminConnectionsResponse(
            items=[
                TenantConnectionAdminItem(
                    id=row.id,
                    provider=row.provider,
                    status=row.status,
                    created_at=row.created_at,
                )
                for row in rows
            ],
        )

    @r.delete(
        "/tenants/{tenant_id}/connections/{provider}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def admin_disconnect_tenant_connector(
        tenant_id: uuid.UUID,
        provider: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> Response:
        """Remove a workspace integration (GitHub, Linear, or Slack) for support / testing."""
        _assert_tenant(db, tenant_id)
        runtimes = runtime_by_id()
        runtime = runtimes.get(provider)
        if runtime is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"Unknown connector provider: {provider!r}.",
            ) from None
        runtime.disconnect_tenant(db, tenant_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @r.get("/tenants/{tenant_id}/raw-ingestion", response_model=RawIngestionAdminPage)
    def list_raw_ingestion(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> RawIngestionAdminPage:
        _assert_tenant(db, tenant_id)
        page = dbg.list_raw_ingestion_records_for_tenant(
            db,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        items = [
            RawIngestionAdminItem(
                id=row.id,
                connector=row.connector,
                replay_sequence=int(row.replay_sequence),
                resource_type=row.resource_type,
                external_id=row.external_id,
                fetched_at=row.fetched_at,
                http_status=row.http_status,
            )
            for row in page.items
        ]
        return RawIngestionAdminPage(
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get(
        "/tenants/{tenant_id}/raw-ingestion/{record_id}",
        response_model=RawIngestionAdminDetailResponse,
    )
    def get_raw_ingestion_detail(
        tenant_id: uuid.UUID,
        record_id: Annotated[int, Path(ge=1)],
        db: Annotated[Session, Depends(get_db)],
    ) -> RawIngestionAdminDetailResponse:
        _assert_tenant(db, tenant_id)
        row = dbg.get_raw_ingestion_record_for_tenant(
            db,
            tenant_id=tenant_id,
            record_id=record_id,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Raw ingestion record not found")
        detail = RawIngestionAdminDetail(
            id=row.id,
            connection_id=row.connection_id,
            run_id=row.run_id,
            connector=row.connector,
            source_trigger=row.source_trigger,
            replay_sequence=int(row.replay_sequence),
            resource_type=row.resource_type,
            external_id=row.external_id,
            api_endpoint=row.api_endpoint,
            query_params=row.query_params,
            payload_hash=row.payload_hash,
            http_status=row.http_status,
            fetched_at=row.fetched_at,
            payload_body=row.payload_body,
        )
        return RawIngestionAdminDetailResponse(item=detail)

    @r.post(
        "/tenants/{tenant_id}/raw-ingestion/reset",
        response_model=AdminStep1RawResetResponse,
    )
    def reset_tenant_step1_raw_ingestion(
        tenant_id: uuid.UUID,
        body: AdminStep1RawResetRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminStep1RawResetResponse:
        """Wipe Step 1 for tenant (raw rows, ingestion runs, sync state). No connector calls."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != STEP1_RAW_RESET_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Confirmation phrase does not match. Open the Step1 Raw admin tab for the "
                    "exact text — this only deletes Step 1 data, not OAuth or Step 2/3."
                ),
            )
        stats = wipe_step1_raw_for_tenant(db, tenant_id=tenant_id)
        db.commit()
        return AdminStep1RawResetResponse(
            deleted_raw_records=stats["deleted_raw_records"],
            deleted_ingestion_runs=stats["deleted_ingestion_runs"],
            deleted_sync_state_rows=stats["deleted_sync_state_rows"],
        )

    @r.post("/tenants/{tenant_id}/ingestion/github-sync")
    def admin_trigger_github_step1_sync(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> dict[str, Any]:
        """GitHub poll Step 1; drain projection + canonical if run succeeds."""
        _assert_tenant(db, tenant_id)
        preflight_mock_connectors_reachable(settings)
        try:
            run = connector_sync.run_github_poll_sync_with_drains(db, settings, tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        return {
            "run_id": str(run.id),
            "status": run.status,
            "error_summary": run.error_summary,
            "stats": run.stats,
        }

    @r.post("/tenants/{tenant_id}/ingestion/linear-sync")
    def admin_trigger_linear_step1_sync(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> dict[str, Any]:
        """Linear GraphQL Step 1 raw rows only (product linear/sync parity)."""
        _assert_tenant(db, tenant_id)
        preflight_mock_connectors_reachable(settings)
        try:
            run = run_linear_graphql_ingestion_for_tenant(db, settings, tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        return {
            "run_id": str(run.id),
            "status": run.status,
            "error_summary": run.error_summary,
            "stats": run.stats,
        }

    @r.get(
        "/tenants/{tenant_id}/github/ingestion/runs",
        response_model=GithubIngestionRunsListResponse,
    )
    def list_github_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> GithubIngestionRunsListResponse:
        _assert_tenant(db, tenant_id)
        runs = ing_queries.list_github_ingestion_runs_for_tenant(
            db,
            tenant_id,
            limit=limit,
        )
        counts = ing_queries.record_counts_for_run_ids(db, [r.id for r in runs])
        items = [
            GithubIngestionRunListItem(
                id=run.id,
                connection_id=run.connection_id,
                status=run.status,
                source_trigger=run.source_trigger,
                started_at=run.started_at,
                finished_at=run.finished_at,
                error_summary=run.error_summary,
                stats=run.stats,
                records_written=counts.get(run.id, 0),
            )
            for run in runs
        ]
        return GithubIngestionRunsListResponse(items=items)

    @r.get(
        "/tenants/{tenant_id}/projections/github/{connection_id}/rows",
        response_model=ProjectionRowsResponse,
    )
    def projection_rows(
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        entity: Annotated[str, Query(description="repositories | pull_requests | …")],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query(description="Filter substring")] = None,
    ) -> ProjectionRowsResponse:
        _assert_tenant(db, tenant_id)
        if entity not in GITHUB_ENTITIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity '{entity}'.",
            ) from None
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Connection not found for tenant.",
            ) from None
        listers: dict[str, Any] = {
            "repositories": dbg.list_github_repositories,
            "pull_requests": dbg.list_github_pull_requests,
            "issues": dbg.list_github_issues,
            "commits": dbg.list_github_commits,
            "users": dbg.list_github_users,
        }
        page = listers[entity](
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(row) for row in page.items]
        return ProjectionRowsResponse(
            connector="github",
            connection_id=connection_id,
            entity=entity,
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get("/tenants/{tenant_id}/canonical/actors", response_model=PaginatedResponse)
    def list_actors(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_actors(db, tenant_id=tenant_id, limit=limit, offset=offset, q=q)
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/artifacts", response_model=PaginatedResponse)
    def list_artifacts(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        artifact_kind_id: Annotated[int | None, Query()] = None,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_artifacts(
            db,
            tenant_id=tenant_id,
            artifact_kind_id=artifact_kind_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/relationships", response_model=PaginatedResponse)
    def list_relationships(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        current_only: Annotated[bool, Query()] = True,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_relationships(
            db,
            tenant_id=tenant_id,
            current_only=current_only,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/external-references", response_model=PaginatedResponse)
    def list_external_references(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_external_references(
            db,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/mapping-events", response_model=PaginatedResponse)
    def list_mapping_events(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        external_reference_id: Annotated[uuid.UUID | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_mapping_events(
            db,
            tenant_id=tenant_id,
            external_reference_id=external_reference_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/actors/{actor_id}")
    def get_actor(
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.actor_detail(db, tenant_id=tenant_id, actor_id=actor_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Actor not found.") from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/artifacts/{artifact_id}")
    def get_artifact(
        tenant_id: uuid.UUID,
        artifact_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.artifact_detail(db, tenant_id=tenant_id, artifact_id=artifact_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact not found.") from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/relationships/{relationship_id}")
    def get_relationship(
        tenant_id: uuid.UUID,
        relationship_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.relationship_detail(
            db,
            tenant_id=tenant_id,
            relationship_id=relationship_id,
        )
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Relationship not found.",
            ) from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/external-references/{xref_id}")
    def get_external_reference(
        tenant_id: uuid.UUID,
        xref_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.external_reference_detail(db, tenant_id=tenant_id, xref_id=xref_id)
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="External reference not found.",
            ) from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/status", response_model=CanonicalStatusResponse)
    def canonical_status(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> CanonicalStatusResponse:
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        lag, meta = count_canonical_lag(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
        )
        cursor_row = db.get(Step3CanonicalCursor, (connection_id, connector))
        ts = cursor_row.last_processed_at if cursor_row else None
        return CanonicalStatusResponse(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            step3_last_processed_replay_sequence=int(meta["step3_last_processed_replay_sequence"]),
            step3_last_processed_id=int(meta["step3_last_processed_id"]),
            step3_lag_rows=lag,
            step3_last_processed_timestamp=ts,
            step2_watermark_replay_sequence=int(meta["step2_watermark_replay_sequence"]),
            step2_watermark_id=int(meta["step2_watermark_id"]),
        )

    @r.get("/tenants/{tenant_id}/canonical/subgraph", response_model=SubgraphResponse)
    def subgraph(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        artifact_id: Annotated[uuid.UUID | None, Query()] = None,
        actor_id: Annotated[uuid.UUID | None, Query()] = None,
        depth: Annotated[int, Query(ge=0, le=5)] = 2,
        include_historical: Annotated[bool, Query()] = False,
    ) -> SubgraphResponse:
        _assert_tenant(db, tenant_id)
        if (artifact_id is None) == (actor_id is None):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Provide exactly one of artifact_id or actor_id.",
            ) from None
        if artifact_id is not None:
            anchor_lit: Literal["artifact", "actor"] = "artifact"
            anchor_uuid: uuid.UUID = artifact_id
        else:
            anchor_lit = "actor"
            assert actor_id is not None
            anchor_uuid = actor_id
        nodes, edges, trunc, treason = cq.build_subgraph(
            db,
            tenant_id=tenant_id,
            anchor_type=anchor_lit,
            anchor_id=anchor_uuid,
            depth=min(depth, 5),
            max_nodes=400,
            current_only=not include_historical,
        )
        return SubgraphResponse(
            anchor=SubgraphAnchor(type=anchor_lit, id=anchor_uuid),
            depth=depth,
            nodes=[SubgraphNode.model_validate(n) for n in nodes],
            edges=[
                SubgraphEdge(
                    id=uuid.UUID(e["id"]),
                    source_id=uuid.UUID(e["source_id"]),
                    target_id=uuid.UUID(e["target_id"]),
                    relation_kind=e["relation_kind"],
                    directed=bool(e["directed"]),
                    valid_from=e["valid_from"],
                    valid_to=e["valid_to"],
                )
                for e in edges
            ],
            truncated=trunc,
            truncation_reason=treason,
        )

    @r.post("/tenants/{tenant_id}/canonical/drain")
    def trigger_canonical_drain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        m = drain_github_canonical(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
        )
        return {
            "raw_rows_processed": m.raw_rows_processed,
            "batches_committed": m.batches_committed,
        }

    @r.post("/tenants/{tenant_id}/canonical/reset-and-resync")
    def reset_and_resync_canonical(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "RESET":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=RESET.",
            ) from None
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None

        reset_github_pipeline_state(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        run = run_github_poll_ingestion_for_tenant(db, settings, tenant_id)
        if run.status == RUN_STATUS_SUCCEEDED:
            p = drain_github_projections(
                db,
                tenant_id=tenant_id,
                connection_id=run.connection_id,
            )
            c = drain_github_canonical(
                db,
                tenant_id=tenant_id,
                connection_id=run.connection_id,
            )
        else:
            p = None
            c = None
        return {
            "reset": True,
            "connection_id": str(connection_id),
            "ingestion_run_id": str(run.id),
            "ingestion_status": run.status,
            "projection_rows_processed": p.raw_rows_processed if p else 0,
            "canonical_rows_processed": c.raw_rows_processed if c else 0,
            "warning": (
                None
                if run.status == RUN_STATUS_SUCCEEDED
                else "Ingestion failed; projections/canonical not drained."
            ),
        }

    @r.post("/tenants/{tenant_id}/canonical/rebuild-from-step1")
    def rebuild_from_step1_github(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "REBUILD":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=REBUILD.",
            ) from None
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        p, c = rebuild_derived_from_step1_github(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return {
            "rebuilt_from_step1": True,
            "connection_id": str(connection_id),
            "projection_rows_processed": p.raw_rows_processed,
            "canonical_rows_processed": c.raw_rows_processed,
        }

    return r

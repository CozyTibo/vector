"""Operator admin HTTP routes."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.admin_request_timing import admin_request_timing
from vector.api.http.deps import get_db, settings_dep
from vector.contracts.operator_admin import (
    AdminBuildInfoResponse,
    OperatorActionRequest,
    OperatorActionResponse,
    OperatorEdgeProvenanceResponse,
    OperatorExecutionThreadResponse,
    OperatorGraphComponentRefreshResponse,
    OperatorGraphSnapshotResponse,
    OperatorIslandsListResponse,
    OperatorOverviewResponse,
    OperatorPeopleDirectoryResponse,
    OperatorPersonProfileResponse,
    OperatorQueuesResponse,
    OperatorRetrievalEntriesResponse,
    OperatorRetrievalEpochsResponse,
    OperatorRetrievalLineageResponse,
    OperatorRuntimeResponse,
    OperatorSynthesisJobsResponse,
)
from vector.domains.cortex.identity.people_directory_v1 import (
    build_people_directory_v1,
    build_person_profile_v1,
)
from vector.domains.cortex.pipeline.admin_graph_component_snapshot import (
    enqueue_graph_component_snapshot_refresh_v1,
)
from vector.domains.cortex.pipeline.operator_admin_actions import execute_operator_action_v1
from vector.domains.cortex.pipeline.operator_admin_inspect import (
    build_operator_graph_snapshot_v1,
    build_operator_islands_list_v1,
    lookup_edge_provenance_v1,
)
from vector.domains.cortex.pipeline.operator_admin_inspect_chains import (
    build_operator_retrieval_epochs_v1,
    build_operator_retrieval_lineage_v1,
    search_operator_execution_thread_v1,
    search_operator_retrieval_entries_v1,
    search_operator_synthesis_jobs_v1,
)
from vector.domains.cortex.pipeline.operator_admin_overview import build_operator_overview_v1
from vector.domains.cortex.pipeline.operator_admin_queues import build_operator_queues_v1
from vector.domains.cortex.pipeline.operator_admin_runtime import build_operator_runtime_v1
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RetrievalIngressError,
    validate_retrieval_ingress_artifact_kind_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.build_info import build_deploy_info_payload
from vector.settings import Settings


def register_cortex_operator_routes(router: APIRouter) -> None:
    @router.get("/build-info", response_model=AdminBuildInfoResponse)
    def get_admin_build_info(
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminBuildInfoResponse:
        return AdminBuildInfoResponse.model_validate(build_deploy_info_payload(settings=settings))

    op = APIRouter(prefix="/tenants/{tenant_id}/cortex/operator", tags=["cortex-operator"])

    def _assert_tenant(db: Session, tenant_id: uuid.UUID) -> None:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")


    @op.get("/overview", response_model=OperatorOverviewResponse)
    def get_operator_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> OperatorOverviewResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.overview", tenant_id=tenant_id):
            raw = build_operator_overview_v1(db, settings, tenant_id=tenant_id)
        return OperatorOverviewResponse.model_validate(raw)

    @op.get("/runtime", response_model=OperatorRuntimeResponse)
    def get_operator_runtime(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        transition_limit: Annotated[int, Query(ge=1, le=200)] = 50,
        transition_offset: Annotated[int, Query(ge=0)] = 0,
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
    ) -> OperatorRuntimeResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.runtime", tenant_id=tenant_id):
            raw = build_operator_runtime_v1(
                db,
                tenant_id=tenant_id,
                transition_limit=transition_limit,
                transition_offset=transition_offset,
                pipeline_run_id=pipeline_run_id,
            )
        return OperatorRuntimeResponse.model_validate(raw)

    @op.post("/actions", response_model=OperatorActionResponse)
    def post_operator_action(
        tenant_id: uuid.UUID,
        body: OperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> OperatorActionResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = execute_operator_action_v1(
                db,
                settings,
                tenant_id=tenant_id,
                action=body.action,
                start_phase=body.start_phase,
                from_phase=body.from_phase,
                confirmation=body.confirmation,
                force=body.force,
                break_glass=body.break_glass,
                scope=body.scope,
                pipeline_run_id=body.pipeline_run_id,
                p0_strategy=body.p0_strategy,
                source_pipeline_run_id=body.source_pipeline_run_id,
            )
            db.commit()
            return OperatorActionResponse.model_validate(raw)
        except ValueError as exc:
            detail = str(exc)
            if detail == "confirmation_mismatch":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Confirmation phrase does not match.",
                ) from exc
            if detail == "p0_recover_failed":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="P0 recovery could not start.",
                ) from exc
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc

    @op.get("/snapshots/graph", response_model=OperatorGraphSnapshotResponse)
    def get_operator_graph_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> OperatorGraphSnapshotResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.snapshots.graph", tenant_id=tenant_id):
            raw = build_operator_graph_snapshot_v1(db, tenant_id=tenant_id)
        return OperatorGraphSnapshotResponse.model_validate(raw)

    @op.post("/snapshots/graph/refresh", response_model=OperatorGraphComponentRefreshResponse)
    def post_operator_graph_snapshot_refresh(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> OperatorGraphComponentRefreshResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.snapshots.graph.refresh", tenant_id=tenant_id):
            raw = enqueue_graph_component_snapshot_refresh_v1(db, tenant_id=tenant_id)
        db.commit()
        return OperatorGraphComponentRefreshResponse.model_validate(raw)

    @op.get("/queues", response_model=OperatorQueuesResponse)
    def get_operator_queues(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        tab: Annotated[
            Literal["synthesis_failed", "tcre_queued", "deferrals", "ingestion_failed"],
            Query(),
        ] = "synthesis_failed",
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> OperatorQueuesResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.queues", tenant_id=tenant_id):
            raw = build_operator_queues_v1(
                db,
                tenant_id=tenant_id,
                tab=tab,
                limit=limit,
                offset=offset,
            )
        return OperatorQueuesResponse.model_validate(raw)

    @op.get("/inspect/edges", response_model=OperatorEdgeProvenanceResponse)
    def get_operator_edge_provenance(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        source: Annotated[uuid.UUID | None, Query()] = None,
        target: Annotated[uuid.UUID | None, Query()] = None,
        link_id: Annotated[uuid.UUID | None, Query()] = None,
        link_type: Annotated[str | None, Query()] = None,
        rule_id: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> OperatorEdgeProvenanceResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = lookup_edge_provenance_v1(
                db,
                tenant_id=tenant_id,
                source_entity_id=source,
                target_entity_id=target,
                link_id=link_id,
                link_type=link_type,
                rule_id=rule_id,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return OperatorEdgeProvenanceResponse.model_validate(raw)

    @op.get("/inspect/islands", response_model=OperatorIslandsListResponse)
    def get_operator_islands_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> OperatorIslandsListResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.inspect.islands", tenant_id=tenant_id):
            raw = build_operator_islands_list_v1(db, tenant_id=tenant_id)
        return OperatorIslandsListResponse.model_validate(raw)

    @op.get("/inspect/retrieval/epochs", response_model=OperatorRetrievalEpochsResponse)
    def get_operator_retrieval_epochs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=20)] = 5,
    ) -> OperatorRetrievalEpochsResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.inspect.retrieval.epochs", tenant_id=tenant_id):
            raw = build_operator_retrieval_epochs_v1(db, tenant_id=tenant_id, limit=limit)
        return OperatorRetrievalEpochsResponse.model_validate(raw)

    @op.get("/inspect/retrieval/entries", response_model=OperatorRetrievalEntriesResponse)
    def get_operator_retrieval_entries(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        entity_id: Annotated[str | None, Query()] = None,
        scope_ref: Annotated[str | None, Query()] = None,
        index_kind: Annotated[str | None, Query()] = None,
        walk_id: Annotated[str | None, Query()] = None,
        external_url: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> OperatorRetrievalEntriesResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = search_operator_retrieval_entries_v1(
                db,
                tenant_id=tenant_id,
                entity_id=entity_id,
                scope_ref=scope_ref,
                index_kind=index_kind,
                walk_id=walk_id,
                external_url=external_url,
                limit=limit,
                offset=offset,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return OperatorRetrievalEntriesResponse.model_validate(raw)

    @op.get("/inspect/retrieval/lineage/{artifact_kind}/{artifact_ref:path}", response_model=OperatorRetrievalLineageResponse)
    def get_operator_retrieval_lineage(
        tenant_id: uuid.UUID,
        artifact_kind: str,
        artifact_ref: str,
        db: Annotated[Session, Depends(get_db)],
        max_lineage_hops: Annotated[int, Query(ge=1, le=256)] = 64,
    ) -> OperatorRetrievalLineageResponse:
        _assert_tenant(db, tenant_id)
        try:
            validate_retrieval_ingress_artifact_kind_v1(artifact_kind)
        except RetrievalIngressError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.code) from exc
        with admin_request_timing(endpoint="operator.inspect.retrieval.lineage", tenant_id=tenant_id):
            raw = build_operator_retrieval_lineage_v1(
                db,
                tenant_id=tenant_id,
                artifact_kind=artifact_kind,
                artifact_ref=artifact_ref,
                max_hops=max_lineage_hops,
            )
        return OperatorRetrievalLineageResponse.model_validate(raw)

    @op.get("/inspect/synthesis/jobs", response_model=OperatorSynthesisJobsResponse)
    def get_operator_synthesis_jobs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        status: Annotated[str | None, Query()] = None,
        q: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> OperatorSynthesisJobsResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.inspect.synthesis.jobs", tenant_id=tenant_id):
            raw = search_operator_synthesis_jobs_v1(
                db,
                tenant_id=tenant_id,
                status=status,
                q=q,
                limit=limit,
                offset=offset,
            )
        return OperatorSynthesisJobsResponse.model_validate(raw)

    @op.get("/inspect/execution/thread", response_model=OperatorExecutionThreadResponse)
    def get_operator_execution_thread(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        walk_id: Annotated[uuid.UUID | None, Query()] = None,
        tcre_job_id: Annotated[uuid.UUID | None, Query()] = None,
        scope_ref: Annotated[str | None, Query()] = None,
        replay_identity: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> OperatorExecutionThreadResponse:
        _assert_tenant(db, tenant_id)
        try:
            raw = search_operator_execution_thread_v1(
                db,
                tenant_id=tenant_id,
                walk_id=walk_id,
                tcre_job_id=tcre_job_id,
                scope_ref=scope_ref,
                replay_identity=replay_identity,
                limit=limit,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return OperatorExecutionThreadResponse.model_validate(raw)

    @op.get("/people", response_model=OperatorPeopleDirectoryResponse)
    def get_operator_people_directory(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> OperatorPeopleDirectoryResponse:
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.people.directory", tenant_id=tenant_id):
            raw = build_people_directory_v1(db, tenant_id=tenant_id, limit=limit, offset=offset)
        return OperatorPeopleDirectoryResponse.model_validate(raw)

    @op.get("/people/{person_id}", response_model=OperatorPersonProfileResponse)
    def get_operator_person_profile(
        tenant_id: uuid.UUID,
        person_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        activity_limit: Annotated[int, Query(ge=1, le=200)] = 80,
    ) -> OperatorPersonProfileResponse:
        _assert_tenant(db, tenant_id)
        try:
            with admin_request_timing(endpoint="operator.people.profile", tenant_id=tenant_id):
                raw = build_person_profile_v1(
                    db,
                    tenant_id=tenant_id,
                    entity_id=person_id,
                    activity_limit=activity_limit,
                )
        except ValueError as exc:
            if str(exc) == "person_not_found":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return OperatorPersonProfileResponse.model_validate(raw)

    router.include_router(op)

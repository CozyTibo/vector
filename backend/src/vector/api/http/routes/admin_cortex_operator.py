"""Operator admin v2 routes (dark launch behind CORTEX_ADMIN_V2)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from vector.api.http.admin_request_timing import admin_request_timing
from vector.api.http.deps import get_db, settings_dep
from vector.contracts.operator_admin import AdminBuildInfoResponse, OperatorOverviewResponse
from vector.domains.cortex.pipeline.operator_admin_overview import build_operator_overview_v1
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

    def _require_operator_v2(settings: Settings) -> None:
        if not settings.cortex_admin_v2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="operator_admin_v2_disabled",
            )

    @op.get("/overview", response_model=OperatorOverviewResponse)
    def get_operator_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> OperatorOverviewResponse:
        _require_operator_v2(settings)
        _assert_tenant(db, tenant_id)
        with admin_request_timing(endpoint="operator.overview", tenant_id=tenant_id):
            raw = build_operator_overview_v1(db, settings, tenant_id=tenant_id)
        return OperatorOverviewResponse.model_validate(raw)

    router.include_router(op)

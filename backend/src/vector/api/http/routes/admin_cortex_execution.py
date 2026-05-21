"""M8 — consolidated admin execution surface (inspect + engine commands only)."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.execution.admin_commands import (
    build_execution_inspect_v1,
    clear_derived_execution_outputs_v1,
    execution_rerun_v1,
    restart_execution_from_phase_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def register_cortex_execution_routes(router: APIRouter) -> None:
    er = APIRouter(prefix="/tenants/{tenant_id}/cortex/execution", tags=["cortex-execution"])

    def _assert_tenant(db: Session, tenant_id: uuid.UUID) -> None:
        if tenancy_repo.get_tenant_by_id(db, tenant_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant_not_found")

    @er.get("/state")
    def get_execution_state(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
        transition_limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        """Inspect lease, progression snapshot, and recent FSM transitions."""
        _assert_tenant(db, tenant_id)
        return build_execution_inspect_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            transition_limit=transition_limit,
        )

    @er.get("/transition-log")
    def get_execution_transition_log(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        """Transition log slice (subset of ``/state``)."""
        _assert_tenant(db, tenant_id)
        body = build_execution_inspect_v1(
            db,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            transition_limit=limit,
        )
        return {
            "surface_kind": "execution_transition_log",
            "tenant_id": str(tenant_id),
            "transitions": body.get("transitions") or [],
        }

    @er.post("/restart")
    def post_execution_restart(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        from_phase: Annotated[str, Query()],
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
        force: Annotated[bool, Query()] = False,
        break_glass: Annotated[bool, Query()] = False,
    ) -> dict[str, Any]:
        """Set execution cursor, mark dirty, enqueue execution slice."""
        _assert_tenant(db, tenant_id)
        try:
            out = restart_execution_from_phase_v1(
                db,
                tenant_id=tenant_id,
                from_phase=from_phase,
                pipeline_run_id=pipeline_run_id,
                force=force,
                break_glass=break_glass,
            )
            db.commit()
            return out
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @er.post("/clear")
    def post_execution_clear(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        from_phase: Annotated[str, Query()],
        scope: Annotated[str | None, Query()] = None,
        flush_all: Annotated[bool, Query()] = False,
    ) -> dict[str, Any]:
        """Clear derived outputs from ``from_phase`` (replay matrix)."""
        _assert_tenant(db, tenant_id)
        try:
            out = clear_derived_execution_outputs_v1(
                db,
                tenant_id=tenant_id,
                from_phase=from_phase,
                scope=scope,
                flush_all=flush_all,
            )
            db.commit()
            return out
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @er.post("/rerun")
    def post_execution_rerun(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        from_phase: Annotated[str, Query()],
        pipeline_run_id: Annotated[uuid.UUID | None, Query()] = None,
        scope: Annotated[str | None, Query()] = None,
        force: Annotated[bool, Query()] = False,
        break_glass: Annotated[bool, Query()] = False,
        flush_all: Annotated[bool, Query()] = False,
        run_determinism_repair: Annotated[bool, Query()] = False,
    ) -> dict[str, Any]:
        """Atomic clear + restart (replaces legacy admin bypass mutations)."""
        _assert_tenant(db, tenant_id)
        try:
            out = execution_rerun_v1(
                db,
                tenant_id=tenant_id,
                from_phase=from_phase,
                pipeline_run_id=pipeline_run_id,
                scope=scope,
                force=force,
                break_glass=break_glass,
                flush_all=flush_all,
                run_determinism_repair=run_determinism_repair,
            )
            db.commit()
            return out
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    router.include_router(er)

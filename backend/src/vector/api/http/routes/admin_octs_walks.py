"""Admin HTTP routes for OCTS traversal (**P05-17**–**25**).

Walks: ``phase-05-walk-api-contracts.md``; derived index replay verify: **Step 20**
``phase-05-index-replay-doctrine.md``; traversal equivalence / engine identity: **Step 21**
``phase-05-traversal-equivalence-doctrine.md``; control plane aggregate: **Step 24**
``phase-05-control-plane-doctrine.md``; readiness + economics receipts: **Step 25**
``phase-05-readiness-economics-doctrine.md``.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Annotated, Any

import jsonschema  # type: ignore[import-untyped]
from fastapi import APIRouter, Body, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db
from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    TraversalReasoningBoundaryError,
    validate_oct_walk_request_v1,
)
from vector.domains.cortex.traversal.derived_index_contract import (
    DerivedIndexContractError,
    compute_index_content_hash_v1,
    validate_derived_index_artifact_contract_v1,
)
from vector.domains.cortex.traversal.index_replay_contract import (
    INDEX_REPLAY_CONTRACT_SCHEMA_VERSION,
    validate_oct_derived_index_replay_verify_body_v1,
)
from vector.domains.cortex.traversal.traversal_control_plane import build_octs_traversal_control_plane_v1
from vector.domains.cortex.traversal.traversal_readiness_economics import (
    ProbeProfileV1,
    build_octs_traversal_readiness_economics_receipt_v1,
)
from vector.domains.cortex.traversal.traversal_equivalence_contract import (
    OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION,
    OctsEngineIdentityError,
    resolve_oct_engine_build_id_v1,
)
from vector.domains.cortex.traversal.walk_api_contract import (
    API_WALK_CONTRACT_SCHEMA_VERSION,
    WalkApiRecordV1,
    build_stub_completed_walk_payload_v1,
    canonical_octs_api_error_body_v1,
    completed_sync_walk_api_public_document_v1,
    list_fs_api01_sync_request_json_cap_violations_v1,
    list_fs_api01_sync_response_json_cap_violations_v1,
    octs_walk_api_memory_store_v1,
    sync_walk_policy_cap_errors_for_api_v1,
)
from vector.domains.cortex.traversal.walk_policy import (
    WalkPolicyInvariantError,
    validate_walk_policy_for_request_v1,
)
from vector.domains.cortex.traversal.walk_replay_contract import (
    WalkReplayResolutionError,
    prepare_effective_oct_walk_request_v1,
)
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

_STRICT_IDEMPOTENCY_ENV = "VECTOR_OCTS_STRICT_IDEMPOTENCY"
_ENFORCE_ENGINE_IDENTITY_ENV = "VECTOR_OCTS_ENFORCE_ENGINE_IDENTITY"


def _assert_tenant_or_error(session: Session, tenant_id: uuid.UUID) -> JSONResponse | None:
    if tenancy_repo.get_tenant_by_id(session, tenant_id) is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=canonical_octs_api_error_body_v1("tenant_not_found", {}),
        )
    return None


def _api_err(status_code: int, error_code: str, **details: str | int | bool) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=canonical_octs_api_error_body_v1(error_code, details),
    )


def register_octs_walk_traversal_routes(router: APIRouter) -> None:
    """Register ``/tenants/{tenant_id}/cortex/traversal/*`` OCTS admin subtree."""

    walk = APIRouter(
        prefix="/tenants/{tenant_id}/cortex/traversal", tags=["admin-cortex-traversal"]
    )

    @walk.post("/walks", response_model=None)
    def post_octs_walk(
        tenant_id: uuid.UUID,
        body: Annotated[dict[str, Any], Body(...)],
        db: Annotated[Session, Depends(get_db)],
        async_q: Annotated[str | None, Query(alias="async")] = None,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> JSONResponse | dict[str, Any]:
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad

        if os.environ.get(_STRICT_IDEMPOTENCY_ENV, "").lower() in ("1", "true", "yes"):
            if not idempotency_key or not str(idempotency_key).strip():
                return _api_err(
                    status.HTTP_400_BAD_REQUEST,
                    "idempotency_key_required",
                    mode="strict",
                )

        try:
            validate_oct_walk_request_v1(body)
        except TraversalReasoningBoundaryError:
            return _api_err(status.HTTP_400_BAD_REQUEST, "walk_request_schema")

        store = octs_walk_api_memory_store_v1()
        try:
            effective, replay_lineage = prepare_effective_oct_walk_request_v1(
                body, tenant_id=tenant_id, store=store
            )
        except WalkReplayResolutionError as exc:
            return _api_err(exc.http_status, exc.error_code, **exc.details)

        if isinstance(effective.get("temporal_anchor"), dict):
            ta_tid = str(effective["temporal_anchor"].get("tenant_id", "")).lower()
            if ta_tid != str(tenant_id).lower():
                return _api_err(
                    status.HTTP_400_BAD_REQUEST,
                    "tenant_mismatch",
                    field="temporal_anchor.tenant_id",
                )

        if (
            os.environ.get(_ENFORCE_ENGINE_IDENTITY_ENV, "").lower() in ("1", "true", "yes")
            and async_q != "1"
            and effective.get("exploration_mode") is not True
        ):
            try:
                resolve_oct_engine_build_id_v1()
            except OctsEngineIdentityError as exc:
                return _api_err(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "engine_identity_unavailable",
                    reason=exc.error_code,
                )

        is_async = async_q == "1"
        if not is_async:
            req_cap = list_fs_api01_sync_request_json_cap_violations_v1(effective)
            if req_cap:
                return JSONResponse(
                    status_code=413,
                    content=canonical_octs_api_error_body_v1(
                        "walk_too_large",
                        {"violations": ";".join(sorted(req_cap))},
                    ),
                )

        if not is_async:
            cap_errs = sync_walk_policy_cap_errors_for_api_v1(effective["walk_policy"])
            if cap_errs:
                return JSONResponse(
                    status_code=413,
                    content=canonical_octs_api_error_body_v1(
                        "walk_too_large",
                        {"violations": ";".join(sorted(cap_errs))},
                    ),
                )

        try:
            validate_walk_policy_for_request_v1(
                effective["walk_policy"],
                walk_execution_strategy=str(effective["walk_execution_strategy"]),
                exploration_mode=bool(effective["exploration_mode"]),
                enforce_sync_caps=False,
            )
        except WalkPolicyInvariantError:
            return _api_err(status.HTTP_400_BAD_REQUEST, "walk_policy_invalid")

        idem = str(idempotency_key).strip() if idempotency_key else None
        if idem:
            existing = store.lookup_idempotency(tenant_id, idem)
            if existing is not None:
                rec = store.get(tenant_id, existing)
                if rec is not None:
                    return _poll_walk_or_sync_response_cap_v1(rec)

        walk_id = uuid.uuid4()
        if is_async:
            job_id = str(uuid.uuid4())
            rec = store.insert_async_accepted(
                tenant_id=tenant_id,
                walk_id=walk_id,
                job_id=job_id,
                request_body=dict(effective),
                idempotency_key=idem,
            )
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "octs_walk_api_version": API_WALK_CONTRACT_SCHEMA_VERSION,
                    "walk_id": str(rec.walk_id),
                    "status": rec.status,
                    "job_id": job_id,
                },
            )

        try:
            payload = build_stub_completed_walk_payload_v1(
                effective,
                tenant_id=tenant_id,
                replay_lineage=replay_lineage,
            )
        except ValueError:
            return _api_err(status.HTTP_400_BAD_REQUEST, "stub_build_failed")

        preview = completed_sync_walk_api_public_document_v1(walk_id, payload)
        cap_v = list_fs_api01_sync_response_json_cap_violations_v1(preview)
        if cap_v:
            return JSONResponse(
                status_code=413,
                content=canonical_octs_api_error_body_v1(
                    "walk_too_large",
                    {"violations": ";".join(sorted(cap_v))},
                ),
            )

        rec = store.insert_completed_sync(
            tenant_id=tenant_id,
            walk_id=walk_id,
            request_body=dict(effective),
            walk_payload=payload,
            idempotency_key=idem,
        )
        return _poll_walk_or_sync_response_cap_v1(rec)

    @walk.get("/control-plane", response_model=None)
    def get_octs_traversal_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        include_exploration: Annotated[str | None, Query(alias="include_exploration")] = None,
    ) -> JSONResponse | dict[str, Any]:
        """**P05-24** — structural operator aggregate (queue / abort classes / budget histogram)."""
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad
        inc: bool | None
        if include_exploration is None or str(include_exploration).strip() == "":
            inc = None
        elif str(include_exploration).strip() in ("1", "true", "yes"):
            inc = True
        elif str(include_exploration).strip() in ("0", "false", "no"):
            inc = False
        else:
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "control_plane_bad_include_exploration",
            )
        return build_octs_traversal_control_plane_v1(db, tenant_id=tenant_id, include_exploration=inc)

    @walk.get("/readiness-economics", response_model=None)
    def get_octs_traversal_readiness_economics(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        probe_profile: Annotated[str | None, Query(alias="probe_profile")] = None,
    ) -> JSONResponse | dict[str, Any]:
        """**P05-25** — numeric readiness / economics receipt (golden fixtures; read-only)."""
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad
        raw = (probe_profile or "clean").strip().lower()
        if raw in ("", "clean"):
            profile: ProbeProfileV1 = "clean"
        elif raw == "hostile":
            profile = "hostile"
        else:
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "readiness_economics_bad_probe_profile",
            )
        return build_octs_traversal_readiness_economics_receipt_v1(
            tenant_id=tenant_id,
            profile=profile,
        )

    @walk.get("/engine-identity", response_model=None)
    def get_octs_engine_identity(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """**P05-21** — resolved ``engine_build_id`` for operators (**ENG**), non-throwing."""
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad
        try:
            bid = resolve_oct_engine_build_id_v1()
        except OctsEngineIdentityError as exc:
            return {
                "octs_traversal_equivalence_contract_version": OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION,
                "engine_identity_available": False,
                "engine_build_id": None,
                "error_code": exc.error_code,
            }
        return {
            "octs_traversal_equivalence_contract_version": OCTS_TRAVERSAL_EQUIVALENCE_CONTRACT_SCHEMA_VERSION,
            "engine_identity_available": True,
            "engine_build_id": bid,
        }

    @walk.get("/walks/{walk_id}", response_model=None)
    def get_octs_walk(
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad
        rec = octs_walk_api_memory_store_v1().get(tenant_id, walk_id)
        if rec is None:
            return _api_err(status.HTTP_404_NOT_FOUND, "walk_not_found")
        return _poll_walk_or_sync_response_cap_v1(rec)

    @walk.post("/walks/{walk_id}/cancel", response_model=None)
    def post_octs_walk_cancel(
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad
        store = octs_walk_api_memory_store_v1()
        rec = store.get(tenant_id, walk_id)
        if rec is None:
            return _api_err(status.HTTP_404_NOT_FOUND, "walk_not_found")
        if rec.status in ("completed", "failed", "cancelled"):
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "cannot_cancel_terminal",
                terminal_status=rec.status,
            )
        updated = store.cancel(tenant_id, walk_id)
        assert updated is not None
        return {
            "octs_walk_api_version": API_WALK_CONTRACT_SCHEMA_VERSION,
            "walk_id": str(updated.walk_id),
            "status": updated.status,
        }

    @walk.post("/derived-index/replay-verify", response_model=None)
    def post_derived_index_replay_verify(
        tenant_id: uuid.UUID,
        body: Annotated[dict[str, Any], Body(...)],
        db: Annotated[Session, Depends(get_db)],
    ) -> JSONResponse | dict[str, Any]:
        """**P05-20** — recompute ``index_content_hash``; optional strict expected pin (**IRJ**)."""
        bad = _assert_tenant_or_error(db, tenant_id)
        if bad is not None:
            return bad

        try:
            validate_oct_derived_index_replay_verify_body_v1(dict(body))
        except jsonschema.ValidationError:
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "index_replay_verify_schema",
                reason="json_schema",
            )
        except (OSError, RuntimeError, TypeError, ValueError):
            return _api_err(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "index_replay_verify_schema_load_failed",
            )

        artifact = body.get("artifact")
        if not isinstance(artifact, dict):
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "index_replay_verify_schema",
                reason="artifact_not_object",
            )

        try:
            validate_derived_index_artifact_contract_v1(artifact)
        except DerivedIndexContractError:
            return _api_err(
                status.HTTP_400_BAD_REQUEST,
                "derived_index_artifact_invalid",
            )

        h1 = compute_index_content_hash_v1(artifact)
        h2 = compute_index_content_hash_v1(json.loads(json.dumps(artifact)))
        if h1 != h2:
            return _api_err(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "index_replay_double_run_internal_mismatch",
            )

        exp = body.get("expected_index_content_hash")
        if exp is not None and str(exp) != str(h1):
            return JSONResponse(
                status_code=409,
                content=canonical_octs_api_error_body_v1(
                    "index_replay_hash_mismatch",
                    {"expected": str(exp), "actual": str(h1)},
                ),
            )

        return {
            "octs_index_replay_api_version": INDEX_REPLAY_CONTRACT_SCHEMA_VERSION,
            "index_content_hash": str(h1),
            "double_run_equal": True,
        }

    router.include_router(walk)


def _poll_walk_or_sync_response_cap_v1(rec: WalkApiRecordV1) -> JSONResponse | dict[str, Any]:
    """**FS-API-01** — completed sync poll/POST bodies must fit **SYNC_MAX_RESPONSE_JSON_BYTES**."""
    data = _serialize_get_walk(rec)
    if rec.status == "completed" and rec.walk_payload is not None:
        vio = list_fs_api01_sync_response_json_cap_violations_v1(data)
        if vio:
            return JSONResponse(
                status_code=413,
                content=canonical_octs_api_error_body_v1(
                    "walk_too_large",
                    {"violations": ";".join(sorted(vio))},
                ),
            )
    return data


def _serialize_get_walk(rec: WalkApiRecordV1) -> dict[str, Any]:
    if rec.status == "completed" and rec.walk_payload is not None:
        return completed_sync_walk_api_public_document_v1(rec.walk_id, rec.walk_payload)
    out: dict[str, Any] = {
        "octs_walk_api_version": API_WALK_CONTRACT_SCHEMA_VERSION,
        "walk_id": str(rec.walk_id),
        "status": rec.status,
    }
    if rec.job_id:
        out["job_id"] = rec.job_id
    return out

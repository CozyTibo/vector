"""Phase 05 P05-17/18/19/21 — walk HTTP API contracts (**RULE API-0/ERR**, **G-P05-API-01..03**).

Normative: ``DOCS/cortex/05-traversal/phase-05-walk-api-contracts.md`` (Steps **17–19**).
Authoritative request shape: ``schemas/octs-walk-request-v1.schema.json``.
OpenAPI fragment: ``schemas/generated/octs-walk-api-v1.openapi.json`` (generator script; **Step 21**
``GET …/engine-identity``).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Final, Literal, cast

from vector.domains.cortex.traversal.exploration_mode_contract import (
    EXECUTION_PARTITION_EXPLORATION,
)
from vector.domains.cortex.traversal.walk_policy import (
    SYNC_MAX_EDGES_VISITED,
    SYNC_MAX_HOPS,
    SYNC_MAX_REQUEST_JSON_BYTES,
    SYNC_MAX_RESPONSE_JSON_BYTES,
    SYNC_MAX_WALL_MS,
    compute_policy_hash_v1,
    list_walk_policy_sync_cap_violations_v1,
)
from vector.domains.cortex.traversal.walk_result_contract import (
    compute_walk_result_hash_v1,
    validate_walk_result_hash_body_contract_v1,
)

API_WALK_CONTRACT_SCHEMA_VERSION: Final[int] = 3

OCTS_STUB_ENGINE_BUILD_ID: Final[str] = "octs.walk.stub.v1"

WalkApiStatusV1 = Literal["queued", "running", "completed", "failed", "cancelled"]


def resolve_engine_build_ref_for_persist_v1() -> str:
    """Pinned ``engine_build_id`` when configured; else stub ref (async accept / CI)."""
    from vector.domains.cortex.traversal.traversal_equivalence_contract import (
        OctsEngineIdentityError,
        resolve_oct_engine_build_id_v1,
    )

    try:
        return resolve_oct_engine_build_id_v1()
    except OctsEngineIdentityError:
        return OCTS_STUB_ENGINE_BUILD_ID


def _repo_root_with_oct_schemas() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = (
            root
            / "DOCS"
            / "cortex"
            / "05-traversal"
            / "schemas"
            / "octs-walk-request-v1.schema.json"
        )
        if marker.is_file():
            return root
    msg = "Could not locate DOCS/cortex/05-traversal/schemas from walk_api_contract."
    raise RuntimeError(msg)


def octs_walk_api_openapi_path() -> Path:
    """Generated OpenAPI 3 document for admin walk paths (**RULE API-0**)."""
    root = _repo_root_with_oct_schemas()
    return (
        root
        / "DOCS"
        / "cortex"
        / "05-traversal"
        / "schemas"
        / "generated"
        / "octs-walk-api-v1.openapi.json"
    )


def canonical_octs_api_error_body_v1(
    error_code: str,
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """**RULE API-ERR** — sorted ``details`` keys; values JSON primitives only."""
    raw: dict[str, Any] = {}
    if details:
        for k in sorted(details.keys(), key=str):
            v = details[k]
            if v is None:
                continue
            if isinstance(v, bool | int | str | float):
                raw[str(k)] = v
            else:
                msg = f"details.{k} must be a JSON primitive"
                raise TypeError(msg)
    return {"error_code": str(error_code), "details": raw}


def canonical_octs_walk_api_json_utf8_len_v1(obj: Any) -> int:
    """Canonical JSON UTF-8 length (**OCTS-CANON-1**-style) for **Step 18** byte caps."""
    return len(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def list_fs_api01_sync_request_json_cap_violations_v1(body: Mapping[str, Any]) -> list[str]:
    """**FS-API-01** — sync POST JSON body must fit **SYNC_MAX_REQUEST_JSON_BYTES**."""
    n = canonical_octs_walk_api_json_utf8_len_v1(dict(body))
    if n > SYNC_MAX_REQUEST_JSON_BYTES:
        return [f"sync_request_json_bytes:{n}>{SYNC_MAX_REQUEST_JSON_BYTES}"]
    return []


def list_fs_api01_sync_response_json_cap_violations_v1(response: Mapping[str, Any]) -> list[str]:
    """**FS-API-01** — sync GET/POST completed view must fit **SYNC_MAX_RESPONSE_JSON_BYTES**."""
    n = canonical_octs_walk_api_json_utf8_len_v1(dict(response))
    if n > SYNC_MAX_RESPONSE_JSON_BYTES:
        return [f"sync_response_json_bytes:{n}>{SYNC_MAX_RESPONSE_JSON_BYTES}"]
    return []


def completed_sync_walk_api_public_document_v1(
    walk_id: uuid.UUID,
    walk_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Public JSON shape for a **completed** sync walk (**RULE API-01**)."""
    pl = dict(walk_payload)
    wr = pl["walk_result"]
    return {
        "octs_walk_api_version": API_WALK_CONTRACT_SCHEMA_VERSION,
        "walk_id": str(walk_id),
        "status": "completed",
        "walk_result": wr,
        "telemetry": pl.get("telemetry", {}),
    }


def verify_gp05_api03_sync_walk_limits_static() -> dict[str, Any]:
    """**G-P05-API-03** — doctrine sync caps + golden stub response under byte cap."""
    errors: list[str] = []
    if SYNC_MAX_HOPS != 32:
        errors.append(f"SYNC_MAX_HOPS_drift:{SYNC_MAX_HOPS}")
    if SYNC_MAX_EDGES_VISITED != 10_000:
        errors.append(f"SYNC_MAX_EDGES_VISITED_drift:{SYNC_MAX_EDGES_VISITED}")
    if SYNC_MAX_WALL_MS != 150:
        errors.append(f"SYNC_MAX_WALL_MS_drift:{SYNC_MAX_WALL_MS}")
    if SYNC_MAX_RESPONSE_JSON_BYTES != 256 * 1024:
        errors.append(f"SYNC_MAX_RESPONSE_JSON_BYTES_drift:{SYNC_MAX_RESPONSE_JSON_BYTES}")
    if SYNC_MAX_REQUEST_JSON_BYTES != 256 * 1024:
        errors.append(f"SYNC_MAX_REQUEST_JSON_BYTES_drift:{SYNC_MAX_REQUEST_JSON_BYTES}")

    if not errors:
        try:
            from vector.domains.cortex.traversal.traversal_vs_reasoning import (
                oct_walk_request_minimal_fixture_path,
            )

            inner = json.loads(oct_walk_request_minimal_fixture_path().read_text(encoding="utf-8"))
            if not isinstance(inner, dict):
                errors.append("walk_request_minimal_not_object")
            else:
                ta = inner.get("temporal_anchor")
                if not isinstance(ta, dict) or not ta.get("tenant_id"):
                    errors.append("walk_request_minimal_missing_tenant")
                else:
                    tid = uuid.UUID(str(ta["tenant_id"]))
                    payload = build_stub_completed_walk_payload_v1(inner, tenant_id=tid)
                    wid = uuid.UUID("00000000-0000-4000-8000-0000000000a1")
                    view = completed_sync_walk_api_public_document_v1(wid, payload)
                    cap = list_fs_api01_sync_response_json_cap_violations_v1(view)
                    if cap:
                        errors.extend(cap)
                    req_v = list_fs_api01_sync_request_json_cap_violations_v1(inner)
                    if req_v:
                        errors.extend(req_v)
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            errors.append(f"fixture_or_build_failed:{exc}")

    return _api_gate("G-P05-API-03", "sync_walk_limits_doctrine", errors)


def verify_gp05_api01_openapi_walk_paths_static() -> dict[str, Any]:
    """**G-P05-API-01** — generated OpenAPI lists normative admin traversal paths (walks + Step 20–21)."""
    errors: list[str] = []
    p = octs_walk_api_openapi_path()
    if not p.is_file():
        errors.append(f"missing_openapi:{p}")
        return _api_gate("G-P05-API-01", "openapi_walk_contract_paths", errors)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"openapi_json_invalid:{exc}")
        return _api_gate("G-P05-API-01", "openapi_walk_contract_paths", errors)
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        errors.append("openapi_paths_missing")
        return _api_gate("G-P05-API-01", "openapi_walk_contract_paths", errors)
    expected_post = "/admin/tenants/{tid}/cortex/traversal/walks"
    expected_get = "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}"
    expected_cancel = "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}/cancel"
    expected_engine = "/admin/tenants/{tid}/cortex/traversal/engine-identity"
    expected_replay = "/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify"
    expected_control = "/admin/tenants/{tid}/cortex/traversal/control-plane"
    expected_readiness = "/admin/tenants/{tid}/cortex/traversal/readiness-economics"
    for ep in (
        expected_post,
        expected_get,
        expected_cancel,
        expected_engine,
        expected_replay,
        expected_control,
        expected_readiness,
    ):
        if ep not in paths:
            errors.append(f"missing_path:{ep}")
    post_obj = paths.get(expected_post)
    if isinstance(post_obj, dict) and "post" not in post_obj:
        errors.append("missing_post_on_walks_collection")
    get_obj = paths.get(expected_get)
    if isinstance(get_obj, dict) and "get" not in get_obj:
        errors.append("missing_get_on_walk_item")
    cancel_obj = paths.get(expected_cancel)
    if isinstance(cancel_obj, dict) and "post" not in cancel_obj:
        errors.append("missing_post_on_cancel")
    replay_obj = paths.get(expected_replay)
    if isinstance(replay_obj, dict) and "post" not in replay_obj:
        errors.append("missing_post_on_derived_index_replay_verify")
    engine_obj = paths.get(expected_engine)
    if isinstance(engine_obj, dict) and "get" not in engine_obj:
        errors.append("missing_get_on_engine_identity")
    control_obj = paths.get(expected_control)
    if isinstance(control_obj, dict) and "get" not in control_obj:
        errors.append("missing_get_on_control_plane")
    readiness_obj = paths.get(expected_readiness)
    if isinstance(readiness_obj, dict) and "get" not in readiness_obj:
        errors.append("missing_get_on_readiness_economics")
    return _api_gate("G-P05-API-01", "openapi_walk_contract_paths", errors)


def verify_gp05_api02_openapi_security_static() -> dict[str, Any]:
    """**G-P05-API-02** — OpenAPI declares HTTP Basic security for walk admin paths."""
    errors: list[str] = []
    p = octs_walk_api_openapi_path()
    if not p.is_file():
        errors.append(f"missing_openapi:{p}")
        return _api_gate("G-P05-API-02", "openapi_admin_security", errors)
    doc = json.loads(p.read_text(encoding="utf-8"))
    comps = doc.get("components")
    if not isinstance(comps, dict) or "securitySchemes" not in comps:
        errors.append("missing_components_security_schemes")
        return _api_gate("G-P05-API-02", "openapi_admin_security", errors)
    schemes = comps["securitySchemes"]
    if not isinstance(schemes, dict) or "admin_basic" not in schemes:
        errors.append("missing_admin_basic_security_scheme")
    return _api_gate("G-P05-API-02", "openapi_admin_security", errors)


def _api_gate(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "api_walk_contract_schema_version": API_WALK_CONTRACT_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def build_stub_completed_walk_payload_v1(
    request: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
    replay_lineage: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Deterministic minimal completed walk for sync stub (**RULE API-01** shape).

    When ``replay_lineage`` is set (**Step 19**), telemetry includes **WRJ** lineage fields
    (``engine_build_id``, ``replay_of_walk_id``, ``original_walk_result_hash``).
    """
    ta = request.get("temporal_anchor")
    if not isinstance(ta, dict):
        msg = "temporal_anchor required for sync stub completion"
        raise ValueError(msg)
    if str(ta.get("tenant_id", "")).lower() != str(tenant_id).lower():
        msg = "temporal_anchor.tenant_id must match path tenant"
        raise ValueError(msg)
    policy = request["walk_policy"]
    strategy = str(request["walk_execution_strategy"])
    policy_hash = compute_policy_hash_v1(
        cast(Mapping[str, Any], policy), walk_execution_strategy=strategy
    )
    starts = request["start_node_ids"]
    if not isinstance(starts, list):
        msg = "start_node_ids must be a list"
        raise ValueError(msg)
    hash_body: dict[str, Any] = {
        "octs_schema_version": 1,
        "temporal_anchor": dict(ta),
        "policy_hash": policy_hash,
        "start_node_ids": sorted(str(x) for x in starts),
        "termination_reason": "budget_exhausted",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
    }
    if request.get("exploration_mode") is True:
        hash_body["execution_partition"] = EXECUTION_PARTITION_EXPLORATION
        hash_body["non_authoritative"] = True
    validate_walk_result_hash_body_contract_v1(hash_body)
    wh = compute_walk_result_hash_v1(hash_body)
    telemetry: dict[str, Any] = {
        "wall_ms": 0,
        "worker_hostname": "stub",
        "engine_build_id": OCTS_STUB_ENGINE_BUILD_ID,
    }
    if replay_lineage is not None:
        telemetry["replay_of_walk_id"] = str(replay_lineage["replay_of_walk_id"])
        telemetry["original_walk_result_hash"] = str(
            replay_lineage["original_walk_result_hash"]
        )
    return {
        "walk_result": {"hash_body": hash_body, "walk_result_hash": wh},
        "telemetry": telemetry,
    }


@dataclass
class WalkApiRecordV1:
    walk_id: uuid.UUID
    tenant_id: uuid.UUID
    status: WalkApiStatusV1
    request_body: dict[str, Any]
    walk_payload: dict[str, Any] | None = None
    job_id: str | None = None
    idempotency_key: str | None = None


class OctsWalkApiMemoryStore:
    """Process-local walk records (Step 17 stub — replaced by durable store in later steps)."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_walk: dict[tuple[uuid.UUID, uuid.UUID], WalkApiRecordV1] = {}
        self._by_idem: dict[tuple[uuid.UUID, str], uuid.UUID] = {}

    def get(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None:
        with self._lock:
            return self._by_walk.get((tenant_id, walk_id))

    def insert_completed_sync(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        request_body: dict[str, Any],
        walk_payload: dict[str, Any],
        idempotency_key: str | None,
        replay_lineage: dict[str, Any] | None = None,
    ) -> WalkApiRecordV1:
        rec = WalkApiRecordV1(
            walk_id=walk_id,
            tenant_id=tenant_id,
            status="completed",
            request_body=request_body,
            walk_payload=walk_payload,
            idempotency_key=idempotency_key,
        )
        with self._lock:
            self._by_walk[(tenant_id, walk_id)] = rec
            if idempotency_key:
                self._by_idem[(tenant_id, idempotency_key)] = walk_id
        return rec

    def insert_async_accepted(
        self,
        *,
        tenant_id: uuid.UUID,
        walk_id: uuid.UUID,
        job_id: str,
        request_body: dict[str, Any],
        idempotency_key: str | None,
    ) -> WalkApiRecordV1:
        rec = WalkApiRecordV1(
            walk_id=walk_id,
            tenant_id=tenant_id,
            status="running",
            request_body=request_body,
            walk_payload=None,
            job_id=job_id,
            idempotency_key=idempotency_key,
        )
        with self._lock:
            self._by_walk[(tenant_id, walk_id)] = rec
            if idempotency_key:
                self._by_idem[(tenant_id, idempotency_key)] = walk_id
        return rec

    def lookup_idempotency(self, tenant_id: uuid.UUID, key: str) -> uuid.UUID | None:
        with self._lock:
            return self._by_idem.get((tenant_id, key))

    def cancel(self, tenant_id: uuid.UUID, walk_id: uuid.UUID) -> WalkApiRecordV1 | None:
        with self._lock:
            rec = self._by_walk.get((tenant_id, walk_id))
            if rec is None:
                return None
            if rec.status in ("completed", "failed", "cancelled"):
                return rec
            rec.status = "cancelled"
            return rec

    def walk_queue_depth_for_tenant(self, tenant_id: uuid.UUID) -> int:
        """Count **queued** + **running** walks for ``tenant_id`` (structural queue depth)."""
        with self._lock:
            return sum(
                1
                for (tid, _wid), rec in self._by_walk.items()
                if tid == tenant_id and rec.status in ("queued", "running")
            )

    def list_walk_records_for_tenant_v1(self, tenant_id: uuid.UUID) -> list[WalkApiRecordV1]:
        """All walk records for ``tenant_id``, sorted by ``walk_id`` (deterministic control-plane reads)."""
        with self._lock:
            items = [rec for (tid, _wid), rec in self._by_walk.items() if tid == tenant_id]
        items.sort(key=lambda r: str(r.walk_id))
        return items


_GLOBAL_STORE = OctsWalkApiMemoryStore()


def octs_walk_api_memory_store_v1() -> OctsWalkApiMemoryStore:
    return _GLOBAL_STORE


def sync_walk_policy_cap_errors_for_api_v1(walk_policy: Mapping[str, Any]) -> list[str]:
    """**FS-API-01** / Step 18 sync caps — reuse **G-P05-POL-02** list."""
    return list_walk_policy_sync_cap_violations_v1(walk_policy)

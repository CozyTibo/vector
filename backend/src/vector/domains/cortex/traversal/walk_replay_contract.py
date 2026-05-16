"""Phase 05 Step 19 — walk replay resolution (**``phase-05-walk-replay-doctrine.md``**).

Pinned **inherit** replay against the Step **17** in-memory walk store: resolve
``inherit_walk_id`` to the parent completed request snapshot, enforce input equality
(**WRJ** replay pin semantics at the HTTP stub layer), optional
``expected_walk_result_hash`` strict check, and emit replay lineage fields in stub
telemetry (``engine_build_id``, ``replay_of_walk_id``, ``original_walk_result_hash``).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.traversal.runtime.durable_walk_store import OctsWalkStoreProtocol

OCTS_WALK_REPLAY_RESOLUTION_SCHEMA_VERSION: Final[int] = 1


def canonical_json_equality_v1(a: Any, b: Any) -> bool:
    """Structural equality under **OCTS-CANON-1**-style compact sorted JSON."""
    return json.dumps(a, sort_keys=True, separators=(",", ":")) == json.dumps(
        b, sort_keys=True, separators=(",", ":")
    )


class WalkReplayResolutionError(Exception):
    """Raised when ``inherit_walk_id`` replay cannot be resolved (**FS-WRJ-*** layer)."""

    def __init__(
        self,
        *,
        error_code: str,
        http_status: int = 400,
        details: dict[str, str | int | bool] | None = None,
    ) -> None:
        super().__init__(error_code)
        self.error_code = error_code
        self.http_status = http_status
        self.details = details or {}


def prepare_effective_oct_walk_request_v1(
    body: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
    store: OctsWalkStoreProtocol,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    """Return ``(effective_request, replay_lineage)`` for ``build_stub_completed_walk_payload_v1``.

    ``replay_lineage`` is ``None`` when this is not an inherit replay.
    """
    raw = dict(body)
    inherit = raw.get("inherit_walk_id")
    if inherit is None or inherit == "":
        return raw, None

    try:
        parent_id = uuid.UUID(str(inherit))
    except ValueError as exc:
        raise WalkReplayResolutionError(
            error_code="walk_request_schema",
            details={"field": "inherit_walk_id"},
        ) from exc

    parent = store.get(tenant_id, parent_id)
    if parent is None:
        raise WalkReplayResolutionError(
            error_code="source_walk_not_found",
            http_status=404,
            details={"inherit_walk_id": str(parent_id)},
        )
    if parent.status != "completed" or parent.walk_payload is None:
        raise WalkReplayResolutionError(
            error_code="source_walk_not_replayable",
            details={"inherit_walk_id": str(parent_id), "status": str(parent.status)},
        )

    parent_req = dict(parent.request_body)
    parent_wr = parent.walk_payload["walk_result"]["walk_result_hash"]

    if raw.get("temporal_anchor") is not None:
        p_ta = parent_req.get("temporal_anchor")
        if not canonical_json_equality_v1(raw["temporal_anchor"], p_ta):
            raise WalkReplayResolutionError(
                error_code="replay_anchor_mismatch",
                details={"field": "temporal_anchor"},
            )

    for key in ("walk_policy", "start_node_ids", "walk_execution_strategy", "exploration_mode"):
        if key not in raw:
            raise WalkReplayResolutionError(
                error_code="walk_request_schema",
                details={"field": key},
            )
        if key not in parent_req:
            raise WalkReplayResolutionError(
                error_code="source_walk_not_replayable",
                details={"reason": "missing_parent_field", "field": key},
            )
        if not canonical_json_equality_v1(raw[key], parent_req[key]):
            raise WalkReplayResolutionError(
                error_code="replay_input_mismatch",
                details={"field": key},
            )

    p_pin = parent_req.get("pinned_index_epoch")
    r_pin = raw.get("pinned_index_epoch")
    if r_pin is not None or p_pin is not None:
        if not canonical_json_equality_v1(r_pin, p_pin):
            raise WalkReplayResolutionError(
                error_code="replay_input_mismatch",
                details={"field": "pinned_index_epoch"},
            )

    exp_hash = raw.get("expected_walk_result_hash")
    if exp_hash is not None and str(exp_hash) != str(parent_wr):
        raise WalkReplayResolutionError(
            error_code="replay_hash_mismatch",
            details={"field": "expected_walk_result_hash"},
        )

    effective = dict(parent_req)
    effective["inherit_walk_id"] = str(parent_id)
    if exp_hash is not None:
        effective["expected_walk_result_hash"] = str(exp_hash)

    lineage = {
        "replay_of_walk_id": str(parent_id),
        "original_walk_result_hash": str(parent_wr),
    }
    return effective, lineage


def verify_oct_walk_replay_stub_inherit_resolution_static() -> dict[str, Any]:
    """Structural gate: inherit replay reproduces parent **walk_result_hash** (stub)."""
    errors: list[str] = []
    try:
        from vector.domains.cortex.traversal.traversal_vs_reasoning import (
            oct_walk_request_minimal_fixture_path,
        )
        from vector.domains.cortex.traversal.walk_api_contract import (
            OctsWalkApiMemoryStore,
            build_stub_completed_walk_payload_v1,
        )

        inner = json.loads(oct_walk_request_minimal_fixture_path().read_text(encoding="utf-8"))
        if not isinstance(inner, dict):
            errors.append("fixture_not_object")
        else:
            ta = inner.get("temporal_anchor")
            if not isinstance(ta, dict) or not ta.get("tenant_id"):
                errors.append("fixture_missing_tenant")
            else:
                tid = uuid.UUID(str(ta["tenant_id"]))
                store = OctsWalkApiMemoryStore()
                wid = uuid.uuid4()
                first = build_stub_completed_walk_payload_v1(inner, tenant_id=tid)
                store.insert_completed_sync(
                    tenant_id=tid,
                    walk_id=wid,
                    request_body=dict(inner),
                    walk_payload=first,
                    idempotency_key=None,
                )
                child_req = {
                    **{k: inner[k] for k in inner if k != "temporal_anchor"},
                    "inherit_walk_id": str(wid),
                }
                eff, lin = prepare_effective_oct_walk_request_v1(
                    child_req, tenant_id=tid, store=store
                )
                if lin is None:
                    errors.append("expected_replay_lineage")
                second = build_stub_completed_walk_payload_v1(
                    eff, tenant_id=tid, replay_lineage=lin
                )
                h1 = first["walk_result"]["walk_result_hash"]
                h2 = second["walk_result"]["walk_result_hash"]
                if h1 != h2:
                    errors.append(f"hash_mismatch:{h1}!={h2}")
                tel = second.get("telemetry") or {}
                if tel.get("replay_of_walk_id") != str(wid):
                    errors.append("telemetry_missing_replay_of_walk_id")
                if tel.get("original_walk_result_hash") != h1:
                    errors.append("telemetry_missing_original_walk_result_hash")
                if not str(tel.get("engine_build_id", "")).strip():
                    errors.append("telemetry_missing_engine_build_id")
    except WalkReplayResolutionError as exc:
        errors.append(f"resolution:{exc.error_code}")
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        errors.append(f"exception:{exc}")

    gate_id = "octs-walk-replay-stub-inherit-v1"
    return {
        "id": gate_id,
        "name": "oct_walk_replay_stub_inherit_resolution",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "octs_walk_replay_resolution_schema_version": OCTS_WALK_REPLAY_RESOLUTION_SCHEMA_VERSION,
            "errors": errors,
        },
    }

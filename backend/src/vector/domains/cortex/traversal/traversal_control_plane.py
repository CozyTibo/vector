"""Phase 05 Step **24** — OCTS operator control plane aggregate (**P05-24**).

Normative: ``DOCS/cortex/05-traversal/phase-05-control-plane-doctrine.md`` (structural tables only;
**FS-CP-02** exploration visibility toggle).

Reads are derived from the in-process walk API store (**Step 17** stub) — no walk artifact mutation.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any, Final, Mapping

from sqlalchemy.orm import Session

from vector.domains.cortex.traversal.walk_api_contract import octs_walk_api_memory_store_v1

OCTS_TRAVERSAL_CONTROL_PLANE_SCHEMA_VERSION: Final[int] = 1
OCTS_TRAVERSAL_CONTROL_PLANE_CONTRACT: Final[str] = "octs_traversal_control_plane_v1"

VECTOR_OCTS_CONTROL_PLANE_SHOW_EXPLORATION_ENV: Final[str] = "VECTOR_OCTS_CONTROL_PLANE_SHOW_EXPLORATION"

# Normative admin traversal OpenAPI paths (**G-P05-CP-01** matrix + **G-P05-API-01**).
OCTS_TRAVERSAL_ADMIN_OPENAPI_PATHS_V1: Final[tuple[str, ...]] = (
    "/admin/tenants/{tid}/cortex/traversal/control-plane",
    "/admin/tenants/{tid}/cortex/traversal/derived-index/replay-verify",
    "/admin/tenants/{tid}/cortex/traversal/engine-identity",
    "/admin/tenants/{tid}/cortex/traversal/readiness-economics",
    "/admin/tenants/{tid}/cortex/traversal/walks",
    "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}",
    "/admin/tenants/{tid}/cortex/traversal/walks/{walk_id}/cancel",
)

_FORBIDDEN_PATH_SUBSTRINGS_CP01: Final[tuple[str, ...]] = (
    "summarize",
    "prompt=",
    "/llm",
    "insight",
)


def octs_control_plane_show_exploration_v1() -> bool:
    """**FS-CP-02** — when false, exploration partition rows are omitted from the queue listing."""
    return os.environ.get(VECTOR_OCTS_CONTROL_PLANE_SHOW_EXPLORATION_ENV, "").lower() in (
        "1",
        "true",
        "yes",
    )


def _exploration_request(body: Mapping[str, Any]) -> bool:
    return body.get("exploration_mode") is True


def _snapshot_unix_ns_from_request(body: Mapping[str, Any]) -> int | None:
    ta = body.get("temporal_anchor")
    if not isinstance(ta, dict):
        return None
    s = ta.get("snapshot_unix_ns")
    if isinstance(s, int):
        return int(s)
    if isinstance(s, dict):
        inner = s.get("unix_ns")
        if isinstance(inner, int):
            return int(inner)
    return None


def build_octs_traversal_control_plane_v1(
    _session: Session,
    *,
    tenant_id: uuid.UUID,
    include_exploration: bool | None = None,
) -> dict[str, Any]:
    """Structural aggregate: traversal queue, abort-class counts, ``max_hops`` histogram (**integers only**).

    ``_session`` reserved for future durable store reads.
    """
    if include_exploration is None:
        include_exploration = octs_control_plane_show_exploration_v1()

    now = datetime.now(tz=UTC)
    store = octs_walk_api_memory_store_v1()
    records = store.list_walk_records_for_tenant_v1(tenant_id)

    queue_rows: list[dict[str, Any]] = []
    budget_hist: dict[str, int] = {}
    abort_classes: dict[str, int] = {}
    t_as_of_max: int | None = None

    for rec in records:
        body = rec.request_body
        if not include_exploration and _exploration_request(body):
            continue
        snap = _snapshot_unix_ns_from_request(body)
        if snap is not None:
            t_as_of_max = snap if t_as_of_max is None else max(t_as_of_max, snap)

        wp = body.get("walk_policy")
        mh: int | None = None
        if isinstance(wp, dict):
            raw_mh = wp.get("max_hops")
            if isinstance(raw_mh, int):
                mh = raw_mh
                key = str(mh)
                budget_hist[key] = budget_hist.get(key, 0) + 1

        ep = "exploration" if _exploration_request(body) else "authoritative"
        row: dict[str, Any] = {
            "execution_partition": ep,
            "exploration_mode": bool(_exploration_request(body)),
            "status": rec.status,
            "walk_id": str(rec.walk_id),
        }
        if mh is not None:
            row["max_hops"] = mh
        if snap is not None:
            row["t_as_of_unix_ns"] = snap
        if rec.job_id:
            row["job_id"] = rec.job_id
        queue_rows.append(dict(sorted(row.items())))

    queue_rows.sort(key=lambda r: r["walk_id"], reverse=True)

    for rec in records:
        if not include_exploration and _exploration_request(rec.request_body):
            continue
        if rec.status != "completed" or rec.walk_payload is None:
            continue
        wr = rec.walk_payload.get("walk_result")
        if not isinstance(wr, dict):
            continue
        hb = wr.get("hash_body")
        if not isinstance(hb, dict):
            continue
        tr = hb.get("termination_reason")
        if isinstance(tr, str):
            abort_classes[tr] = abort_classes.get(tr, 0) + 1

    budget_histogram = {k: budget_hist[k] for k in sorted(budget_hist, key=int)}
    abort_sorted = dict(sorted(abort_classes.items()))

    body: dict[str, Any] = {
        "abort_classes": abort_sorted,
        "budget_histogram": budget_histogram,
        "computed_at_utc": now.isoformat(),
        "include_exploration": bool(include_exploration),
        "octs_traversal_control_plane_contract": OCTS_TRAVERSAL_CONTROL_PLANE_CONTRACT,
        "octs_traversal_control_plane_schema_version": OCTS_TRAVERSAL_CONTROL_PLANE_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "t_as_of_unix_ns": t_as_of_max,
        "traversal_queue": queue_rows,
    }
    return dict(sorted(body.items()))


def verify_gp05_cp01_traversal_control_plane_rbac_static() -> dict[str, Any]:
    """**G-P05-CP-01** — admin traversal OpenAPI paths are **admin_basic** only; deny-by-default matrix."""
    from vector.domains.cortex.traversal.walk_api_contract import octs_walk_api_openapi_path

    errors: list[str] = []
    for sub in _FORBIDDEN_PATH_SUBSTRINGS_CP01:
        for p in OCTS_TRAVERSAL_ADMIN_OPENAPI_PATHS_V1:
            if sub in p.lower():
                errors.append(f"forbidden_substring_in_matrix:{sub}:{p}")

    p = octs_walk_api_openapi_path()
    if not p.is_file():
        errors.append(f"missing_openapi:{p}")
        return _cp_gate(errors)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"openapi_json_invalid:{exc}")
        return _cp_gate(errors)
    paths = doc.get("paths")
    if not isinstance(paths, dict):
        errors.append("openapi_paths_missing")
        return _cp_gate(errors)

    for ep in OCTS_TRAVERSAL_ADMIN_OPENAPI_PATHS_V1:
        if ep not in paths:
            errors.append(f"missing_path:{ep}")
            continue
        entry = paths[ep]
        if not isinstance(entry, dict):
            errors.append(f"path_not_object:{ep}")
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in entry:
                continue
            op = entry[method]
            if not isinstance(op, dict):
                errors.append(f"op_not_object:{ep}:{method}")
                continue
            sec = op.get("security")
            if sec != [{"admin_basic": []}]:
                errors.append(f"rbac_security_not_admin_basic:{ep}:{method}")

    return _cp_gate(errors)


def _cp_gate(errors: list[str]) -> dict[str, Any]:
    return {
        "id": "G-P05-CP-01",
        "name": "traversal_control_plane_rbac_openapi",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors, "path_count": len(OCTS_TRAVERSAL_ADMIN_OPENAPI_PATHS_V1)},
    }


def verify_octs_traversal_control_plane_v1_shape(doc: Mapping[str, Any]) -> list[str]:
    """Lightweight shape check for pytest (integers-only counts in histogram / abort_classes)."""
    errs: list[str] = []
    if doc.get("octs_traversal_control_plane_contract") != OCTS_TRAVERSAL_CONTROL_PLANE_CONTRACT:
        errs.append("contract_mismatch")
    if doc.get("octs_traversal_control_plane_schema_version") != OCTS_TRAVERSAL_CONTROL_PLANE_SCHEMA_VERSION:
        errs.append("schema_version_mismatch")
    for k in ("abort_classes", "budget_histogram", "traversal_queue", "tenant_id"):
        if k not in doc:
            errs.append(f"missing_{k}")
    ac = doc.get("abort_classes")
    if isinstance(ac, dict):
        for kk, vv in ac.items():
            if not isinstance(kk, str) or not isinstance(vv, int):
                errs.append("abort_classes_non_int_count")
    bh = doc.get("budget_histogram")
    if isinstance(bh, dict):
        for kk, vv in bh.items():
            if not isinstance(kk, str) or not isinstance(vv, int):
                errs.append("budget_histogram_non_int_count")
    return errs

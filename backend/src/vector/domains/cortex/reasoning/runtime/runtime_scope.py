"""Bounded tenant slice for RUNTIME-01 (one connector / bundle cap)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

TCRE_RUNTIME_SLICE_DEFAULT_LIMIT: Final[int] = 50
TCRE_RUNTIME_SLICE_MAX_LIMIT: Final[int] = 200
TCRE_RUNTIME_SLICE_LABEL_V1: Final[str] = "runtime03_canonical_materializations_v1"


def normalize_reconstruction_scope_v1(scope: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = dict(scope or {})
    lim = raw.get("materialization_limit", TCRE_RUNTIME_SLICE_DEFAULT_LIMIT)
    try:
        n = int(lim)
    except (TypeError, ValueError):
        n = TCRE_RUNTIME_SLICE_DEFAULT_LIMIT
    n = max(1, min(n, TCRE_RUNTIME_SLICE_MAX_LIMIT))
    bundle = raw.get("bundle_id")
    bundle_id = str(bundle).strip() if bundle is not None and str(bundle).strip() else None
    octs_walk_id = raw.get("octs_walk_id")
    walk_id = str(octs_walk_id).strip() if octs_walk_id is not None and str(octs_walk_id).strip() else None
    strict = bool(raw.get("octs_strict_binding", False))
    out: dict[str, Any] = {
        "slice_label": TCRE_RUNTIME_SLICE_LABEL_V1,
        "materialization_limit": n,
        "bundle_id": bundle_id,
        "octs_walk_id": walk_id,
        "octs_strict_binding": strict,
        "traversal_epoch": raw.get("traversal_epoch"),
        "expected_walk_result_hash": raw.get("expected_walk_result_hash"),
        "continuity_proof_ref": raw.get("continuity_proof_ref"),
    }
    pipeline_raw = raw.get("substrate_pipeline_run_id")
    if pipeline_raw is not None and str(pipeline_raw).strip():
        out["substrate_pipeline_run_id"] = str(pipeline_raw).strip()
    return out

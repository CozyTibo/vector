"""Phase 05 P05-16 — traversal runtime execution model (**RULE REM-01/02**, **FS-REM-01..02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-runtime-execution-model.md``.
Neighbor ordering: ``multigraph_model`` (**RULE MG-01**).
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, TypedDict, cast

from vector.domains.cortex.identity.projection_export import validate_org_graph_projection_v1_shape
from vector.domains.cortex.traversal.graph_import_boundary import list_oct_graph_import_violations
from vector.domains.cortex.traversal.multigraph_model import (
    compute_edge_fingerprint_v1,
    list_outgoing_traversable_edges_v1,
)

REM_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_RT01_RUNS: Final[int] = 100

_FORBIDDEN_REM01_ARTIFACT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "async_neighbor_task_ids",
        "parallel_unordered_expansion",
        "race_shared_frontier",
        "promise_all_neighbors",
    }
)


class RuntimeExecutionModelError(ValueError):
    """Raised when reference runtime simulation violates REM / FS-REM."""


class ReferenceWalkResultV1(TypedDict, total=False):
    rem_runtime_schema_version: int
    termination_reason: str
    hops_emitted: int
    edges_considered: int
    max_frontier_observed: int
    visited_link_row_stable_ids_in_order: list[str]
    path_context_ids_in_expand_order: list[str]


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md "
        "from runtime_execution_model."
    )
    raise RuntimeError(msg)


def octs_runtime_execution_fixture_dir() -> Path:
    """Golden / synthetic graphs for **G-P05-RT-01** / **G-P05-RT-02** (**P05-16**)."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "runtime_execution"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"runtime_execution golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def path_context_id_v1(path_node_ids: Sequence[str]) -> str:
    """Opaque deterministic id from path prefix (**terminology §3**)."""
    body = json.dumps(list(path_node_ids), separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


def list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(obj: Any, *, path: str = "root") -> list[str]:
    """**FS-REM-01** — forbid concurrency / shared-mutation markers in emitted artifacts."""
    errors: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            ks = str(k)
            if ks in _FORBIDDEN_REM01_ARTIFACT_KEYS:
                errors.append(f"FS-REM-01:forbidden_key:{path}.{ks}")
            sub = f"{path}.{ks}"
            errors.extend(list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(v, path=sub))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(
                list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(v, path=f"{path}[{i}]")
            )
    return errors


def run_reference_frontier_walk_v1(
    projection_inner: Mapping[str, Any],
    *,
    start_node_id: str,
    target_node_id: str | None,
    max_hops: int,
    max_frontier: int,
    max_edges_visited: int,
    detect_cycles: bool,
    stop_on_cycle: bool = True,
    t_as_of_unix_ns: int | None = None,
) -> ReferenceWalkResultV1:
    """Single-threaded BFS-style reference walk (**RULE REM-01**, **RULE REM-02**).

    Neighbors expanded in **ascending** ``edge_fingerprint`` order. ``emit_receipt_before_expand``
    is always **true** in this reference (receipt counter increments before child enqueue).
    """
    if not isinstance(projection_inner, dict):
        msg = "projection_inner must be an object"
        raise RuntimeExecutionModelError(msg)
    errs = validate_org_graph_projection_v1_shape(projection_inner)
    errs.extend(list_oct_graph_import_violations(projection_inner))
    if errs:
        msg = "projection_inner validation failed: " + "; ".join(errs[:12])
        raise RuntimeExecutionModelError(msg)
    edges = projection_inner.get("edges")
    if not isinstance(edges, list):
        msg = "projection_inner.edges must be an array"
        raise RuntimeExecutionModelError(msg)

    start = str(start_node_id).strip()
    target = str(target_node_id).strip() if target_node_id else None

    frontier: deque[tuple[str, int, str, tuple[str, ...]]] = deque()
    path0: tuple[str, ...] = (start,)
    frontier.append((start, 0, path_context_id_v1(path0), path0))

    visited_link_ids: list[str] = []
    path_ctx_expand_order: list[str] = []
    edges_considered = 0
    max_frontier_peak = len(frontier)
    termination_reason = "empty_frontier"

    while frontier:
        max_frontier_peak = max(max_frontier_peak, len(frontier))
        node, depth, _pctx, path = frontier.popleft()
        outgoing = list_outgoing_traversable_edges_v1(
            cast(list[Mapping[str, Any]], edges),
            source_node_id=node,
            t_as_of_unix_ns=t_as_of_unix_ns,
        )
        outgoing_sorted = sorted(outgoing, key=lambda e: compute_edge_fingerprint_v1(e))

        for edge in outgoing_sorted:
            if edges_considered >= max_edges_visited:
                termination_reason = "budget_exhausted"
                frontier.clear()
                break

            lid = edge.get("link_row_stable_id")
            if not isinstance(lid, str) or not lid.strip():
                msg = "edge missing link_row_stable_id"
                raise RuntimeExecutionModelError(msg)
            child = str(edge.get("target_entity_id"))

            if detect_cycles and child in path:
                if stop_on_cycle:
                    edges_considered += 1
                    visited_link_ids.append(lid.strip())
                    path_ctx_expand_order.append(path_context_id_v1(path + (child,)))
                    termination_reason = "cycle_cut"
                    frontier.clear()
                    break
                continue

            edges_considered += 1
            visited_link_ids.append(lid.strip())

            if target is not None and child == target:
                path_ctx_expand_order.append(path_context_id_v1(path + (child,)))
                termination_reason = "target_reached"
                frontier.clear()
                break

            next_depth = depth + 1
            if next_depth > max_hops:
                continue

            new_path = path + (child,)
            new_ctx = path_context_id_v1(new_path)

            if len(frontier) >= max_frontier:
                termination_reason = "budget_exhausted"
                frontier.clear()
                break

            path_ctx_expand_order.append(new_ctx)
            frontier.append((child, next_depth, new_ctx, new_path))
            max_frontier_peak = max(max_frontier_peak, len(frontier))
        else:
            continue
        break

    if max_frontier_peak > max_frontier:
        msg = "FS-REM-02: max_frontier_observed exceeds policy cap (internal error)"
        raise RuntimeExecutionModelError(msg)

    out: ReferenceWalkResultV1 = {
        "rem_runtime_schema_version": REM_RUNTIME_SCHEMA_VERSION,
        "termination_reason": termination_reason,
        "hops_emitted": len(visited_link_ids),
        "edges_considered": edges_considered,
        "max_frontier_observed": max_frontier_peak,
        "visited_link_row_stable_ids_in_order": visited_link_ids,
        "path_context_ids_in_expand_order": path_ctx_expand_order,
    }
    rem_errors = list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(dict(out))
    if rem_errors:
        msg = "; ".join(rem_errors)
        raise RuntimeExecutionModelError(msg)
    return out


def _canonical_result_bytes(result: ReferenceWalkResultV1) -> bytes:
    return json.dumps(dict(result), sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_gp05_rt01_engine_determinism_static() -> dict[str, Any]:
    """**G-P05-RT-01** — reference walk is deterministic across repeated runs."""
    errors: list[str] = []
    d = octs_runtime_execution_fixture_dir()
    inner_path = d / "determinism_inner_v1.json"
    if not inner_path.is_file():
        errors.append(f"missing_fixture:{inner_path}")
        return _rt_result("G-P05-RT-01", "reference_engine_determinism", errors)

    inner = json.loads(inner_path.read_text(encoding="utf-8"))
    if not isinstance(inner, dict):
        errors.append("determinism_inner_not_object")
        return _rt_result("G-P05-RT-01", "reference_engine_determinism", errors)

    first: bytes | None = None
    for _ in range(_RT01_RUNS):
        try:
            r = run_reference_frontier_walk_v1(
                cast(Mapping[str, Any], inner),
                start_node_id="11111111-1111-1111-1111-111111111111",
                target_node_id="22222222-2222-2222-2222-222222222222",
                max_hops=4,
                max_frontier=64,
                max_edges_visited=500,
                detect_cycles=True,
                stop_on_cycle=True,
                t_as_of_unix_ns=None,
            )
        except RuntimeExecutionModelError as exc:
            errors.append(f"simulation_failed:{exc}")
            break
        if list_fs_rem01_reference_walk_artifact_forbidden_keys_v1(dict(r)):
            errors.append("fs_rem01_forbidden_keys_in_reference_result")
            break
        b = _canonical_result_bytes(r)
        if first is None:
            first = b
        elif b != first:
            errors.append("determinism_mismatch_across_runs")
            break
    if first is None and not errors:
        errors.append("no_runs_completed")

    return _rt_result("G-P05-RT-01", "reference_engine_determinism", errors)


def verify_gp05_rt02_frontier_cap_budget_static() -> dict[str, Any]:
    """**G-P05-RT-02** — synthetic star hits ``max_frontier`` with stable ``budget_exhausted``."""
    errors: list[str] = []
    d = octs_runtime_execution_fixture_dir()
    star_path = d / "star_frontier_cap_inner_v1.json"
    if not star_path.is_file():
        errors.append(f"missing_fixture:{star_path}")
        return _rt_result("G-P05-RT-02", "frontier_cap_memory_bound", errors)

    inner = json.loads(star_path.read_text(encoding="utf-8"))
    if not isinstance(inner, dict):
        errors.append("star_frontier_cap_inner_not_object")
        return _rt_result("G-P05-RT-02", "frontier_cap_memory_bound", errors)

    try:
        r = run_reference_frontier_walk_v1(
            cast(Mapping[str, Any], inner),
            start_node_id="11111111-1111-1111-1111-111111111111",
            target_node_id=None,
            max_hops=8,
            max_frontier=2,
            max_edges_visited=10_000,
            detect_cycles=True,
            stop_on_cycle=True,
            t_as_of_unix_ns=None,
        )
    except RuntimeExecutionModelError as exc:
        errors.append(f"simulation_failed:{exc}")
        return _rt_result("G-P05-RT-02", "frontier_cap_memory_bound", errors)

    if r.get("termination_reason") != "budget_exhausted":
        errors.append(
            f"expected_budget_exhausted:got={r.get('termination_reason')!r}",
        )
    if int(r.get("max_frontier_observed", 0)) > 2:
        errors.append("frontier_peak_exceeded_policy_cap")
    if int(r.get("hops_emitted", 0)) < 1:
        errors.append("expected_at_least_one_hop_emitted")

    return _rt_result("G-P05-RT-02", "frontier_cap_memory_bound", errors)


def _rt_result(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"rem_runtime_schema_version": REM_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

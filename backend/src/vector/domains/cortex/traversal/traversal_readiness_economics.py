"""Phase 05 Step **25** — OCTS readiness + economics probes (**P05-25**).

Normative: ``DOCS/cortex/05-traversal/phase-05-readiness-economics-doctrine.md``.

Read-only probes over **pinned golden fixtures** (no tenant mutation; **FS-ECO-01**).
Receipts include **``octs_economics_threshold_table_version``** (**FS-ECO-02**) and
``economics_receipt_hash`` over sorted integer stats (**§5** replay semantics).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Final, Literal, Mapping, cast

from vector.domains.cortex.traversal.derived_index_contract import (
    canonical_derived_index_artifact_json_bytes_v1,
    octs_derived_index_fixture_dir,
)
from vector.domains.cortex.traversal.verification_gates_catalog import octs_golden_vectors_v1_root

OCTS_TRAVERSAL_READINESS_ECONOMICS_SCHEMA_VERSION: Final[int] = 1
OCTS_TRAVERSAL_READINESS_ECONOMICS_CONTRACT: Final[str] = "octs_traversal_readiness_economics_v1"

OCTS_ECONOMICS_THRESHOLD_TABLE_FILENAME: Final[str] = "threshold_table_v1.json"
OCTS_ECONOMICS_PROJECTION_CLEAN: Final[str] = "projection_clean_v1.json"
OCTS_ECONOMICS_PROJECTION_HOSTILE: Final[str] = "projection_hostile_hub_v1.json"
OCTS_ECONOMICS_DERIVED_ARTIFACT_FIXTURE: Final[str] = "derived_index_artifact_good_v1.json"

ProbeProfileV1 = Literal["clean", "hostile"]


def octs_economics_golden_dir_v1() -> Path:
    return octs_golden_vectors_v1_root() / "economics"


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_octs_economics_threshold_table_v1() -> dict[str, Any]:
    p = octs_economics_golden_dir_v1() / OCTS_ECONOMICS_THRESHOLD_TABLE_FILENAME
    return _read_json(p)


def load_octs_economics_projection_fixture_v1(profile: ProbeProfileV1) -> dict[str, Any]:
    name = OCTS_ECONOMICS_PROJECTION_CLEAN if profile == "clean" else OCTS_ECONOMICS_PROJECTION_HOSTILE
    return _read_json(octs_economics_golden_dir_v1() / name)


def _stats_int_map_v1(stats: Mapping[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for k in sorted(stats.keys(), key=str):
        v = stats[k]
        if not isinstance(k, str):
            continue
        if not isinstance(v, int):
            msg = f"economics stat {k!r} must be int"
            raise ValueError(msg)
        out[k] = v
    return out


def compute_economics_receipt_hash_v1(stats: Mapping[str, int]) -> str:
    """Deterministic **economics_receipt_hash** over sorted integer stats map (**§5**)."""
    body = _stats_int_map_v1(stats)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _derived_index_bytes_per_edge_v1() -> tuple[int, int]:
    """Return ``(total_canonical_bytes, edge_count)`` for golden derived artifact."""
    p = octs_derived_index_fixture_dir() / OCTS_ECONOMICS_DERIVED_ARTIFACT_FIXTURE
    art = _read_json(p)
    edges = art.get("derived_edges")
    if not isinstance(edges, list) or len(edges) == 0:
        msg = "derived fixture must have non-empty derived_edges"
        raise ValueError(msg)
    total = len(canonical_derived_index_artifact_json_bytes_v1(art))
    return total, len(edges)


def build_octs_traversal_readiness_economics_receipt_v1(
    *,
    tenant_id: uuid.UUID,
    profile: ProbeProfileV1 = "clean",
) -> dict[str, Any]:
    """Build a numeric readiness / economics receipt (**read-only** golden probes)."""
    threshold = load_octs_economics_threshold_table_v1()
    tt_ver = threshold.get("octs_economics_threshold_table_version")
    if not isinstance(tt_ver, int):
        msg = "threshold_table.octs_economics_threshold_table_version must be int"
        raise ValueError(msg)
    max_deg = threshold.get("octs_max_out_degree")
    wall_ms = threshold.get("async_walk_max_wall_ms")
    max_bpe = threshold.get("derived_index_max_bytes_per_edge")
    if not isinstance(max_deg, int) or not isinstance(wall_ms, int) or not isinstance(max_bpe, int):
        msg = "threshold_table numeric fields must be int"
        raise ValueError(msg)

    proj = load_octs_economics_projection_fixture_v1(profile)
    pch = proj.get("projection_content_hash")
    degrees = proj.get("node_out_degrees")
    cost_ms = proj.get("hub_walk_worst_case_cost_ms")
    if not isinstance(pch, str) or not isinstance(degrees, list) or not isinstance(cost_ms, int):
        msg = "projection fixture shape invalid"
        raise ValueError(msg)
    int_degrees = [int(x) for x in degrees if isinstance(x, int)]
    if len(int_degrees) != len(degrees):
        msg = "node_out_degrees must be ints"
        raise ValueError(msg)
    max_out = max(int_degrees) if int_degrees else 0

    total_b, n_edge = _derived_index_bytes_per_edge_v1()
    bpe = (total_b + n_edge - 1) // n_edge if n_edge else 0

    violations: list[str] = []
    if max_out > max_deg:
        violations.append("P05_ECO_MAX_OUT_DEGREE")
    if cost_ms > wall_ms:
        violations.append("P05_ECO_WALK_WALL_BUDGET")
    if bpe > max_bpe:
        violations.append("P05_ECO_DERIVED_INDEX_BYTES_PER_EDGE")
    violations_sorted = sorted(violations)

    stats: dict[str, int] = {
        "async_walk_max_wall_ms": wall_ms,
        "derived_index_bytes_per_edge": bpe,
        "derived_index_edge_count": n_edge,
        "derived_index_max_bytes_per_edge": max_bpe,
        "derived_index_total_bytes": total_b,
        "eco_violation_count": len(violations_sorted),
        "hub_walk_worst_case_cost_ms": cost_ms,
        "max_out_degree_observed": max_out,
        "octs_economics_threshold_table_version": tt_ver,
        "octs_max_out_degree": max_deg,
    }
    receipt_hash = compute_economics_receipt_hash_v1(stats)

    body: dict[str, Any] = {
        "economics_receipt_hash": receipt_hash,
        "economics_stats": dict(sorted(stats.items())),
        "economics_violations": violations_sorted,
        "octs_economics_threshold_table_version": tt_ver,
        "octs_traversal_readiness_economics_contract": OCTS_TRAVERSAL_READINESS_ECONOMICS_CONTRACT,
        "octs_traversal_readiness_economics_schema_version": OCTS_TRAVERSAL_READINESS_ECONOMICS_SCHEMA_VERSION,
        "probe_profile": profile,
        "projection_content_hash": pch,
        "tenant_id": str(tenant_id),
    }
    return dict(sorted(body.items()))


def verify_octs_readiness_economics_receipt_v1_shape(doc: Mapping[str, Any]) -> list[str]:
    errs: list[str] = []
    if doc.get("octs_traversal_readiness_economics_contract") != OCTS_TRAVERSAL_READINESS_ECONOMICS_CONTRACT:
        errs.append("contract_mismatch")
    if doc.get("octs_traversal_readiness_economics_schema_version") != OCTS_TRAVERSAL_READINESS_ECONOMICS_SCHEMA_VERSION:
        errs.append("schema_version_mismatch")
    if doc.get("octs_economics_threshold_table_version") is None:
        errs.append("missing_threshold_table_version_top_level")
    if "octs_economics_threshold_table_version" not in doc.get("economics_stats", {}):
        errs.append("missing_threshold_table_version_in_stats")
    if not isinstance(doc.get("economics_receipt_hash"), str):
        errs.append("missing_receipt_hash")
    return errs


def _eco_gate(gate_id: str, name: str, passed: bool, detail: Mapping[str, Any]) -> dict[str, Any]:
    from vector.domains.cortex.traversal.verification_gates_catalog import default_severity_for_gate_v1

    return {
        "id": gate_id,
        "name": name,
        "passed": passed,
        "severity": default_severity_for_gate_v1(gate_id),
        "detail": dict(detail),
    }


def verify_gp05_eco01_max_out_degree_golden_static() -> dict[str, Any]:
    """**G-P05-ECO-01** — max out-degree on **clean** golden projection ≤ ``octs_max_out_degree``."""
    threshold = load_octs_economics_threshold_table_v1()
    proj = load_octs_economics_projection_fixture_v1("clean")
    max_deg = int(threshold["octs_max_out_degree"])
    degrees = [int(x) for x in proj["node_out_degrees"] if isinstance(x, int)]
    max_out = max(degrees) if degrees else 0
    passed = max_out <= max_deg
    return _eco_gate(
        "G-P05-ECO-01",
        "max_out_degree_threshold_clean_fixture",
        passed,
        {
            "max_out_degree_observed": max_out,
            "octs_max_out_degree": max_deg,
            "octs_economics_threshold_table_version": threshold.get("octs_economics_threshold_table_version"),
        },
    )


def verify_gp05_eco02_walk_wall_budget_golden_static() -> dict[str, Any]:
    """**G-P05-ECO-02** — synthetic hub walk cost (ms) on **clean** fixture ≤ async wall budget."""
    threshold = load_octs_economics_threshold_table_v1()
    proj = load_octs_economics_projection_fixture_v1("clean")
    wall = int(threshold["async_walk_max_wall_ms"])
    cost = int(proj["hub_walk_worst_case_cost_ms"])
    passed = cost <= wall
    return _eco_gate(
        "G-P05-ECO-02",
        "synthetic_walk_wall_budget_clean_fixture",
        passed,
        {
            "async_walk_max_wall_ms": wall,
            "hub_walk_worst_case_cost_ms": cost,
            "octs_economics_threshold_table_version": threshold.get("octs_economics_threshold_table_version"),
        },
    )


def verify_gp05_eco03_derived_index_bytes_per_edge_golden_static() -> dict[str, Any]:
    """**G-P05-ECO-03** — golden derived index canonical bytes / edge ≤ table budget."""
    threshold = load_octs_economics_threshold_table_v1()
    max_bpe = int(threshold["derived_index_max_bytes_per_edge"])
    total_b, n_edge = _derived_index_bytes_per_edge_v1()
    bpe = (total_b + n_edge - 1) // n_edge
    passed = bpe <= max_bpe
    return _eco_gate(
        "G-P05-ECO-03",
        "derived_index_bytes_per_edge_golden_fixture",
        passed,
        {
            "derived_index_bytes_per_edge": bpe,
            "derived_index_edge_count": n_edge,
            "derived_index_max_bytes_per_edge": max_bpe,
            "derived_index_total_bytes": total_b,
            "octs_economics_threshold_table_version": threshold.get("octs_economics_threshold_table_version"),
        },
    )


def assert_hostile_hub_fixture_breaches_thresholds_v1() -> dict[str, Any]:
    """Test oracle (**§13**) — hostile projection predictably violates **ECO-01** and/or **ECO-02**."""
    threshold = load_octs_economics_threshold_table_v1()
    proj = load_octs_economics_projection_fixture_v1("hostile")
    max_deg = int(threshold["octs_max_out_degree"])
    wall = int(threshold["async_walk_max_wall_ms"])
    degrees = [int(x) for x in proj["node_out_degrees"] if isinstance(x, int)]
    max_out = max(degrees) if degrees else 0
    cost = int(proj["hub_walk_worst_case_cost_ms"])
    return {
        "breach_max_out_degree": max_out > max_deg,
        "breach_wall_budget": cost > wall,
        "hub_walk_worst_case_cost_ms": cost,
        "max_out_degree_observed": max_out,
    }

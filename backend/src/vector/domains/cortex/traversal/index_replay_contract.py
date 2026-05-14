"""Phase 05 Step 20 — index replay (**``phase-05-index-replay-doctrine.md``**).

Implements **IRJ-01** determinism checks and static gates aligned with **G-P05-REPLAY-IDX-01**
(double-run ``index_content_hash`` equality) and **G-P05-REPLAY-IDX-02** (corrupt lineage →
deterministic failure). HTTP request schema: ``octs-derived-index-replay-verify-v1.schema.json``.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Final

import jsonschema  # type: ignore[import-untyped]

from vector.domains.cortex.traversal.derived_index_contract import (
    DERIVED_INDEX_CANON_VERSION,
    DerivedIndexContractError,
    compute_index_content_hash_v1,
    list_fs_di01_derived_edge_lineage_violations,
    octs_derived_index_fixture_dir,
    validate_derived_index_artifact_contract_v1,
)

INDEX_REPLAY_CONTRACT_SCHEMA_VERSION: Final[int] = 1


def _repo_root_with_oct_schemas() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = (
            root
            / "DOCS"
            / "cortex"
            / "05-traversal"
            / "schemas"
            / "octs-derived-index-replay-verify-v1.schema.json"
        )
        if marker.is_file():
            return root
    msg = "Could not locate DOCS/cortex/05-traversal/schemas from index_replay_contract."
    raise RuntimeError(msg)


def oct_derived_index_replay_verify_v1_schema_path() -> Path:
    """JSON Schema for **POST …/derived-index/replay-verify** bodies."""
    return (
        _repo_root_with_oct_schemas()
        / "DOCS"
        / "cortex"
        / "05-traversal"
        / "schemas"
        / "octs-derived-index-replay-verify-v1.schema.json"
    )


def load_oct_derived_index_replay_verify_v1_schema() -> dict[str, Any]:
    p = oct_derived_index_replay_verify_v1_schema_path()
    return json.loads(p.read_text(encoding="utf-8"))


def validate_oct_derived_index_replay_verify_body_v1(instance: dict[str, Any]) -> None:
    """Validate replay-verify envelope (**RULE API-0** envelope for Step 20)."""
    schema = load_oct_derived_index_replay_verify_v1_schema()
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    cls(schema).validate(instance)


def list_fs_irj02_incomplete_node_set_compare_violations_v1(
    reference: dict[str, Any],
    candidate: dict[str, Any],
) -> list[str]:
    """**FS-IRJ-02** — forbid silent hash compare when node universes differ."""
    rn = reference.get("nodes")
    cn = candidate.get("nodes")
    if not isinstance(rn, list) or not isinstance(cn, list):
        return ["FS-IRJ-02:nodes_not_arrays"]
    rs = sorted(str(x) for x in rn)
    cs = sorted(str(x) for x in cn)
    if rs != cs:
        return [f"FS-IRJ-02:node_set_mismatch ref={len(rs)} cand={len(cs)}"]
    return []


def verify_gp05_replay_idx01_double_run_equality_static() -> dict[str, Any]:
    """**G-P05-REPLAY-IDX-01** — double regeneration yields identical ``index_content_hash``."""
    errors: list[str] = []
    d = octs_derived_index_fixture_dir()
    art_path = d / "derived_index_artifact_good_v1.json"
    if not art_path.is_file():
        errors.append(f"missing_fixture:{art_path}")
        return _irj_gate("G-P05-REPLAY-IDX-01", "double_run_index_content_hash_equality", errors)

    raw = json.loads(art_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        errors.append("artifact_not_object")
        return _irj_gate("G-P05-REPLAY-IDX-01", "double_run_index_content_hash_equality", errors)
    try:
        validate_derived_index_artifact_contract_v1(raw)
    except DerivedIndexContractError as exc:
        errors.append(f"artifact_invalid:{exc}")
        return _irj_gate("G-P05-REPLAY-IDX-01", "double_run_index_content_hash_equality", errors)

    a1 = copy.deepcopy(raw)
    a2 = json.loads(json.dumps(raw))
    h1 = compute_index_content_hash_v1(a1)
    h2 = compute_index_content_hash_v1(a2)
    if h1 != h2:
        errors.append(f"double_run_mismatch:{h1}!={h2}")
    h3 = compute_index_content_hash_v1(a1)
    if h1 != h3:
        errors.append(f"second_pass_mismatch:{h1}!={h3}")

    return _irj_gate("G-P05-REPLAY-IDX-01", "double_run_index_content_hash_equality", errors)


def verify_gp05_replay_idx02_corrupt_lineage_deterministic_failure_static() -> dict[str, Any]:
    """**G-P05-REPLAY-IDX-02** — corrupt lineage is detected (no silent success)."""
    errors: list[str] = []
    d = octs_derived_index_fixture_dir()
    art_path = d / "derived_index_artifact_good_v1.json"
    if not art_path.is_file():
        errors.append(f"missing_fixture:{art_path}")
        return _irj_gate("G-P05-REPLAY-IDX-02", "corrupt_lineage_deterministic_failure", errors)

    raw = json.loads(art_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        errors.append("artifact_not_object")
        return _irj_gate("G-P05-REPLAY-IDX-02", "corrupt_lineage_deterministic_failure", errors)

    poisoned = copy.deepcopy(raw)
    edges = poisoned.get("derived_edges")
    if not isinstance(edges, list) or not edges or not isinstance(edges[0], dict):
        errors.append("cannot_poison_edges")
        return _irj_gate("G-P05-REPLAY-IDX-02", "corrupt_lineage_deterministic_failure", errors)
    e0 = edges[0]
    e0["source_observed_edge_fingerprints"] = []

    v = list_fs_di01_derived_edge_lineage_violations(
        poisoned.get("derived_edges") if isinstance(poisoned.get("derived_edges"), list) else []
    )
    if not v:
        errors.append("expected_lineage_violations_on_poisoned_artifact")

    try:
        validate_derived_index_artifact_contract_v1(poisoned)
        errors.append("expected_validate_derived_index_to_fail")
    except DerivedIndexContractError:
        pass

    return _irj_gate("G-P05-REPLAY-IDX-02", "corrupt_lineage_deterministic_failure", errors)


def _irj_gate(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "index_replay_contract_schema_version": INDEX_REPLAY_CONTRACT_SCHEMA_VERSION,
            "derived_index_canon_version": DERIVED_INDEX_CANON_VERSION,
            "errors": errors,
        },
    }

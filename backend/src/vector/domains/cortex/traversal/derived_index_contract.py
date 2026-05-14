"""Phase 05 P05-13 — derived index contract (**G-P05-IDX-01**, **G-P05-IDX-02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-derived-index-contract-doctrine.md``.
Hash preamble: ``DERIVED_INDEX_CANON_VERSION`` per ``phase-05-index-replay-doctrine.md`` §8.
Index replay (**Step 20**) builds on ``compute_index_content_hash_v1`` / ``index_replay_contract``.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.observed_vs_derived import (
    WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
)
from vector.domains.cortex.traversal.temporal_walk import (
    TemporalWalkInvariantError,
    validate_temporal_anchor_invariants_v1,
)

DI_RUNTIME_SCHEMA_VERSION: Final[int] = 1

DERIVED_INDEX_CANON_VERSION: Final[int] = 1

_INDEX_CONTENT_HASH_PREFIX: Final[str] = "sha256:"

_SHA256_FP_PATTERN: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

PUBLISH_STATE_BUILDING: Final[str] = "BUILDING"
PUBLISH_STATE_PUBLISHED: Final[str] = "PUBLISHED"


class DerivedIndexContractError(ValueError):
    """Raised when derived index artifacts or publish records violate doctrine."""


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md "
        "from derived_index_contract."
    )
    raise RuntimeError(msg)


def octs_derived_index_fixture_dir() -> Path:
    """Golden vectors for **G-P05-IDX-01** / **G-P05-IDX-02**."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "derived_index"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"derived_index golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def assert_index_content_hash_string_v1(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_FP_PATTERN.fullmatch(value):
        msg = f"{field_name} must match sha256:[0-9a-f]{{64}}"
        raise DerivedIndexContractError(msg)
    return value


def _canonical_json_for_hash_v1(obj: Any) -> Any:
    """Sorted keys + NFC strings (**OCTS-CANON-1** style) for deterministic bytes."""
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {
            str(k): _canonical_json_for_hash_v1(obj[k])
            for k in sorted(obj.keys(), key=str)
        }
    if isinstance(obj, list):
        return [_canonical_json_for_hash_v1(x) for x in obj]
    return obj


def _normalize_derived_edge_for_sort_v1(edge: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical per-edge dict: sorted keys; sorted lineage multiset."""
    out = {str(k): edge[k] for k in sorted(edge.keys(), key=str)}
    fps = out.get("source_observed_edge_fingerprints")
    if isinstance(fps, list) and all(isinstance(x, str) for x in fps):
        out["source_observed_edge_fingerprints"] = sorted(fps)
    return cast(dict[str, Any], _canonical_json_for_hash_v1(out))


def canonical_derived_index_artifact_root_for_hash_v1(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    """**RULE DI-01** — canonical object hashed as ``index_content_hash`` (partition body)."""
    ver = artifact.get("DERIVED_INDEX_CANON_VERSION", DERIVED_INDEX_CANON_VERSION)
    if not isinstance(ver, int) or ver < 0:
        msg = "DERIVED_INDEX_CANON_VERSION must be a non-negative int"
        raise DerivedIndexContractError(msg)

    has_anchor = "materialized_for_anchor" in artifact and artifact.get(
        "materialized_for_anchor"
    ) not in (None, {})
    has_epoch_only = "materialized_for_index_epoch" in artifact and artifact.get(
        "materialized_for_index_epoch"
    ) is not None

    if not has_anchor and not has_epoch_only:
        msg = "artifact must include materialized_for_anchor or materialized_for_index_epoch"
        raise DerivedIndexContractError(msg)

    materialized_for_anchor: dict[str, Any] | None = None
    materialized_for_index_epoch: int | None = None

    if has_anchor:
        a = artifact.get("materialized_for_anchor")
        if not isinstance(a, dict):
            msg = "materialized_for_anchor must be an object"
            raise DerivedIndexContractError(msg)
        materialized_for_anchor = cast(dict[str, Any], dict(a))

    if has_epoch_only:
        raw_e = artifact.get("materialized_for_index_epoch")
        if isinstance(raw_e, bool) or not isinstance(raw_e, int) or raw_e < 0:
            msg = "materialized_for_index_epoch must be a non-negative int (not bool)"
            raise DerivedIndexContractError(msg)
        materialized_for_index_epoch = int(raw_e)

    nodes_raw = artifact.get("nodes")
    if not isinstance(nodes_raw, list) or not all(isinstance(x, str) for x in nodes_raw):
        msg = "nodes must be a JSON array of strings"
        raise DerivedIndexContractError(msg)
    nodes_sorted = sorted(nodes_raw)

    adj_raw = artifact.get("adj")
    if not isinstance(adj_raw, dict):
        msg = "adj must be an object"
        raise DerivedIndexContractError(msg)
    adj_out: dict[str, Any] = {}
    for src in sorted(adj_raw.keys(), key=str):
        targets = adj_raw.get(src)
        if not isinstance(targets, list) or not all(isinstance(x, str) for x in targets):
            msg = f"adj[{src!r}] must be an array of strings"
            raise DerivedIndexContractError(msg)
        adj_out[str(src)] = sorted(targets)

    edges_raw = artifact.get("derived_edges")
    if not isinstance(edges_raw, list):
        msg = "derived_edges must be an array"
        raise DerivedIndexContractError(msg)
    edges_norm: list[dict[str, Any]] = []
    for i, e in enumerate(edges_raw):
        if not isinstance(e, dict):
            msg = f"derived_edges[{i}] must be an object"
            raise DerivedIndexContractError(msg)
        fn = e.get("from_node_id")
        tn = e.get("to_node_id")
        if not isinstance(fn, str) or not isinstance(tn, str):
            msg = f"derived_edges[{i}] requires from_node_id and to_node_id strings"
            raise DerivedIndexContractError(msg)
        edges_norm.append(_normalize_derived_edge_for_sort_v1(cast(Mapping[str, Any], e)))
    edges_sorted = sorted(
        edges_norm,
        key=lambda d: (str(d.get("from_node_id")), str(d.get("to_node_id"))),
    )

    root: dict[str, Any] = {
        "DERIVED_INDEX_CANON_VERSION": int(ver),
        "adj": adj_out,
        "derived_edges": edges_sorted,
        "nodes": nodes_sorted,
    }
    if materialized_for_anchor is not None:
        root["materialized_for_anchor"] = cast(
            dict[str, Any], _canonical_json_for_hash_v1(materialized_for_anchor)
        )
    if materialized_for_index_epoch is not None:
        root["materialized_for_index_epoch"] = materialized_for_index_epoch

    return cast(dict[str, Any], _canonical_json_for_hash_v1(root))


def canonical_derived_index_artifact_json_bytes_v1(artifact: Mapping[str, Any]) -> bytes:
    """UTF-8 JSON bytes fed to SHA-256 for ``index_content_hash``."""
    root = canonical_derived_index_artifact_root_for_hash_v1(artifact)
    return json.dumps(root, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_index_content_hash_v1(artifact: Mapping[str, Any]) -> str:
    """``index_content_hash`` = ``sha256:`` + 64 hex over canonical artifact (**RULE DI-01**)."""
    digest = hashlib.sha256(canonical_derived_index_artifact_json_bytes_v1(artifact)).hexdigest()
    return f"{_INDEX_CONTENT_HASH_PREFIX}{digest}"


def list_fs_di01_derived_edge_lineage_violations(
    derived_edges: Sequence[Any],
) -> list[str]:
    """**FS-DI-01** — each derived edge must carry non-empty observed lineage fingerprints."""
    errors: list[str] = []
    if not isinstance(derived_edges, list):
        return ["derived_edges_not_array"]
    for i, e in enumerate(derived_edges):
        if not isinstance(e, dict):
            errors.append(f"edge[{i}]:not_object")
            continue
        fps = e.get("source_observed_edge_fingerprints")
        if not isinstance(fps, list) or len(fps) == 0:
            errors.append(f"edge[{i}]:FS-DI-01_missing_or_empty_source_observed_edge_fingerprints")
            continue
        for j, fp in enumerate(fps):
            if not isinstance(fp, str) or not _SHA256_FP_PATTERN.fullmatch(fp):
                errors.append(f"edge[{i}].fingerprint[{j}]:invalid_sha256_fingerprint")
    return errors


def list_fs_di03_index_epoch_regression_violations(
    committed_epochs: Sequence[Any],
) -> list[str]:
    """**FS-DI-03** — committed ``index_epoch`` sequence must be strictly non-decreasing."""
    errors: list[str] = []
    prev: int | None = None
    for i, raw in enumerate(committed_epochs):
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            errors.append(f"epoch[{i}]:invalid_non_negative_int")
            continue
        cur = int(raw)
        if prev is not None and cur < prev:
            errors.append(f"FS-DI-03:index_epoch_regression:at[{i}] {cur}<{prev}")
        prev = cur
    return errors


def validate_publish_barrier_record_v1(rec: Mapping[str, Any]) -> None:
    """**FS-DI-02** — partial build must not appear ``PUBLISHED``."""
    state = rec.get("publish_state")
    if state != PUBLISH_STATE_PUBLISHED:
        return
    if rec.get("partial_build") is True:
        msg = "FS-DI-02: partial_build must not be true when publish_state is PUBLISHED"
        raise DerivedIndexContractError(msg)
    if rec.get("lineage_scan_passed") is not True:
        msg = "FS-DI-02: PUBLISHED requires lineage_scan_passed=true"
        raise DerivedIndexContractError(msg)


def validate_stale_derived_read_policy_v1(
    *,
    walk_execution_strategy: str,
    allow_stale_derived_read: bool,
    served_index_epoch: int | None,
    latest_committed_index_epoch: int | None,
) -> None:
    """**RULE DI-02** — default strict observed walks reject stale derived index pins."""
    if walk_execution_strategy != WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED:
        return
    if allow_stale_derived_read:
        return
    if served_index_epoch is None or latest_committed_index_epoch is None:
        return
    if served_index_epoch < latest_committed_index_epoch:
        msg = (
            "RULE DI-02: served_index_epoch < latest_committed_index_epoch for "
            "ONLINE_OBSERVED without allow_stale_derived_read"
        )
        raise DerivedIndexContractError(msg)


def validate_derived_index_artifact_contract_v1(artifact: Mapping[str, Any]) -> None:
    """Structural law + temporal anchor subset when ``materialized_for_anchor`` is used."""
    if not isinstance(artifact, dict):
        msg = "artifact must be an object"
        raise DerivedIndexContractError(msg)

    a = artifact.get("materialized_for_anchor")
    if isinstance(a, dict) and a:
        try:
            validate_temporal_anchor_invariants_v1(a)
        except TemporalWalkInvariantError as exc:
            msg = f"materialized_for_anchor invalid: {exc}"
            raise DerivedIndexContractError(msg) from exc

    v = list_fs_di01_derived_edge_lineage_violations(artifact.get("derived_edges", []))
    if v:
        raise DerivedIndexContractError("G-P05-IDX-02 / FS-DI-01: " + "; ".join(v[:20]))

    # Force hash precomputation — catches canonicalization bugs early.
    compute_index_content_hash_v1(artifact)


def verify_gp05_idx01_index_content_hash_stability_static() -> dict[str, Any]:
    """**G-P05-IDX-01** — golden derived artifact recomputes expected ``index_content_hash``."""
    errors: list[str] = []
    d = octs_derived_index_fixture_dir()
    art_path = d / "derived_index_artifact_good_v1.json"
    expected_path = d / "index_content_hash_expected_v1.txt"
    if not art_path.is_file():
        errors.append(f"missing_fixture:{art_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if errors:
        return _idx01_result(errors)

    raw = json.loads(art_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        errors.append("artifact_not_object")
    else:
        try:
            validate_derived_index_artifact_contract_v1(raw)
        except DerivedIndexContractError as exc:
            errors.append(f"artifact_invalid:{exc}")
        if not errors:
            actual = compute_index_content_hash_v1(raw)
            expected = expected_path.read_text(encoding="utf-8").strip()
            if actual != expected:
                errors.append(f"hash_mismatch:actual={actual!r} expected={expected!r}")

    return _idx01_result(errors)


def _idx01_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-IDX-01",
        "name": "derived_index_content_hash_stability",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"di_runtime_schema_version": DI_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_idx02_lineage_completeness_static() -> dict[str, Any]:
    """**G-P05-IDX-02** — lineage completeness rejects empty / invalid fingerprints."""
    errors: list[str] = []
    d = octs_derived_index_fixture_dir()
    bad_path = d / "derived_edges_lineage_bad_fs_di01_v1.json"
    if not bad_path.is_file():
        errors.append(f"missing_fixture:{bad_path}")
        return _idx02_result(errors)

    raw = json.loads(bad_path.read_text(encoding="utf-8"))
    edges = raw.get("derived_edges") if isinstance(raw, dict) else None
    v = list_fs_di01_derived_edge_lineage_violations(edges if isinstance(edges, list) else [])
    if not v:
        errors.append("expected_lineage_violations_on_bad_fixture")

    good_path = d / "derived_edges_lineage_good_v1.json"
    if not good_path.is_file():
        errors.append(f"missing_fixture:{good_path}")
    else:
        g = json.loads(good_path.read_text(encoding="utf-8"))
        ge = g.get("derived_edges") if isinstance(g, dict) else None
        gv = list_fs_di01_derived_edge_lineage_violations(ge if isinstance(ge, list) else [])
        if gv:
            errors.append(f"unexpected_violations_on_good_fixture:{gv}")

    return _idx02_result(errors)


def _idx02_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-IDX-02",
        "name": "derived_index_lineage_completeness",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"di_runtime_schema_version": DI_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


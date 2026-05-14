"""Phase 05 P05-15 — walk execution strategy (**RULE WES-01/02**, **FS-WES-01..03**).

Normative: ``DOCS/cortex/05-traversal/phase-05-walk-execution-strategy-doctrine.md``.
Strategy enums: ``observed_vs_derived`` (single source of truth for string literals).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.observed_vs_derived import (
    PROVENANCE_CLASS_DERIVED,
    WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
    WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
)

WES_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_WALK_RESULT_HASH_RE: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

_FORBIDDEN_WES03_HASH_BODY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "merged_hops",
        "merged_hop_paths",
        "hop_receipt_generation_skipped",
        "receipts_omitted",
        "bfs_layer_cache_unlabeled",
    }
)


class WalkExecutionStrategyContractError(ValueError):
    """Raised when walk execution strategy / fast-path / hybrid policy violates doctrine."""


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md "
        "from walk_execution_strategy_contract."
    )
    raise RuntimeError(msg)


def octs_walk_execution_strategy_fixture_dir() -> Path:
    """Golden vectors for **G-P05-EQUIV-01** / **WES** static gates (**P05-15**)."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "walk_execution_strategy"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"walk_execution_strategy golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def _pinned_index_epoch_value(anchor: Mapping[str, Any] | None) -> Any | None:
    """Resolve ``pinned_index_epoch`` from top-level anchor or ``extension`` object."""
    if anchor is None:
        return None
    if "pinned_index_epoch" in anchor:
        return anchor.get("pinned_index_epoch")
    ext = anchor.get("extension")
    if isinstance(ext, dict) and "pinned_index_epoch" in ext:
        return ext.get("pinned_index_epoch")
    return None


def validate_fs_wes01_materialized_requires_pinned_index_epoch_v1(
    walk_execution_strategy: str,
    temporal_anchor: Mapping[str, Any] | None,
) -> None:
    """**FS-WES-01** — ``MATERIALIZED_DERIVED`` requires ``pinned_index_epoch`` (§6)."""
    if walk_execution_strategy == WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED:
        return
    if walk_execution_strategy not in (
        WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
        WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    ):
        msg = f"unknown walk_execution_strategy: {walk_execution_strategy!r}"
        raise WalkExecutionStrategyContractError(msg)
    epoch = _pinned_index_epoch_value(temporal_anchor)
    if epoch is None:
        msg = (
            "FS-WES-01: MATERIALIZED_DERIVED or HYBRID_PINNED requires "
            "temporal_anchor.pinned_index_epoch (or extension.pinned_index_epoch)"
        )
        raise WalkExecutionStrategyContractError(msg)
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        msg = "pinned_index_epoch must be a non-negative int (not bool)"
        raise WalkExecutionStrategyContractError(msg)


def validate_hybrid_policy_integer_threshold_for_strategy_v1(
    walk_execution_strategy: str,
    walk_policy: Mapping[str, Any],
) -> None:
    """**WES §3** — ``HYBRID_PINNED`` requires ``hybrid_switch_at_index_epoch`` (int) in policy."""
    if walk_execution_strategy != WALK_EXECUTION_STRATEGY_HYBRID_PINNED:
        return
    if not isinstance(walk_policy, dict):
        msg = "walk_policy must be an object"
        raise WalkExecutionStrategyContractError(msg)
    if "hybrid_switch_at_index_epoch" not in walk_policy:
        msg = (
            "HYBRID_PINNED requires walk_policy.hybrid_switch_at_index_epoch "
            "(integer threshold; doctrine §3)"
        )
        raise WalkExecutionStrategyContractError(msg)
    raw = walk_policy["hybrid_switch_at_index_epoch"]
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        msg = "hybrid_switch_at_index_epoch must be a non-negative int (not bool)"
        raise WalkExecutionStrategyContractError(msg)
    fpa = walk_policy.get("fast_path_allowed")
    if fpa is not None and not isinstance(fpa, bool):
        msg = "fast_path_allowed must be a boolean when present"
        raise WalkExecutionStrategyContractError(msg)


def validate_temporal_anchor_extension_sorted_keys_v1(extension: Mapping[str, Any]) -> None:
    """**WES §8** — extension object keys UTF-8 sorted (canonical ordering)."""
    if not isinstance(extension, dict):
        msg = "temporal_anchor.extension must be an object when present"
        raise WalkExecutionStrategyContractError(msg)
    keys = list(extension.keys())
    if keys != sorted(keys, key=str):
        msg = "temporal_anchor.extension keys must be sorted UTF-8 ascending"
        raise WalkExecutionStrategyContractError(msg)


def validate_materialized_adjacency_hop_receipt_v1(receipt: Mapping[str, Any]) -> None:
    """**§7** — hops via materialized adjacency require derived provenance + edge record id."""
    if receipt.get("via_materialized_adjacency") is not True:
        return
    if receipt.get("provenance_class") != PROVENANCE_CLASS_DERIVED:
        msg = "via_materialized_adjacency requires provenance_class=derived"
        raise WalkExecutionStrategyContractError(msg)
    mid = receipt.get("materialized_edge_record_id")
    if not isinstance(mid, str) or not mid.strip():
        msg = "materialized_edge_record_id required when via_materialized_adjacency=true"
        raise WalkExecutionStrategyContractError(msg)


def list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1(
    hash_body: Any,
    *,
    path: str = "hash_body",
) -> list[str]:
    """**FS-WES-03** — forbidden optimization markers under ``hash_body`` (doctrine §11)."""
    errors: list[str] = []
    if isinstance(hash_body, dict):
        for k, v in hash_body.items():
            ks = str(k)
            if ks in _FORBIDDEN_WES03_HASH_BODY_KEYS:
                errors.append(f"FS-WES-03:forbidden_key:{path}.{ks}")
            sub = f"{path}.{ks}"
            errors.extend(list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1(v, path=sub))
    elif isinstance(hash_body, list):
        for i, v in enumerate(hash_body):
            errors.extend(
                list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1(v, path=f"{path}[{i}]")
            )
    return errors


def validate_fast_path_equivalence_record_v1(record: Mapping[str, Any]) -> None:
    """**RULE WES-02** / **FS-WES-02** — when ``fast_path_allowed``, online vs fast hashes match."""
    if not isinstance(record, dict):
        msg = "equivalence record must be an object"
        raise WalkExecutionStrategyContractError(msg)
    if record.get("fast_path_allowed") is not True:
        return
    online = record.get("online_walk_result_hash")
    fast = record.get("fast_path_walk_result_hash")
    for label, h in (("online_walk_result_hash", online), ("fast_path_walk_result_hash", fast)):
        if not isinstance(h, str) or not _WALK_RESULT_HASH_RE.fullmatch(h):
            msg = f"{label} must match sha256:[0-9a-f]{{64}} when fast_path_allowed=true"
            raise WalkExecutionStrategyContractError(msg)
    if online != fast:
        msg = (
            "FS-WES-02: online_walk_result_hash must equal fast_path_walk_result_hash "
            "when fast_path_allowed=true"
        )
        raise WalkExecutionStrategyContractError(msg)


def verify_gp05_equiv01_fast_path_online_equivalence_static() -> dict[str, Any]:
    """**G-P05-EQUIV-01** — golden record: fast path hash matches online reference."""
    errors: list[str] = []
    d = octs_walk_execution_strategy_fixture_dir()
    good = d / "equiv_fast_path_online_match_v1.json"
    if not good.is_file():
        errors.append(f"missing_fixture:{good}")
    else:
        raw = json.loads(good.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            errors.append("equiv_fast_path_online_match_v1_not_object")
        else:
            try:
                validate_fast_path_equivalence_record_v1(cast(Mapping[str, Any], raw))
            except WalkExecutionStrategyContractError as exc:
                errors.append(f"good_fixture_failed:{exc}")

    bad = d / "equiv_fast_path_online_mismatch_v1.json"
    if not bad.is_file():
        errors.append(f"missing_fixture:{bad}")
    else:
        raw_b = json.loads(bad.read_text(encoding="utf-8"))
        if not isinstance(raw_b, dict):
            errors.append("equiv_fast_path_online_mismatch_v1_not_object")
        else:
            try:
                validate_fast_path_equivalence_record_v1(cast(Mapping[str, Any], raw_b))
            except WalkExecutionStrategyContractError:
                pass
            else:
                errors.append("expected_mismatch_fixture_to_fail_equivalence")

    passed = len(errors) == 0
    return {
        "id": "G-P05-EQUIV-01",
        "name": "fast_path_online_walk_result_hash_equivalence",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wes_runtime_schema_version": WES_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_wes01_strategy_affects_policy_hash_static() -> dict[str, Any]:
    """**RULE WES-01** — ``walk_execution_strategy`` is merged into ``policy_hash`` material."""
    errors: list[str] = []
    try:
        from vector.domains.cortex.traversal.walk_policy import compute_policy_hash_v1
    except ImportError as exc:  # pragma: no cover
        errors.append(f"import_walk_policy:{exc}")
        return _wes01_result(errors)

    policy: dict[str, Any] = {
        "max_hops": 8,
        "max_frontier": 64,
        "max_edges_visited": 500,
        "max_wall_ms": 100,
        "hop_class_allowlist": ["org.handle_links_canonical"],
        "tie_break": ["fingerprint", "org_link_id"],
        "respect_validity": True,
        "policy_version": 1,
    }
    h_online = compute_policy_hash_v1(
        policy, walk_execution_strategy=WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED
    )
    h_mat = compute_policy_hash_v1(
        policy, walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED
    )
    if h_online == h_mat:
        errors.append("expected_policy_hash_to_differ_when_walk_execution_strategy_changes")

    return _wes01_result(errors)


def _wes01_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-WES-01",
        "name": "walk_execution_strategy_in_policy_hash",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wes_runtime_schema_version": WES_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_wes03_forbidden_optimization_hash_body_scan_static() -> dict[str, Any]:
    """**FS-WES-03** — static scan rejects known forbidden optimization key names."""
    errors: list[str] = []
    bad_body = {"hop_receipts": [], "merged_hops": [1, 2]}
    if list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1(bad_body) == []:
        errors.append("expected_merged_hops_to_trigger_fs_wes03")

    good_body = {"hop_receipts": [], "termination_reason": "max_hops_reached"}
    if list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1(good_body) != []:
        errors.append("unexpected_violation_on_clean_hash_body_shape")

    passed = len(errors) == 0
    return {
        "id": "G-P05-WES-02",
        "name": "forbidden_optimization_keys_under_hash_body",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wes_runtime_schema_version": WES_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

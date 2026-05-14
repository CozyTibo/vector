"""Phase 05 P05-05 — traversal vs reasoning (output algebra + schema closure).

Normative: ``DOCS/cortex/05-traversal/phase-05-traversal-vs-reasoning-doctrine.md``.
JSON Schema: ``DOCS/cortex/05-traversal/schemas/octs-walk-request-v1.schema.json``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast

import jsonschema  # type: ignore[import-untyped]

from vector.domains.cortex.traversal.anti_goals import (
    validate_octs_canonical_json_mapping_no_cognition_leakage,
)

TVR_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# **RULE TVR-01** strict — hash-body key closure v1
# (``phase-05-walk-result-contract.md`` §4 + structural extras from TVR §3).
WALK_RESULT_HASH_BODY_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "octs_schema_version",
        "temporal_anchor",
        "policy_hash",
        "start_node_ids",
        "termination_reason",
        "hop_receipts",
        "execution_path_contains_derived",
        "path_edge_fingerprints_ordered",
        "execution_partition",
        "non_authoritative",
        "vertices",
        "edges",
        "diagnostics",
    }
)


class TraversalReasoningBoundaryError(ValueError):
    """Raised when a walk result hash body violates TVR / FS-TVR-* closure."""


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
    msg = (
        "Could not locate DOCS/cortex/05-traversal/schemas/octs-walk-request-v1.schema.json "
        "from traversal_vs_reasoning module path."
    )
    raise RuntimeError(msg)


def oct_walk_request_v1_schema_path() -> Path:
    root = _repo_root_with_oct_schemas()
    return (
        root / "DOCS" / "cortex" / "05-traversal" / "schemas" / "octs-walk-request-v1.schema.json"
    )


def oct_walk_request_minimal_fixture_path() -> Path:
    """Resolve the golden walk-request fixture.

    Monorepo checkout: ``<repo>/backend/tests/vector/...``.
    Backend Docker image (``WORKDIR /app``, Compose mounts): ``<app>/tests/vector/...``.
    """
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "walks"
        / "walk_request_minimal_v1.json"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_file():
        return flat
    if nested.is_file():
        return nested
    msg = f"Could not find walk_request_minimal_v1.json; tried {flat} and {nested}"
    raise RuntimeError(msg)


def load_oct_walk_request_v1_schema() -> dict[str, Any]:
    text = oct_walk_request_v1_schema_path().read_text(encoding="utf-8")
    return cast(dict[str, Any], json.loads(text))


def validate_oct_walk_request_v1(instance: Mapping[str, Any]) -> None:
    """**G-P05-SCHEMA-01** — validate POST body against authoritative JSON Schema."""
    schema = load_oct_walk_request_v1_schema()
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    try:
        cls(schema).validate(dict(instance))
    except jsonschema.ValidationError as exc:
        msg = f"OCT walk request v1 schema violation: {exc.message}"
        raise TraversalReasoningBoundaryError(msg) from exc


def list_walk_result_hash_body_unknown_keys_v1(body: Mapping[str, Any]) -> list[str]:
    """Return keys present in ``body`` but not in ``WALK_RESULT_HASH_BODY_KEYS_V1``."""
    extra = sorted(set(body.keys()) - WALK_RESULT_HASH_BODY_KEYS_V1)
    return [f"unknown_hash_body_key:{k}" for k in extra]


def validate_walk_result_hash_body_tvr_strict_v1(body: Mapping[str, Any]) -> None:
    """**RULE TVR-01** strict + **FS-TVR-01..03** via cognition scan (``anti_goals``)."""
    unknown = list_walk_result_hash_body_unknown_keys_v1(body)
    if unknown:
        msg = "walk result hash_body strict closure failed: " + "; ".join(unknown[:20])
        if len(unknown) > 20:
            msg += f"; …(+{len(unknown) - 20} more)"
        raise TraversalReasoningBoundaryError(msg)
    validate_octs_canonical_json_mapping_no_cognition_leakage(body)


def verify_gp05_tvr01_walk_result_hash_body_strict_static() -> dict[str, Any]:
    """**G-P05-TVR-01** — strict hash-body allowlist + anti-cognition keys."""
    errors: list[str] = []
    good: dict[str, Any] = {
        "octs_schema_version": 1,
        "temporal_anchor": {"tenant_id": "00000000-0000-0000-0000-000000000001"},
        "policy_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "start_node_ids": ["00000000-0000-0000-0000-000000000002"],
        "termination_reason": "target_reached",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
    }
    try:
        validate_walk_result_hash_body_tvr_strict_v1(good)
    except TraversalReasoningBoundaryError as exc:
        errors.append(f"unexpected_rejection_good_body:{exc}")

    bad_extra = {**good, "why_this_path": "illegal prose"}
    try:
        validate_walk_result_hash_body_tvr_strict_v1(bad_extra)
    except TraversalReasoningBoundaryError:
        pass
    else:
        errors.append("expected_rejection_for_why_this_path")

    bad_unknown = {**good, "utility": 1}
    try:
        validate_walk_result_hash_body_tvr_strict_v1(bad_unknown)
    except TraversalReasoningBoundaryError:
        pass
    else:
        errors.append("expected_rejection_for_unknown_top_level_key")

    passed = len(errors) == 0
    return {
        "id": "G-P05-TVR-01",
        "name": "walk_result_hash_body_strict_closure_v1",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"tvr_runtime_schema_version": TVR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_schema01_oct_walk_request_v1_static() -> dict[str, Any]:
    """**G-P05-SCHEMA-01** — golden walk request validates; extra top-level key rejected."""
    errors: list[str] = []
    path = oct_walk_request_minimal_fixture_path()
    if not path.is_file():
        errors.append(f"missing_fixture:{path}")
        return {
            "id": "G-P05-SCHEMA-01",
            "name": "oct_walk_request_json_schema_v1",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"tvr_runtime_schema_version": TVR_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        validate_oct_walk_request_v1(raw)
    except TraversalReasoningBoundaryError as exc:
        errors.append(f"golden_fixture_invalid:{exc}")

    poisoned = {**raw, "smuggled_field": True}
    try:
        validate_oct_walk_request_v1(poisoned)
    except TraversalReasoningBoundaryError:
        pass
    else:
        errors.append("expected_additional_properties_reject_smuggled_field")

    passed = len(errors) == 0
    return {
        "id": "G-P05-SCHEMA-01",
        "name": "oct_walk_request_json_schema_v1",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"tvr_runtime_schema_version": TVR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

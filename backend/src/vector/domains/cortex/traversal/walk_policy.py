"""Phase 05 P05-08 — walk policy (hashable ``walk_policy``, caps, **G-P05-POL-01/02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-walk-policy-doctrine.md``.
JSON Schema: ``DOCS/cortex/05-traversal/schemas/octs-walk-policy-v1.schema.json``.
Sync caps: ``phase-05-walk-api-contracts.md`` §Sync limits (Step 18).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast

import jsonschema  # type: ignore[import-untyped]

WP_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# ``phase-05-walk-api-contracts.md`` §Sync limits (default strict, **Step 18**).
SYNC_MAX_HOPS: Final[int] = 32
SYNC_MAX_EDGES_VISITED: Final[int] = 10_000
SYNC_MAX_WALL_MS: Final[int] = 150
# Sync **HTTP response** JSON (canonical UTF-8 length; **FS-API-01**).
SYNC_MAX_RESPONSE_JSON_BYTES: Final[int] = 256 * 1024
# Sync **POST** JSON body (canonical UTF-8 length; abuse defense §11 same doc).
SYNC_MAX_REQUEST_JSON_BYTES: Final[int] = 256 * 1024

_POLICY_HASH_PREFIX: Final[str] = "sha256:"
_TIE_BREAK_ORDER_ALLOWED: Final[frozenset[str]] = frozenset(
    {"fingerprint", "org_link_id", "lex_org_link_id"}
)

_FORBIDDEN_RANKING_POLICY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "edge_weights",
        "ranking_weights",
        "semantic_scores",
    }
)


class WalkPolicyInvariantError(ValueError):
    """Raised when ``walk_policy`` violates WP / FS-WP-* / sync caps."""


_OCT_WALK_POLICY_SCHEMA_FILENAME_V1: Final[str] = "octs-walk-policy-v1.schema.json"
_BUNDLED_SCHEMA_DIR_V1: Final[Path] = Path(__file__).resolve().parent / "schemas"
_DOCS_SCHEMA_REL_V1: Final[Path] = (
    Path("DOCS")
    / "cortex"
    / "05-traversal"
    / "schemas"
    / _OCT_WALK_POLICY_SCHEMA_FILENAME_V1
)


def bundled_oct_walk_policy_v1_schema_path() -> Path:
    """Packaged schema shipped in worker/API images (``src/.../traversal/schemas``)."""
    return _BUNDLED_SCHEMA_DIR_V1 / _OCT_WALK_POLICY_SCHEMA_FILENAME_V1


def _repo_root_with_oct_schemas() -> Path:
    """Monorepo root for golden fixtures (dev/CI only; not required in production images)."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        if (root / _DOCS_SCHEMA_REL_V1).is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/schemas/octs-walk-policy-v1.schema.json "
        "from walk_policy module path."
    )
    raise RuntimeError(msg)


def oct_walk_policy_v1_schema_path() -> Path:
    """Resolve OCTS walk policy JSON Schema (bundled first, monorepo DOCS fallback)."""
    bundled = bundled_oct_walk_policy_v1_schema_path()
    if bundled.is_file():
        return bundled
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        docs_path = root / _DOCS_SCHEMA_REL_V1
        if docs_path.is_file():
            return docs_path
    msg = (
        f"Could not locate {_OCT_WALK_POLICY_SCHEMA_FILENAME_V1}: "
        f"expected bundled path {bundled} or monorepo {_DOCS_SCHEMA_REL_V1}"
    )
    raise RuntimeError(msg)


def octs_walk_policy_fixture_dir() -> Path:
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "walk_policy"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"walk_policy golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def load_oct_walk_policy_v1_schema() -> dict[str, Any]:
    text = oct_walk_policy_v1_schema_path().read_text(encoding="utf-8")
    return cast(dict[str, Any], json.loads(text))


def validate_oct_walk_policy_v1_jsonschema(instance: Mapping[str, Any]) -> None:
    """Validate ``walk_policy`` subtree against **octs-walk-policy-v1**."""
    schema = load_oct_walk_policy_v1_schema()
    cls = jsonschema.validators.validator_for(schema)
    cls.check_schema(schema)
    try:
        cls(schema).validate(dict(instance))
    except jsonschema.ValidationError as exc:
        msg = f"OCT walk policy v1 schema violation: {exc.message}"
        raise WalkPolicyInvariantError(msg) from exc


def _nfc_json_strings(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _nfc_json_strings(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_nfc_json_strings(x) for x in obj]
    return obj


def list_policy_hash_forbidden_key_violations(policy: Mapping[str, Any]) -> list[str]:
    """**§8** — keys that MUST NOT enter ``policy_hash`` material."""
    errors: list[str] = []
    for k in policy.keys():
        if k == "human_label":
            errors.append("forbidden_policy_key:human_label")
        elif str(k).endswith("_telemetry"):
            errors.append(f"forbidden_policy_key:{k}")
    return errors


def walk_policy_merged_for_hash_v1(
    walk_policy: Mapping[str, Any],
    *,
    walk_execution_strategy: str,
) -> dict[str, Any]:
    """Merge execution strategy into policy material; strip hash-forbidden keys."""
    base: dict[str, Any] = {}
    for k, v in walk_policy.items():
        if k == "human_label" or str(k).endswith("_telemetry"):
            continue
        base[str(k)] = v
    base["walk_execution_strategy"] = walk_execution_strategy
    return cast(dict[str, Any], _nfc_json_strings(base))


def walk_policy_canonical_json_bytes_for_hash_v1(
    walk_policy: Mapping[str, Any],
    *,
    walk_execution_strategy: str,
) -> bytes:
    """Canonical UTF-8 JSON for ``policy_hash`` (**§8**, **normative index**)."""
    merged = walk_policy_merged_for_hash_v1(
        walk_policy, walk_execution_strategy=walk_execution_strategy
    )
    return json.dumps(merged, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_policy_hash_v1(
    walk_policy: Mapping[str, Any],
    *,
    walk_execution_strategy: str,
) -> str:
    """``policy_hash`` = ``sha256:`` + 64 hex over canonical merged policy (**§8**)."""
    body = walk_policy_canonical_json_bytes_for_hash_v1(
        walk_policy, walk_execution_strategy=walk_execution_strategy
    )
    digest = hashlib.sha256(body).hexdigest()
    return f"{_POLICY_HASH_PREFIX}{digest}"


def _reject_floats_recursive(obj: Any, path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(obj, float):
        errors.append(f"fs_wp_03_float_at:{path}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            errors.extend(_reject_floats_recursive(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(_reject_floats_recursive(v, f"{path}[{i}]"))
    return errors


def list_walk_policy_rank_smuggling_violations_v1(policy: Mapping[str, Any]) -> list[str]:
    """Reject score-like maps forbidden by doctrine §11 (static class)."""
    errors: list[str] = []
    for k in policy:
        if k in _FORBIDDEN_RANKING_POLICY_KEYS:
            errors.append(f"forbidden_ranking_policy_key:{k}")
    return errors


def list_walk_policy_strict_semantic_violations_v1(
    walk_policy: Mapping[str, Any],
    *,
    exploration_mode: bool,
) -> list[str]:
    """**FS-WP-01**, **FS-WP-02**, **FS-WP-03**, **§6** ``respect_validity``, **§8** keys."""
    errors: list[str] = []
    if not isinstance(walk_policy, dict):
        return ["walk_policy_not_object"]

    errors.extend(list_policy_hash_forbidden_key_violations(walk_policy))
    errors.extend(_reject_floats_recursive(walk_policy, "walk_policy"))
    errors.extend(list_walk_policy_rank_smuggling_violations_v1(walk_policy))

    if "max_hops" not in walk_policy:
        errors.append("fs_wp_01_max_hops_absent")

    hops = walk_policy.get("max_hops")
    if isinstance(hops, bool) or not isinstance(hops, int):
        if "max_hops" in walk_policy:
            errors.append("max_hops_not_integer")
    elif hops < 1:
        errors.append("max_hops_below_one")

    allow = walk_policy.get("hop_class_allowlist")
    if isinstance(allow, list):
        has_wildcard = any(isinstance(x, str) and x.strip() == "*" for x in allow)
        if has_wildcard and not exploration_mode:
            errors.append("fs_wp_02_wildcard_hop_class_without_exploration_partition")

    tb = walk_policy.get("tie_break")
    if isinstance(tb, list):
        for i, token in enumerate(tb):
            if not isinstance(token, str):
                errors.append(f"tie_break_{i}_not_string")
            elif token not in _TIE_BREAK_ORDER_ALLOWED:
                errors.append(f"tie_break_unknown_token:{token!r}")

    rv = walk_policy.get("respect_validity", True)
    if rv is False:
        diag = walk_policy.get("diagnostics_only", False)
        if not exploration_mode and not diag:
            errors.append("respect_validity_false_requires_exploration_or_diagnostics_only")

    return errors


def list_walk_policy_sync_cap_violations_v1(walk_policy: Mapping[str, Any]) -> list[str]:
    """**G-P05-POL-02** — sync path caps (``phase-05-walk-api-contracts.md`` §Sync limits)."""
    errors: list[str] = []
    if not isinstance(walk_policy, dict):
        return errors
    mh = walk_policy.get("max_hops")
    if isinstance(mh, int) and mh > SYNC_MAX_HOPS:
        errors.append(f"sync_cap_max_hops:{mh}>{SYNC_MAX_HOPS}")
    me = walk_policy.get("max_edges_visited")
    if isinstance(me, int) and me > SYNC_MAX_EDGES_VISITED:
        errors.append(f"sync_cap_max_edges_visited:{me}>{SYNC_MAX_EDGES_VISITED}")
    mw = walk_policy.get("max_wall_ms")
    if isinstance(mw, int) and mw > SYNC_MAX_WALL_MS:
        errors.append(f"sync_cap_max_wall_ms:{mw}>{SYNC_MAX_WALL_MS}")
    return errors


def validate_walk_policy_for_request_v1(
    walk_policy: Mapping[str, Any],
    *,
    walk_execution_strategy: str,
    exploration_mode: bool,
    enforce_sync_caps: bool,
) -> None:
    """Full policy validation: JSON Schema + semantics + optional sync caps."""
    validate_oct_walk_policy_v1_jsonschema(walk_policy)
    sem = list_walk_policy_strict_semantic_violations_v1(
        walk_policy, exploration_mode=exploration_mode
    )
    if sem:
        msg = "walk policy semantic violations: " + "; ".join(sem[:20])
        raise WalkPolicyInvariantError(msg)
    if enforce_sync_caps:
        caps = list_walk_policy_sync_cap_violations_v1(walk_policy)
        if caps:
            msg = "walk policy sync cap violations: " + "; ".join(caps)
            raise WalkPolicyInvariantError(msg)

    from vector.domains.cortex.traversal.walk_execution_strategy_contract import (
        WalkExecutionStrategyContractError,
        validate_hybrid_policy_integer_threshold_for_strategy_v1,
    )

    try:
        validate_hybrid_policy_integer_threshold_for_strategy_v1(
            walk_execution_strategy, walk_policy
        )
    except WalkExecutionStrategyContractError as exc:
        raise WalkPolicyInvariantError(str(exc)) from exc


def verify_gp05_pol01_walk_policy_schema_and_hash_static() -> dict[str, Any]:
    """**G-P05-POL-01** — JSON Schema + semantics + golden ``policy_hash``."""
    errors: list[str] = []
    d = octs_walk_policy_fixture_dir()
    bundle_path = d / "bundle_good_v1.json"
    expected_path = d / "policy_hash_expected_v1.txt"
    if not bundle_path.is_file():
        errors.append(f"missing_fixture:{bundle_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if errors:
        return {
            "id": "G-P05-POL-01",
            "name": "walk_policy_schema_and_hash",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"wp_runtime_schema_version": WP_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        errors.append("bundle_good_v1_not_object")
    else:
        policy = bundle.get("walk_policy")
        strat = bundle.get("walk_execution_strategy")
        expl = bundle.get("exploration_mode", False)
        if not isinstance(policy, dict) or not isinstance(strat, str):
            errors.append("bundle_good_v1_invalid_shape")
        else:
            try:
                validate_walk_policy_for_request_v1(
                    policy,
                    walk_execution_strategy=strat,
                    exploration_mode=bool(expl),
                    enforce_sync_caps=False,
                )
            except WalkPolicyInvariantError as exc:
                errors.append(f"policy_validation_failed:{exc}")
            if not errors:
                actual = compute_policy_hash_v1(policy, walk_execution_strategy=strat)
                expected = expected_path.read_text(encoding="utf-8").strip()
                if actual != expected:
                    errors.append(f"policy_hash_mismatch:actual={actual!r} expected={expected!r}")

    over = d / "bundle_sync_over_cap_v1.json"
    if over.is_file():
        ob = json.loads(over.read_text(encoding="utf-8"))
        if isinstance(ob, dict) and isinstance(ob.get("walk_policy"), dict):
            caps = list_walk_policy_sync_cap_violations_v1(ob["walk_policy"])
            if caps == []:
                errors.append("expected_sync_over_cap_fixture_to_fail_caps")
        elif ob is not None:
            errors.append("bundle_sync_over_cap_invalid_shape")
    else:
        errors.append(f"missing_fixture:{over}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-POL-01",
        "name": "walk_policy_schema_and_hash",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wp_runtime_schema_version": WP_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_pol02_sync_caps_reject_static() -> dict[str, Any]:
    """**G-P05-POL-02** — sync caps reject over-limit budgets."""
    errors: list[str] = []
    d = octs_walk_policy_fixture_dir()
    over_path = d / "bundle_sync_over_cap_v1.json"
    if not over_path.is_file():
        errors.append(f"missing_fixture:{over_path}")
    else:
        ob = json.loads(over_path.read_text(encoding="utf-8"))
        if isinstance(ob, dict) and isinstance(ob.get("walk_policy"), dict):
            policy = ob["walk_policy"]
            strat = ob.get("walk_execution_strategy", "ONLINE_OBSERVED")
            expl = bool(ob.get("exploration_mode", False))
            if not isinstance(strat, str):
                errors.append("bundle_sync_over_cap_bad_strategy")
            else:
                try:
                    validate_walk_policy_for_request_v1(
                        policy,
                        walk_execution_strategy=strat,
                        exploration_mode=expl,
                        enforce_sync_caps=True,
                    )
                except WalkPolicyInvariantError:
                    pass
                else:
                    errors.append("expected_sync_cap_enforcement_to_fail")
        else:
            errors.append("bundle_sync_over_cap_invalid_shape")

    good_path = d / "bundle_good_v1.json"
    if good_path.is_file():
        gb = json.loads(good_path.read_text(encoding="utf-8"))
        if isinstance(gb, dict) and isinstance(gb.get("walk_policy"), dict):
            try:
                wes = str(gb.get("walk_execution_strategy", "ONLINE_OBSERVED"))
                validate_walk_policy_for_request_v1(
                    gb["walk_policy"],
                    walk_execution_strategy=wes,
                    exploration_mode=bool(gb.get("exploration_mode", False)),
                    enforce_sync_caps=True,
                )
            except WalkPolicyInvariantError as exc:
                errors.append(f"good_bundle_should_pass_sync_caps:{exc}")
    else:
        errors.append(f"missing_fixture:{good_path}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-POL-02",
        "name": "walk_policy_sync_caps",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wp_runtime_schema_version": WP_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

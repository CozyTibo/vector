"""Phase 05 P05-11 — exploration mode (partition + authority markers, **G-P05-EXP-01/02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-exploration-mode-doctrine.md``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    TraversalReasoningBoundaryError,
    load_oct_walk_request_v1_schema,
    validate_oct_walk_request_v1,
)

EX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

EXECUTION_PARTITION_AUTHORITATIVE: Final[str] = "authoritative"
EXECUTION_PARTITION_EXPLORATION: Final[str] = "exploration"
EXECUTION_PARTITION_DERIVED_AUDIT: Final[str] = "derived_audit"
EXECUTION_PARTITION_VALUES: Final[frozenset[str]] = frozenset(
    {
        EXECUTION_PARTITION_AUTHORITATIVE,
        EXECUTION_PARTITION_EXPLORATION,
        EXECUTION_PARTITION_DERIVED_AUDIT,
    }
)

TABLE_CORTEX_OCTS_WALK_EXPLORATION: Final[str] = "cortex_octs_walk_exploration"
TABLE_CORTEX_OCTS_WALK_AUTHORITATIVE: Final[str] = "cortex_octs_walk_authoritative"

CACHE_KEY_PREFIX_EXPLORATION: Final[str] = "octs:explore:"
CACHE_KEY_PREFIX_AUTHORITATIVE: Final[str] = "octs:auth:"

CELERY_QUEUE_EXPLORATION: Final[str] = "octs.walk.exploration"
CELERY_QUEUE_AUTHORITATIVE: Final[str] = "octs.walk.authoritative"

OTEL_EXPLORATION_SINK_NAME: Final[str] = "octs-exploration"

CODEC_CLASS_EXPLORATION: Final[str] = "ExplorationOCTSCodec"
CODEC_CLASS_AUTHORITATIVE: Final[str] = "AuthoritativeOCTSCodec"


class ExplorationModeContractError(ValueError):
    """Raised when exploration / authority isolation rules are violated."""


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
    msg = "Could not locate DOCS/cortex/05-traversal/schemas from exploration_mode_contract."
    raise RuntimeError(msg)


def octs_exploration_fixture_dir() -> Path:
    """Directory holding **G-P05-EXP-01** / **G-P05-EXP-02** golden vectors."""
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "exploration"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"exploration golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def exploration_partition_id_v1(walk_id: str) -> str:
    """``partition_id = explore:`` + ``walk_id`` (**§3** ``exploration_mode``)."""
    w = str(walk_id).strip()
    if not w:
        msg = "walk_id must be non-empty for exploration_partition_id_v1"
        raise ExplorationModeContractError(msg)
    return f"explore:{w}"


def validate_execution_partition_enum_v1(body: Mapping[str, Any]) -> None:
    """**§8** — ``execution_partition`` when present must be a known enum value."""
    ep = body.get("execution_partition")
    if ep is None:
        return
    if not isinstance(ep, str) or ep not in EXECUTION_PARTITION_VALUES:
        msg = f"execution_partition must be one of {sorted(EXECUTION_PARTITION_VALUES)!r}"
        raise ExplorationModeContractError(msg)


def validate_exploration_hash_body_invariants_v1(body: Mapping[str, Any]) -> None:
    """**RULE EX-01**, **FS-EX-02**, **§7** hop ``partition`` when exploration markers are set."""
    validate_execution_partition_enum_v1(body)
    ep = body.get("execution_partition")
    na = body.get("non_authoritative")
    exploration_marked = ep == EXECUTION_PARTITION_EXPLORATION or na is True
    if not exploration_marked:
        return
    if ep != EXECUTION_PARTITION_EXPLORATION or na is not True:
        msg = (
            "FS-EX-02 / RULE EX-01: exploration hash_body requires "
            "execution_partition='exploration' and non_authoritative=true together"
        )
        raise ExplorationModeContractError(msg)
    hrs = body.get("hop_receipts")
    if not isinstance(hrs, list) or not hrs:
        return
    for i, r in enumerate(hrs):
        if not isinstance(r, dict):
            continue
        if r.get("partition") != EXECUTION_PARTITION_EXPLORATION:
            msg = (
                f"hop[{i}]: exploration walks require hop_receipt.partition="
                f"{EXECUTION_PARTITION_EXPLORATION!r}"
            )
            raise ExplorationModeContractError(msg)


def validate_row_destination_exploration_law_v1(*, table_name: str, partition: str) -> None:
    """**G-P05-EXP-02** / **RULE EX-P1** — exploration rows forbidden on authoritative table."""
    t = table_name.strip().lower()
    auth = TABLE_CORTEX_OCTS_WALK_AUTHORITATIVE.lower()
    if t == auth or t.endswith(auth):
        if partition == EXECUTION_PARTITION_EXPLORATION:
            msg = (
                "exploration partition rows must not target authoritative-only table "
                f"{TABLE_CORTEX_OCTS_WALK_AUTHORITATIVE!r}"
            )
            raise ExplorationModeContractError(msg)


def assert_redis_cache_key_namespace_v1(key: str, *, exploration: bool) -> None:
    """**RULE EX-P2** / **FS-EX-04** — Redis key prefix by authority lane."""
    if exploration:
        if not key.startswith(CACHE_KEY_PREFIX_EXPLORATION):
            msg = (
                f"FS-EX-04: exploration cache key must start with {CACHE_KEY_PREFIX_EXPLORATION!r}"
            )
            raise ExplorationModeContractError(msg)
        return
    if not key.startswith(CACHE_KEY_PREFIX_AUTHORITATIVE):
        msg = (
            f"FS-EX-04: authoritative cache key must start with {CACHE_KEY_PREFIX_AUTHORITATIVE!r}"
        )
        raise ExplorationModeContractError(msg)


def verify_gp05_exp01_walk_request_explicit_exploration_mode_static() -> dict[str, Any]:
    """**G-P05-EXP-01** — schema requires explicit ``exploration_mode``; golden default is false."""
    errors: list[str] = []
    schema = load_oct_walk_request_v1_schema()
    req = schema.get("required") or []
    if "exploration_mode" not in req:
        errors.append("schema_must_require_exploration_mode_key")

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
    path_found: Path | None = None
    for path in (root / "tests" / rel, root / "backend" / "tests" / rel):
        if path.is_file():
            path_found = path
            break
    if path_found is None:
        errors.append("missing_walk_request_minimal_v1_fixture")
    else:
        raw = json.loads(path_found.read_text(encoding="utf-8"))
        if raw.get("exploration_mode") is not False:
            errors.append(f"golden_walk_request_exploration_mode_not_false:{path_found}")
        try:
            validate_oct_walk_request_v1(raw)
        except TraversalReasoningBoundaryError as exc:
            errors.append(f"golden_walk_request_invalid:{exc}")
        bad = dict(raw)
        bad.pop("exploration_mode", None)
        try:
            validate_oct_walk_request_v1(bad)
        except TraversalReasoningBoundaryError:
            pass
        else:
            errors.append("expected_schema_reject_when_exploration_mode_omitted")

    passed = len(errors) == 0
    return {
        "id": "G-P05-EXP-01",
        "name": "walk_request_explicit_exploration_mode",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ex_runtime_schema_version": EX_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_exp02_authoritative_table_rejects_exploration_partition_static() -> dict[str, Any]:
    """**G-P05-EXP-02** — authoritative storage must not accept exploration partition."""
    errors: list[str] = []
    try:
        validate_row_destination_exploration_law_v1(
            table_name=TABLE_CORTEX_OCTS_WALK_AUTHORITATIVE,
            partition=EXECUTION_PARTITION_EXPLORATION,
        )
    except ExplorationModeContractError:
        pass
    else:
        errors.append("expected_authoritative_plus_exploration_partition_to_fail")

    try:
        validate_row_destination_exploration_law_v1(
            table_name=TABLE_CORTEX_OCTS_WALK_AUTHORITATIVE,
            partition=EXECUTION_PARTITION_AUTHORITATIVE,
        )
    except ExplorationModeContractError as exc:
        errors.append(f"unexpected_rejection_authoritative_partition:{exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-EXP-02",
        "name": "authoritative_table_exploration_partition_law",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ex_runtime_schema_version": EX_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

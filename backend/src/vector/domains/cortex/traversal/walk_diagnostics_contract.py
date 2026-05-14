"""Phase 05 P05-12 — walk diagnostics (closed enums, **G-P05-DIAG-01**, **G-P05-DIAG-02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-walk-diagnostics-doctrine.md``.
Cycle multiset law: ``multigraph_model.canonical_diagnostic_multiset_fingerprints_v1`` (**§7**).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.multigraph_model import (
    canonical_diagnostic_multiset_fingerprints_v1,
)

WD_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_SHA256_FP_PATTERN: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

TERMINATION_REASON_VALUES_V1: Final[frozenset[str]] = frozenset(
    {
        "target_reached",
        "budget_exhausted",
        "empty_frontier",
        "cycle_cut",
        "invalid_edge_at_t",
        "policy_rejected",
        "error_internal",
        "dangling_evidence",
        "import_hash_mismatch",
    }
)

SKIP_REASON_VALUES_V1: Final[frozenset[str]] = frozenset(
    {
        "not_in_allowlist",
        "filtered_by_authority",
        "invalid_at_t",
        "deduped_revisit_forbidden",
    }
)


class WalkDiagnosticsContractError(ValueError):
    """Raised when walk diagnostics / hash_body diagnostics violate doctrine."""


def _repo_root_with_oct_schemas() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = (
            root
            / "DOCS"
            / "cortex"
            / "05-traversal"
            / "schemas"
            / "octs-walk-diagnostics-enums-v1.schema.json"
        )
        if marker.is_file():
            return root
    msg = (
        "Could not locate octs-walk-diagnostics-enums-v1.schema.json "
        "from walk_diagnostics_contract."
    )
    raise RuntimeError(msg)


def octs_walk_diagnostics_fixture_dir() -> Path:
    """Golden vectors for **G-P05-DIAG-02** (cycle fingerprint)."""
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "diagnostics"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"diagnostics golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def octs_walk_diagnostics_enums_schema_path() -> Path:
    root = _repo_root_with_oct_schemas()
    return (
        root
        / "DOCS"
        / "cortex"
        / "05-traversal"
        / "schemas"
        / "octs-walk-diagnostics-enums-v1.schema.json"
    )


def assert_sha256_fingerprint_string_v1(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not _SHA256_FP_PATTERN.fullmatch(value):
        msg = f"{field_name} must match sha256:[0-9a-f]{{64}}"
        raise WalkDiagnosticsContractError(msg)
    return value


def compute_cycle_fingerprint_v1(edge_fingerprints_on_cycle: Sequence[str]) -> str:
    """**§7** — SHA-256 over JSON encoding of sorted multiset of cycle edge fingerprints."""
    ordered = canonical_diagnostic_multiset_fingerprints_v1(list(edge_fingerprints_on_cycle))
    for fp in ordered:
        assert_sha256_fingerprint_string_v1(fp, field_name="cycle_edge_fingerprint")
    payload = json.dumps(ordered, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_skip_reason_enum_v1(value: object) -> None:
    """**FS-WD-01** — per-hop ``skip_reason`` closed enum when present."""
    if not isinstance(value, str) or value not in SKIP_REASON_VALUES_V1:
        msg = f"FS-WD-01: unknown skip_reason: {value!r}"
        raise WalkDiagnosticsContractError(msg)


def validate_termination_reason_enum_v1(value: object) -> None:
    """**FS-WD-01** / **FS-WD-02** — walk ``termination_reason``."""
    if value is None:
        msg = "FS-WD-02: termination_reason missing"
        raise WalkDiagnosticsContractError(msg)
    if not isinstance(value, str) or value not in TERMINATION_REASON_VALUES_V1:
        msg = f"FS-WD-01: unknown termination_reason: {value!r}"
        raise WalkDiagnosticsContractError(msg)


def _diagnostics_is_absent_or_empty_v1(diag: object) -> bool:
    return diag is None or diag == [] or diag == {}


def _validate_invalid_edge_record_v1(rec: object) -> None:
    """**§6** — ``invalid_edge_record`` allowlist shape (keys sorted at canonicalize time)."""
    if not isinstance(rec, dict):
        msg = "invalid_edge_record must be an object"
        raise WalkDiagnosticsContractError(msg)
    keys = frozenset(rec.keys())
    allowed = frozenset({"offending_edge_fingerprint"})
    if keys - allowed:
        msg = f"invalid_edge_record unknown keys: {sorted(keys - allowed)}"
        raise WalkDiagnosticsContractError(msg)
    if "offending_edge_fingerprint" not in rec:
        msg = "invalid_edge_record missing offending_edge_fingerprint"
        raise WalkDiagnosticsContractError(msg)
    assert_sha256_fingerprint_string_v1(
        rec["offending_edge_fingerprint"],
        field_name="offending_edge_fingerprint",
    )


def validate_hash_body_diagnostics_contract_v1(body: Mapping[str, Any]) -> None:
    """**RULE WD-01**, termination-linked diagnostics, **FS-WD-03** path/receipt coherence."""
    tr_raw = body.get("termination_reason")
    validate_termination_reason_enum_v1(tr_raw)
    tr = str(tr_raw)

    diag = body.get("diagnostics")

    if tr == "budget_exhausted" and not _diagnostics_is_absent_or_empty_v1(diag):
        msg = (
            "RULE WD-01: budget_exhausted hash_body must not carry non-empty diagnostics "
            "(frontier state belongs in sibling telemetry only)"
        )
        raise WalkDiagnosticsContractError(msg)

    hrs = body.get("hop_receipts")
    path = body.get("path_edge_fingerprints_ordered")
    if tr == "target_reached":
        if isinstance(hrs, list) and len(hrs) > 0:
            if not isinstance(path, list) or len(path) != len(hrs):
                msg = (
                    "FS-WD-03: target_reached with non-empty hop_receipts requires "
                    "path_edge_fingerprints_ordered length to equal hop_receipts length"
                )
                raise WalkDiagnosticsContractError(msg)

    if _diagnostics_is_absent_or_empty_v1(diag):
        if tr == "cycle_cut":
            msg = "cycle_cut requires diagnostics.cycle_fingerprint in hash_body"
            raise WalkDiagnosticsContractError(msg)
        if tr == "invalid_edge_at_t":
            msg = "invalid_edge_at_t requires diagnostics.invalid_edge_record in hash_body"
            raise WalkDiagnosticsContractError(msg)
        return

    if isinstance(diag, list):
        if len(diag) != 0:
            msg = "diagnostics must be an object when non-empty, not a non-empty array"
            raise WalkDiagnosticsContractError(msg)
        return

    if not isinstance(diag, dict):
        msg = "diagnostics must be an object, empty array, or omitted"
        raise WalkDiagnosticsContractError(msg)

    allowed_keys = frozenset({"cycle_fingerprint", "invalid_edge_record"})
    extra = set(diag.keys()) - allowed_keys
    if extra:
        msg = f"diagnostics unknown keys: {sorted(extra)}"
        raise WalkDiagnosticsContractError(msg)

    if tr == "cycle_cut":
        if "cycle_fingerprint" not in diag:
            msg = "cycle_cut requires diagnostics.cycle_fingerprint"
            raise WalkDiagnosticsContractError(msg)
        assert_sha256_fingerprint_string_v1(
            diag["cycle_fingerprint"],
            field_name="cycle_fingerprint",
        )
        if "invalid_edge_record" in diag:
            msg = "cycle_cut diagnostics must not include invalid_edge_record"
            raise WalkDiagnosticsContractError(msg)
    elif tr == "invalid_edge_at_t":
        if "invalid_edge_record" not in diag:
            msg = "invalid_edge_at_t requires diagnostics.invalid_edge_record"
            raise WalkDiagnosticsContractError(msg)
        _validate_invalid_edge_record_v1(diag["invalid_edge_record"])
        if "cycle_fingerprint" in diag:
            msg = "invalid_edge_at_t diagnostics must not include cycle_fingerprint"
            raise WalkDiagnosticsContractError(msg)
    elif diag:
        msg = (
            f"termination_reason={tr!r} forbids non-empty diagnostics object "
            "(only cycle_cut / invalid_edge_at_t may carry structured diagnostics)"
        )
        raise WalkDiagnosticsContractError(msg)


def _read_enum_from_schema_defs(schema: Mapping[str, Any], def_name: str) -> frozenset[str] | None:
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return None
    block = defs.get(def_name)
    if not isinstance(block, dict):
        return None
    enum = block.get("enum")
    if not isinstance(enum, list) or not all(isinstance(x, str) for x in enum):
        return None
    return frozenset(enum)


def verify_gp05_diag01_enum_exhaustiveness_vs_schema_static() -> dict[str, Any]:
    """**G-P05-DIAG-01** — Python allowlists match authoritative JSON Schema (OpenAPI source)."""
    errors: list[str] = []
    path = octs_walk_diagnostics_enums_schema_path()
    if not path.is_file():
        errors.append(f"missing_schema:{path}")
        return _diag01_result(errors)

    try:
        schema = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as exc:
        errors.append(f"schema_load_failed:{exc}")
        return _diag01_result(errors)

    tr_enum = _read_enum_from_schema_defs(schema, "termination_reason_v1")
    sk_enum = _read_enum_from_schema_defs(schema, "skip_reason_v1")
    if tr_enum is None:
        errors.append("schema_missing_or_invalid:$defs.termination_reason_v1.enum")
    elif tr_enum != TERMINATION_REASON_VALUES_V1:
        errors.append(
            "termination_reason_enum_mismatch:"
            f"python={sorted(TERMINATION_REASON_VALUES_V1)!r} "
            f"schema={sorted(tr_enum)!r}"
        )
    if sk_enum is None:
        errors.append("schema_missing_or_invalid:$defs.skip_reason_v1.enum")
    elif sk_enum != SKIP_REASON_VALUES_V1:
        errors.append(
            "skip_reason_enum_mismatch:"
            f"python={sorted(SKIP_REASON_VALUES_V1)!r} schema={sorted(sk_enum)!r}"
        )

    return _diag01_result(errors)


def _diag01_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-DIAG-01",
        "name": "walk_diagnostic_enums_exhaustive_vs_schema",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wd_runtime_schema_version": WD_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_diag02_cycle_fingerprint_golden_static() -> dict[str, Any]:
    """**G-P05-DIAG-02** — multiset cycle fingerprints match golden expected digest."""
    errors: list[str] = []
    d = octs_walk_diagnostics_fixture_dir()
    edges_path = d / "cycle_fingerprint_edges_v1.json"
    expected_path = d / "cycle_fingerprint_expected_v1.txt"
    if not edges_path.is_file():
        errors.append(f"missing_fixture:{edges_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if errors:
        return _diag02_result(errors)

    raw = json.loads(edges_path.read_text(encoding="utf-8"))
    fps = raw.get("edge_fingerprints_on_cycle") if isinstance(raw, dict) else None
    if not isinstance(fps, list) or not all(isinstance(x, str) for x in fps):
        errors.append("edge_fingerprints_on_cycle_invalid")
    else:
        try:
            actual = compute_cycle_fingerprint_v1(fps)
        except WalkDiagnosticsContractError as exc:
            errors.append(f"compute_failed:{exc}")
        else:
            expected = expected_path.read_text(encoding="utf-8").strip()
            if actual != expected:
                errors.append(f"cycle_fingerprint_mismatch:actual={actual!r} expected={expected!r}")

    return _diag02_result(errors)


def _diag02_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-DIAG-02",
        "name": "cycle_fingerprint_golden_v1",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wd_runtime_schema_version": WD_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def validate_walk_diagnostics_hash_body_contract_v1(body: Mapping[str, Any]) -> None:
    """Invoked from ``walk_result_contract`` (after FS-WR-03, before hop receipts)."""
    validate_hash_body_diagnostics_contract_v1(body)

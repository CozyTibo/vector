"""Phase 05 P05-09 — walk result contract (``walk_result_hash``, **G-P05-HASH-01/02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-walk-result-contract.md``.
Canonical profile: ``phase-05-canonicalization-profile.md`` (**OCTS-CANON-1**).
Non-empty ``hop_receipts`` are validated via ``hop_receipt_contract`` (**P05-10** / **FS-HR-***).
Exploration markers on ``hash_body`` use ``exploration_mode_contract`` (**P05-11** / **EX-01**,
**FS-EX-02**).
Walk diagnostics (termination / skip enums, diagnostics shape) use ``walk_diagnostics_contract``
(**P05-12** / **RULE WD-01**, **FS-WD-01..03**, **G-P05-DIAG-01/02**).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.exploration_mode_contract import (
    ExplorationModeContractError,
    validate_exploration_hash_body_invariants_v1,
)
from vector.domains.cortex.traversal.hop_receipt_contract import (
    HopReceiptContractError,
    validate_hop_receipt_list_for_hash_body_v1,
)
from vector.domains.cortex.traversal.temporal_walk import (
    TemporalWalkInvariantError,
    validate_temporal_anchor_invariants_v1,
)
from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    TraversalReasoningBoundaryError,
    validate_walk_result_hash_body_tvr_strict_v1,
)
from vector.domains.cortex.traversal.walk_diagnostics_contract import (
    WalkDiagnosticsContractError,
    validate_walk_diagnostics_hash_body_contract_v1,
)

WR_RUNTIME_SCHEMA_VERSION: Final[int] = 1

_WALK_RESULT_HASH_PREFIX: Final[str] = "sha256:"

# **RULE WR-02** — MUST NOT appear anywhere under ``hash_body`` (including nested keys).
_FORBIDDEN_HASH_BODY_KEY_NAMES: Final[frozenset[str]] = frozenset(
    {
        "human_label",
        "request_trace_id",
        "telemetry",
        "wall_ms",
        "worker_hostname",
    }
)


class WalkResultContractError(ValueError):
    """Raised when a walk result / ``hash_body`` violates the walk result contract."""


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
    msg = "Could not locate DOCS/cortex/05-traversal/schemas from walk_result_contract."
    raise RuntimeError(msg)


def octs_walk_result_fixture_dir() -> Path:
    root = _repo_root_with_oct_schemas()
    rel = (
        Path("vector") / "domains" / "cortex" / "traversal" / "octs_golden_vectors" / "v1" / "walks"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"walks golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def list_wr02_forbidden_key_violations_under_hash_body(obj: Any, path: str) -> list[str]:
    """**RULE WR-02** / **FS-WR-02** — forbidden keys anywhere under ``hash_body``."""
    errors: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _FORBIDDEN_HASH_BODY_KEY_NAMES:
                key_path = f"{path}.{k}" if path else k
                errors.append(f"forbidden_wr02_key:{key_path}")
            sub = f"{path}.{k}" if path else str(k)
            errors.extend(list_wr02_forbidden_key_violations_under_hash_body(v, sub))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            subpath = f"{path}[{i}]" if path else f"[{i}]"
            errors.extend(list_wr02_forbidden_key_violations_under_hash_body(v, subpath))
    return errors


def list_fs_wr03_duplicate_hop_sequence_violations(hop_receipts: Any) -> list[str]:
    """**FS-WR-03** — duplicate ``hop_sequence`` in ``hop_receipts``."""
    if not isinstance(hop_receipts, list):
        return []
    seen: set[int] = set()
    errors: list[str] = []
    for i, r in enumerate(hop_receipts):
        if not isinstance(r, dict):
            continue
        seq = r.get("hop_sequence")
        if isinstance(seq, int):
            if seq in seen:
                errors.append(f"duplicate_hop_sequence:{seq}_at_index_{i}")
            seen.add(seq)
    return errors


def _omit_optional_empty_tvr_extras(body: dict[str, Any]) -> None:
    """§8 — optional empty arrays for TVR extras may be omitted."""
    for k in ("vertices", "edges", "diagnostics"):
        if k in body and body[k] == []:
            del body[k]
    if body.get("diagnostics") == {}:
        del body["diagnostics"]


def _omit_exploration_defaults_inplace(body: dict[str, Any]) -> None:
    """§8 — omit non-exploration authority markers from canonical hash input."""
    na = body.get("non_authoritative")
    if na is False:
        body.pop("non_authoritative", None)
    ep = body.get("execution_partition")
    if ep == "authoritative":
        body.pop("execution_partition", None)


def _sort_start_node_ids_inplace(body: dict[str, Any]) -> None:
    s = body.get("start_node_ids")
    if isinstance(s, list) and all(isinstance(x, str) for x in s):
        body["start_node_ids"] = sorted(s)


def _sort_hop_receipts_by_sequence_inplace(body: dict[str, Any]) -> None:
    """**RULE WR-01** — ``hop_receipts`` sorted by ``hop_sequence``."""
    hr = body.get("hop_receipts")
    if not isinstance(hr, list) or not hr:
        return
    if not all(isinstance(x, dict) and isinstance(x.get("hop_sequence"), int) for x in hr):
        return
    body["hop_receipts"] = sorted(hr, key=lambda x: int(x["hop_sequence"]))  # type: ignore[arg-type]


def _canonicalize_json_value(obj: Any) -> Any:
    """NFC strings + recursively sorted object keys (**OCTS-CANON-1** style)."""
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, dict):
        return {str(k): _canonicalize_json_value(obj[k]) for k in sorted(obj.keys(), key=str)}
    if isinstance(obj, list):
        return [_canonicalize_json_value(x) for x in obj]
    return obj


def normalize_walk_result_hash_body_v1(body: Mapping[str, Any]) -> dict[str, Any]:
    """Apply §8 omissions where applicable, WR-01 ordering helpers, then canonicalize."""
    raw = dict(body)
    _omit_optional_empty_tvr_extras(raw)
    _omit_exploration_defaults_inplace(raw)
    _sort_start_node_ids_inplace(raw)
    _sort_hop_receipts_by_sequence_inplace(raw)
    return cast(dict[str, Any], _canonicalize_json_value(raw))


def canonical_walk_result_hash_body_bytes_v1(body: Mapping[str, Any]) -> bytes:
    """UTF-8 JSON bytes fed to SHA-256 for ``walk_result_hash`` (**REPLAY REQUIREMENT WR-01**)."""
    norm = normalize_walk_result_hash_body_v1(body)
    return json.dumps(norm, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_walk_result_hash_v1(body: Mapping[str, Any]) -> str:
    """``walk_result_hash`` = ``sha256:`` + 64 hex over canonical ``hash_body``."""
    digest = hashlib.sha256(canonical_walk_result_hash_body_bytes_v1(body)).hexdigest()
    return f"{_WALK_RESULT_HASH_PREFIX}{digest}"


def extract_walk_result_hash_body_v1(response: Mapping[str, Any]) -> dict[str, Any]:
    """Accept API-shaped ``{walk_result: {hash_body: ...}}`` or a raw ``hash_body`` object."""
    if "walk_result" not in response:
        if all(
            k in response
            for k in (
                "octs_schema_version",
                "temporal_anchor",
                "policy_hash",
                "start_node_ids",
            )
        ):
            return dict(response)
        msg = "response missing walk_result.hash_body or hash_body keys"
        raise WalkResultContractError(msg)
    wr = response["walk_result"]
    if not isinstance(wr, dict):
        msg = "walk_result must be an object"
        raise WalkResultContractError(msg)
    hb = wr.get("hash_body")
    if not isinstance(hb, dict):
        msg = "walk_result.hash_body must be an object"
        raise WalkResultContractError(msg)
    return dict(hb)


def validate_walk_result_hash_body_contract_v1(body: Mapping[str, Any]) -> None:
    """Structural + temporal + **RULE WR-02** + **FS-WR-03** + **G-P05-TVR-01**."""
    if not isinstance(body, dict):
        msg = "hash_body must be an object"
        raise WalkResultContractError(msg)

    ta = body.get("temporal_anchor")
    if isinstance(ta, dict):
        try:
            validate_temporal_anchor_invariants_v1(ta)
        except TemporalWalkInvariantError as exc:
            msg = f"temporal_anchor invalid: {exc}"
            raise WalkResultContractError(msg) from exc

    wr02 = list_wr02_forbidden_key_violations_under_hash_body(body, "")
    if wr02:
        msg = "RULE WR-02 violations: " + "; ".join(wr02[:20])
        raise WalkResultContractError(msg)

    dup = list_fs_wr03_duplicate_hop_sequence_violations(body.get("hop_receipts"))
    if dup:
        msg = "FS-WR-03: " + "; ".join(dup)
        raise WalkResultContractError(msg)

    try:
        validate_walk_diagnostics_hash_body_contract_v1(body)
    except WalkDiagnosticsContractError as exc:
        raise WalkResultContractError(str(exc)) from exc

    hrs = body.get("hop_receipts")
    if isinstance(hrs, list) and hrs:
        try:
            validate_hop_receipt_list_for_hash_body_v1(hrs)
        except HopReceiptContractError as exc:
            raise WalkResultContractError(str(exc)) from exc

    try:
        validate_exploration_hash_body_invariants_v1(body)
    except ExplorationModeContractError as exc:
        raise WalkResultContractError(str(exc)) from exc

    try:
        validate_walk_result_hash_body_tvr_strict_v1(body)
    except TraversalReasoningBoundaryError as exc:
        raise WalkResultContractError(str(exc)) from exc


def verify_gp05_hash01_walk_result_hash_recompute_static() -> dict[str, Any]:
    """**G-P05-HASH-01** — golden ``hash_body`` recomputes to expected ``walk_result_hash``."""
    errors: list[str] = []
    d = octs_walk_result_fixture_dir()
    body_path = d / "hash_body_minimal_v1.json"
    expected_path = d / "walk_result_hash_expected_v1.txt"
    if not body_path.is_file():
        errors.append(f"missing_fixture:{body_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if errors:
        return {
            "id": "G-P05-HASH-01",
            "name": "walk_result_hash_recompute",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"wr_runtime_schema_version": WR_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }

    body = json.loads(body_path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        errors.append("hash_body_minimal_v1_not_object")
    else:
        try:
            validate_walk_result_hash_body_contract_v1(body)
        except WalkResultContractError as exc:
            errors.append(f"hash_body_invalid:{exc}")
        if not errors:
            actual = compute_walk_result_hash_v1(body)
            expected = expected_path.read_text(encoding="utf-8").strip()
            if actual != expected:
                errors.append(f"hash_mismatch:actual={actual!r} expected={expected!r}")

    poison_path = d / "hash_body_nested_telemetry_bad_v1.json"
    if poison_path.is_file():
        poison = json.loads(poison_path.read_text(encoding="utf-8"))
        if isinstance(poison, dict):
            try:
                validate_walk_result_hash_body_contract_v1(poison)
            except WalkResultContractError:
                pass
            else:
                errors.append("expected_nested_telemetry_fixture_to_fail")
        else:
            errors.append("hash_body_nested_telemetry_bad_not_object")
    else:
        errors.append(f"missing_fixture:{poison_path}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-HASH-01",
        "name": "walk_result_hash_recompute",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wr_runtime_schema_version": WR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_hash02_telemetry_separation_static() -> dict[str, Any]:
    """**G-P05-HASH-02** — sibling telemetry mutations do not change ``walk_result_hash``."""
    errors: list[str] = []
    d = octs_walk_result_fixture_dir()
    bundle_path = d / "walk_response_telemetry_variants_v1.json"
    if not bundle_path.is_file():
        errors.append(f"missing_fixture:{bundle_path}")
        return {
            "id": "G-P05-HASH-02",
            "name": "walk_result_telemetry_separation",
            "passed": False,
            "severity": "hard_fail",
            "detail": {"wr_runtime_schema_version": WR_RUNTIME_SCHEMA_VERSION, "errors": errors},
        }

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        errors.append("telemetry_variants_not_object")
    else:
        a = bundle.get("variant_a")
        b = bundle.get("variant_b")
        if not isinstance(a, dict) or not isinstance(b, dict):
            errors.append("variant_a_or_b_invalid")
        else:
            try:
                hb_a = extract_walk_result_hash_body_v1(a)
                hb_b = extract_walk_result_hash_body_v1(b)
            except WalkResultContractError as exc:
                errors.append(f"extract_failed:{exc}")
            else:
                h1 = compute_walk_result_hash_v1(hb_a)
                h2 = compute_walk_result_hash_v1(hb_b)
                if h1 != h2:
                    errors.append(f"hashes_differ_on_identical_hash_body:{h1!r}!={h2!r}")
                # Telemetry must differ between variants (otherwise test is vacuous).
                ta = a.get("telemetry")
                tb = b.get("telemetry")
                if ta == tb:
                    errors.append("expected_telemetry_payloads_to_differ")

    passed = len(errors) == 0
    return {
        "id": "G-P05-HASH-02",
        "name": "walk_result_telemetry_separation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"wr_runtime_schema_version": WR_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

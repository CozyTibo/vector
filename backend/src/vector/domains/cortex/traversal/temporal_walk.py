"""Phase 05 P05-07 — temporal walk (anchor, monotonicity, half-open validity).

Normative: ``DOCS/cortex/05-traversal/phase-05-temporal-walk-doctrine.md``,
``DOCS/cortex/05-traversal/phase-05-canonicalization-profile.md`` (**OCTS-CANON-1** §TIME).

**RULE TW-02** — ``graph_as_of_unix_ns`` within ``snapshot_unix_ns`` ± ``MAX_CLOCK_SKEW_NS``.
**INVARIANT TA-01** — committed ``export_sequence`` strictly +1 per tenant (fixtures + static gate).
"""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.graph_import_boundary import (
    GraphImportBoundaryError,
    validate_temporal_anchor_has_projection_content_hash,
)

TW_RUNTIME_SCHEMA_VERSION: Final[int] = 1

MAX_CLOCK_SKEW_NS: Final[int] = 300_000_000_000

UINT64_MAX: Final[int] = 18446744073709551615

_TEMPORAL_ANCHOR_TOP_KEYS: Final[frozenset[str]] = frozenset(
    {
        "export_id",
        "export_sequence",
        "graph_as_of_unix_ns",
        "projection_content_hash",
        "snapshot_unix_ns",
        "tenant_id",
    }
)

_UUID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

# RFC 3339-like / ISO-8601 date fragments inside anchor bodies are forbidden
# (**§8**, **G-P05-TEMP-01**).
_ISOISH_SUBSTRING_RE: Final[re.Pattern[str]] = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}"
)


class TemporalWalkInvariantError(ValueError):
    """Raised when ``temporal_anchor`` or temporal laws are violated."""


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md from temporal_walk."
    )
    raise RuntimeError(msg)


def octs_temporal_fixture_dir() -> Path:
    """Directory for **G-P05-TEMP-01** / **G-P05-TEMP-02** golden JSON."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "temporal"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"temporal golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def _nfc_str(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _assert_uuid_lowercase_field(value: Any, field: str) -> str:
    if not isinstance(value, str):
        msg = f"temporal_anchor.{field} must be a string UUID"
        raise TemporalWalkInvariantError(msg)
    s = _nfc_str(value.strip().lower())
    try:
        parsed = uuid.UUID(s)
    except ValueError as exc:
        msg = f"temporal_anchor.{field} must be a UUID string"
        raise TemporalWalkInvariantError(msg) from exc
    canon = str(parsed)
    if canon != s or not _UUID_RE.match(s):
        msg = f"temporal_anchor.{field} must be lowercase canonical UUID"
        raise TemporalWalkInvariantError(msg)
    return s


def _assert_sha256_projection_hash(value: Any) -> str:
    if not isinstance(value, str):
        msg = "temporal_anchor.projection_content_hash must be a string"
        raise TemporalWalkInvariantError(msg)
    s = _nfc_str(value.strip().lower())
    if not _SHA256_RE.match(s):
        msg = "temporal_anchor.projection_content_hash must match sha256:<64 hex>"
        raise TemporalWalkInvariantError(msg)
    return s


def _assert_unix_ns_object(value: Any, field: str) -> dict[str, int]:
    if not isinstance(value, dict):
        msg = f"temporal_anchor.{field} must be an object"
        raise TemporalWalkInvariantError(msg)
    if set(value.keys()) != {"unix_ns"}:
        msg = f'temporal_anchor.{field} must be exactly {{"unix_ns": <uint>}}'
        raise TemporalWalkInvariantError(msg)
    ns = value["unix_ns"]
    if isinstance(ns, bool) or not isinstance(ns, int):
        msg = f"temporal_anchor.{field}.unix_ns must be a non-negative integer"
        raise TemporalWalkInvariantError(msg)
    if ns < 0:
        msg = f"temporal_anchor.{field}.unix_ns must be non-negative"
        raise TemporalWalkInvariantError(msg)
    if ns > UINT64_MAX:
        msg = f"temporal_anchor.{field}.unix_ns exceeds uint64"
        raise TemporalWalkInvariantError(msg)
    return {"unix_ns": ns}


def _reject_floats_recursive(obj: Any, path: str) -> None:
    if isinstance(obj, float):
        msg = f"temporal_anchor forbids floats at {path}"
        raise TemporalWalkInvariantError(msg)
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_floats_recursive(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_floats_recursive(v, f"{path}[{i}]")


def _reject_iso_strings_in_anchor(anchor: Mapping[str, Any]) -> None:
    """**§8** — no ISO-8601 strings inside anchor objects that enter walk hashes."""

    def walk(obj: Any, path: str) -> None:
        if isinstance(obj, str):
            if path.endswith("tenant_id") or path.endswith("export_id"):
                return
            if path.endswith("projection_content_hash"):
                return
            if _ISOISH_SUBSTRING_RE.search(obj):
                msg = f"temporal_anchor forbids ISO-like instant strings at {path}"
                raise TemporalWalkInvariantError(msg)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")

    walk(dict(anchor), "temporal_anchor")


def validate_temporal_anchor_invariants_v1(anchor: Mapping[str, Any]) -> None:
    """Structural checks for ``temporal_anchor`` (**§3.1**, **FS-TW-01**)."""
    if not isinstance(anchor, dict):
        msg = "temporal_anchor must be an object"
        raise TemporalWalkInvariantError(msg)
    keys = set(anchor.keys())
    if keys != _TEMPORAL_ANCHOR_TOP_KEYS:
        extra = sorted(keys - _TEMPORAL_ANCHOR_TOP_KEYS)
        missing = sorted(_TEMPORAL_ANCHOR_TOP_KEYS - keys)
        msg = f"temporal_anchor keys mismatch extra={extra!r} missing={missing!r}"
        raise TemporalWalkInvariantError(msg)

    _reject_floats_recursive(anchor, "temporal_anchor")
    _reject_iso_strings_in_anchor(anchor)

    _assert_uuid_lowercase_field(anchor["tenant_id"], "tenant_id")
    _assert_uuid_lowercase_field(anchor["export_id"], "export_id")

    seq = anchor["export_sequence"]
    if isinstance(seq, bool) or not isinstance(seq, int):
        msg = "temporal_anchor.export_sequence must be a uint64 integer"
        raise TemporalWalkInvariantError(msg)
    if seq < 0 or seq > UINT64_MAX:
        msg = "temporal_anchor.export_sequence out of uint64 range"
        raise TemporalWalkInvariantError(msg)

    _assert_sha256_projection_hash(anchor["projection_content_hash"])
    _assert_unix_ns_object(anchor["snapshot_unix_ns"], "snapshot_unix_ns")
    _assert_unix_ns_object(anchor["graph_as_of_unix_ns"], "graph_as_of_unix_ns")

    try:
        validate_temporal_anchor_has_projection_content_hash(anchor)
    except GraphImportBoundaryError as exc:
        raise TemporalWalkInvariantError(str(exc)) from exc
    validate_graph_as_of_vs_snapshot_clock_skew_v1(anchor)


def temporal_anchor_canonical_dict_v1(anchor: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical dict (sorted at dump time) after validation."""
    validate_temporal_anchor_invariants_v1(anchor)
    snap = cast(dict[str, Any], anchor["snapshot_unix_ns"])
    gas = cast(dict[str, Any], anchor["graph_as_of_unix_ns"])
    proj = _assert_sha256_projection_hash(anchor["projection_content_hash"])
    return {
        "export_id": _assert_uuid_lowercase_field(anchor["export_id"], "export_id"),
        "export_sequence": int(anchor["export_sequence"]),
        "graph_as_of_unix_ns": {"unix_ns": int(gas["unix_ns"])},
        "projection_content_hash": proj,
        "snapshot_unix_ns": {"unix_ns": int(snap["unix_ns"])},
        "tenant_id": _assert_uuid_lowercase_field(anchor["tenant_id"], "tenant_id"),
    }


def temporal_anchor_canonical_json_bytes_v1(anchor: Mapping[str, Any]) -> bytes:
    """Deterministic UTF-8 JSON for anchor identity (**REPLAY REQUIREMENT TW-01**)."""
    body = temporal_anchor_canonical_dict_v1(anchor)
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_graph_as_of_vs_snapshot_clock_skew_v1(anchor: Mapping[str, Any]) -> None:
    """**RULE TW-02** — ``graph_as_of`` within snapshot ± ``MAX_CLOCK_SKEW_NS``."""
    snap = cast(dict[str, Any], anchor["snapshot_unix_ns"])
    gas = cast(dict[str, Any], anchor["graph_as_of_unix_ns"])
    s_ns = int(snap["unix_ns"])
    g_ns = int(gas["unix_ns"])
    lo = s_ns - MAX_CLOCK_SKEW_NS
    hi = s_ns + MAX_CLOCK_SKEW_NS
    if g_ns < lo or g_ns > hi:
        msg = (
            "RULE TW-02: graph_as_of_unix_ns out of allowed skew from snapshot_unix_ns "
            f"(graph={g_ns}, snapshot={s_ns}, max_skew_ns={MAX_CLOCK_SKEW_NS})"
        )
        raise TemporalWalkInvariantError(msg)


def org_link_eligible_half_open_unix_ns_v1(
    *,
    valid_from_unix_ns: int | None,
    valid_to_unix_ns: int | None,
    graph_as_of_unix_ns: int,
    open_to_sentinel: int = UINT64_MAX,
) -> bool:
    """Half-open **[vf, vt)** on **POSIX unix_ns** (**§3.6** + multigraph §6).

    ``valid_to_unix_ns`` absent → ``open_to_sentinel`` (**UINT64_MAX** per doctrine).
    ``valid_from_unix_ns`` absent → no lower bound (always active from left).
    """
    if valid_from_unix_ns is not None and graph_as_of_unix_ns < valid_from_unix_ns:
        return False
    upper = valid_to_unix_ns if valid_to_unix_ns is not None else open_to_sentinel
    if graph_as_of_unix_ns >= upper:
        return False
    return True


def list_export_sequence_monotonicity_violations_v1(
    rows: Sequence[tuple[int, str]],
) -> list[str]:
    """**INVARIANT TA-01** / **FS-TW-SEQ** — committed sequences for one tenant.

    ``rows`` are ``(export_sequence, export_id)``; duplicates and **+1** gaps are illegal.
    """
    errors: list[str] = []
    if not rows:
        return errors
    by_seq: dict[int, list[str]] = {}
    for seq, eid in rows:
        by_seq.setdefault(seq, []).append(eid)
    for seq in sorted(by_seq):
        eids = by_seq[seq]
        if len(eids) > 1:
            errors.append(f"fs_tw_seq_duplicate_sequence:{seq}:exports={sorted(set(eids))}")
    unique_seqs = sorted(by_seq)
    for a, b in zip(unique_seqs, unique_seqs[1:]):
        if b != a + 1:
            errors.append(f"export_sequence_gap_or_jump:from_{a}_to_{b}")
    return errors


def list_superseded_link_still_present_violations_v1(
    edges: Sequence[Mapping[str, Any]],
) -> list[str]:
    """**RULE SUP-01** — superseded link row must not remain in traversable export."""
    superseded_ids: set[str] = set()
    for e in edges:
        if not isinstance(e, dict):
            continue
        sid = e.get("supersedes_link_id")
        if isinstance(sid, str) and sid.strip():
            superseded_ids.add(sid.strip())
    present = {str(e["id"]) for e in edges if isinstance(e, dict) and isinstance(e.get("id"), str)}
    errors: list[str] = []
    for sid in sorted(superseded_ids):
        if sid in present:
            errors.append(f"superseded_link_still_present:{sid}")
    return errors


def linearized_export_sequence_commits_v1(
    *,
    tail_before: int,
    commit_sequences_in_order: Sequence[int],
) -> list[str]:
    """Model **RULE CONC-01** / **TA-01**: each commit must be ``previous_tail + 1``."""
    errors: list[str] = []
    tail = tail_before
    for seq in commit_sequences_in_order:
        if seq != tail + 1:
            errors.append(f"illegal_sequence_commit:tail_was_{tail}_got_{seq}_expected_{tail + 1}")
        else:
            tail = seq
    return errors


def verify_gp05_temp01_sequence_validity_supersession_static() -> dict[str, Any]:
    """**G-P05-TEMP-01** — golden fixtures: monotonicity, half-open, supersession."""
    errors: list[str] = []
    d = octs_temporal_fixture_dir()

    def load(name: str) -> Any:
        p = d / name
        if not p.is_file():
            errors.append(f"missing_fixture:{p}")
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    good = load("export_sequence_good_v1.json")
    if isinstance(good, dict) and isinstance(good.get("rows"), list):
        rows = []
        for raw in good["rows"]:
            if isinstance(raw, list) and len(raw) == 2:
                rows.append((int(raw[0]), str(raw[1])))
        errors.extend(list_export_sequence_monotonicity_violations_v1(rows))
    elif good is not None:
        errors.append("export_sequence_good_v1_invalid_shape")

    gap = load("export_sequence_gap_v1.json")
    if isinstance(gap, dict) and isinstance(gap.get("rows"), list):
        rows_g = [
            (int(r[0]), str(r[1])) for r in gap["rows"] if isinstance(r, list) and len(r) == 2
        ]
        if list_export_sequence_monotonicity_violations_v1(rows_g) == []:
            errors.append("expected_gap_fixture_to_fail_monotonicity")
    elif gap is not None:
        errors.append("export_sequence_gap_v1_invalid_shape")

    dup = load("export_sequence_duplicate_v1.json")
    if isinstance(dup, dict) and isinstance(dup.get("rows"), list):
        rows_d = [
            (int(r[0]), str(r[1])) for r in dup["rows"] if isinstance(r, list) and len(r) == 2
        ]
        if list_export_sequence_monotonicity_violations_v1(rows_d) == []:
            errors.append("expected_duplicate_fixture_to_fail_monotonicity")
    elif dup is not None:
        errors.append("export_sequence_duplicate_v1_invalid_shape")

    hoc = load("half_open_cases_v1.json")
    if isinstance(hoc, list):
        for i, case in enumerate(hoc):
            if not isinstance(case, dict):
                continue
            vf = case.get("valid_from_unix_ns")
            vt = case.get("valid_to_unix_ns")
            t = case.get("graph_as_of_unix_ns")
            exp = case.get("eligible")
            if not isinstance(t, int) or not isinstance(exp, bool):
                errors.append(f"half_open_case_{i}_invalid")
                continue
            vf_i = int(vf) if isinstance(vf, int) else None
            vt_i = int(vt) if isinstance(vt, int) else None
            got = org_link_eligible_half_open_unix_ns_v1(
                valid_from_unix_ns=vf_i,
                valid_to_unix_ns=vt_i,
                graph_as_of_unix_ns=t,
            )
            if got != exp:
                errors.append(f"half_open_case_{i}_mismatch:got={got} expected={exp}")
    elif hoc is not None:
        errors.append("half_open_cases_v1_invalid_shape")

    sup = load("supersession_edges_bad_v1.json")
    if isinstance(sup, dict) and isinstance(sup.get("edges"), list):
        if list_superseded_link_still_present_violations_v1(sup["edges"]) == []:
            errors.append("expected_supersession_fixture_to_fail")
    elif sup is not None:
        errors.append("supersession_edges_bad_v1_invalid_shape")

    anchor = load("anchor_good_v1.json")
    if isinstance(anchor, dict):
        try:
            validate_temporal_anchor_invariants_v1(anchor)
        except TemporalWalkInvariantError as exc:
            errors.append(f"anchor_good_v1_invalid:{exc}")
    elif anchor is not None:
        errors.append("anchor_good_v1_invalid_shape")

    passed = len(errors) == 0
    return {
        "id": "G-P05-TEMP-01",
        "name": "temporal_validity_sequence_supersession",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"tw_runtime_schema_version": TW_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_temp02_anchor_roundtrip_and_concurrency_static() -> dict[str, Any]:
    """**G-P05-TEMP-02** — canonical anchor bytes round-trip; sequence commit linearization."""
    errors: list[str] = []
    d = octs_temporal_fixture_dir()
    anchor_path = d / "anchor_good_v1.json"
    expected_path = d / "anchor_good_canonical_v1.txt"
    if not anchor_path.is_file():
        errors.append(f"missing_fixture:{anchor_path}")
    if not expected_path.is_file():
        errors.append(f"missing_fixture:{expected_path}")
    if not errors:
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        if isinstance(anchor, dict):
            try:
                actual = temporal_anchor_canonical_json_bytes_v1(anchor)
            except TemporalWalkInvariantError as exc:
                errors.append(f"anchor_canonical_failed:{exc}")
            else:
                expected = expected_path.read_bytes().rstrip(b"\n\r")
                if actual != expected:
                    errors.append(
                        f"anchor_canonical_bytes_mismatch:actual={actual!r} expected={expected!r}"
                    )
        else:
            errors.append("anchor_good_v1_not_object")

    dup_commits = linearized_export_sequence_commits_v1(
        tail_before=3, commit_sequences_in_order=[4, 4]
    )
    if not dup_commits:
        errors.append("expected_double_commit_same_sequence_to_fail")

    ok_commits = linearized_export_sequence_commits_v1(
        tail_before=3, commit_sequences_in_order=[4, 5]
    )
    if ok_commits:
        errors.append(f"linearizer_should_accept_4_5:errors={ok_commits}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-TEMP-02",
        "name": "anchor_roundtrip_export_sequence_linearizer",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"tw_runtime_schema_version": TW_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

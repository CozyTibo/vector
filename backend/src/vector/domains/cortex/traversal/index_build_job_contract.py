"""Phase 05 P05-14 — index build job FSM (**G-P05-JOB-01**, **G-P05-JOB-02**).

Normative: ``DOCS/cortex/05-traversal/phase-05-index-build-job-doctrine.md``.
Receipt hashes: ``derived_index_contract.assert_index_content_hash_string_v1``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

from vector.domains.cortex.traversal.derived_index_contract import (
    assert_index_content_hash_string_v1,
)

IBJ_RUNTIME_SCHEMA_VERSION: Final[int] = 1

INDEX_BUILD_JOB_STATE_QUEUED: Final[str] = "QUEUED"
INDEX_BUILD_JOB_STATE_BUILDING: Final[str] = "BUILDING"
INDEX_BUILD_JOB_STATE_VALIDATING: Final[str] = "VALIDATING"
INDEX_BUILD_JOB_STATE_PUBLISHING: Final[str] = "PUBLISHING"
INDEX_BUILD_JOB_STATE_COMMITTED: Final[str] = "COMMITTED"
INDEX_BUILD_JOB_STATE_FAILED: Final[str] = "FAILED"

INDEX_BUILD_JOB_STATES_V1: Final[frozenset[str]] = frozenset(
    {
        INDEX_BUILD_JOB_STATE_QUEUED,
        INDEX_BUILD_JOB_STATE_BUILDING,
        INDEX_BUILD_JOB_STATE_VALIDATING,
        INDEX_BUILD_JOB_STATE_PUBLISHING,
        INDEX_BUILD_JOB_STATE_COMMITTED,
        INDEX_BUILD_JOB_STATE_FAILED,
    }
)

_UUID_RE: Final[re.Pattern[str]] = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

_ALLOWED_TRANSITIONS_V1: Final[dict[str, frozenset[str]]] = {
    INDEX_BUILD_JOB_STATE_QUEUED: frozenset(
        {INDEX_BUILD_JOB_STATE_BUILDING, INDEX_BUILD_JOB_STATE_FAILED}
    ),
    INDEX_BUILD_JOB_STATE_BUILDING: frozenset(
        {INDEX_BUILD_JOB_STATE_VALIDATING, INDEX_BUILD_JOB_STATE_FAILED}
    ),
    INDEX_BUILD_JOB_STATE_VALIDATING: frozenset(
        {INDEX_BUILD_JOB_STATE_PUBLISHING, INDEX_BUILD_JOB_STATE_FAILED}
    ),
    INDEX_BUILD_JOB_STATE_PUBLISHING: frozenset(
        {INDEX_BUILD_JOB_STATE_COMMITTED, INDEX_BUILD_JOB_STATE_FAILED}
    ),
    INDEX_BUILD_JOB_STATE_COMMITTED: frozenset(),
    INDEX_BUILD_JOB_STATE_FAILED: frozenset(),
}


class IndexBuildJobContractError(ValueError):
    """Raised when index build job FSM / receipts / leases violate doctrine."""


def _repo_root_with_octs_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "05-traversal" / "phase-05-normative-index.md"
        if marker.is_file():
            return root
    msg = (
        "Could not locate DOCS/cortex/05-traversal/phase-05-normative-index.md "
        "from index_build_job_contract."
    )
    raise RuntimeError(msg)


def octs_index_build_job_fixture_dir() -> Path:
    """Golden vectors for **G-P05-JOB-01** / **G-P05-JOB-02**."""
    root = _repo_root_with_octs_docs()
    rel = (
        Path("vector")
        / "domains"
        / "cortex"
        / "traversal"
        / "octs_golden_vectors"
        / "v1"
        / "index_build_job"
    )
    flat = root / "tests" / rel
    nested = root / "backend" / "tests" / rel
    if flat.is_dir():
        return flat
    if nested.is_dir():
        return nested
    msg = f"index_build_job golden dir missing: tried {flat} and {nested}"
    raise RuntimeError(msg)


def validate_index_build_job_state_transition_v1(from_state: str, to_state: str) -> None:
    """Single-step FSM edge check (doctrine §3)."""
    if from_state not in INDEX_BUILD_JOB_STATES_V1:
        msg = f"unknown from_state: {from_state!r}"
        raise IndexBuildJobContractError(msg)
    if to_state not in INDEX_BUILD_JOB_STATES_V1:
        msg = f"unknown to_state: {to_state!r}"
        raise IndexBuildJobContractError(msg)
    allowed = _ALLOWED_TRANSITIONS_V1.get(from_state, frozenset())
    if to_state not in allowed:
        msg = f"illegal index build job transition: {from_state!r} -> {to_state!r}"
        raise IndexBuildJobContractError(msg)


def validate_index_build_job_state_sequence_v1(states: Sequence[str]) -> None:
    """Validate a linear audit trail of ``to_state`` values (inclusive chain)."""
    if not states:
        msg = "state sequence must be non-empty"
        raise IndexBuildJobContractError(msg)
    for i in range(len(states) - 1):
        validate_index_build_job_state_transition_v1(states[i], states[i + 1])


def compute_index_build_idempotency_key_v1(
    *,
    tenant_id: str,
    projection_content_hash: str,
    derivation_rule_id: str,
    target_schema_version: int,
) -> str:
    """**RULE IBJ-02** — deterministic idempotency key over pinned rebuild inputs."""
    if not isinstance(tenant_id, str) or not _UUID_RE.fullmatch(tenant_id.strip().lower()):
        msg = "tenant_id must be lowercase canonical UUID string"
        raise IndexBuildJobContractError(msg)
    tid = tenant_id.strip().lower()
    assert_index_content_hash_string_v1(projection_content_hash, field_name="projection_content_hash")
    if not isinstance(derivation_rule_id, str) or not derivation_rule_id.strip():
        msg = "derivation_rule_id must be a non-empty string"
        raise IndexBuildJobContractError(msg)
    dr = derivation_rule_id.strip()
    if isinstance(target_schema_version, bool) or not isinstance(target_schema_version, int):
        msg = "target_schema_version must be int (not bool)"
        raise IndexBuildJobContractError(msg)
    if target_schema_version < 0:
        msg = "target_schema_version must be non-negative"
        raise IndexBuildJobContractError(msg)
    payload = json.dumps(
        [tid, projection_content_hash, dr, int(target_schema_version)],
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def validate_index_build_job_receipt_v1(receipt: Mapping[str, Any]) -> None:
    """§7 — receipt lists ``input_projection_hash``, ``output_index_hash``, ``index_epoch``."""
    if not isinstance(receipt, dict):
        msg = "receipt must be an object"
        raise IndexBuildJobContractError(msg)
    for k in ("input_projection_hash", "output_index_hash", "index_epoch"):
        if k not in receipt:
            msg = f"job receipt missing required field: {k}"
            raise IndexBuildJobContractError(msg)
    assert_index_content_hash_string_v1(
        receipt["input_projection_hash"],
        field_name="input_projection_hash",
    )
    assert_index_content_hash_string_v1(
        receipt["output_index_hash"],
        field_name="output_index_hash",
    )
    ep = receipt["index_epoch"]
    if isinstance(ep, bool) or not isinstance(ep, int) or ep < 0:
        msg = "index_epoch must be a non-negative int (not bool)"
        raise IndexBuildJobContractError(msg)


def list_rule_ibj01_simultaneous_building_lease_violations(
    lease_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """**RULE IBJ-01** — at most one ``BUILDING`` row per ``index_partition_key``."""
    building_by_key: dict[str, int] = {}
    errors: list[str] = []
    for i, row in enumerate(lease_rows):
        if not isinstance(row, dict):
            errors.append(f"lease[{i}]:not_object")
            continue
        key = row.get("index_partition_key")
        st = row.get("job_state")
        if not isinstance(key, str) or not key.strip():
            errors.append(f"lease[{i}]:bad_index_partition_key")
            continue
        if st == INDEX_BUILD_JOB_STATE_BUILDING:
            building_by_key[key] = building_by_key.get(key, 0) + 1
    for key, count in sorted(building_by_key.items()):
        if count > 1:
            errors.append(f"RULE-IBJ-01:multiple_BUILDING_for_partition:{key}:count={count}")
    return errors


def list_fs_ibj02_duplicate_committed_epoch_different_hash_violations(
    committed_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """**FS-IBJ-02** — same ``index_epoch`` must not commit two different ``output_index_hash``."""
    by_epoch: dict[int, str] = {}
    errors: list[str] = []
    for i, row in enumerate(committed_rows):
        if not isinstance(row, dict):
            errors.append(f"row[{i}]:not_object")
            continue
        if row.get("job_state") != INDEX_BUILD_JOB_STATE_COMMITTED:
            continue
        ep = row.get("index_epoch")
        oh = row.get("output_index_hash")
        if isinstance(ep, bool) or not isinstance(ep, int) or ep < 0:
            errors.append(f"row[{i}]:bad_index_epoch")
            continue
        if not isinstance(oh, str):
            errors.append(f"row[{i}]:bad_output_index_hash")
            continue
        prev = by_epoch.get(ep)
        if prev is None:
            by_epoch[ep] = oh
        elif prev != oh:
            errors.append(
                f"FS-IBJ-02:epoch_{ep}_hash_mismatch:first={prev!r} second={oh!r}_at_row_{i}"
            )
    return errors


def validate_fs_ibj03_shadow_store_visibility_v1(record: Mapping[str, Any]) -> None:
    """**FS-IBJ-03** — shadow prefix must not serve as live without ``BUILDING`` lease gate."""
    if record.get("shadow_served_as_live_without_building_lease") is True:
        lease = record.get("active_partition_lease_job_state")
        if lease != INDEX_BUILD_JOB_STATE_BUILDING:
            msg = (
                "FS-IBJ-03: shadow bytes may not be readable as live without an active "
                "BUILDING lease on the partition"
            )
            raise IndexBuildJobContractError(msg)


def _event_to_state(ev: Mapping[str, Any]) -> str:
    if "to_state" in ev:
        raw = ev.get("to_state")
    else:
        raw = ev.get("state")
    if not isinstance(raw, str):
        msg = "event missing to_state/state string"
        raise IndexBuildJobContractError(msg)
    return raw


def validate_index_build_completion_events_v1(events: Sequence[Mapping[str, Any]]) -> None:
    """Ordered job events: legal FSM + **FS-IBJ-01** validating success before publish/commit."""
    if not isinstance(events, list) or not events:
        msg = "events must be a non-empty array"
        raise IndexBuildJobContractError(msg)
    states: list[str] = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            msg = f"events[{i}] must be an object"
            raise IndexBuildJobContractError(msg)
        states.append(_event_to_state(cast(Mapping[str, Any], ev)))
    validate_index_build_job_state_sequence_v1(states)

    if states[-1] == INDEX_BUILD_JOB_STATE_COMMITTED:
        try:
            pub_idx = states.index(INDEX_BUILD_JOB_STATE_PUBLISHING)
        except ValueError as exc:
            msg = "FS-IBJ-01: COMMITTED requires a PUBLISHING state in history"
            raise IndexBuildJobContractError(msg) from exc
        ok = False
        for i, st in enumerate(states):
            if i >= pub_idx:
                break
            if st == INDEX_BUILD_JOB_STATE_VALIDATING:
                ev = events[i]
                if ev.get("validation_passed") is True:
                    ok = True
                    break
        if not ok:
            msg = "FS-IBJ-01: COMMITTED requires VALIDATING success before PUBLISHING"
            raise IndexBuildJobContractError(msg)


def verify_gp05_job01_index_build_fsm_illegal_transitions_static() -> dict[str, Any]:
    """**G-P05-JOB-01** — illegal FSM edges are rejected; legal edges pass."""
    errors: list[str] = []
    for from_s in sorted(INDEX_BUILD_JOB_STATES_V1):
        for to_s in sorted(INDEX_BUILD_JOB_STATES_V1):
            allowed = to_s in _ALLOWED_TRANSITIONS_V1.get(from_s, frozenset())
            try:
                validate_index_build_job_state_transition_v1(from_s, to_s)
            except IndexBuildJobContractError:
                if allowed:
                    errors.append(f"unexpected_reject_legal:{from_s}->{to_s}")
            else:
                if not allowed:
                    errors.append(f"expected_reject_illegal:{from_s}->{to_s}")
    passed = len(errors) == 0
    return {
        "id": "G-P05-JOB-01",
        "name": "index_build_job_fsm_illegal_transitions",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ibj_runtime_schema_version": IBJ_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }


def verify_gp05_job02_validating_publish_audit_static() -> dict[str, Any]:
    """**G-P05-JOB-02** — crash / skip semantics: bad audit fails; good audit passes."""
    errors: list[str] = []
    d = octs_index_build_job_fixture_dir()
    bad_path = d / "audit_trail_bad_skip_validating_v1.json"
    good_path = d / "audit_trail_good_committed_v1.json"
    if not bad_path.is_file():
        errors.append(f"missing_fixture:{bad_path}")
    if not good_path.is_file():
        errors.append(f"missing_fixture:{good_path}")
    if errors:
        return _job02_result(errors)

    bad_raw = json.loads(bad_path.read_text(encoding="utf-8"))
    bad_events = bad_raw.get("events") if isinstance(bad_raw, dict) else None
    if not isinstance(bad_events, list):
        errors.append("bad_fixture.events_invalid")
    else:
        try:
            validate_index_build_completion_events_v1(
                cast(list[Mapping[str, Any]], bad_events),
            )
        except IndexBuildJobContractError:
            pass
        else:
            errors.append("expected_bad_audit_trail_to_fail")

    good_raw = json.loads(good_path.read_text(encoding="utf-8"))
    good_events = good_raw.get("events") if isinstance(good_raw, dict) else None
    if not isinstance(good_events, list):
        errors.append("good_fixture.events_invalid")
    else:
        try:
            validate_index_build_completion_events_v1(
                cast(list[Mapping[str, Any]], good_events),
            )
        except IndexBuildJobContractError as exc:
            errors.append(f"unexpected_good_rejection:{exc}")

    return _job02_result(errors)


def _job02_result(errors: list[str]) -> dict[str, Any]:
    passed = len(errors) == 0
    return {
        "id": "G-P05-JOB-02",
        "name": "index_build_job_validating_publish_audit",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"ibj_runtime_schema_version": IBJ_RUNTIME_SCHEMA_VERSION, "errors": errors},
    }

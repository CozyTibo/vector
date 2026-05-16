"""Phase 06 P06-06 — chronology legality (projection + CHRON‑FORB‑1).

Normative:
``DOCS/cortex/reasoning/chronology-legality-law.md``,
``DOCS/cortex/reasoning/chronology-replay-legality-state-machine.md``,
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``chronology_skew_projection_v1``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

PHASE06_CHRONOLOGY_LEGALITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

CHRONOLOGY_LEGALITY_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "chronology_strict",
        "chronology_partial",
        "chronology_unresolved",
        "chronology_degraded",
    }
)

REPLAY_SAFE_ORDERING_CHRONOLOGY: Final[frozenset[str]] = frozenset({"strict", "partial", "unresolved"})

TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST: Final[str] = (
    "d48f77eb363cc2828b7af5351365d3e96dc5e1b4464c5fa1b6a5d6c56590f470"
)


class ChronologyLegalityError(ValueError):
    """Fail-closed chronology projection / CHRON‑FORB‑1 violation."""


def _bool_norm(value: object) -> bool:
    return bool(value)


def _canonical_row_sort_key(m: Mapping[str, Any]) -> tuple[int, int, int, int]:
    order = ("strict", "partial", "unresolved")
    r = m.get("replay_safe_ordering")
    ri = order.index(r) if r in order else 99
    return (
        ri,
        1 if _bool_norm(m.get("skew_detected")) else 0,
        1 if _bool_norm(m.get("late_arrival")) else 0,
        1 if _bool_norm(m.get("export_sequence_conflict")) else 0,
    )


def _row_identity(m: Mapping[str, Any]) -> tuple[str, bool, bool, bool]:
    return (
        str(m.get("replay_safe_ordering")),
        _bool_norm(m.get("skew_detected")),
        _bool_norm(m.get("late_arrival")),
        _bool_norm(m.get("export_sequence_conflict")),
    )


def find_chronology_skew_projection_row(
    rows: Sequence[Mapping[str, Any]],
    *,
    replay_safe_ordering: str,
    skew_detected: bool,
    late_arrival: bool,
    export_sequence_conflict: bool,
    partitioned_exception: bool | None = None,
) -> Mapping[str, Any] | None:
    """§2.1 / §2.2 — find the unique policy row matching the snapshot booleans.

    Primary lookup (``partitioned_exception is None``) ignores rows tagged
    ``partitioned_exception: true`` so a base row and an override row can share
    the same boolean key.
    """
    want = (replay_safe_ordering, skew_detected, late_arrival, export_sequence_conflict)
    matches: list[Mapping[str, Any]] = []
    for m in rows:
        is_partition_row = _bool_norm(m.get("partitioned_exception"))
        if partitioned_exception is True:
            if not is_partition_row:
                continue
        else:
            if is_partition_row:
                continue
        got = _row_identity(m)
        if got == want:
            matches.append(m)
    if len(matches) > 1:
        raise ChronologyLegalityError("multiple chronology_skew_projection_v1 rows matched the same snapshot key")
    return matches[0] if matches else None


def chronology_projection_matched_row_canonical_index(
    rows: Sequence[Mapping[str, Any]],
    matched: Mapping[str, Any],
) -> int:
    """§2.1 step 6 — index of ``matched`` in canonical sort order of ``rows``."""
    want_fp = _row_identity(matched)
    canonical = sorted(rows, key=_canonical_row_sort_key)
    for i, row in enumerate(canonical):
        if _row_identity(row) == want_fp:
            return i
    raise ChronologyLegalityError("matched row not found in chronology_skew_projection_v1 table")


def validate_chron_forb1(
    replay_safe_ordering: str,
    chronology_legality_class: str,
    *,
    skew_detected: bool,
    partitioned_exception_applied: bool,
) -> None:
    """§3 CHRON‑FORB‑1 — hard constraints on published ``(R, C)``."""
    r, c = replay_safe_ordering, chronology_legality_class
    if (r, c) == ("strict", "chronology_unresolved"):
        if not partitioned_exception_applied:
            raise ChronologyLegalityError("CHRON-FORB-1: (strict, chronology_unresolved) forbidden without §2.2")
    if (r, c) == ("unresolved", "chronology_strict"):
        raise ChronologyLegalityError("CHRON-FORB-1: (unresolved, chronology_strict) forbidden")
    if (r, c) == ("partial", "chronology_strict"):
        raise ChronologyLegalityError("CHRON-FORB-1: (partial, chronology_strict) forbidden")
    if (r, c) == ("strict", "chronology_degraded"):
        if not skew_detected and not partitioned_exception_applied:
            raise ChronologyLegalityError(
                "CHRON-FORB-1: (strict, chronology_degraded) forbidden without skew_detected or §2.2"
            )


def project_chronology_legality_class_v1(
    snapshot: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> tuple[str, int, bool]:
    """§2.1–§2.2 — return ``(C, matched_row_canonical_index, partitioned_exception_applied)``."""
    rows_obj = policy.get("chronology_skew_projection_v1")
    if not isinstance(rows_obj, list):
        raise ChronologyLegalityError("policy.chronology_skew_projection_v1 must be a list")
    rows: list[Mapping[str, Any]] = [m for m in rows_obj if isinstance(m, Mapping)]

    r = snapshot.get("replay_safe_ordering")
    if not isinstance(r, str) or r not in REPLAY_SAFE_ORDERING_CHRONOLOGY:
        raise ChronologyLegalityError(f"invalid replay_safe_ordering: {r!r}")
    skew = _bool_norm(snapshot.get("skew_detected"))
    late = _bool_norm(snapshot.get("late_arrival"))
    export = _bool_norm(snapshot.get("export_sequence_conflict"))

    m = find_chronology_skew_projection_row(
        rows,
        replay_safe_ordering=r,
        skew_detected=skew,
        late_arrival=late,
        export_sequence_conflict=export,
    )
    if m is None:
        raise ChronologyLegalityError("no chronology_skew_projection_v1 row matched snapshot (fail closed)")

    c = m.get("chronology_legality_class")
    if not isinstance(c, str) or c not in CHRONOLOGY_LEGALITY_CLASSES:
        raise ChronologyLegalityError(f"invalid chronology_legality_class from policy row: {c!r}")

    partitioned_applied = False
    matched_for_index: Mapping[str, Any] = m
    classes = snapshot.get("active_conflict_classes")
    if isinstance(classes, list) and "partitioned" in classes:
        m_exc = find_chronology_skew_projection_row(
            rows,
            replay_safe_ordering=r,
            skew_detected=skew,
            late_arrival=late,
            export_sequence_conflict=export,
            partitioned_exception=True,
        )
        if m_exc is not None:
            c2 = m_exc.get("chronology_legality_class")
            if isinstance(c2, str) and c2 in CHRONOLOGY_LEGALITY_CLASSES:
                c = c2
                partitioned_applied = True
                matched_for_index = m_exc

    validate_chron_forb1(r, c, skew_detected=skew, partitioned_exception_applied=partitioned_applied)
    idx = chronology_projection_matched_row_canonical_index(rows, matched_for_index)
    return c, idx, partitioned_applied


def should_emit_cd_chron_from_policy(
    *,
    chronology_legality_class: str,
    policy: Mapping[str, Any],
) -> bool:
    """``chronology-legality-law.md`` §2 + default ``degradation_thresholds`` flag when present."""
    thresholds = policy.get("degradation_thresholds")
    if not isinstance(thresholds, Mapping):
        return False
    if thresholds.get("emit_cd_chron_on_any_chronology_non_strict") is True:
        return chronology_legality_class != "chronology_strict"
    return False


def default_reasoning_policy_pack_path(start: Path | None = None) -> Path:
    """Resolve ``ReasoningPolicyPackV1_Default.json`` from a checkout root."""
    root_start = start or Path(__file__).resolve()
    for root in [root_start, *root_start.parents]:
        candidate = (
            root / "DOCS" / "cortex" / "reasoning" / "fixtures" / "ReasoningPolicyPackV1_Default.json"
        )
        if candidate.is_file():
            return candidate
    raise ChronologyLegalityError(
        "Could not locate DOCS/cortex/reasoning/fixtures/ReasoningPolicyPackV1_Default.json"
    )


def load_default_reasoning_policy_pack(*, start: Path | None = None) -> dict[str, Any]:
    """Parse the canonical default policy pack JSON (doctrine fixture)."""
    path = default_reasoning_policy_pack_path(start)
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def verify_default_policy_pack_digest(*, start: Path | None = None) -> None:
    """Optional integrity check — must match ``TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST``."""
    import hashlib

    path = default_reasoning_policy_pack_path(start)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST:
        raise ChronologyLegalityError(
            f"default policy pack digest mismatch: got {digest}, expected "
            f"{TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST}"
        )


def verify_gp06_chron01_default_policy_rows_static(*, start: Path | None = None) -> dict[str, Any]:
    """Static: default fixture has 24 projection rows + digest law."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack(start=start)
        rows = pack.get("chronology_skew_projection_v1")
        if not isinstance(rows, list) or len(rows) != 24:
            errors.append(f"expected_24_chronology_rows_got_{type(rows).__name__}:{len(rows) if isinstance(rows, list) else 'n/a'}")
        verify_default_policy_pack_digest(start=start)
    except ChronologyLegalityError as exc:
        errors.append(str(exc))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"load_error:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-06-chron-default-pack",
        "name": "default_chronology_skew_projection_v1",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_chronology_legality_runtime_schema_version": (
                PHASE06_CHRONOLOGY_LEGALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_chron02_projection_closure_static(*, start: Path | None = None) -> dict[str, Any]:
    """Static: every boolean key projects and satisfies CHRON‑FORB‑1 on default pack."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack(start=start)
        for r in ("strict", "partial", "unresolved"):
            for skew in (False, True):
                for late in (False, True):
                    for export in (False, True):
                        snap: dict[str, Any] = {
                            "replay_safe_ordering": r,
                            "skew_detected": skew,
                            "late_arrival": late,
                            "export_sequence_conflict": export,
                            "active_conflict_classes": [],
                        }
                        try:
                            project_chronology_legality_class_v1(snap, pack)
                        except ChronologyLegalityError as exc:
                            errors.append(f"projection_failed:{r},{skew},{late},{export}:{exc}")
    except ChronologyLegalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-06-chron-forb-closure",
        "name": "chronology_projection_chron_forb1_default_pack",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_chronology_legality_runtime_schema_version": (
                PHASE06_CHRONOLOGY_LEGALITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors[:24],
        },
    }

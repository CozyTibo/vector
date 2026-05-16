"""Phase 06 P06-27 — causal drift proofs (breakpoint ids + drift receipt linkage).

Normative:
``DOCS/cortex/reasoning/causal-breakpoint-detection-spec.md`` §§5–6,
``DOCS/cortex/reasoning/causal-degradation-spec.md`` (``CD‑*`` receipts),
``deterministic-causal-chain-spec.md`` (policy digest shape).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    ChronologyDegradationPropagationError,
    normalize_degradation_corpus_token_v1,
)
from vector.domains.cortex.reasoning.deterministic_causal_chain import (
    DeterministicCausalChainError,
    validate_tcre_policy_bundle_digest_shape_v1,
)

PHASE06_CAUSAL_DRIFT_PROOFS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

CAUSAL_BREAKPOINT_DETECTION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/causal-breakpoint-detection-spec.md §5"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")


class CausalDriftProofsError(ValueError):
    """Fail-closed drift receipt ↔ breakpoint index linkage + ``breakpoint_id`` law."""


def _require_sha256(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CausalDriftProofsError(f"{label} must be a non-empty string")
    s = value.strip()
    if s != s.lower():
        raise CausalDriftProofsError(f"{label} must be lowercase hex sha256")
    if not _SHA256_HEX_RE.match(s):
        raise CausalDriftProofsError(f"{label} must be 64-char lowercase hex sha256")
    return s


def _canonical_json_sha256_hex(body: Mapping[str, Any]) -> str:
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_breakpoint_id_body_v1(
    *,
    rule_id: str,
    at_vertex_id: str,
    frontier_snapshot_digest_pre: str,
    frontier_snapshot_digest_post: str,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any]:
    """``causal-breakpoint-detection-spec`` §5 — canonical JSON body for ``breakpoint_id``."""
    if not isinstance(rule_id, str) or not rule_id.strip():
        raise CausalDriftProofsError("rule_id must be a non-empty string")
    if not isinstance(at_vertex_id, str) or not at_vertex_id.strip():
        raise CausalDriftProofsError("at_vertex_id must be a non-empty string")
    try:
        validate_tcre_policy_bundle_digest_shape_v1(tcre_policy_bundle_digest)
    except DeterministicCausalChainError as exc:
        raise CausalDriftProofsError(str(exc)) from exc
    pre = _require_sha256("frontier_snapshot_digest_pre", frontier_snapshot_digest_pre)
    post = _require_sha256("frontier_snapshot_digest_post", frontier_snapshot_digest_post)
    bundle = tcre_policy_bundle_digest.strip()
    return {
        "at_vertex_id": at_vertex_id.strip(),
        "frontier_snapshot_digest_post": post,
        "frontier_snapshot_digest_pre": pre,
        "rule_id": rule_id.strip(),
        "tcre_policy_bundle_digest": bundle,
    }


def hash_breakpoint_id_v1(
    *,
    rule_id: str,
    at_vertex_id: str,
    frontier_snapshot_digest_pre: str,
    frontier_snapshot_digest_post: str,
    tcre_policy_bundle_digest: str,
) -> str:
    """§5 — ``breakpoint_id`` = **sha256** hex over canonical JSON of the frozen body."""
    body = canonical_breakpoint_id_body_v1(
        rule_id=rule_id,
        at_vertex_id=at_vertex_id,
        frontier_snapshot_digest_pre=frontier_snapshot_digest_pre,
        frontier_snapshot_digest_post=frontier_snapshot_digest_post,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
    )
    return _canonical_json_sha256_hex(body)


def _breakpoint_index_sort_key(row: Mapping[str, Any]) -> tuple[str, str, str]:
    o = row.get("observed_at_iso")
    v = row.get("at_vertex_id")
    r = row.get("rule_id")
    if not isinstance(o, str) or not o.strip():
        raise CausalDriftProofsError("breakpoint_index row requires non-empty observed_at_iso")
    if not isinstance(v, str) or not v.strip():
        raise CausalDriftProofsError("breakpoint_index row requires non-empty at_vertex_id")
    if not isinstance(r, str) or not r.strip():
        raise CausalDriftProofsError("breakpoint_index row requires non-empty rule_id")
    return (o.strip(), v.strip(), r.strip())


def sort_breakpoint_index_rows_v1(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """§5 ``breakpoint_index`` — sort by ``(observed_at_iso, at_vertex_id, rule_id)``."""
    parsed: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise CausalDriftProofsError(f"breakpoint_index[{i}] must be a mapping")
        row = dict(raw)
        bid = row.get("breakpoint_id")
        if not isinstance(bid, str) or not bid.strip():
            raise CausalDriftProofsError(f"breakpoint_index[{i}].breakpoint_id must be non-empty")
        _require_sha256(f"breakpoint_index[{i}].breakpoint_id", bid)
        row["breakpoint_id"] = bid.strip()
        _breakpoint_index_sort_key(row)
        parsed.append(row)
    return sorted(parsed, key=_breakpoint_index_sort_key)


def validate_breakpoint_index_sorted_v1(rows: Sequence[Mapping[str, Any]]) -> None:
    """Reject if ``rows`` violate §5 ``(observed_at_iso, at_vertex_id, rule_id)`` order."""
    if not rows:
        raise CausalDriftProofsError("breakpoint_index_rows must be non-empty")
    keys: list[tuple[str, str, str]] = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise CausalDriftProofsError(f"breakpoint_index[{i}] must be a mapping")
        keys.append(_breakpoint_index_sort_key(raw))
    if keys != sorted(keys):
        raise CausalDriftProofsError("breakpoint_index must be sorted per §5 tuple order")


def validate_drift_degradation_receipt_links_breakpoints_v1(
    *,
    cd_codes_sorted: Sequence[str],
    breakpoint_rule_ids_sorted: Sequence[str],
    breakpoint_index_rows: Sequence[Mapping[str, Any]],
) -> None:
    """Link drift evidence to breakpoints (sorted CD codes + rule id coverage)."""
    if not isinstance(cd_codes_sorted, list) or not cd_codes_sorted:
        raise CausalDriftProofsError("cd_codes_sorted must be a non-empty list")
    canon_cd: list[str] = []
    for i, c in enumerate(cd_codes_sorted):
        if not isinstance(c, str) or not c.strip():
            raise CausalDriftProofsError(f"cd_codes_sorted[{i}] must be a non-empty string")
        try:
            canon_cd.append(normalize_degradation_corpus_token_v1(c.strip()))
        except ChronologyDegradationPropagationError as exc:
            raise CausalDriftProofsError(str(exc)) from exc
    if canon_cd != sorted(set(canon_cd)):
        raise CausalDriftProofsError("cd_codes_sorted must be sorted unique canonical CD-* codes")

    if not isinstance(breakpoint_rule_ids_sorted, list):
        raise CausalDriftProofsError("breakpoint_rule_ids_sorted must be a list")
    rules = [str(x).strip() for x in breakpoint_rule_ids_sorted if isinstance(x, str) and x.strip()]
    if rules != sorted(set(rules)):
        raise CausalDriftProofsError("breakpoint_rule_ids_sorted must be sorted unique strings")

    if not breakpoint_index_rows:
        raise CausalDriftProofsError("breakpoint_index_rows must be non-empty for linkage proof")
    validate_breakpoint_index_sorted_v1(breakpoint_index_rows)
    index_rules = {str(r.get("rule_id", "")).strip() for r in breakpoint_index_rows}
    index_rules.discard("")
    allowed = set(rules)
    missing = sorted(index_rules - allowed)
    if missing:
        raise CausalDriftProofsError(
            "drift receipt breakpoint_rule_ids_sorted must cover every rule_id in "
            f"breakpoint_index; missing: {missing!r}"
        )


def _cdp_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_causal_drift_proofs_runtime_schema_version": (
            PHASE06_CAUSAL_DRIFT_PROOFS_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_cdp01_breakpoint_id_body_key_oracle_static() -> dict[str, Any]:
    """P06-27 — §5 canonical body keys are the frozen five fields."""
    errors: list[str] = []
    d = "a" * 64
    try:
        body = canonical_breakpoint_id_body_v1(
            rule_id="r1",
            at_vertex_id="v1",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest=d,
        )
        want = {
            "at_vertex_id",
            "frontier_snapshot_digest_post",
            "frontier_snapshot_digest_pre",
            "rule_id",
            "tcre_policy_bundle_digest",
        }
        if frozenset(body.keys()) != want:
            errors.append("breakpoint_id_body_key_mismatch")
    except CausalDriftProofsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-27-cdp-breakpoint-body",
        "name": "gp06_cdp01_breakpoint_id_body_key_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _cdp_detail(errors),
    }


def verify_gp06_cdp02_breakpoint_index_sort_stable_static() -> dict[str, Any]:
    """P06-27 — §5 index sort is permutation-invariant for the same rows."""
    errors: list[str] = []
    d = "b" * 64
    try:
        r1 = {
            "breakpoint_id": hash_breakpoint_id_v1(
                rule_id="rule-a",
                at_vertex_id="v1",
                frontier_snapshot_digest_pre=d,
                frontier_snapshot_digest_post=d,
                tcre_policy_bundle_digest=d,
            ),
            "rule_id": "rule-a",
            "at_vertex_id": "v1",
            "observed_at_iso": "2020-01-01T00:00:00Z",
        }
        r2 = {
            "breakpoint_id": hash_breakpoint_id_v1(
                rule_id="rule-b",
                at_vertex_id="v2",
                frontier_snapshot_digest_pre=d,
                frontier_snapshot_digest_post=d,
                tcre_policy_bundle_digest=d,
            ),
            "rule_id": "rule-b",
            "at_vertex_id": "v2",
            "observed_at_iso": "2020-01-02T00:00:00Z",
        }
        s1 = sort_breakpoint_index_rows_v1([r1, r2])
        s2 = sort_breakpoint_index_rows_v1([r2, r1])
        if s1 != s2:
            errors.append("breakpoint_index_sort_unstable")
    except CausalDriftProofsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-27-cdp-index-sort",
        "name": "gp06_cdp02_breakpoint_index_sort_stable",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _cdp_detail(errors),
    }


def verify_gp06_cdp03_drift_receipt_requires_sorted_cd_static() -> dict[str, Any]:
    """P06-27 — drift linkage rejects unsorted ``cd_codes_sorted``."""
    errors: list[str] = []
    from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON, CD_CONT

    d = "c" * 64
    idx = [
        {
            "breakpoint_id": hash_breakpoint_id_v1(
                rule_id="r-x",
                at_vertex_id="vx",
                frontier_snapshot_digest_pre=d,
                frontier_snapshot_digest_post=d,
                tcre_policy_bundle_digest=d,
            ),
            "rule_id": "r-x",
            "at_vertex_id": "vx",
            "observed_at_iso": "2020-01-01T00:00:00Z",
        }
    ]
    try:
        validate_drift_degradation_receipt_links_breakpoints_v1(
            cd_codes_sorted=[CD_CONT, CD_CHRON],
            breakpoint_rule_ids_sorted=["r-x"],
            breakpoint_index_rows=idx,
        )
    except CausalDriftProofsError:
        pass
    else:
        errors.append("expected_reject_unsorted_cd_codes")
    passed = len(errors) == 0
    return {
        "id": "P06-27-cdp-drift-cd-sort",
        "name": "gp06_cdp03_drift_receipt_requires_sorted_cd",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _cdp_detail(errors),
    }


def verify_gp06_cdp04_breakpoint_id_roundtrip_static() -> dict[str, Any]:
    """P06-27 — same body ⇒ identical ``breakpoint_id``."""
    errors: list[str] = []
    d = "d" * 64
    try:
        h1 = hash_breakpoint_id_v1(
            rule_id="r",
            at_vertex_id="v",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest=d,
        )
        h2 = hash_breakpoint_id_v1(
            rule_id="r",
            at_vertex_id="v",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest=d,
        )
        if h1 != h2:
            errors.append("breakpoint_id_not_stable")
    except CausalDriftProofsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-27-cdp-breakpoint-id-roundtrip",
        "name": "gp06_cdp04_breakpoint_id_roundtrip",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _cdp_detail(errors),
    }


def verify_gp06_cdp05_policy_digest_shape_enforced_static() -> dict[str, Any]:
    """P06-27 — ``tcre_policy_bundle_digest`` participates with registry shape."""
    errors: list[str] = []
    d = "e" * 64
    try:
        hash_breakpoint_id_v1(
            rule_id="r",
            at_vertex_id="v",
            frontier_snapshot_digest_pre=d,
            frontier_snapshot_digest_post=d,
            tcre_policy_bundle_digest="NOT_HEX",
        )
    except CausalDriftProofsError:
        pass
    else:
        errors.append("expected_reject_bad_policy_digest")
    passed = len(errors) == 0
    return {
        "id": "P06-27-cdp-policy-digest",
        "name": "gp06_cdp05_policy_digest_shape_enforced",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _cdp_detail(errors),
    }

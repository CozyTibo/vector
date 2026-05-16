"""Phase 06 P06-26 — temporal / causal replay proofs (**``G‑P06‑REPLAY‑01``**).

Normative:
``DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md`` §§2–3,
``DOCS/cortex/reasoning/replay-aware-reasoning-law.md`` §1 (pinned tuple),
``replay_chronology`` (``reasoning_replay_permutation_v1`` profile id).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.reasoning.replay_chronology import (
    REASONING_REPLAY_PERMUTATION_PROFILE_ID,
)

PHASE06_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP06_REPLAY_01_GATE_ID_V1: Final[str] = "G-P06-REPLAY-01"

REPLAY_EQUIVALENCE_SPEC_SECTION_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md §2"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")


class ReplayEquivalenceProofsError(ValueError):
    """Fail-closed **``G‑P06‑REPLAY‑01``** digest bundle / double-run comparison."""


def _require_sha256(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReplayEquivalenceProofsError(f"{label} must be a non-empty string")
    s = value.strip()
    if s != s.lower():
        raise ReplayEquivalenceProofsError(f"{label} must be lowercase hex sha256")
    if not _SHA256_HEX_RE.match(s):
        raise ReplayEquivalenceProofsError(f"{label} must be 64-char lowercase hex sha256")
    return s


def _parse_bool(value: object, *, field: str) -> bool:
    if value is True:
        return True
    if value is False:
        return False
    raise ReplayEquivalenceProofsError(f"{field} must be bool True or False")


def _validate_sorted_unique_chain_ids(ids: object) -> list[str]:
    if not isinstance(ids, list) or not ids:
        raise ReplayEquivalenceProofsError("causal_chain_ids_sorted must be a non-empty list")
    out: list[str] = []
    for i, x in enumerate(ids):
        if not isinstance(x, str) or not x.strip():
            raise ReplayEquivalenceProofsError(
                f"causal_chain_ids_sorted[{i}] must be a non-empty string"
            )
        out.append(x.strip())
    if out != sorted(set(out)):
        raise ReplayEquivalenceProofsError(
            "causal_chain_ids_sorted must be strictly sorted unique strings"
        )
    return out


def validate_gp06_replay_01_equivalence_claim_scope_v1(
    *,
    causal_chain_id_only_assertion: bool,
    chronology_participates: bool,
    ambiguity_active: bool,
) -> None:
    """§2 — causal-only claims are insufficient when chronology/ambiguity receipts apply."""
    if not causal_chain_id_only_assertion:
        return
    if chronology_participates or ambiguity_active:
        raise ReplayEquivalenceProofsError(
            f"{GP06_REPLAY_01_GATE_ID_V1}: causal_chain_id-only assertion is insufficient when "
            "chronology participates or ambiguity receipts are active (§2 law)"
        )


def normalize_gp06_replay_01_comparison_vector_v1(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """§2 — build the byte-stable digest vector compared across golden twin runs."""
    if not isinstance(bundle, Mapping):
        raise ReplayEquivalenceProofsError("bundle must be a mapping")
    chain_ids = _validate_sorted_unique_chain_ids(bundle.get("causal_chain_ids_sorted"))
    chronology_participates = _parse_bool(
        bundle.get("chronology_participates"),
        field="chronology_participates",
    )
    ambiguity_active = _parse_bool(bundle.get("ambiguity_active"), field="ambiguity_active")
    walk_consumed = _parse_bool(bundle.get("walk_consumed"), field="walk_consumed")
    validate_gp06_replay_01_equivalence_claim_scope_v1(
        causal_chain_id_only_assertion=bool(bundle.get("causal_chain_id_only_assertion")),
        chronology_participates=chronology_participates,
        ambiguity_active=ambiguity_active,
    )
    equiv = _require_sha256(
        "reasoning_equivalence_receipt_digest",
        bundle.get("reasoning_equivalence_receipt_digest"),
    )
    out: dict[str, Any] = {
        "causal_chain_ids_sorted": chain_ids,
        "reasoning_equivalence_receipt_digest": equiv,
    }
    if chronology_participates:
        out["reasoning_chronology_receipt_digest"] = _require_sha256(
            "reasoning_chronology_receipt_digest",
            bundle.get("reasoning_chronology_receipt_digest"),
        )
    if ambiguity_active:
        out["reasoning_ambiguity_receipt_digest"] = _require_sha256(
            "reasoning_ambiguity_receipt_digest",
            bundle.get("reasoning_ambiguity_receipt_digest"),
        )
    if walk_consumed:
        out["reasoning_replay_receipt_digest"] = _require_sha256(
            "reasoning_replay_receipt_digest",
            bundle.get("reasoning_replay_receipt_digest"),
        )
    return out


def compare_gp06_replay_01_double_run_v1(
    bundle_a: Mapping[str, Any],
    bundle_b: Mapping[str, Any],
) -> None:
    """``G‑P06‑REPLAY‑01`` — require identical normalized comparison vectors."""
    va = normalize_gp06_replay_01_comparison_vector_v1(bundle_a)
    vb = normalize_gp06_replay_01_comparison_vector_v1(bundle_b)
    if va != vb:
        raise ReplayEquivalenceProofsError(
            f"{GP06_REPLAY_01_GATE_ID_V1}: double-run digest vector mismatch: "
            f"{json.dumps(va, sort_keys=True)} != {json.dumps(vb, sort_keys=True)}"
        )


def _req_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_replay_equivalence_proofs_runtime_schema_version": (
            PHASE06_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_req01_replay_01_gate_id_oracle_static() -> dict[str, Any]:
    """P06-26 — **``G‑P06‑REPLAY‑01``** gate id literal."""
    errors: list[str] = []
    if GP06_REPLAY_01_GATE_ID_V1 != "G-P06-REPLAY-01":
        errors.append("gate_id_mismatch")
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-gate-id",
        "name": "gp06_req01_replay_01_gate_id_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }


def verify_gp06_req02_permutation_profile_id_literal_static() -> dict[str, Any]:
    """P06-26 — ``reasoning_replay_permutation_v1`` profile id frozen (§3)."""
    errors: list[str] = []
    if REASONING_REPLAY_PERMUTATION_PROFILE_ID != "reasoning_replay_permutation_v1":
        errors.append("permutation_profile_id_mismatch")
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-permutation-profile",
        "name": "gp06_req02_permutation_profile_id_literal",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }


def _minimal_bundle_v1(
    *,
    chronology_digest: str | None,
    ambiguity_digest: str | None,
    replay_digest: str | None,
) -> dict[str, Any]:
    d = "a" * 64
    b: dict[str, Any] = {
        "causal_chain_ids_sorted": ["chain-1"],
        "chronology_participates": chronology_digest is not None,
        "ambiguity_active": ambiguity_digest is not None,
        "walk_consumed": replay_digest is not None,
        "reasoning_equivalence_receipt_digest": d,
        "causal_chain_id_only_assertion": False,
    }
    if chronology_digest is not None:
        b["reasoning_chronology_receipt_digest"] = chronology_digest
    if ambiguity_digest is not None:
        b["reasoning_ambiguity_receipt_digest"] = ambiguity_digest
    if replay_digest is not None:
        b["reasoning_replay_receipt_digest"] = replay_digest
    return b


def verify_gp06_req03_minimal_bundle_double_run_match_static() -> dict[str, Any]:
    """P06-26 — identical bundles normalize equal under **``G‑P06‑REPLAY‑01``**."""
    errors: list[str] = []
    try:
        c = "b" * 64
        a = b = _minimal_bundle_v1(
            chronology_digest=c,
            ambiguity_digest=None,
            replay_digest=None,
        )
        compare_gp06_replay_01_double_run_v1(a, b)
    except ReplayEquivalenceProofsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-double-run-match",
        "name": "gp06_req03_minimal_bundle_double_run_match",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }


def verify_gp06_req04_chronology_digest_required_when_participates_static() -> dict[str, Any]:
    """P06-26 — chronology digest required when ``chronology_participates``."""
    errors: list[str] = []
    bad = _minimal_bundle_v1(chronology_digest=None, ambiguity_digest=None, replay_digest=None)
    bad["chronology_participates"] = True
    try:
        normalize_gp06_replay_01_comparison_vector_v1(bad)
    except ReplayEquivalenceProofsError:
        pass
    else:
        errors.append("expected_missing_chronology_digest")
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-chronology-required",
        "name": "gp06_req04_chronology_digest_required_when_participates",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }


def verify_gp06_req05_double_run_mismatch_raises_static() -> dict[str, Any]:
    """P06-26 — differing chronology digest fails closed."""
    errors: list[str] = []
    c1 = "c" * 64
    c2 = "d" * 64
    a = _minimal_bundle_v1(chronology_digest=c1, ambiguity_digest=None, replay_digest=None)
    b = _minimal_bundle_v1(chronology_digest=c2, ambiguity_digest=None, replay_digest=None)
    try:
        compare_gp06_replay_01_double_run_v1(a, b)
    except ReplayEquivalenceProofsError:
        pass
    else:
        errors.append("expected_mismatch_raises")
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-mismatch",
        "name": "gp06_req05_double_run_mismatch_raises",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }


def verify_gp06_req06_causal_only_insufficient_when_receipts_static() -> dict[str, Any]:
    """P06-26 — §2 law rejects causal-only assertion when chronology/ambiguity active."""
    errors: list[str] = []
    try:
        validate_gp06_replay_01_equivalence_claim_scope_v1(
            causal_chain_id_only_assertion=True,
            chronology_participates=True,
            ambiguity_active=False,
        )
    except ReplayEquivalenceProofsError:
        pass
    else:
        errors.append("expected_reject_causal_only_with_chronology")
    try:
        validate_gp06_replay_01_equivalence_claim_scope_v1(
            causal_chain_id_only_assertion=True,
            chronology_participates=False,
            ambiguity_active=True,
        )
    except ReplayEquivalenceProofsError:
        pass
    else:
        errors.append("expected_reject_causal_only_with_ambiguity")
    passed = len(errors) == 0
    return {
        "id": "P06-26-req-causal-only-law",
        "name": "gp06_req06_causal_only_insufficient_when_receipts",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _req_detail(errors),
    }

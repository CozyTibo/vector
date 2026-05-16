"""Phase 06 P06-28 — proof bundle composition (inner digest + equivalence receipt set).

Normative:
``DOCS/cortex/reasoning/reasoning-receipts-and-proof-artifacts.md`` §§1–2,
``DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md`` §2 (frozen digest scope),
``reasoning_receipts_proof_artifacts`` (``REASONING_CANON_VERSION_V1``, canonical JSON **sha256**).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    REASONING_AMBIGUITY_RECEIPT_TYPE,
    REASONING_CANON_VERSION_V1,
    REASONING_CAUSAL_RECEIPT_TYPE,
    REASONING_CHRONOLOGY_RECEIPT_TYPE,
    REASONING_EQUIVALENCE_RECEIPT_TYPE,
    REASONING_REPLAY_RECEIPT_TYPE,
    hash_reasoning_canonical_json_sha256_v1,
    validate_reasoning_receipt_type_literal_v1,
)

PHASE06_PROOF_BUNDLE_COMPOSITION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PROOF_BUNDLE_COMPOSITION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-receipts-and-proof-artifacts.md §2; "
    "DOCS/cortex/reasoning/replay-equivalence-reasoning-spec.md §2"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")


class ProofBundleCompositionError(ValueError):
    """Fail-closed inner proof bundle digest + equivalence receipt set law."""


def _require_sha256(label: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProofBundleCompositionError(f"{label} must be a non-empty string")
    s = value.strip()
    if s != s.lower():
        raise ProofBundleCompositionError(f"{label} must be lowercase hex sha256")
    if not _SHA256_HEX_RE.match(s):
        raise ProofBundleCompositionError(f"{label} must be 64-char lowercase hex sha256")
    return s


def build_proof_bundle_inner_digest_body_v1(
    *,
    receipt_type_digest_pairs: Sequence[tuple[str, str]],
    reasoning_canon_version_v1: int | None = None,
) -> dict[str, Any]:
    """§2 inner body — sorted ``(receipt_type, digest)`` rows + ``REASONING_CANON_VERSION_V1``."""
    if not isinstance(receipt_type_digest_pairs, (list, tuple)) or not receipt_type_digest_pairs:
        raise ProofBundleCompositionError("receipt_type_digest_pairs must be a non-empty sequence")
    if reasoning_canon_version_v1 is None:
        v = REASONING_CANON_VERSION_V1
    else:
        v = int(reasoning_canon_version_v1)
    if v < 1:
        raise ProofBundleCompositionError("reasoning_canon_version_v1 must be >= 1")
    rows: list[dict[str, str]] = []
    for i, pair in enumerate(receipt_type_digest_pairs):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ProofBundleCompositionError(
                f"receipt_type_digest_pairs[{i}] must be a (type, digest) tuple"
            )
        rt, dig = pair
        if not isinstance(rt, str) or not rt.strip():
            raise ProofBundleCompositionError(
                f"receipt_type_digest_pairs[{i}][0] must be non-empty str"
            )
        try:
            validate_reasoning_receipt_type_literal_v1(rt.strip())
        except Exception as exc:
            raise ProofBundleCompositionError(str(exc)) from exc
        rows.append({"digest": _require_sha256(f"digest[{i}]", dig), "receipt_type": rt.strip()})
    rows.sort(key=lambda r: (r["receipt_type"], r["digest"]))
    return {
        "reasoning_canon_version_v1": v,
        "receipt_pairs_sorted": rows,
    }


def hash_proof_bundle_inner_digest_v1(
    *,
    receipt_type_digest_pairs: Sequence[tuple[str, str]],
    reasoning_canon_version_v1: int | None = None,
) -> str:
    """``reasoning-receipts-and-proof-artifacts`` §2 — **sha256** over canonical inner JSON."""
    body = build_proof_bundle_inner_digest_body_v1(
        receipt_type_digest_pairs=receipt_type_digest_pairs,
        reasoning_canon_version_v1=reasoning_canon_version_v1,
    )
    return hash_reasoning_canonical_json_sha256_v1(body)


def validate_proof_bundle_equivalence_receipt_set_v1(
    *,
    receipt_type_digest_pairs: Sequence[tuple[str, str]],
    chronology_participates: bool,
    ambiguity_active: bool,
    walk_consumed: bool,
) -> None:
    """§2 — required receipt kinds for the given participation flags (replay-equivalence spec)."""
    if chronology_participates not in (True, False):
        raise ProofBundleCompositionError("chronology_participates must be bool")
    if ambiguity_active not in (True, False):
        raise ProofBundleCompositionError("ambiguity_active must be bool")
    if walk_consumed not in (True, False):
        raise ProofBundleCompositionError("walk_consumed must be bool")
    types = {
        str(rt).strip()
        for rt, _ in receipt_type_digest_pairs
        if isinstance(rt, str) and rt.strip()
    }
    required: set[str] = {
        REASONING_EQUIVALENCE_RECEIPT_TYPE,
        REASONING_CAUSAL_RECEIPT_TYPE,
    }
    if chronology_participates:
        required.add(REASONING_CHRONOLOGY_RECEIPT_TYPE)
    if ambiguity_active:
        required.add(REASONING_AMBIGUITY_RECEIPT_TYPE)
    if walk_consumed:
        required.add(REASONING_REPLAY_RECEIPT_TYPE)
    missing = sorted(required - types)
    if missing:
        raise ProofBundleCompositionError(
            f"proof bundle missing required receipt types for §2 scope: {missing!r}"
        )


def _pbc_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_proof_bundle_composition_runtime_schema_version": (
            PHASE06_PROOF_BUNDLE_COMPOSITION_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_pbc01_inner_body_sorted_pairs_oracle_static() -> dict[str, Any]:
    """P06-28 — inner body sorts receipt pairs lexicographically."""
    errors: list[str] = []
    d = "a" * 64
    try:
        body = build_proof_bundle_inner_digest_body_v1(
            receipt_type_digest_pairs=[
                (REASONING_CAUSAL_RECEIPT_TYPE, d),
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
            ],
        )
        pairs = body["receipt_pairs_sorted"]
        if pairs[0]["receipt_type"] != REASONING_CAUSAL_RECEIPT_TYPE:
            errors.append("sort_order_causal_first")
    except ProofBundleCompositionError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-28-pbc-inner-sort",
        "name": "gp06_pbc01_inner_body_sorted_pairs_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _pbc_detail(errors),
    }


def verify_gp06_pbc02_equivalence_receipt_always_required_static() -> dict[str, Any]:
    """P06-28 — §2 always requires ``reasoning_equivalence_receipt`` in the set."""
    errors: list[str] = []
    d = "b" * 64
    try:
        validate_proof_bundle_equivalence_receipt_set_v1(
            receipt_type_digest_pairs=[(REASONING_CAUSAL_RECEIPT_TYPE, d)],
            chronology_participates=False,
            ambiguity_active=False,
            walk_consumed=False,
        )
    except ProofBundleCompositionError:
        pass
    else:
        errors.append("expected_missing_equivalence_receipt")
    passed = len(errors) == 0
    return {
        "id": "P06-28-pbc-equiv-required",
        "name": "gp06_pbc02_equivalence_receipt_always_required",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _pbc_detail(errors),
    }


def verify_gp06_pbc03_chronology_required_when_participates_static() -> dict[str, Any]:
    """P06-28 — §2 chronology digest required when reducer participates."""
    errors: list[str] = []
    d = "c" * 64
    try:
        validate_proof_bundle_equivalence_receipt_set_v1(
            receipt_type_digest_pairs=[
                (REASONING_CAUSAL_RECEIPT_TYPE, d),
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
            ],
            chronology_participates=True,
            ambiguity_active=False,
            walk_consumed=False,
        )
    except ProofBundleCompositionError:
        pass
    else:
        errors.append("expected_missing_chronology_receipt")
    passed = len(errors) == 0
    return {
        "id": "P06-28-pbc-chronology-required",
        "name": "gp06_pbc03_chronology_required_when_participates",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _pbc_detail(errors),
    }


def verify_gp06_pbc04_inner_hash_permutation_invariant_static() -> dict[str, Any]:
    """P06-28 — §2 canonical JSON inner digest ignores pair insertion order."""
    errors: list[str] = []
    d = "d" * 64
    try:
        h1 = hash_proof_bundle_inner_digest_v1(
            receipt_type_digest_pairs=[
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
                (REASONING_CAUSAL_RECEIPT_TYPE, d),
            ],
        )
        h2 = hash_proof_bundle_inner_digest_v1(
            receipt_type_digest_pairs=[
                (REASONING_CAUSAL_RECEIPT_TYPE, d),
                (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
            ],
        )
        if h1 != h2:
            errors.append("inner_digest_not_permutation_invariant")
    except ProofBundleCompositionError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-28-pbc-inner-hash",
        "name": "gp06_pbc04_inner_hash_permutation_invariant",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _pbc_detail(errors),
    }


def verify_gp06_pbc05_full_minimal_bundle_validates_static() -> dict[str, Any]:
    """P06-28 — minimal §2-complete set (no optional chronology/ambiguity/replay) validates."""
    errors: list[str] = []
    d = "e" * 64
    try:
        pairs = [
            (REASONING_CAUSAL_RECEIPT_TYPE, d),
            (REASONING_EQUIVALENCE_RECEIPT_TYPE, d),
        ]
        validate_proof_bundle_equivalence_receipt_set_v1(
            receipt_type_digest_pairs=pairs,
            chronology_participates=False,
            ambiguity_active=False,
            walk_consumed=False,
        )
        h = hash_proof_bundle_inner_digest_v1(receipt_type_digest_pairs=pairs)
        if len(h) != 64:
            errors.append("bad_hash_len")
    except ProofBundleCompositionError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-28-pbc-minimal-valid",
        "name": "gp06_pbc05_full_minimal_bundle_validates",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _pbc_detail(errors),
    }

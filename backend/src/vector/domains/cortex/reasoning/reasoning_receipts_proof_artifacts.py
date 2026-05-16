"""Phase 06 P06-25 — reasoning receipts + proof artifacts (types + canonical hashing).

Normative: ``DOCS/cortex/reasoning/reasoning-receipts-and-proof-artifacts.md`` §§1–2;
``temporal_anchor_resolution`` (``hash_reasoning_receipt_canonical_v1``);
``interval_continuity`` / ``replay_chronology`` (existing receipt types).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
    CausalAmbiguityPropagationError,
    validate_ambiguity_class_id_causal_registry_v1,
)
from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    ChronologyDegradationPropagationError,
    normalize_degradation_corpus_token_v1,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    ExecutionCausalityConstraintError,
    validate_causal_legality_class,
)
from vector.domains.cortex.reasoning.interval_continuity import REASONING_CHRONOLOGY_RECEIPT_TYPE
from vector.domains.cortex.reasoning.replay_chronology import REASONING_REPLAY_RECEIPT_TYPE
from vector.domains.cortex.reasoning.temporal_anchor_resolution import (
    REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE,
    hash_reasoning_receipt_canonical_v1,
)

PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# ``reasoning-receipts-and-proof-artifacts.md`` §2 — canonical JSON digest policy version tag.
REASONING_CANON_VERSION_V1: Final[int] = 1

REASONING_CAUSAL_RECEIPT_TYPE: Final[str] = "reasoning_causal_receipt"
REASONING_AMBIGUITY_RECEIPT_TYPE: Final[str] = "reasoning_ambiguity_receipt"
REASONING_EQUIVALENCE_RECEIPT_TYPE: Final[str] = "reasoning_equivalence_receipt"

REASONING_RECEIPT_TYPES_V1: Final[frozenset[str]] = frozenset(
    {
        REASONING_CHRONOLOGY_RECEIPT_TYPE,
        REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE,
        REASONING_CAUSAL_RECEIPT_TYPE,
        REASONING_REPLAY_RECEIPT_TYPE,
        REASONING_AMBIGUITY_RECEIPT_TYPE,
        REASONING_EQUIVALENCE_RECEIPT_TYPE,
    }
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[a-f0-9]{64}$")

__all__ = [
    "REASONING_AMBIGUITY_RECEIPT_TYPE",
    "REASONING_CANON_VERSION_V1",
    "REASONING_CAUSAL_RECEIPT_TYPE",
    "REASONING_CHRONOLOGY_RECEIPT_TYPE",
    "REASONING_EQUIVALENCE_RECEIPT_TYPE",
    "REASONING_RECEIPT_TYPES_V1",
    "REASONING_REPLAY_RECEIPT_TYPE",
    "ReasoningReceiptsProofArtifactsError",
    "hash_reasoning_canonical_json_sha256_v1",
    "validate_reasoning_receipt_type_literal_v1",
]


class ReasoningReceiptsProofArtifactsError(ValueError):
    """Fail-closed reasoning receipt catalog / body / digest rules."""


def hash_reasoning_canonical_json_sha256_v1(body: Mapping[str, Any]) -> str:
    """§2 — sorted-keys JSON UTF-8 ``sha256`` hex (delegates to shared receipt hasher)."""
    return hash_reasoning_receipt_canonical_v1(body)


def validate_reasoning_receipt_type_literal_v1(value: object) -> None:
    """§1 — ``receipt_type`` must be one of the six normative receipt kinds."""
    if not isinstance(value, str) or not value.strip():
        raise ReasoningReceiptsProofArtifactsError("receipt_type must be a non-empty string")
    s = value.strip()
    if s not in REASONING_RECEIPT_TYPES_V1:
        allowed = ", ".join(sorted(REASONING_RECEIPT_TYPES_V1))
        raise ReasoningReceiptsProofArtifactsError(
            f"receipt_type must be one of: {allowed}; got {s!r}"
        )


def _require_sha256_digest(label: str, digest: object) -> str:
    if not isinstance(digest, str) or not digest.strip():
        raise ReasoningReceiptsProofArtifactsError(f"{label} must be a non-empty string")
    s = digest.strip()
    if s != s.lower():
        raise ReasoningReceiptsProofArtifactsError(f"{label} must be lowercase hex sha256")
    if not _SHA256_HEX_RE.match(s):
        raise ReasoningReceiptsProofArtifactsError(f"{label} must be 64-char lowercase hex sha256")
    return s


def _normalize_sorted_unique_cd_codes(codes: Sequence[str]) -> list[str]:
    out: list[str] = []
    for i, c in enumerate(codes):
        if not isinstance(c, str) or not c.strip():
            raise ReasoningReceiptsProofArtifactsError(
                f"sorted_cd_codes[{i}] must be a non-empty string"
            )
        try:
            out.append(normalize_degradation_corpus_token_v1(c.strip()))
        except ChronologyDegradationPropagationError as exc:
            raise ReasoningReceiptsProofArtifactsError(str(exc)) from exc
    canon = sorted(set(out))
    if canon != out:
        raise ReasoningReceiptsProofArtifactsError(
            "sorted_cd_codes must be strictly sorted unique canonical CD-* literals"
        )
    return canon


def _validate_sorted_unique_edge_ids(ids: Sequence[str]) -> list[str]:
    out: list[str] = []
    for i, e in enumerate(ids):
        if not isinstance(e, str) or not e.strip():
            raise ReasoningReceiptsProofArtifactsError(
                f"sorted_tcre_causal_edge_ids[{i}] must be a non-empty string"
            )
        out.append(e.strip())
    if out != sorted(set(out)):
        raise ReasoningReceiptsProofArtifactsError(
            "sorted_tcre_causal_edge_ids must be strictly sorted unique strings"
        )
    return out


def reasoning_causal_receipt_body_v1(
    *,
    sorted_tcre_causal_edge_ids: Sequence[str],
    sorted_cd_codes: Sequence[str],
    causal_legality_class: str,
) -> dict[str, Any]:
    """§1 ``reasoning_causal_receipt`` — hash input sketch (caller hashes body via §2)."""
    ids = _validate_sorted_unique_edge_ids(sorted_tcre_causal_edge_ids)
    cds = _normalize_sorted_unique_cd_codes(sorted_cd_codes)
    if not isinstance(causal_legality_class, str) or not causal_legality_class.strip():
        raise ReasoningReceiptsProofArtifactsError(
            "causal_legality_class must be a non-empty string"
        )
    try:
        validate_causal_legality_class(causal_legality_class.strip())
    except ExecutionCausalityConstraintError as exc:
        raise ReasoningReceiptsProofArtifactsError(str(exc)) from exc
    return {
        "receipt_type": REASONING_CAUSAL_RECEIPT_TYPE,
        "phase06_reasoning_receipts_proof_artifacts_runtime_schema_version": (
            PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION
        ),
        "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
        "sorted_tcre_causal_edge_ids": ids,
        "sorted_cd_codes": cds,
        "causal_legality_class": causal_legality_class.strip(),
    }


def reasoning_ambiguity_receipt_body_v1(
    *,
    ambiguity_class_id: str,
    blocked_derivation_rules_hash: str,
) -> dict[str, Any]:
    """§1 ``reasoning_ambiguity_receipt`` — sorted ``AMB‑*`` + blocked rules digest."""
    if not isinstance(ambiguity_class_id, str) or not ambiguity_class_id.strip():
        raise ReasoningReceiptsProofArtifactsError("ambiguity_class_id must be a non-empty string")
    try:
        validate_ambiguity_class_id_causal_registry_v1(ambiguity_class_id.strip())
    except CausalAmbiguityPropagationError as exc:
        raise ReasoningReceiptsProofArtifactsError(str(exc)) from exc
    h = _require_sha256_digest("blocked_derivation_rules_hash", blocked_derivation_rules_hash)
    return {
        "receipt_type": REASONING_AMBIGUITY_RECEIPT_TYPE,
        "phase06_reasoning_receipts_proof_artifacts_runtime_schema_version": (
            PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION
        ),
        "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
        "ambiguity_class_id_sorted_singleton": [ambiguity_class_id.strip()],
        "blocked_derivation_rules_hash": h,
    }


def reasoning_equivalence_receipt_body_v1(
    *,
    double_run_digest_a: str,
    double_run_digest_b: str,
) -> dict[str, Any]:
    """§1 ``reasoning_equivalence_receipt`` — double-run digest pair (``replay-equivalence``)."""
    da = _require_sha256_digest("double_run_digest_a", double_run_digest_a)
    db = _require_sha256_digest("double_run_digest_b", double_run_digest_b)
    return {
        "receipt_type": REASONING_EQUIVALENCE_RECEIPT_TYPE,
        "phase06_reasoning_receipts_proof_artifacts_runtime_schema_version": (
            PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION
        ),
        "reasoning_canon_version_v1": REASONING_CANON_VERSION_V1,
        "double_run_digest_a": da,
        "double_run_digest_b": db,
    }


def _rra_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_reasoning_receipts_proof_artifacts_runtime_schema_version": (
            PHASE06_REASONING_RECEIPTS_PROOF_ARTIFACTS_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_rra01_receipt_type_catalog_oracle_static() -> dict[str, Any]:
    """P06-25 — §1 six receipt kinds + cross-module literal alignment."""
    errors: list[str] = []
    expected = frozenset(
        {
            "reasoning_chronology_receipt",
            "reasoning_temporal_anchor_resolution_receipt",
            "reasoning_causal_receipt",
            "reasoning_replay_receipt",
            "reasoning_ambiguity_receipt",
            "reasoning_equivalence_receipt",
        }
    )
    if REASONING_RECEIPT_TYPES_V1 != expected:
        errors.append("receipt_type_catalog_mismatch")
    if len(REASONING_RECEIPT_TYPES_V1) != 6:
        errors.append("expected_six_receipt_types")
    if REASONING_CHRONOLOGY_RECEIPT_TYPE != "reasoning_chronology_receipt":
        errors.append("chronology_receipt_type_drift")
    tar = REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE
    if tar != "reasoning_temporal_anchor_resolution_receipt":
        errors.append("temporal_anchor_receipt_type_drift")
    if REASONING_REPLAY_RECEIPT_TYPE != "reasoning_replay_receipt":
        errors.append("replay_receipt_type_drift")
    passed = len(errors) == 0
    return {
        "id": "P06-25-rra-catalog",
        "name": "gp06_rra01_receipt_type_catalog_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rra_detail(errors),
    }


def verify_gp06_rra02_canonical_hash_stable_under_key_order_static() -> dict[str, Any]:
    """P06-25 — §2 canonical JSON ignores mapping insertion order."""
    errors: list[str] = []
    a = {"z": 1, "a": 2, "m": {"nested": True}}
    b = {"a": 2, "m": {"nested": True}, "z": 1}
    h1 = hash_reasoning_canonical_json_sha256_v1(a)
    h2 = hash_reasoning_canonical_json_sha256_v1(b)
    if h1 != h2:
        errors.append("hash_key_order_instability")
    passed = len(errors) == 0
    return {
        "id": "P06-25-rra-hash",
        "name": "gp06_rra02_canonical_hash_stable_under_key_order",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rra_detail(errors),
    }


def verify_gp06_rra03_causal_receipt_sorted_ids_enforced_static() -> dict[str, Any]:
    """P06-25 — causal receipt rejects unsorted edge ids."""
    errors: list[str] = []
    try:
        reasoning_causal_receipt_body_v1(
            sorted_tcre_causal_edge_ids=["b", "a"],
            sorted_cd_codes=[],
            causal_legality_class="causal_replay_equivalent",
        )
    except ReasoningReceiptsProofArtifactsError:
        pass
    else:
        errors.append("expected_reject_unsorted_edge_ids")
    passed = len(errors) == 0
    return {
        "id": "P06-25-rra-causal-sort",
        "name": "gp06_rra03_causal_receipt_sorted_ids_enforced",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rra_detail(errors),
    }


def verify_gp06_rra04_ambiguity_receipt_happy_path_static() -> dict[str, Any]:
    """P06-25 — ambiguity receipt builds + hashes."""
    errors: list[str] = []
    digest = "a" * 64
    try:
        from vector.domains.cortex.reasoning.organizational_continuity_reasoning import AMB_NONE

        body = reasoning_ambiguity_receipt_body_v1(
            ambiguity_class_id=AMB_NONE,
            blocked_derivation_rules_hash=digest,
        )
        h = hash_reasoning_canonical_json_sha256_v1(body)
        if len(h) != 64:
            errors.append("hash_len")
    except ReasoningReceiptsProofArtifactsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-25-rra-ambiguity",
        "name": "gp06_rra04_ambiguity_receipt_happy_path",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rra_detail(errors),
    }


def verify_gp06_rra05_equivalence_receipt_happy_path_static() -> dict[str, Any]:
    """P06-25 — equivalence receipt builds + hashes."""
    errors: list[str] = []
    da = "b" * 64
    db = "c" * 64
    try:
        body = reasoning_equivalence_receipt_body_v1(
            double_run_digest_a=da,
            double_run_digest_b=db,
        )
        h = hash_reasoning_canonical_json_sha256_v1(body)
        if len(h) != 64:
            errors.append("hash_len")
    except ReasoningReceiptsProofArtifactsError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-25-rra-equivalence",
        "name": "gp06_rra05_equivalence_receipt_happy_path",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rra_detail(errors),
    }

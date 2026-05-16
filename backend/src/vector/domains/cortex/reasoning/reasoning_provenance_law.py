"""Phase 06 P06-24 — reasoning provenance law (mandatory artifact envelope).

Normative: ``DOCS/cortex/reasoning/reasoning-provenance-law.md`` §§1–2;
``golden-thread-replay-corpus-spec.md`` §5 (replay posture literals);
``causal-degradation-spec.md`` (``CD‑*`` + coarse tag);
``execution-causality-constraints.md`` §4; ``chronology-replay-legality-state-machine.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import (
    DeterministicConfidenceSource,
)
from vector.domains.cortex.reasoning.causal_ambiguity_propagation import (
    CausalAmbiguityPropagationError,
    validate_ambiguity_class_id_causal_registry_v1,
)
from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    ChronologyDegradationPropagationError,
    degradation_coarse_tag_v1,
    normalize_degradation_corpus_token_v1,
)
from vector.domains.cortex.reasoning.chronology_legality import CHRONOLOGY_LEGALITY_CLASSES
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    ExecutionCausalityConstraintError,
    validate_causal_legality_class,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    OrganizationalContinuityReasoningError,
    validate_evidence_lineage_has_raw_or_ledger_hop,
)
from vector.domains.cortex.reasoning.unverifiable_degraded_causality import (
    UnverifiableDegradedCausalityError,
    validate_unverifiable_causality_requires_cd_codes_v1,
)

PHASE06_REASONING_PROVENANCE_LAW_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_PROVENANCE_LAW_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/reasoning/reasoning-provenance-law.md §1"
)

# ``golden-thread-replay-corpus-spec.md`` §5 — align ``replay_posture`` on Phase **06** artifacts.
REASONING_REPLAY_POSTURE_LITERALS_V1: Final[frozenset[str]] = frozenset(
    {
        "replay_equivalent",
        "replay_degraded",
        "replay_partial",
        "replay_unverifiable",
        "replay_conflicted",
    }
)

_DETERMINISTIC_CONFIDENCE_SOURCES_V1: Final[frozenset[str]] = frozenset(
    {m.value for m in DeterministicConfidenceSource}
)

_DEPRECATED_VAGUE_DEGRADATION_SEMANTICS_V1: Final[frozenset[str]] = frozenset(
    {"chronology", "causal", "continuity"}
)


class ReasoningProvenanceLawError(ValueError):
    """Fail-closed ``reasoning-provenance-law`` §1 envelope."""


def _require_str_field(artifact: Mapping[str, Any], key: str) -> str:
    v = artifact.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ReasoningProvenanceLawError(f"{key} must be a non-empty string")
    return v.strip()


def _normalize_cd_codes_list(codes: object) -> list[str]:
    if not isinstance(codes, list):
        raise ReasoningProvenanceLawError("cd_codes must be a list of CD-* literals")
    out: list[str] = []
    for i, c in enumerate(codes):
        if not isinstance(c, str) or not c.strip():
            raise ReasoningProvenanceLawError(f"cd_codes[{i}] must be a non-empty string")
        try:
            out.append(normalize_degradation_corpus_token_v1(c.strip()))
        except ChronologyDegradationPropagationError as exc:
            raise ReasoningProvenanceLawError(str(exc)) from exc
    canon = sorted(set(out))
    if canon != out:
        raise ReasoningProvenanceLawError(
            "cd_codes must be sorted unique canonical CD-* literals (strictly increasing order)"
        )
    return canon


def validate_reasoning_artifact_provenance_envelope_v1(artifact: Mapping[str, Any]) -> None:
    """§1 — mandatory conceptual fields on a Phase **06** reducer artifact mapping."""
    if not isinstance(artifact, Mapping):
        raise ReasoningProvenanceLawError("artifact must be a mapping")

    legacy = artifact.get("degradation_semantics")
    if (
        isinstance(legacy, str)
        and legacy.strip().lower() in _DEPRECATED_VAGUE_DEGRADATION_SEMANTICS_V1
    ):
        raise ReasoningProvenanceLawError(
            "deprecated degradation_semantics single-word tag without CD-* is forbidden "
            f"(got {legacy!r}); use cd_codes + optional degradation_coarse"
        )

    try:
        validate_evidence_lineage_has_raw_or_ledger_hop(artifact.get("evidence_lineage"))
    except OrganizationalContinuityReasoningError as exc:
        raise ReasoningProvenanceLawError(str(exc)) from exc

    rp = _require_str_field(artifact, "replay_posture")
    if rp not in REASONING_REPLAY_POSTURE_LITERALS_V1:
        allowed = ", ".join(sorted(REASONING_REPLAY_POSTURE_LITERALS_V1))
        raise ReasoningProvenanceLawError(
            f"replay_posture must be one of: {allowed}; got {rp!r}"
        )

    ch = _require_str_field(artifact, "chronology_legality_class")
    if ch not in CHRONOLOGY_LEGALITY_CLASSES:
        allowed = ", ".join(sorted(CHRONOLOGY_LEGALITY_CLASSES))
        raise ReasoningProvenanceLawError(
            f"chronology_legality_class must be one of: {allowed}; got {ch!r}"
        )

    causal = _require_str_field(artifact, "causal_legality_class")
    try:
        validate_causal_legality_class(causal)
    except ExecutionCausalityConstraintError as exc:
        raise ReasoningProvenanceLawError(str(exc)) from exc

    cs = _require_str_field(artifact, "confidence_source")
    if cs not in _DETERMINISTIC_CONFIDENCE_SOURCES_V1:
        allowed = ", ".join(sorted(_DETERMINISTIC_CONFIDENCE_SOURCES_V1))
        raise ReasoningProvenanceLawError(
            "confidence_source must be a DeterministicConfidenceSource literal; "
            f"got {cs!r}; allowed: {allowed}"
        )

    amb = _require_str_field(artifact, "ambiguity_class_id")
    try:
        validate_ambiguity_class_id_causal_registry_v1(amb)
    except CausalAmbiguityPropagationError as exc:
        raise ReasoningProvenanceLawError(str(exc)) from exc

    cross = artifact.get("cross_system_causal", False)
    if cross is True:
        ols = artifact.get("org_link_support")
        if not isinstance(ols, Mapping) or not ols:
            raise ReasoningProvenanceLawError(
                "cross_system_causal requires non-empty org_link_support "
                "(Phase 04 continuity bridge refs)"
            )

    raw_ids = artifact.get("source_raw_record_ids")
    if raw_ids is not None:
        if not isinstance(raw_ids, list):
            raise ReasoningProvenanceLawError("source_raw_record_ids must be a list when present")
        for i, x in enumerate(raw_ids):
            if not isinstance(x, int) or isinstance(x, bool):
                raise ReasoningProvenanceLawError(
                    f"source_raw_record_ids[{i}] must be int (non-bool) when present"
                )

    raw_cd_list = artifact.get("cd_codes", [])
    _normalize_cd_codes_list(raw_cd_list)

    dc = artifact.get("degradation_coarse")
    if dc is not None:
        if not isinstance(dc, str) or dc not in ("none", "composite"):
            raise ReasoningProvenanceLawError(
                "degradation_coarse must be omitted or one of: none, composite"
            )
        try:
            expected = degradation_coarse_tag_v1(raw_cd_list)
        except ChronologyDegradationPropagationError as exc:
            raise ReasoningProvenanceLawError(str(exc)) from exc
        if dc != expected:
            raise ReasoningProvenanceLawError(
                f"degradation_coarse {dc!r} inconsistent with cd_codes (expected {expected!r})"
            )

    try:
        validate_unverifiable_causality_requires_cd_codes_v1(
            causal_legality_class=causal,
            cd_codes=raw_cd_list,
        )
    except UnverifiableDegradedCausalityError as exc:
        raise ReasoningProvenanceLawError(str(exc)) from exc


def reasoning_provenance_minimal_valid_fixture_v1(
    *,
    cross_system_causal: bool = False,
) -> dict[str, Any]:
    """Deterministic happy-path mapping for static gates and contract tests."""
    from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
        AMB_NONE,
        LINK_AUTHORITY_AUTHORITATIVE,
    )

    out: dict[str, Any] = {
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "replay_posture": "replay_equivalent",
        "chronology_legality_class": "chronology_strict",
        "causal_legality_class": "causal_replay_equivalent",
        "confidence_source": DeterministicConfidenceSource.EXPLICIT_RULE_ID.value,
        "ambiguity_class_id": AMB_NONE,
        "cd_codes": [],
    }
    if cross_system_causal:
        out["cross_system_causal"] = True
        out["org_link_support"] = {
            "link_authority": LINK_AUTHORITY_AUTHORITATIVE,
            "temporal_validity_ok": True,
        }
    return out


def _rpl_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_reasoning_provenance_law_runtime_schema_version": (
            PHASE06_REASONING_PROVENANCE_LAW_RUNTIME_SCHEMA_VERSION
        ),
    }


def verify_gp06_rpl01_replay_posture_literal_oracle_static() -> dict[str, Any]:
    """P06-24 — §1 / golden-thread §5 replay posture literals."""
    errors: list[str] = []
    if REASONING_REPLAY_POSTURE_LITERALS_V1 != frozenset(
        {
            "replay_equivalent",
            "replay_degraded",
            "replay_partial",
            "replay_unverifiable",
            "replay_conflicted",
        }
    ):
        errors.append("replay_posture_literal_mismatch")
    if len(REASONING_REPLAY_POSTURE_LITERALS_V1) != 5:
        errors.append("expected_five_replay_postures")
    passed = len(errors) == 0
    return {
        "id": "P06-24-rpl-replay-posture-oracle",
        "name": "gp06_rpl01_replay_posture_literal_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rpl_detail(errors),
    }


def verify_gp06_rpl02_minimal_envelope_happy_path_static() -> dict[str, Any]:
    """P06-24 — minimal §1 envelope validates."""
    errors: list[str] = []
    try:
        validate_reasoning_artifact_provenance_envelope_v1(reasoning_provenance_minimal_valid_fixture_v1())
    except ReasoningProvenanceLawError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-24-rpl-minimal-envelope",
        "name": "gp06_rpl02_minimal_envelope_happy_path",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rpl_detail(errors),
    }


def verify_gp06_rpl03_missing_lineage_rejected_static() -> dict[str, Any]:
    """P06-24 — provenance requires substrate hops."""
    errors: list[str] = []
    bad = dict(reasoning_provenance_minimal_valid_fixture_v1())
    bad["evidence_lineage"] = []
    try:
        validate_reasoning_artifact_provenance_envelope_v1(bad)
    except ReasoningProvenanceLawError:
        pass
    else:
        errors.append("expected_reject_empty_lineage")
    passed = len(errors) == 0
    return {
        "id": "P06-24-rpl-lineage",
        "name": "gp06_rpl03_missing_lineage_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rpl_detail(errors),
    }


def verify_gp06_rpl04_cross_system_requires_org_link_static() -> dict[str, Any]:
    """P06-24 — continuity bridge refs when ``cross_system_causal``."""
    errors: list[str] = []
    bad = dict(reasoning_provenance_minimal_valid_fixture_v1(cross_system_causal=True))
    del bad["org_link_support"]
    try:
        validate_reasoning_artifact_provenance_envelope_v1(bad)
    except ReasoningProvenanceLawError:
        pass
    else:
        errors.append("expected_reject_cross_system_without_org_link")
    passed = len(errors) == 0
    return {
        "id": "P06-24-rpl-cross-system",
        "name": "gp06_rpl04_cross_system_requires_org_link",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rpl_detail(errors),
    }


def verify_gp06_rpl05_deprecated_degradation_semantics_rejected_static() -> dict[str, Any]:
    """P06-24 — §1 deprecated vague ``degradation_semantics`` without ``CD‑*``."""
    errors: list[str] = []
    bad = dict(reasoning_provenance_minimal_valid_fixture_v1())
    bad["degradation_semantics"] = "chronology"
    try:
        validate_reasoning_artifact_provenance_envelope_v1(bad)
    except ReasoningProvenanceLawError:
        pass
    else:
        errors.append("expected_reject_legacy_degradation_semantics")
    passed = len(errors) == 0
    return {
        "id": "P06-24-rpl-legacy-degradation",
        "name": "gp06_rpl05_deprecated_degradation_semantics_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _rpl_detail(errors),
    }

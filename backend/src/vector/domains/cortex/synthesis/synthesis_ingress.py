"""Phase 08 P08-04 — retrieval evidence ingress law (``RetrievalEvidenceIngressV1``).

Normative: ``DOCS/cortex/synthesis/phase-08-data-contracts.md`` §Ingress.
``G-P08-INGRESS-01`` — validate Phase **07** responses before synthesis LLM phases.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.anti_goals import (
    list_retrieval_authoritative_output_algebra_violations,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import retrieval_policy_pack_digest_v1
SD_UPSTREAM_LEG_V1: Final[str] = "SD-UPSTREAM-LEG"

PHASE08_INGRESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION: Final[int] = 1

GP08_INGRESS01_GATE_ID_V1: Final[str] = "G-P08-INGRESS-01"

SYN_INGRESS_LEG01_V1: Final[str] = "SYN-INGRESS-LEG-01"
SYN_INGRESS_REP01_V1: Final[str] = "SYN-INGRESS-REP-01"
SYN_INGRESS_HIT01_V1: Final[str] = "SYN-INGRESS-HIT-01"
SYN_INGRESS_ALG01_V1: Final[str] = "SYN-INGRESS-ALG-01"
SYN_INGRESS_PAR01_V1: Final[str] = "SYN-INGRESS-PAR-01"
SYN_INGRESS_POL01_V1: Final[str] = "SYN-INGRESS-POL-01"

SYN_INGRESS_GATE_IDS_V1: Final[tuple[str, ...]] = (
    SYN_INGRESS_LEG01_V1,
    SYN_INGRESS_REP01_V1,
    SYN_INGRESS_HIT01_V1,
    SYN_INGRESS_ALG01_V1,
    SYN_INGRESS_PAR01_V1,
    SYN_INGRESS_POL01_V1,
)

_AUTHORITATIVE_RETRIEVAL_LEGALITY_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_replay_safe",
        "retrieval_degraded",
        "retrieval_partial",
    }
)

_EXPLORATION_RETRIEVAL_LEGALITY_V1: Final[frozenset[str]] = frozenset(
    _AUTHORITATIVE_RETRIEVAL_LEGALITY_V1 | {"retrieval_unverifiable"}
)

_RETRIEVAL_LEGALITY_COPY_FIELDS_V1: Final[tuple[str, ...]] = (
    "retrieval_legality_class",
    "causal_legality_class",
    "chronology_legality_class",
)

_INGRESS_REJECT_METRIC_NAMES_V1: Final[tuple[str, ...]] = (
    "synthesis_ingress_legality_reject_total",
    "synthesis_ingress_replay_identity_missing_total",
    "synthesis_ingress_hits_missing_total",
    "synthesis_ingress_algebra_violation_total",
    "synthesis_ingress_partition_mismatch_total",
    "synthesis_ingress_policy_digest_mismatch_total",
)


class SynthesisIngressError(ValueError):
    """Raised when a Phase **07** retrieval response fails synthesis ingress law."""

    def __init__(
        self,
        code: str,
        *,
        gate_id: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.gate_id = gate_id
        self.detail = dict(detail or {})
        super().__init__(f"{gate_id}:{code}")


def _gate_violations(gate_id: str, violations: list[str]) -> list[dict[str, str]]:
    return [{"gate_id": gate_id, "violation": v} for v in violations]


def list_synthesis_ingress_exploration_partition_violations_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_execution_partition: str,
) -> list[str]:
    """SYN-INGRESS-PAR-01 — exploration retrieval only for exploration synthesis jobs."""
    if job_execution_partition.strip().lower() == "exploration":
        return []
    if retrieval_response.get("non_authoritative") is True:
        return ["exploration_retrieval_for_authoritative_synthesis_job"]
    return []


def list_synthesis_ingress_replay_identity_violations_v1(
    retrieval_response: Mapping[str, Any],
) -> list[str]:
    """SYN-INGRESS-REP-01 — ``retrieval_query_replay_identity`` required."""
    rid = retrieval_response.get(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    if not isinstance(rid, str) or not rid.strip():
        return [f"missing:{PHASE07_REPLAY_IDENTITY_FIELD_V1}"]
    return []


def list_synthesis_ingress_hits_violations_v1(retrieval_response: Mapping[str, Any]) -> list[str]:
    """SYN-INGRESS-HIT-01 — evidence hits array must be present (may be empty)."""
    hits = retrieval_response.get("retrieval_evidence_hits")
    if hits is None:
        hits = retrieval_response.get("hits")
    if hits is None:
        return ["missing:retrieval_evidence_hits"]
    if not isinstance(hits, list):
        return ["invalid:retrieval_evidence_hits_not_array"]
    return []


def list_synthesis_ingress_legality_violations_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_execution_partition: str = "authoritative",
) -> list[str]:
    """SYN-INGRESS-LEG-01 — retrieval legality allowed for synthesis partition."""
    legality = str(retrieval_response.get("retrieval_legality_class") or "").strip()
    if not legality:
        return ["missing:retrieval_legality_class"]
    allowed = (
        _EXPLORATION_RETRIEVAL_LEGALITY_V1
        if job_execution_partition.strip().lower() == "exploration"
        else _AUTHORITATIVE_RETRIEVAL_LEGALITY_V1
    )
    if legality == "retrieval_forbidden":
        return ["retrieval_legality_forbidden"]
    if legality not in allowed:
        return [f"retrieval_legality_not_allowed:{legality}"]
    if legality == "retrieval_unverifiable" and job_execution_partition.strip().lower() == "authoritative":
        return ["retrieval_unverifiable_blocks_authoritative_synthesis"]
    return []


def list_synthesis_ingress_algebra_violations_v1(
    retrieval_response: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> list[str]:
    """SYN-INGRESS-ALG-01 — response must satisfy Phase **07** authoritative output algebra."""
    return list_retrieval_authoritative_output_algebra_violations(
        retrieval_response,
        execution_partition=execution_partition,
    )


def list_synthesis_ingress_policy_digest_violations_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
) -> list[str]:
    """SYN-INGRESS-POL-01 — pinned policy digest must match retrieval response when declared."""
    if job_envelope is None:
        return []
    pins = job_envelope.get("retrieval_pins")
    if not isinstance(pins, Mapping):
        pins = {}
    pinned_digest = str(
        pins.get("retrieval_policy_pack_digest")
        or job_envelope.get("synthesis_policy_pack_digest")
        or "",
    ).strip()
    if not pinned_digest:
        return []
    actual = str(retrieval_response.get("retrieval_policy_pack_digest") or "").strip()
    if not actual:
        actual = retrieval_policy_pack_digest_v1()
    if pinned_digest != actual:
        return [f"policy_digest_mismatch:{pinned_digest}!={actual}"]
    return []


def list_synthesis_ingress_pinned_receipt_violations_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
) -> list[str]:
    """Optional ``pinned_retrieval_receipt`` must agree on replay identity."""
    if job_envelope is None:
        return []
    pinned = job_envelope.get("pinned_retrieval_receipt")
    if not isinstance(pinned, Mapping):
        return []
    pinned_rid = pinned.get(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    actual_rid = retrieval_response.get(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    if pinned_rid and actual_rid and str(pinned_rid) != str(actual_rid):
        return ["pinned_receipt_replay_identity_mismatch"]
    return []


def extract_retrieval_legality_copy_v1(retrieval_response: Mapping[str, Any]) -> dict[str, str]:
    """Fields Phase **08** must copy from retrieval without LLM reprojection (SYN-BND-07-02)."""
    out: dict[str, str] = {}
    for field in _RETRIEVAL_LEGALITY_COPY_FIELDS_V1:
        val = retrieval_response.get(field)
        if isinstance(val, str) and val.strip():
            out[field] = val.strip()
    upstream_causal = retrieval_response.get("upstream_causal_legality_class")
    upstream_chronology = retrieval_response.get("upstream_chronology_legality_class")
    if isinstance(upstream_causal, str) and upstream_causal.strip():
        out.setdefault("upstream_causal_legality_class", upstream_causal.strip())
    if isinstance(upstream_chronology, str) and upstream_chronology.strip():
        out.setdefault("upstream_chronology_legality_class", upstream_chronology.strip())
    return out


def build_retrieval_evidence_ingress_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_execution_partition: str = "authoritative",
    gate_results: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build ``RetrievalEvidenceIngressV1`` snapshot for job persistence / digest."""
    hits = retrieval_response.get("retrieval_evidence_hits")
    if hits is None:
        hits = retrieval_response.get("hits")
    omissions = retrieval_response.get("retrieval_omission_rows")
    if omissions is None:
        omissions = retrieval_response.get("omissions")
    omission_list = [o for o in omissions if isinstance(o, Mapping)] if isinstance(omissions, list) else []
    from vector.domains.cortex.synthesis.phase_boundaries import (
        propagate_retrieval_omissions_to_sd_rows_v1,
    )

    sd_rows = propagate_retrieval_omissions_to_sd_rows_v1(omission_list)
    ingress: dict[str, Any] = {
        "schema_version": int(RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION),
        "phase08_ingress_runtime_schema_version": int(PHASE08_INGRESS_RUNTIME_SCHEMA_VERSION),
        "execution_partition": job_execution_partition,
        PHASE07_REPLAY_IDENTITY_FIELD_V1: retrieval_response.get(PHASE07_REPLAY_IDENTITY_FIELD_V1),
        "retrieval_legality_copy": extract_retrieval_legality_copy_v1(retrieval_response),
        "retrieval_evidence_hit_count": len(hits) if isinstance(hits, list) else 0,
        "retrieval_omission_rows": omission_list,
        "synthesis_omission_rows": sd_rows,
        "retrieval_policy_pack_digest": retrieval_response.get("retrieval_policy_pack_digest"),
        "retrieval_query_receipt_digest": (
            (retrieval_response.get("retrieval_query_receipt") or {}).get("receipt_digest")
            if isinstance(retrieval_response.get("retrieval_query_receipt"), Mapping)
            else None
        ),
        "non_authoritative": bool(retrieval_response.get("non_authoritative")),
        "upstream_sd_legality_floor": (
            SD_UPSTREAM_LEG_V1
            if any(r.get("synthesis_omission_class") == SD_UPSTREAM_LEG_V1 for r in sd_rows)
            else None
        ),
    }
    if gate_results is not None:
        ingress["gate_results"] = list(gate_results)
    ingress["retrieval_ingress_digest"] = compute_retrieval_ingress_digest_v1(ingress)
    return ingress


def compute_retrieval_ingress_digest_v1(ingress: Mapping[str, Any]) -> str:
    """Canonical digest stored on synthesis job rows as ``retrieval_ingress_digest``."""
    body = {k: v for k, v in ingress.items() if k != "retrieval_ingress_digest"}
    return hash_reasoning_canonical_json_sha256_v1(dict(body))


def collect_synthesis_ingress_gate_results_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
    job_execution_partition: str = "authoritative",
) -> tuple[list[dict[str, str]], list[str]]:
    """Evaluate all SYN-INGRESS gates; return (gate_results, flat_violations)."""
    partition = job_execution_partition
    if job_envelope is not None:
        partition = str(job_envelope.get("execution_partition") or partition)

    checks: list[tuple[str, list[str]]] = [
        (
            SYN_INGRESS_PAR01_V1,
            list_synthesis_ingress_exploration_partition_violations_v1(
                retrieval_response,
                job_execution_partition=partition,
            ),
        ),
        (SYN_INGRESS_REP01_V1, list_synthesis_ingress_replay_identity_violations_v1(retrieval_response)),
        (SYN_INGRESS_HIT01_V1, list_synthesis_ingress_hits_violations_v1(retrieval_response)),
        (
            SYN_INGRESS_LEG01_V1,
            list_synthesis_ingress_legality_violations_v1(
                retrieval_response,
                job_execution_partition=partition,
            ),
        ),
        (
            SYN_INGRESS_ALG01_V1,
            list_synthesis_ingress_algebra_violations_v1(
                retrieval_response,
                execution_partition=partition,
            ),
        ),
        (
            SYN_INGRESS_POL01_V1,
            list_synthesis_ingress_policy_digest_violations_v1(
                retrieval_response,
                job_envelope=job_envelope,
            )
            + list_synthesis_ingress_pinned_receipt_violations_v1(
                retrieval_response,
                job_envelope=job_envelope,
            ),
        ),
    ]

    gate_results: list[dict[str, str]] = []
    flat: list[str] = []
    for gate_id, violations in checks:
        gate_results.extend(_gate_violations(gate_id, violations))
        flat.extend(violations)
    return gate_results, flat


def _primary_gate_for_violations(violations: Sequence[str]) -> str:
    if any("exploration_retrieval" in v for v in violations):
        return SYN_INGRESS_PAR01_V1
    if any(PHASE07_REPLAY_IDENTITY_FIELD_V1 in v for v in violations):
        return SYN_INGRESS_REP01_V1
    if any("retrieval_evidence_hits" in v for v in violations):
        return SYN_INGRESS_HIT01_V1
    if any("retrieval_legality" in v for v in violations):
        return SYN_INGRESS_LEG01_V1
    if any("forbidden_top_level" in v or "algebra" in v for v in violations):
        return SYN_INGRESS_ALG01_V1
    if any("policy_digest" in v or "pinned_receipt" in v for v in violations):
        return SYN_INGRESS_POL01_V1
    return SYN_INGRESS_LEG01_V1


def validate_retrieval_evidence_ingress_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
    job_execution_partition: str = "authoritative",
) -> dict[str, Any]:
    """Validate Phase **07** retrieval response; return ``RetrievalEvidenceIngressV1``."""
    gate_results, violations = collect_synthesis_ingress_gate_results_v1(
        retrieval_response,
        job_envelope=job_envelope,
        job_execution_partition=job_execution_partition,
    )
    if violations:
        gate_id = _primary_gate_for_violations(violations)
        raise SynthesisIngressError(
            "retrieval_evidence_ingress_invalid",
            gate_id=gate_id,
            detail={"violations": violations[:32], "gate_results": gate_results[:32]},
        )
    partition = job_execution_partition
    if job_envelope is not None:
        partition = str(job_envelope.get("execution_partition") or partition)
    return build_retrieval_evidence_ingress_v1(
        retrieval_response,
        job_execution_partition=partition,
        gate_results=gate_results,
    )


def enforce_retrieval_evidence_ingress_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
    job_execution_partition: str = "authoritative",
) -> dict[str, Any]:
    """Ingress law gate — raises ``SynthesisIngressError`` on failure."""
    return validate_retrieval_evidence_ingress_v1(
        retrieval_response,
        job_envelope=job_envelope,
        job_execution_partition=job_execution_partition,
    )


def build_synthesis_ingress_law_catalog_v1() -> dict[str, Any]:
    """Operator/admin ingress law table (P08-04)."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase08_ingress_runtime_schema_version": int(PHASE08_INGRESS_RUNTIME_SCHEMA_VERSION),
        "retrieval_evidence_ingress_schema_version": int(RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION),
        "spec_ref": "DOCS/cortex/synthesis/phase-08-data-contracts.md#ingress--retrievalevidenceingressv1",
        "gate_ids": list(SYN_INGRESS_GATE_IDS_V1),
        "gp08_ingress_gate_id": GP08_INGRESS01_GATE_ID_V1,
        "authoritative_retrieval_legality_classes": sorted(_AUTHORITATIVE_RETRIEVAL_LEGALITY_V1),
        "exploration_retrieval_legality_classes": sorted(_EXPLORATION_RETRIEVAL_LEGALITY_V1),
        "retrieval_legality_copy_fields": list(_RETRIEVAL_LEGALITY_COPY_FIELDS_V1),
        "ingress_reject_metrics": list(_INGRESS_REJECT_METRIC_NAMES_V1),
        "sd_upstream_legality_code": SD_UPSTREAM_LEG_V1,
        "rules": [
            {
                "id": SYN_INGRESS_LEG01_V1,
                "text": "retrieval_legality_class must be allowed for synthesis execution_partition.",
            },
            {
                "id": SYN_INGRESS_REP01_V1,
                "text": "retrieval_query_replay_identity must be present on ingress.",
            },
            {
                "id": SYN_INGRESS_HIT01_V1,
                "text": "retrieval_evidence_hits array must be present (empty allowed).",
            },
            {
                "id": SYN_INGRESS_ALG01_V1,
                "text": "Response must satisfy Phase 07 authoritative output algebra.",
            },
            {
                "id": SYN_INGRESS_PAR01_V1,
                "text": "non_authoritative retrieval only when synthesis job is exploration.",
            },
            {
                "id": SYN_INGRESS_POL01_V1,
                "text": "Pinned retrieval_policy_pack_digest must match response when declared.",
            },
        ],
    }


def build_synthesis_ingress_inspector_fields_v1() -> dict[str, Any]:
    """Ingress inspector field catalog for admin job detail / preview surfaces."""
    return {
        "retrieval_query_replay_identity": {"type": "string", "required": True},
        "retrieval_legality_class": {"type": "string", "required": True},
        "retrieval_evidence_hit_count": {"type": "integer", "minimum": 0},
        "retrieval_ingress_digest": {"type": "string", "format": "sha256-hex"},
        "retrieval_policy_pack_digest": {"type": "string"},
        "retrieval_query_receipt_digest": {"type": "string", "nullable": True},
        "execution_partition": {"type": "enum", "values": ["authoritative", "exploration"]},
        "non_authoritative": {"type": "boolean"},
        "synthesis_omission_rows": {"type": "array", "items": "SD-* omission row"},
        "upstream_sd_legality_floor": {"type": "string", "example": SD_UPSTREAM_LEG_V1},
    }


def build_synthesis_ingress_inspector_v1(
    retrieval_response: Mapping[str, Any],
    *,
    job_envelope: Mapping[str, Any] | None = None,
    job_execution_partition: str = "authoritative",
) -> dict[str, Any]:
    """Build operator ingress inspector payload (pass or fail with gate breakdown)."""
    gate_results, violations = collect_synthesis_ingress_gate_results_v1(
        retrieval_response,
        job_envelope=job_envelope,
        job_execution_partition=job_execution_partition,
    )
    passed = len(violations) == 0
    ingress: dict[str, Any] | None = None
    if passed:
        ingress = build_retrieval_evidence_ingress_v1(
            retrieval_response,
            job_execution_partition=(
                str(job_envelope.get("execution_partition"))
                if isinstance(job_envelope, Mapping) and job_envelope.get("execution_partition")
                else job_execution_partition
            ),
            gate_results=gate_results,
        )
    return {
        "surface_kind": "verification_probe" if not passed else "doctrine_catalog",
        "ingress_passed": passed,
        "gate_id": GP08_INGRESS01_GATE_ID_V1,
        "gate_results": gate_results,
        "violations": violations[:32],
        "retrieval_evidence_ingress": ingress,
        "inspector_fields": build_synthesis_ingress_inspector_fields_v1(),
    }


def verify_gp08_ingress01_retrieval_evidence_ingress_static() -> dict[str, Any]:
    """``G-P08-INGRESS-01`` — synthesis ingress gate battery."""
    errors: list[str] = []

    legal = {
        "retrieval_legality_class": "retrieval_replay_safe",
        PHASE07_REPLAY_IDENTITY_FIELD_V1: "rqid:legal",
        "retrieval_evidence_hits": [],
        "retrieval_omission_rows": [],
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(),
        "retrieval_query_receipt": {"receipt_digest": "sha256:00"},
    }
    try:
        ingress = validate_retrieval_evidence_ingress_v1(legal, job_execution_partition="authoritative")
        if ingress.get("schema_version") != RETRIEVAL_EVIDENCE_INGRESS_SCHEMA_VERSION:
            errors.append("ingress_schema_version")
        if not ingress.get("retrieval_ingress_digest"):
            errors.append("missing_ingress_digest")
    except SynthesisIngressError as exc:
        errors.append(f"unexpected_rejection_legal:{exc}")

    try:
        validate_retrieval_evidence_ingress_v1(
            {**legal, "non_authoritative": True},
            job_execution_partition="authoritative",
        )
    except SynthesisIngressError as exc:
        if exc.gate_id != SYN_INGRESS_PAR01_V1:
            errors.append(f"wrong_gate_exploration:{exc.gate_id}")
    else:
        errors.append("expected_exploration_partition_rejection")

    bad = dict(legal)
    bad.pop(PHASE07_REPLAY_IDENTITY_FIELD_V1)
    try:
        validate_retrieval_evidence_ingress_v1(bad)
    except SynthesisIngressError as exc:
        if exc.gate_id != SYN_INGRESS_REP01_V1:
            errors.append(f"wrong_gate_replay:{exc.gate_id}")
    else:
        errors.append("expected_replay_identity_rejection")

    cat = build_synthesis_ingress_law_catalog_v1()
    if set(cat["gate_ids"]) != set(SYN_INGRESS_GATE_IDS_V1):
        errors.append("catalog_gate_ids_mismatch")

    passed = len(errors) == 0
    return {
        "id": GP08_INGRESS01_GATE_ID_V1,
        "name": "retrieval_evidence_ingress_validation",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

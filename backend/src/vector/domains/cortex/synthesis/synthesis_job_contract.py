"""Phase 08 P08-05 — synthesis workload classes + intent taxonomy.

Normative: ``DOCS/cortex/synthesis/phase-08-data-contracts.md`` §1–2.
``G-P08-SCHEMA-01`` — closed workload + intent registry aligned with job envelope schema.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.synthesis.normative import (
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
)

PHASE08_SYNTHESIS_JOB_CONTRACT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1: Final[int] = 1

GP08_SCHEMA01_WORKLOAD_INTENT_GATE_ID_V1: Final[str] = "G-P08-SCHEMA-01"

DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1: Final[str] = "SynthesisPolicyPackV1_Default"

# §1 — closed synthesis workload class enum (8).
SYNTHESIS_WORKLOAD_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_understanding",
        "operational_synthesis",
        "execution_narrative",
        "management_intelligence",
        "continuity_assessment",
        "degradation_brief",
        "replay_equivalence_synthesis",
        "pipeline_default",
    }
)

# §2 — closed synthesis intent enum (5).
SYNTHESIS_INTENT_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "inspect",
        "prove",
        "audit",
        "enumerate",
        "diff",
    }
)

_DEFAULT_SELECTION_CAPS_BASE_V1: Final[dict[str, int]] = {
    "max_claims": 64,
    "max_retrieval_subqueries": 8,
    "max_llm_tokens": 8192,
}

SYNTHESIS_WORKLOAD_CLASS_DEFAULT_CAPS_V1: Final[dict[str, dict[str, int]]] = {
    "execution_understanding": {"max_claims": 32, "max_retrieval_subqueries": 4, "max_llm_tokens": 8192},
    "operational_synthesis": {"max_claims": 48, "max_retrieval_subqueries": 6, "max_llm_tokens": 8192},
    "execution_narrative": {"max_claims": 24, "max_retrieval_subqueries": 4, "max_llm_tokens": 6144},
    "management_intelligence": {"max_claims": 16, "max_retrieval_subqueries": 2, "max_llm_tokens": 4096},
    "continuity_assessment": {"max_claims": 40, "max_retrieval_subqueries": 6, "max_llm_tokens": 6144},
    "degradation_brief": {"max_claims": 64, "max_retrieval_subqueries": 8, "max_llm_tokens": 4096},
    "replay_equivalence_synthesis": {"max_claims": 8, "max_retrieval_subqueries": 2, "max_llm_tokens": 4096},
    "pipeline_default": {"max_claims": 32, "max_retrieval_subqueries": 4, "max_llm_tokens": 8192},
}

SYNTHESIS_WORKLOAD_CLASS_METADATA_V1: Final[dict[str, dict[str, str]]] = {
    "execution_understanding": {
        "purpose": "Execution understanding from causal chain + chronology",
        "retrieval_plan_profile": "causal_chain + chronology_window",
        "primary_artifact_kind": "execution_brief",
    },
    "operational_synthesis": {
        "purpose": "Operational synthesis from degradation + causal evidence",
        "retrieval_plan_profile": "degradation_survey + causal_chain",
        "primary_artifact_kind": "operational_synthesis",
    },
    "execution_narrative": {
        "purpose": "Bounded execution narrative with traversal lineage",
        "retrieval_plan_profile": "causal_chain + traversal_lineage",
        "primary_artifact_kind": "execution_narrative",
    },
    "management_intelligence": {
        "purpose": "Management intelligence rollup over operational synthesis",
        "retrieval_plan_profile": "operational_synthesis rollup",
        "primary_artifact_kind": "management_intelligence",
    },
    "continuity_assessment": {
        "purpose": "Ownership + execution continuity assessment",
        "retrieval_plan_profile": "ownership_continuity + execution_continuity",
        "primary_artifact_kind": "continuity_assessment",
    },
    "degradation_brief": {
        "purpose": "Degradation survey brief for operators",
        "retrieval_plan_profile": "degradation_survey",
        "primary_artifact_kind": "degradation_brief",
    },
    "replay_equivalence_synthesis": {
        "purpose": "Structural twin / certification synthesis (internal)",
        "retrieval_plan_profile": "replay_equivalence (prove)",
        "primary_artifact_kind": "internal cert only",
    },
    "pipeline_default": {
        "purpose": "Substrate pipeline default per tenant policy row",
        "retrieval_plan_profile": "policy-driven per index row",
        "primary_artifact_kind": "island_brief",
    },
}

SYNTHESIS_INTENT_CLASS_METADATA_V1: Final[dict[str, dict[str, str]]] = {
    "inspect": {"meaning": "Operator understanding", "llm_allowed": "yes_bounded"},
    "prove": {"meaning": "Certification / structural twin", "llm_allowed": "yes_structural_twin"},
    "audit": {"meaning": "Fail-closed on unverifiable upstream", "llm_allowed": "limited_narration"},
    "enumerate": {"meaning": "List claims only, minimal glue", "llm_allowed": "optional"},
    "diff": {"meaning": "Compare two pinned artifact digests", "llm_allowed": "yes_diff_claims_only"},
}

_REPLAY_PROOF_INTENTS_V1: Final[frozenset[str]] = frozenset({"prove", "diff", "audit"})

SYNTHESIS_WORKLOAD_ALLOWED_INTENTS_V1: Final[dict[str, frozenset[str]]] = {
    "replay_equivalence_synthesis": _REPLAY_PROOF_INTENTS_V1,
}


class SynthesisJobContractError(ValueError):
    """Raised when workload class or intent violates the synthesis job contract."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def normalize_synthesis_workload_class_v1(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def normalize_synthesis_intent_v1(value: str) -> str:
    return value.strip().lower()


def validate_synthesis_workload_class_v1(workload_class: str) -> str:
    """Return normalized workload class or raise (**SYN-QC-01** / schema enum)."""
    norm = normalize_synthesis_workload_class_v1(workload_class)
    if norm not in SYNTHESIS_WORKLOAD_CLASSES_V1:
        allowed = ", ".join(sorted(SYNTHESIS_WORKLOAD_CLASSES_V1))
        raise SynthesisJobContractError(
            "unknown_synthesis_workload_class",
            detail={"synthesis_workload_class": workload_class, "allowed": allowed},
        )
    return norm


def validate_synthesis_intent_v1(intent: str) -> str:
    """Return normalized intent or raise."""
    norm = normalize_synthesis_intent_v1(intent)
    if norm not in SYNTHESIS_INTENT_CLASSES_V1:
        allowed = ", ".join(sorted(SYNTHESIS_INTENT_CLASSES_V1))
        raise SynthesisJobContractError(
            "unknown_synthesis_intent",
            detail={"synthesis_intent": intent, "allowed": allowed},
        )
    return norm


def validate_synthesis_intent_allowed_for_workload_v1(*, workload_class: str, intent: str) -> None:
    wl = validate_synthesis_workload_class_v1(workload_class)
    it = validate_synthesis_intent_v1(intent)
    allowed = SYNTHESIS_WORKLOAD_ALLOWED_INTENTS_V1.get(wl)
    if allowed is not None and it not in allowed:
        raise SynthesisJobContractError(
            "intent_not_allowed_for_synthesis_workload",
            detail={
                "synthesis_workload_class": wl,
                "synthesis_intent": it,
                "allowed_intents": sorted(allowed),
            },
        )


def selection_policy_caps_for_synthesis_workload_v1(workload_class: str) -> dict[str, int]:
    """Per-workload selection caps (§3 selection_policy defaults)."""
    wl = validate_synthesis_workload_class_v1(workload_class)
    caps = dict(_DEFAULT_SELECTION_CAPS_BASE_V1)
    caps.update(SYNTHESIS_WORKLOAD_CLASS_DEFAULT_CAPS_V1.get(wl, {}))
    return caps


def build_synthesis_workload_class_catalog_v1() -> list[dict[str, Any]]:
    """Admin job debugger workload picker rows."""
    rows: list[dict[str, Any]] = []
    for wl in sorted(SYNTHESIS_WORKLOAD_CLASSES_V1):
        meta = SYNTHESIS_WORKLOAD_CLASS_METADATA_V1.get(wl, {})
        allowed_intents = SYNTHESIS_WORKLOAD_ALLOWED_INTENTS_V1.get(wl, SYNTHESIS_INTENT_CLASSES_V1)
        rows.append(
            {
                "synthesis_workload_class": wl,
                "purpose": meta.get("purpose", ""),
                "retrieval_plan_profile": meta.get("retrieval_plan_profile", ""),
                "primary_artifact_kind": meta.get("primary_artifact_kind", ""),
                "allowed_intents": sorted(allowed_intents),
                "default_selection_policy": selection_policy_caps_for_synthesis_workload_v1(wl),
            },
        )
    return rows


def build_synthesis_intent_class_catalog_v1() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for it in sorted(SYNTHESIS_INTENT_CLASSES_V1):
        meta = SYNTHESIS_INTENT_CLASS_METADATA_V1.get(it, {})
        rows.append(
            {
                "synthesis_intent": it,
                "meaning": meta.get("meaning", ""),
                "llm_allowed": meta.get("llm_allowed", ""),
            },
        )
    return rows


def build_synthesis_job_contract_catalog_v1() -> dict[str, Any]:
    """Full §1–2 contract catalog for admin / observability."""
    return {
        "surface_kind": "doctrine_catalog",
        "phase08_synthesis_job_contract_runtime_schema_version": int(
            PHASE08_SYNTHESIS_JOB_CONTRACT_RUNTIME_SCHEMA_VERSION,
        ),
        "envelope_schema_version": int(SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1),
        "default_synthesis_policy_pack_id": DEFAULT_SYNTHESIS_POLICY_PACK_ID_V1,
        "gp08_schema_gate_id": GP08_SCHEMA01_WORKLOAD_INTENT_GATE_ID_V1,
        "synthesis_workload_classes": build_synthesis_workload_class_catalog_v1(),
        "synthesis_intent_classes": build_synthesis_intent_class_catalog_v1(),
        "replay_identity_fields": {
            "synthesis_job_replay_identity": PHASE08_REPLAY_IDENTITY_FIELD_V1,
            "upstream_retrieval_replay_identity": PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1,
        },
        "jobs_by_workload_metric": "synthesis_jobs_by_workload_total",
    }


def build_synthesis_job_replay_identity_scope_v1(
    *,
    synthesis_workload_class: str,
    synthesis_intent: str,
    tenant_id: str | None = None,
    extra_pins: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pins workload + intent into synthesis replay identity scope (Step 08)."""
    wl = validate_synthesis_workload_class_v1(synthesis_workload_class)
    it = validate_synthesis_intent_v1(synthesis_intent)
    validate_synthesis_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    scope: dict[str, Any] = {
        PHASE08_REPLAY_IDENTITY_FIELD_V1: {
            "synthesis_workload_class": wl,
            "synthesis_intent": it,
        },
        "synthesis_workload_class": wl,
        "synthesis_intent": it,
    }
    if tenant_id:
        scope["tenant_id"] = tenant_id
    if extra_pins:
        scope["pins"] = dict(extra_pins)
    return scope


def enforce_synthesis_job_workload_and_intent_v1(body: Mapping[str, Any]) -> tuple[str, str]:
    """Validate envelope workload + intent; return normalized pair."""
    raw_wl = body.get("synthesis_workload_class")
    raw_it = body.get("synthesis_intent")
    if raw_wl is None or raw_it is None:
        raise SynthesisJobContractError(
            "synthesis_workload_class_and_intent_required",
            detail={"synthesis_workload_class": raw_wl, "synthesis_intent": raw_it},
        )
    wl = validate_synthesis_workload_class_v1(str(raw_wl))
    it = validate_synthesis_intent_v1(str(raw_it))
    validate_synthesis_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    return wl, it


def resolve_synthesis_workload_and_intent_v1(
    body: Mapping[str, Any],
    *,
    default_workload_class: str = "pipeline_default",
    default_intent: str = "inspect",
) -> tuple[str, str]:
    """Resolve workload/intent from body, applying defaults for minimal admin paths."""
    raw_wl = body.get("synthesis_workload_class")
    raw_it = body.get("synthesis_intent")
    if raw_wl is not None and raw_it is not None:
        return enforce_synthesis_job_workload_and_intent_v1(body)
    wl = validate_synthesis_workload_class_v1(str(raw_wl or default_workload_class))
    it = validate_synthesis_intent_v1(str(raw_it or default_intent))
    validate_synthesis_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    return wl, it


def validate_synthesis_job_envelope_schema_version_v1(body: Mapping[str, Any]) -> int:
    """Envelope ``schema_version`` must be ``1``."""
    ver = body.get("schema_version")
    if ver is None:
        raise SynthesisJobContractError(
            "schema_version_required",
            detail={"schema_version": ver},
        )
    if int(ver) != SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1:
        raise SynthesisJobContractError(
            "schema_version_mismatch",
            detail={
                "schema_version": ver,
                "expected": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
            },
        )
    return int(ver)


def synthesis_job_envelope_schema_path_v1() -> Path:
    """Normative JSON Schema path for ``SynthesisJobEnvelopeV1``."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        candidate = (
            root
            / "DOCS"
            / "cortex"
            / "synthesis"
            / "schemas"
            / "synthesis-job-envelope-v1.schema.json"
        )
        if candidate.is_file():
            return candidate
    return (
        start.parents[4]
        / "DOCS"
        / "cortex"
        / "synthesis"
        / "schemas"
        / "synthesis-job-envelope-v1.schema.json"
    )


def verify_gp08_schema01_synthesis_workload_intent_registry_static() -> dict[str, Any]:
    """``G-P08-SCHEMA-01`` — closed registry matches doctrine §1–2 and job envelope schema."""
    errors: list[str] = []

    if len(SYNTHESIS_WORKLOAD_CLASSES_V1) != 8:
        errors.append(f"workload_class_count:{len(SYNTHESIS_WORKLOAD_CLASSES_V1)}")
    if len(SYNTHESIS_INTENT_CLASSES_V1) != 5:
        errors.append(f"intent_class_count:{len(SYNTHESIS_INTENT_CLASSES_V1)}")

    for wl in SYNTHESIS_WORKLOAD_CLASSES_V1:
        if wl not in SYNTHESIS_WORKLOAD_CLASS_METADATA_V1:
            errors.append(f"missing_metadata:{wl}")
        if wl not in SYNTHESIS_WORKLOAD_CLASS_DEFAULT_CAPS_V1:
            errors.append(f"missing_caps:{wl}")

    try:
        validate_synthesis_workload_class_v1("execution_understanding")
        validate_synthesis_intent_v1("inspect")
        validate_synthesis_intent_allowed_for_workload_v1(
            workload_class="execution_understanding",
            intent="inspect",
        )
    except SynthesisJobContractError as exc:
        errors.append(f"unexpected_rejection_legal_pair:{exc}")

    try:
        validate_synthesis_workload_class_v1("chat_summary")
    except SynthesisJobContractError:
        pass
    else:
        errors.append("expected_unknown_workload_rejection")

    try:
        validate_synthesis_intent_allowed_for_workload_v1(
            workload_class="replay_equivalence_synthesis",
            intent="enumerate",
        )
    except SynthesisJobContractError:
        pass
    else:
        errors.append("expected_intent_workload_mismatch_rejection")

    path = synthesis_job_envelope_schema_path_v1()
    if not path.is_file():
        errors.append(f"missing_schema_file:{path}")
    else:
        import json

        schema = json.loads(path.read_text(encoding="utf-8"))
        wl_enum = set(schema["properties"]["synthesis_workload_class"]["enum"])
        it_enum = set(schema["properties"]["synthesis_intent"]["enum"])
        if wl_enum != set(SYNTHESIS_WORKLOAD_CLASSES_V1):
            errors.append("schema_workload_enum_mismatch")
        if it_enum != set(SYNTHESIS_INTENT_CLASSES_V1):
            errors.append("schema_intent_enum_mismatch")

    cat = build_synthesis_job_contract_catalog_v1()
    if len(cat["synthesis_workload_classes"]) != 8:
        errors.append("catalog_workload_rows")
    if len(cat["synthesis_intent_classes"]) != 5:
        errors.append("catalog_intent_rows")

    passed = len(errors) == 0
    return {
        "id": GP08_SCHEMA01_WORKLOAD_INTENT_GATE_ID_V1,
        "name": "synthesis_workload_intent_registry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase08_synthesis_job_contract_runtime_schema_version": (
                PHASE08_SYNTHESIS_JOB_CONTRACT_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }

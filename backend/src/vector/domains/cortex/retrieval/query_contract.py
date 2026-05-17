"""Phase 07 P07-05 — query workload classes + retrieval intent taxonomy.

Normative: ``DOCS/cortex/retrieval/phase-07-query-contract-doctrine.md`` §1–2.
``G-P07-QC-01`` — closed workload + intent registry (RET-QC-01).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1

PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1: Final[int] = 1

GP07_QC01_GATE_ID_V1: Final[str] = "G-P07-QC-01"

RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1: Final[str] = "RD-ADDRESSING-UNRESOLVED"

# §1 — closed workload class enum (14).
RETRIEVAL_WORKLOAD_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_continuity",
        "chronology_window",
        "ownership_continuity",
        "causal_chain",
        "causal_edge",
        "degradation_survey",
        "dependency_propagation",
        "replay_divergence",
        "escalation",
        "traversal_lineage",
        "replay_equivalence",
        "lineage_explorer",
        "continuity_topology",
        "materialization_as_of",
    }
)

# §2 — closed intent enum (5).
RETRIEVAL_INTENT_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "inspect",
        "enumerate",
        "prove",
        "audit",
        "diff",
    }
)

RETRIEVAL_ADDRESSING_REF_KEYS_V1: Final[tuple[str, ...]] = (
    "retrieval_lookup_id",
    "retrieval_chain_ref",
    "retrieval_window_ref",
    "retrieval_walk_ref",
    "retrieval_lineage_ref",
    "causal_chain_id",
    "causal_chain_ref",
    "tcre_causal_edge_id",
    "materialization_id",
    "chronology_window_ref",
    "org_entity_id",
    "org_link_id",
)


def addressing_has_resolvable_ref_v1(addressing: Mapping[str, Any]) -> bool:
    for key in RETRIEVAL_ADDRESSING_REF_KEYS_V1:
        val = addressing.get(key)
        if val is not None and str(val).strip():
            return True
    return False


# Per-workload default selection caps (policy floor; Step 13 may override via policy pack).
_DEFAULT_CAPS_BASE_V1: Final[dict[str, int]] = {
    "max_hits": 100,
    "max_chronology_rows": 500,
    "max_edges": 200,
    "max_lineage_hops": 64,
}

RETRIEVAL_WORKLOAD_CLASS_DEFAULT_CAPS_V1: Final[dict[str, dict[str, int]]] = {
    "execution_continuity": {"max_hits": 1, "max_chronology_rows": 50, "max_edges": 20, "max_lineage_hops": 16},
    "chronology_window": {"max_hits": 100, "max_chronology_rows": 500, "max_edges": 50, "max_lineage_hops": 32},
    "ownership_continuity": {"max_hits": 200, "max_chronology_rows": 100, "max_edges": 200, "max_lineage_hops": 32},
    "causal_chain": {"max_hits": 1, "max_chronology_rows": 200, "max_edges": 100, "max_lineage_hops": 32},
    "causal_edge": {"max_hits": 1, "max_chronology_rows": 50, "max_edges": 1, "max_lineage_hops": 16},
    "degradation_survey": {"max_hits": 500, "max_chronology_rows": 500, "max_edges": 200, "max_lineage_hops": 32},
    "dependency_propagation": {"max_hits": 200, "max_chronology_rows": 200, "max_edges": 200, "max_lineage_hops": 32},
    "replay_divergence": {"max_hits": 10, "max_chronology_rows": 200, "max_edges": 50, "max_lineage_hops": 32},
    "escalation": {"max_hits": 100, "max_chronology_rows": 100, "max_edges": 100, "max_lineage_hops": 32},
    "traversal_lineage": {"max_hits": 100, "max_chronology_rows": 100, "max_edges": 200, "max_lineage_hops": 64},
    "replay_equivalence": {"max_hits": 2, "max_chronology_rows": 200, "max_edges": 50, "max_lineage_hops": 32},
    "lineage_explorer": {"max_hits": 64, "max_chronology_rows": 100, "max_edges": 50, "max_lineage_hops": 64},
    "continuity_topology": {"max_hits": 500, "max_chronology_rows": 100, "max_edges": 500, "max_lineage_hops": 32},
    "materialization_as_of": {"max_hits": 100, "max_chronology_rows": 500, "max_edges": 100, "max_lineage_hops": 32},
}

RETRIEVAL_WORKLOAD_CLASS_METADATA_V1: Final[dict[str, dict[str, str]]] = {
    "execution_continuity": {
        "purpose": "Materialization + chronology state at anchor",
        "typical_upstream": "TCRE job / mat id",
    },
    "chronology_window": {
        "purpose": "Half-open interval of chronology receipts",
        "typical_upstream": "chronology_window_ref",
    },
    "ownership_continuity": {
        "purpose": "Org entity + authoritative link neighborhood",
        "typical_upstream": "Phase 04 graph",
    },
    "causal_chain": {
        "purpose": "Deterministic chain by causal_chain_id",
        "typical_upstream": "TCRE",
    },
    "causal_edge": {
        "purpose": "Single tcre_causal_edge_id + evidence",
        "typical_upstream": "TCRE",
    },
    "degradation_survey": {
        "purpose": "CD-* / RD-* rollup for scope",
        "typical_upstream": "TCRE + retrieval",
    },
    "dependency_propagation": {
        "purpose": "Escalation/blocker edges from policy rows",
        "typical_upstream": "TCRE",
    },
    "replay_divergence": {
        "purpose": "Twin job diff / equivalence failure",
        "typical_upstream": "TCRE RUNTIME-02",
    },
    "escalation": {
        "purpose": "Coordination escalation edges (bounded)",
        "typical_upstream": "TCRE",
    },
    "traversal_lineage": {
        "purpose": "Walk receipt + hop lineage",
        "typical_upstream": "OCTS",
    },
    "replay_equivalence": {
        "purpose": "Double-run retrieval proof",
        "typical_upstream": "Retrieval + TCRE",
    },
    "lineage_explorer": {
        "purpose": "Artifact lineage chain terminal→root",
        "typical_upstream": "Phase 07 lineage",
    },
    "continuity_topology": {
        "purpose": "Continuity graph projection snapshot",
        "typical_upstream": "Phase 07 continuity",
    },
    "materialization_as_of": {
        "purpose": "Canonical + chronology at t_as_of",
        "typical_upstream": "Phase 03 + TCRE",
    },
}

# Intent restrictions per workload (empty set = all intents allowed).
_REPLAY_PROOF_INTENTS_V1: Final[frozenset[str]] = frozenset({"prove", "diff", "audit"})
_SINGLE_HIT_INTENTS_V1: Final[frozenset[str]] = frozenset({"inspect"})

RETRIEVAL_WORKLOAD_ALLOWED_INTENTS_V1: Final[dict[str, frozenset[str]]] = {
    "replay_equivalence": _REPLAY_PROOF_INTENTS_V1,
    "replay_divergence": _REPLAY_PROOF_INTENTS_V1,
    "causal_edge": _SINGLE_HIT_INTENTS_V1 | frozenset({"audit", "prove"}),
}


class RetrievalQueryContractError(ValueError):
    """Raised when workload class or intent violates the query contract."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def normalize_workload_class_v1(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def normalize_intent_v1(value: str) -> str:
    return value.strip().lower()


def validate_retrieval_workload_class_v1(workload_class: str) -> str:
    """Return normalized workload class or raise (**RET-QC-01**)."""
    norm = normalize_workload_class_v1(workload_class)
    if norm not in RETRIEVAL_WORKLOAD_CLASSES_V1:
        allowed = ", ".join(sorted(RETRIEVAL_WORKLOAD_CLASSES_V1))
        raise RetrievalQueryContractError(
            "unknown_workload_class",
            detail={"workload_class": workload_class, "allowed": allowed},
        )
    return norm


def validate_retrieval_intent_v1(intent: str) -> str:
    """Return normalized intent or raise."""
    norm = normalize_intent_v1(intent)
    if norm not in RETRIEVAL_INTENT_CLASSES_V1:
        allowed = ", ".join(sorted(RETRIEVAL_INTENT_CLASSES_V1))
        raise RetrievalQueryContractError(
            "unknown_intent",
            detail={"intent": intent, "allowed": allowed},
        )
    return norm


def validate_intent_allowed_for_workload_v1(*, workload_class: str, intent: str) -> None:
    wl = validate_retrieval_workload_class_v1(workload_class)
    it = validate_retrieval_intent_v1(intent)
    allowed = RETRIEVAL_WORKLOAD_ALLOWED_INTENTS_V1.get(wl)
    if allowed is not None and it not in allowed:
        raise RetrievalQueryContractError(
            "intent_not_allowed_for_workload",
            detail={
                "workload_class": wl,
                "intent": it,
                "allowed_intents": sorted(allowed),
            },
        )


def selection_policy_caps_for_workload_v1(workload_class: str) -> dict[str, int]:
    """Per-class policy caps (§6 defaults specialized by workload)."""
    wl = validate_retrieval_workload_class_v1(workload_class)
    caps = dict(_DEFAULT_CAPS_BASE_V1)
    caps.update(RETRIEVAL_WORKLOAD_CLASS_DEFAULT_CAPS_V1.get(wl, {}))
    return caps


def build_retrieval_workload_class_catalog_v1() -> list[dict[str, Any]]:
    """Admin query-debugger workload picker."""
    rows: list[dict[str, Any]] = []
    for wl in sorted(RETRIEVAL_WORKLOAD_CLASSES_V1):
        meta = RETRIEVAL_WORKLOAD_CLASS_METADATA_V1.get(wl, {})
        allowed_intents = RETRIEVAL_WORKLOAD_ALLOWED_INTENTS_V1.get(wl, RETRIEVAL_INTENT_CLASSES_V1)
        rows.append(
            {
                "workload_class": wl,
                "purpose": meta.get("purpose", ""),
                "typical_upstream": meta.get("typical_upstream", ""),
                "allowed_intents": sorted(allowed_intents),
                "default_selection_caps": selection_policy_caps_for_workload_v1(wl),
            }
        )
    return rows


def build_retrieval_intent_class_catalog_v1() -> list[dict[str, Any]]:
    return [
        {"intent": "inspect", "meaning": "Single-address lookup — max 1 primary hit"},
        {"intent": "enumerate", "meaning": "Bounded list in deterministic order"},
        {"intent": "prove", "meaning": "Emit equivalence / replay receipt set"},
        {"intent": "audit", "meaning": "Omission-forward — list exclusions explicitly"},
        {"intent": "diff", "meaning": "Structural compare two pinned scopes (replay twin)"},
    ]


def build_retrieval_query_contract_catalog_v1() -> dict[str, Any]:
    """Full §1–2 contract catalog for admin / observability."""
    return {
        "phase07_query_contract_runtime_schema_version": PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION,
        "envelope_schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
        "workload_classes": build_retrieval_workload_class_catalog_v1(),
        "intent_classes": build_retrieval_intent_class_catalog_v1(),
        "rd_addressing_unresolved": RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
        "queries_by_workload_metric": "retrieval_queries_by_workload_total",
    }


def build_retrieval_query_replay_identity_scope_v1(
    *,
    workload_class: str,
    intent: str,
    tenant_id: str | None = None,
    extra_pins: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pins workload + intent into replay identity scope (canonical scope in Step 8)."""
    wl = validate_retrieval_workload_class_v1(workload_class)
    it = validate_retrieval_intent_v1(intent)
    validate_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    scope: dict[str, Any] = {
        PHASE07_REPLAY_IDENTITY_FIELD_V1: {
            "workload_class": wl,
            "intent": it,
        },
        "workload_class": wl,
        "intent": it,
    }
    if tenant_id:
        scope["tenant_id"] = tenant_id
    if extra_pins:
        scope["pins"] = dict(extra_pins)
    return scope


def enforce_retrieval_query_workload_and_intent_v1(body: Mapping[str, Any]) -> tuple[str, str]:
    """Validate envelope workload + intent; return normalized pair."""
    raw_wl = body.get("workload_class")
    raw_it = body.get("intent")
    if raw_wl is None or raw_it is None:
        raise RetrievalQueryContractError(
            "workload_class_and_intent_required",
            detail={"workload_class": raw_wl, "intent": raw_it},
        )
    wl = validate_retrieval_workload_class_v1(str(raw_wl))
    it = validate_retrieval_intent_v1(str(raw_it))
    validate_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    return wl, it


def resolve_retrieval_workload_and_intent_v1(
    body: Mapping[str, Any],
    *,
    default_workload_class: str = "causal_chain",
    default_intent: str = "inspect",
) -> tuple[str, str]:
    """Resolve workload/intent from body, applying defaults for minimal admin lookup paths."""
    wl_raw = body.get("workload_class")
    it_raw = body.get("intent")
    if wl_raw is not None and it_raw is not None:
        return enforce_retrieval_query_workload_and_intent_v1(body)
    wl = validate_retrieval_workload_class_v1(str(wl_raw or default_workload_class))
    it = validate_retrieval_intent_v1(str(it_raw or default_intent))
    validate_intent_allowed_for_workload_v1(workload_class=wl, intent=it)
    return wl, it


def verify_gp07_qc01_workload_intent_registry_static() -> dict[str, Any]:
    """``G-P07-QC-01`` — closed registry matches doctrine §1–2."""
    errors: list[str] = []
    if len(RETRIEVAL_WORKLOAD_CLASSES_V1) != 14:
        errors.append(f"workload_class_count:{len(RETRIEVAL_WORKLOAD_CLASSES_V1)}")
    if len(RETRIEVAL_INTENT_CLASSES_V1) != 5:
        errors.append(f"intent_class_count:{len(RETRIEVAL_INTENT_CLASSES_V1)}")
    for wl in RETRIEVAL_WORKLOAD_CLASSES_V1:
        if wl not in RETRIEVAL_WORKLOAD_CLASS_METADATA_V1:
            errors.append(f"missing_metadata:{wl}")
        if wl not in RETRIEVAL_WORKLOAD_CLASS_DEFAULT_CAPS_V1:
            errors.append(f"missing_caps:{wl}")
    try:
        validate_retrieval_workload_class_v1("causal_chain")
        validate_retrieval_intent_v1("inspect")
        validate_intent_allowed_for_workload_v1(workload_class="causal_chain", intent="inspect")
    except RetrievalQueryContractError as exc:
        errors.append(f"unexpected_rejection_legal_pair:{exc}")
    try:
        validate_retrieval_workload_class_v1("not_a_real_workload")
    except RetrievalQueryContractError:
        pass
    else:
        errors.append("expected_unknown_workload_rejection")
    try:
        validate_intent_allowed_for_workload_v1(
            workload_class="replay_equivalence", intent="enumerate"
        )
    except RetrievalQueryContractError:
        pass
    else:
        errors.append("expected_intent_workload_mismatch_rejection")
    cat = build_retrieval_query_contract_catalog_v1()
    if len(cat["workload_classes"]) != 14:
        errors.append("catalog_workload_rows")
    passed = len(errors) == 0
    return {
        "id": GP07_QC01_GATE_ID_V1,
        "name": "retrieval_workload_intent_registry",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase07_query_contract_runtime_schema_version": (
                PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }

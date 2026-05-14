"""Phase 05 P05-03 — anti-goals / cognition leakage guards (pure validators).

Normative: ``DOCS/cortex/05-traversal/phase-05-anti-goals-doctrine.md``,
``DOCS/cortex/05-traversal/phase-05-traversal-vs-reasoning-doctrine.md`` (FS-TVR-*).
"""

from __future__ import annotations

import copy
import uuid
from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.identity.projection_export import (
    ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
    ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
    verify_org_graph_export_forbidden_leakage,
)

ANTI_GOALS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

# Lowercase exact keys forbidden in any canonical walk / hop JSON object (FS-AG-01, FS-TVR-01).
_FORBIDDEN_COGNITION_KEYS_LOWER: Final[frozenset[str]] = frozenset(
    {
        "insight",
        "insights",
        "recommendation",
        "recommendations",
        "root_cause",
        "summary",
        "summaries",
        "narrative",
        "narratives",
        "relevance_score",
        "confidence_narrative",
        "llm_output",
        "llm_response",
        "embedding",
        "embeddings",
        "notes",
        "edge_explanation",
        "why_this_path",
        "explanation",
        "conclusion",
        "conclusions",
        "scoring",
        "utility_score",
        "business_value",
        "importance",
        "semantic_score",
        "ranking",
        "rankings",
        "causal_window",
        "likely_next_event_time",
        "estimated_delay",
        "most_relevant",
    }
)

# If any object key (lowercased) contains one of these substrings, reject (AG-02 / smuggling).
_FORBIDDEN_KEY_SUBSTRINGS_LOWER: Final[tuple[str, ...]] = (
    "insight",
    "narrative",
    "recommendation",
    "relevance_score",
    "root_cause",
    "llm",
    "embedding",
)


class CognitionLeakageError(ValueError):
    """Raised when a canonical OCTS JSON body contains forbidden cognition-shaped keys."""


def _key_violations(key: str) -> list[str]:
    lk = key.lower()
    out: list[str] = []
    if lk.startswith("ext_"):
        out.append("forbidden_dynamic_ext_prefix")
    if lk in _FORBIDDEN_COGNITION_KEYS_LOWER:
        out.append("forbidden_exact_cognition_key")
    for sub in _FORBIDDEN_KEY_SUBSTRINGS_LOWER:
        if sub in lk:
            out.append(f"forbidden_key_substring:{sub}")
            break
    return out


def list_forbidden_cognition_key_violations(obj: Any, *, path: str = "") -> list[str]:
    """Return human-readable violation paths for **G-P05-ANTI-01** style scans."""
    violations: list[str] = []
    if isinstance(obj, Mapping):
        for raw_k, v in obj.items():
            if not isinstance(raw_k, str):
                continue
            prefix = f"{path}.{raw_k}" if path else raw_k
            for reason in _key_violations(raw_k):
                violations.append(f"{prefix}:{reason}")
            violations.extend(list_forbidden_cognition_key_violations(v, path=prefix))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            violations.extend(list_forbidden_cognition_key_violations(item, path=f"{path}[{i}]"))
    return violations


def validate_octs_canonical_json_mapping_no_cognition_leakage(body: Mapping[str, Any]) -> None:
    """RULE AG / FS-AG-01 — reject canonical bodies that smuggle cognition keys.

    Raises:
        CognitionLeakageError: when ``list_forbidden_cognition_key_violations`` is non-empty.
    """
    hits = list_forbidden_cognition_key_violations(body)
    if hits:
        msg = "cognition leakage in canonical JSON: " + "; ".join(hits[:12])
        if len(hits) > 12:
            msg += f"; …(+{len(hits) - 12} more)"
        raise CognitionLeakageError(msg)


def verify_gp05_anti01_forbidden_cognition_keys_static() -> dict[str, Any]:
    """G-P05-ANTI-01 — pattern scan on representative canonical bodies."""
    errors: list[str] = []

    illegal = {"diagnostics": {"ok": True}, "insight": "blocked"}
    if not list_forbidden_cognition_key_violations(illegal):
        errors.append("expected_violation_for_insight_key")

    illegal_nested = {"walk": {"hop_receipts": [{"hop_sequence": 0, "narrative": "x"}]}}
    if not list_forbidden_cognition_key_violations(illegal_nested):
        errors.append("expected_violation_for_nested_narrative")

    ext_dyn = {"ext_foo": 1}
    if not list_forbidden_cognition_key_violations(ext_dyn):
        errors.append("expected_violation_for_ext_prefix")

    legal = {
        "diagnostics": {"termination_reason": "budget_exhausted", "edges_visited": 42},
        "walk_result_hash": "sha256:00",
        "hop_receipts": [],
    }
    if list_forbidden_cognition_key_violations(legal):
        errors.append(
            f"unexpected_violations_on_legal_stub:{list_forbidden_cognition_key_violations(legal)}"
        )

    try:
        validate_octs_canonical_json_mapping_no_cognition_leakage(legal)
    except CognitionLeakageError as exc:
        errors.append(f"unexpected_raise_on_legal_stub:{exc}")

    passed = len(errors) == 0
    return {
        "id": "G-P05-ANTI-01",
        "name": "forbidden_cognition_keys",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "anti_goals_runtime_schema_version": ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }


def verify_gp05_anti02_traversal_ingress_no_phase03_tokens_static() -> dict[str, Any]:
    """G-P05-ANTI-02 — reuse P04 export forbidden-token scan on traversal ingress shape."""
    errors: list[str] = []
    minimal: dict[str, Any] = {
        "projection_schema_version": ORG_GRAPH_PROJECTION_SCHEMA_VERSION,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [],
    }
    leaks = verify_org_graph_export_forbidden_leakage(minimal)
    if leaks:
        errors.append(f"minimal_clean_projection_leaked:{leaks}")

    poisoned = copy.deepcopy(minimal)
    poisoned["nodes"][0]["entity_kind"] = "x cortex_canonical_transform y"
    poison_hits = verify_org_graph_export_forbidden_leakage(poisoned)
    if not poison_hits:
        errors.append("expected_poisoned_projection_to_fail_phase03_token_scan")

    passed = len(errors) == 0
    return {
        "id": "G-P05-ANTI-02",
        "name": "traversal_ingress_no_phase03_topology_tokens",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "anti_goals_runtime_schema_version": ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
            "errors": errors,
        },
    }

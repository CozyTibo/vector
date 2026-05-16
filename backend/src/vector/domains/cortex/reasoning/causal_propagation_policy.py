"""Phase 06 P06-16 — escalation / dependency / blocker propagation (policy tables only).

Normative:
``DOCS/cortex/reasoning/causal-reconstruction-doctrine.md`` §4,
``DOCS/cortex/reasoning/reasoning-policy-pack-v1.md`` (``merge_rules_coordination_edges``),
``DOCS/cortex/reasoning/tcre-causal-edge-registry-v1.md`` (**M‑INJ‑1** merge discipline).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_legality import ChronologyLegalityError, load_default_reasoning_policy_pack
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
    TCRE_CAUSAL_EDGE_KINDS,
    TCRE_KINDS_ALLOWING_COORDINATION_SENTINEL_ONLY,
    ExecutionCausalityConstraintError,
)

PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PROPAGATION_RULE_TABLE_V1_KEY: Final[str] = "propagation_rule_table_v1"


class CausalPropagationPolicyError(ValueError):
    """Fail-closed policy-scoped propagation / merge rule tables."""


def validate_merge_rules_coordination_edges_v1(policy: Mapping[str, Any]) -> None:
    """``reasoning-policy-pack-v1.md`` — ``merge_rules_coordination_edges`` rows are typed + id-stable."""
    raw = policy.get("merge_rules_coordination_edges")
    if raw is None:
        raise CausalPropagationPolicyError("policy.merge_rules_coordination_edges must be present (use [])")
    if not isinstance(raw, list):
        raise CausalPropagationPolicyError("merge_rules_coordination_edges must be a list")
    seen_merge_ids: set[str] = set()
    for i, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise CausalPropagationPolicyError(f"merge_rules_coordination_edges[{i}] must be a mapping")
        mid = row.get("merge_rule_id")
        if not isinstance(mid, str) or not mid.strip():
            raise CausalPropagationPolicyError(
                f"merge_rules_coordination_edges[{i}].merge_rule_id must be a non-empty string"
            )
        mid_s = mid.strip()
        if mid_s in seen_merge_ids:
            raise CausalPropagationPolicyError(f"duplicate merge_rule_id: {mid_s!r}")
        seen_merge_ids.add(mid_s)
        kind = row.get("allowed_tcre_causal_edge_kind")
        if not isinstance(kind, str) or kind not in TCRE_CAUSAL_EDGE_KINDS:
            allowed = ", ".join(sorted(TCRE_CAUSAL_EDGE_KINDS))
            raise CausalPropagationPolicyError(
                f"merge_rules_coordination_edges[{i}].allowed_tcre_causal_edge_kind invalid; "
                f"must be one of: {allowed}"
            )
        cap = row.get("max_underlying_ids")
        if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
            raise CausalPropagationPolicyError(
                f"merge_rules_coordination_edges[{i}].max_underlying_ids must be int >= 1"
            )


def validate_propagation_rule_table_v1_when_present(policy: Mapping[str, Any]) -> None:
    """Doctrine §4 — optional ``propagation_rule_table_v1`` (future table) must be policy-scoped rows."""
    if PROPAGATION_RULE_TABLE_V1_KEY not in policy:
        return
    raw = policy[PROPAGATION_RULE_TABLE_V1_KEY]
    if raw is None:
        return
    if not isinstance(raw, list):
        raise CausalPropagationPolicyError("propagation_rule_table_v1 must be a list when present")
    seen: set[str] = set()
    for i, row in enumerate(raw):
        if not isinstance(row, Mapping):
            raise CausalPropagationPolicyError(f"propagation_rule_table_v1[{i}] must be a mapping")
        rid = row.get("propagation_rule_id")
        if not isinstance(rid, str) or not rid.strip():
            raise CausalPropagationPolicyError(
                f"propagation_rule_table_v1[{i}].propagation_rule_id must be a non-empty string"
            )
        rs = rid.strip()
        if rs in seen:
            raise CausalPropagationPolicyError(f"duplicate propagation_rule_id: {rs!r}")
        seen.add(rs)


def max_underlying_coordination_edges_for_tcre_kind_v1(tcre_causal_edge_kind: str, policy: Mapping[str, Any]) -> int:
    """**M‑INJ‑1** — default **1**; max over matching ``merge_rules_coordination_edges`` rows for this TCRE kind."""
    validate_merge_rules_coordination_edges_v1(policy)
    if not isinstance(tcre_causal_edge_kind, str) or tcre_causal_edge_kind not in TCRE_CAUSAL_EDGE_KINDS:
        raise CausalPropagationPolicyError("tcre_causal_edge_kind must be a known registry literal")
    raw = policy.get("merge_rules_coordination_edges")
    assert isinstance(raw, list)
    caps = [
        int(row["max_underlying_ids"])
        for row in raw
        if isinstance(row, Mapping)
        and row.get("allowed_tcre_causal_edge_kind") == tcre_causal_edge_kind
        and isinstance(row.get("max_underlying_ids"), int)
        and not isinstance(row.get("max_underlying_ids"), bool)
    ]
    return max(caps) if caps else 1


def validate_underlying_coordination_edge_ids_propagation_v1(
    tcre_causal_edge_kind: str,
    ids: Sequence[str],
    policy: Mapping[str, Any],
) -> None:
    """Registry §4.2 + **M‑INJ‑1** with merge caps — sorted unique ids, sentinel rules, max length."""
    if not isinstance(tcre_causal_edge_kind, str) or tcre_causal_edge_kind not in TCRE_CAUSAL_EDGE_KINDS:
        raise CausalPropagationPolicyError("tcre_causal_edge_kind must be a known registry literal")
    if not isinstance(ids, list):
        raise CausalPropagationPolicyError("underlying_coordination_edge_ids must be a list")
    str_ids = [str(x) for x in ids]
    if not str_ids:
        raise CausalPropagationPolicyError("underlying_coordination_edge_ids must be non-empty")
    if not all(x.strip() for x in str_ids):
        raise CausalPropagationPolicyError("underlying_coordination_edge_ids must be non-empty strings")
    if len(set(str_ids)) != len(str_ids):
        raise CausalPropagationPolicyError("underlying_coordination_edge_ids must be unique")
    if str_ids != sorted(str_ids):
        raise CausalPropagationPolicyError(
            "underlying_coordination_edge_ids must be sorted ascending for hash stability"
        )
    sentinel_only = str_ids == [NO_COORDINATION_EDGE_SENTINEL]
    if sentinel_only and tcre_causal_edge_kind not in TCRE_KINDS_ALLOWING_COORDINATION_SENTINEL_ONLY:
        raise CausalPropagationPolicyError(
            f"tcre_causal_edge_kind {tcre_causal_edge_kind!r} may not use {NO_COORDINATION_EDGE_SENTINEL!r} alone"
        )
    if not sentinel_only and NO_COORDINATION_EDGE_SENTINEL in str_ids:
        raise CausalPropagationPolicyError(
            "underlying_coordination_edge_ids must not mix sentinel with concrete coordination edge ids"
        )
    if sentinel_only:
        return
    max_n = max_underlying_coordination_edges_for_tcre_kind_v1(tcre_causal_edge_kind, policy)
    if len(str_ids) > max_n:
        raise CausalPropagationPolicyError(
            f"underlying_coordination_edge_ids length {len(str_ids)} exceeds policy max {max_n} "
            f"for {tcre_causal_edge_kind!r}"
        )


def validate_tcre_edge_v1_stub_with_propagation_policy_v1(
    edge: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> None:
    """Single reducer entry: **P06-03** stub with **P06-16** merge caps from the active policy pack."""
    from vector.domains.cortex.reasoning.execution_causality_constraints import validate_tcre_edge_v1_stub

    kind = edge.get("tcre_causal_edge_kind")
    if not isinstance(kind, str) or kind not in TCRE_CAUSAL_EDGE_KINDS:
        raise CausalPropagationPolicyError("tcre_causal_edge_kind must be a known registry literal")
    max_n = max_underlying_coordination_edges_for_tcre_kind_v1(kind, policy)
    try:
        validate_tcre_edge_v1_stub(edge, max_concrete_coordination_edges=max_n)
    except ExecutionCausalityConstraintError as exc:
        raise CausalPropagationPolicyError(str(exc)) from exc


def verify_gp06_edp01_default_pack_merge_rules_static() -> dict[str, Any]:
    """Static — default fixture has lawful ``merge_rules_coordination_edges`` (empty list)."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack()
        validate_merge_rules_coordination_edges_v1(pack)
        validate_propagation_rule_table_v1_when_present(pack)
    except (CausalPropagationPolicyError, ChronologyLegalityError, OSError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-16-edp-default-merge",
        "name": "gp06_edp01_default_pack_merge_rules",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_propagation_policy_runtime_schema_version": (
                PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_edp02_merge_cap_multi_id_oracle_static() -> dict[str, Any]:
    """Static — merge rule raises max underlying ids for coordination-derived kinds."""
    errors: list[str] = []
    policy: dict[str, Any] = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "merge_escalation_bundle_v1",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_escalation",
                "max_underlying_ids": 3,
            }
        ]
    }
    try:
        if max_underlying_coordination_edges_for_tcre_kind_v1("tcre_coordination_escalation", policy) != 3:
            errors.append("max_cap_not_three")
        validate_underlying_coordination_edge_ids_propagation_v1(
            "tcre_coordination_escalation",
            ["e-a", "e-b", "e-c"],
            policy,
        )
    except CausalPropagationPolicyError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-16-edp-merge-cap",
        "name": "gp06_edp02_merge_cap_multi_id_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_propagation_policy_runtime_schema_version": (
                PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_edp03_default_stub_conflict_with_multi_id_resolved_static() -> dict[str, Any]:
    """Static — combined validator accepts multi-id when merge policy allows it."""
    errors: list[str] = []
    policy: dict[str, Any] = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "merge_dep_v1",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_dependency",
                "max_underlying_ids": 2,
            }
        ]
    }
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["c1", "c2"],
        "derivation_rule_id": "TCRE_MAP_depends_on_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 9}],
    }
    try:
        validate_tcre_edge_v1_stub_with_propagation_policy_v1(edge, policy)
    except CausalPropagationPolicyError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-16-edp-stub-bridge",
        "name": "gp06_edp03_stub_conflict_with_multi_id_resolved",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_causal_propagation_policy_runtime_schema_version": (
                PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }

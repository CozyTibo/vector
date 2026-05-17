"""Phase 07 P07-19 — degradation taxonomy + propagation (**RET-DEG-01/02**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-degradation-taxonomy.md``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    GP07_DEG01_GATE_ID_V1,
    RETRIEVAL_BOUNDED_CAPS_SPEC_REF_V1,
    RETRIEVAL_RD_CODES_REGISTRY_V1,
    RETRIEVAL_SUBSTRATE_HEALTH_STATES_V1,
    RetrievalBoundedCapsError,
    build_retrieval_omission_histogram_v1,
    build_retrieval_policy_pack_default_v1,
    classify_substrate_health_v1,
    normalize_retrieval_omission_law_row_v1,
    normalize_retrieval_omission_law_rows_v1,
    record_retrieval_omissions_to_histogram_v1,
    retrieval_policy_pack_digest_v1,
    validate_rd_code_registered_v1,
)

PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_DEG02_GATE_ID_V1: Final[str] = "G-P07-DEG-02"

GP07_DEG03_GATE_ID_V1: Final[str] = "G-P07-DEG-03"

RETRIEVAL_DEGRADATION_TAXONOMY_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-degradation-taxonomy.md"
)

# Substrate propagation table (doctrine § degradation propagation).
RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "from_stage": "canonical",
        "trigger_class": "canonical_backlog_unmaterialized",
        "to_stage": "retrieval",
        "consequence_code": "RD-TCRE-GAP",
    },
    {
        "from_stage": "identity",
        "trigger_class": "replay_conflicted_identity",
        "to_stage": "retrieval",
        "consequence_code": "RD-REPLAY-UNSAFE",
    },
    {
        "from_stage": "graph",
        "trigger_class": "orphan_artifacts",
        "to_stage": "retrieval",
        "consequence_code": "RD-GRAPH-ORPHAN",
    },
    {
        "from_stage": "graph",
        "trigger_class": "pending_link_candidates",
        "to_stage": "retrieval",
        "consequence_code": "RD-TRAVERSAL-BLOCKED",
    },
    {
        "from_stage": "traversal",
        "trigger_class": "traversal_never_executed",
        "to_stage": "retrieval",
        "consequence_code": "RD-TRAVERSAL-IDLE",
    },
    {
        "from_stage": "tcre",
        "trigger_class": "reconstruction_coverage_gap",
        "to_stage": "retrieval",
        "consequence_code": "RD-TCRE-GAP",
    },
)

RETRIEVAL_UPSTREAM_TRIGGER_TO_RD_V1: Final[dict[str, str]] = {
    row["trigger_class"]: row["consequence_code"] for row in RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1
}

# Lawful missing-data omission semantics (doctrine § lawful missing-data handling).
RETRIEVAL_LAWFUL_MISSING_DATA_CASES_V1: Final[tuple[dict[str, str], ...]] = (
    {
        "case": "artifact_never_existed",
        "behavior": "emit_registered_rd_gap",
        "omission_semantics": "omitted_upstream_gap",
    },
    {
        "case": "artifact_exists_legality_forbids",
        "behavior": "emit_omitted_legality",
        "omission_semantics": "omitted_legality",
    },
    {
        "case": "exploration_in_authoritative_query",
        "behavior": "emit_omitted_exploration_partition",
        "omission_semantics": "omitted_exploration_partition",
    },
)


class RetrievalDegradationTaxonomyError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def map_upstream_trigger_to_rd_code_v1(trigger: str) -> str | None:
    """Map substrate trigger class → closed ``RD-*`` code."""
    return RETRIEVAL_UPSTREAM_TRIGGER_TO_RD_V1.get(str(trigger).strip())


def propagate_upstream_triggers_to_rd_omissions_v1(
    upstream_triggers: Mapping[str, Any] | None,
    *,
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build validated omission rows from upstream triggers + policy propagation table."""
    pack_body = pack or build_retrieval_policy_pack_default_v1()
    rows: list[dict[str, Any]] = []
    triggers = dict(upstream_triggers or {})
    seen_rd: set[str] = set()
    for rule in pack_body.get("degradation_propagation") or []:
        if not isinstance(rule, dict):
            continue
        trigger_class = str(rule.get("trigger_class") or "")
        if not trigger_class or not triggers.get(trigger_class):
            continue
        rd = str(rule.get("consequence_code") or "")
        validate_rd_code_registered_v1(rd)
        if rd in seen_rd:
            continue
        seen_rd.add(rd)
        rows.append(
            {
                "retrieval_omission_class": rd,
                "upstream_trigger": trigger_class,
                "from_stage": str(rule.get("from_stage") or ""),
            }
        )
    for trigger, active in triggers.items():
        if not active:
            continue
        mapped_rd = map_upstream_trigger_to_rd_code_v1(str(trigger))
        if mapped_rd is None or mapped_rd in seen_rd:
            continue
        seen_rd.add(mapped_rd)
        rows.append(
            {
                "retrieval_omission_class": mapped_rd,
                "upstream_trigger": str(trigger),
            }
        )
    return normalize_retrieval_omission_law_rows_v1(rows)


def build_degradation_propagation_chain_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Human-readable propagation chain (Phase 06 completeness style)."""
    _ = pack
    triggers = upstream_triggers if isinstance(upstream_triggers, dict) else {}
    chain: list[dict[str, str]] = []
    for rule in RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1:
        trigger_class = rule["trigger_class"]
        if not triggers.get(trigger_class):
            continue
        consequence = rule["consequence_code"]
        chain.append(
            {
                "from_stage": rule["from_stage"],
                "to_stage": rule["to_stage"],
                "trigger_class": trigger_class,
                "consequence_code": consequence,
                "explanation_summary": (
                    f"{rule['from_stage']} trigger {trigger_class} propagates to "
                    f"{rule['to_stage']} as {consequence}."
                ),
            }
        )
    return chain


def normalize_retrieval_hit_lookup_multiset_v1(
    hits: Sequence[Mapping[str, Any]],
) -> Counter[str]:
    ids: list[str] = []
    for hit in hits:
        lid = str(hit.get("retrieval_lookup_id") or "").strip()
        if lid:
            ids.append(lid)
    return Counter(ids)


def normalize_retrieval_omission_class_multiset_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> Counter[str]:
    codes: list[str] = []
    for row in omissions:
        rd = str(row.get("retrieval_omission_class") or row.get("rd_code") or "").strip()
        if rd:
            codes.append(rd)
    return Counter(codes)


def validate_retrieval_omission_multiset_monotonic_extension_v1(
    before_omissions: Sequence[Mapping[str, Any]],
    after_omissions: Sequence[Mapping[str, Any]],
) -> None:
    """**RET-DEG-02** — omission multiset must not regress when upstream grows."""
    before = normalize_retrieval_omission_class_multiset_v1(before_omissions)
    after = normalize_retrieval_omission_class_multiset_v1(after_omissions)
    for code, count in before.items():
        if after[code] < count:
            raise RetrievalDegradationTaxonomyError(
                "retrieval_omission_multiset_regression",
                detail={"code": code, "before": count, "after": after[code]},
            )


def validate_retrieval_hit_multiset_monotonic_extension_v1(
    before_hits: Sequence[Mapping[str, Any]],
    after_hits: Sequence[Mapping[str, Any]],
) -> None:
    """**RET-DEG-02** — authoritative hit multiset must not shrink without policy change."""
    before = normalize_retrieval_hit_lookup_multiset_v1(before_hits)
    after = normalize_retrieval_hit_lookup_multiset_v1(after_hits)
    for lookup_id, count in before.items():
        if after[lookup_id] < count:
            raise RetrievalDegradationTaxonomyError(
                "retrieval_hit_multiset_regression",
                detail={"retrieval_lookup_id": lookup_id, "before": count, "after": after[lookup_id]},
            )


def build_lawful_missing_data_omission_v1(
    *,
    case: str,
    rd_code: str | None = None,
    upstream_trigger: str = "",
) -> dict[str, Any]:
    """Lawful missing-data rows must use registered ``RD-*`` when applicable."""
    case_row = next((c for c in RETRIEVAL_LAWFUL_MISSING_DATA_CASES_V1 if c["case"] == case), None)
    if case_row is None:
        raise RetrievalDegradationTaxonomyError(
            "unknown_lawful_missing_data_case",
            detail={"case": case},
        )
    if case == "artifact_never_existed":
        if not rd_code:
            raise RetrievalDegradationTaxonomyError("rd_code_required_for_gap")
        validate_rd_code_registered_v1(rd_code)
        return normalize_retrieval_omission_law_row_v1(
            {
                "retrieval_omission_class": rd_code,
                "upstream_trigger": upstream_trigger or "artifact_never_existed",
                "omission_semantics": case_row["omission_semantics"],
            }
        )
    return {
        "retrieval_omission_class": rd_code or "RD-LINEAGE-GAP",
        "upstream_trigger": upstream_trigger or case,
        "omission_semantics": case_row["omission_semantics"],
    }


def build_retrieval_rd_rollup_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """``RD-*`` rollup for observability (per-code counts + total)."""
    multiset = normalize_retrieval_omission_class_multiset_v1(omissions)
    by_code = {code: int(count) for code, count in sorted(multiset.items())}
    return {
        "rd_code_counts": by_code,
        "rd_code_total": sum(by_code.values()),
        "rd_codes_present": sorted(by_code.keys()),
        "retrieval_omission_histogram": build_retrieval_omission_histogram_v1(),
    }


def _assert_rd_registered_v1(code: str) -> None:
    try:
        validate_rd_code_registered_v1(code)
    except RetrievalBoundedCapsError as exc:
        raise RetrievalDegradationTaxonomyError(
            "unknown_retrieval_omission_class",
            detail={"retrieval_omission_class": code, "bounded_caps": exc.code},
        ) from exc


def validate_retrieval_completeness_uses_rd_registry_v1(
    completeness_body: Mapping[str, Any],
) -> None:
    """Completeness / substrate projections MUST reference only registered ``RD-*`` codes."""
    omissions = completeness_body.get("omission_classes")
    if isinstance(omissions, dict):
        for code in omissions:
            _assert_rd_registered_v1(str(code))
    rd_rows = completeness_body.get("rd_rows")
    if isinstance(rd_rows, list):
        for row in rd_rows:
            if isinstance(row, dict):
                rd = str(row.get("retrieval_omission_class") or row.get("rd_code") or "")
                if rd:
                    _assert_rd_registered_v1(rd)
    propagation = completeness_body.get("degradation_propagation") or completeness_body.get(
        "propagation_chain"
    )
    if isinstance(propagation, list):
        for edge in propagation:
            if not isinstance(edge, dict):
                continue
            consequence = str(
                edge.get("consequence_code") or edge.get("propagation_consequence") or ""
            )
            if consequence:
                _assert_rd_registered_v1(consequence)


def build_retrieval_degradation_topology_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin degradation topology — registry, propagation table, health states, rollup."""
    pack = build_retrieval_policy_pack_default_v1()
    return {
        "tenant_id": tenant_id or "",
        "retrieval_degradation_taxonomy_runtime_schema_version": (
            PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION
        ),
        "gate_ids": [GP07_DEG01_GATE_ID_V1, GP07_DEG02_GATE_ID_V1, GP07_DEG03_GATE_ID_V1],
        "retrieval_policy_pack_id": pack.get("retrieval_policy_pack_id"),
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(pack),
        "rd_codes_registry": sorted(RETRIEVAL_RD_CODES_REGISTRY_V1),
        "substrate_propagation_table": list(RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1),
        "policy_pack_degradation_propagation": list(pack.get("degradation_propagation") or []),
        "upstream_trigger_to_rd": dict(RETRIEVAL_UPSTREAM_TRIGGER_TO_RD_V1),
        "substrate_health_states": sorted(RETRIEVAL_SUBSTRATE_HEALTH_STATES_V1),
        "lawful_missing_data_cases": list(RETRIEVAL_LAWFUL_MISSING_DATA_CASES_V1),
        "omission_histogram": build_retrieval_omission_histogram_v1(),
        "rules": [
            {"id": "RET-DEG-01", "text": "Closed RD-* registry; amendment + golden required"},
            {
                "id": "RET-DEG-02",
                "text": "Upstream growth must not remove hits or regress omission multiset",
            },
        ],
        "doctrine_anchors": [
            RETRIEVAL_DEGRADATION_TAXONOMY_SPEC_REF_V1,
            RETRIEVAL_BOUNDED_CAPS_SPEC_REF_V1,
        ],
    }


def apply_retrieval_degradation_taxonomy_to_query_result_v1(
    result: dict[str, Any],
    *,
    upstream_triggers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Attach propagation chain, RD rollup, and completeness registry validation."""
    omissions = result.get("omissions") or result.get("retrieval_omission_rows") or []
    if not isinstance(omissions, list):
        omissions = []
    result["degradation_propagation_chain"] = build_degradation_propagation_chain_v1(
        upstream_triggers=upstream_triggers,
    )
    rollup = build_retrieval_rd_rollup_v1(omissions)
    result["retrieval_rd_rollup"] = rollup
    result["retrieval_omission_histogram"] = rollup.get("retrieval_omission_histogram") or {}
    result["substrate_health_state"] = classify_substrate_health_v1(
        omissions=omissions,
        retrieval_legality_class=str(result.get("retrieval_legality_class") or ""),
    )
    completeness_probe = {
        "omission_classes": result["retrieval_rd_rollup"].get("rd_code_counts"),
        "rd_rows": omissions,
        "propagation_chain": result["degradation_propagation_chain"],
    }
    validate_retrieval_completeness_uses_rd_registry_v1(completeness_probe)
    record_retrieval_omissions_to_histogram_v1(omissions)
    return result


def _deg_tax_meta(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase07_retrieval_degradation_taxonomy_runtime_schema_version": (
                PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp07_deg02_monotonicity_static() -> dict[str, Any]:
    """**RET-DEG-02** — hit and omission multiset monotonicity oracles."""
    errors: list[str] = []
    hits_a = [{"retrieval_lookup_id": "sha256:" + "a" * 64}]
    hits_b = hits_a + [{"retrieval_lookup_id": "sha256:" + "b" * 64}]
    try:
        validate_retrieval_hit_multiset_monotonic_extension_v1(hits_a, hits_b)
    except RetrievalDegradationTaxonomyError as exc:
        errors.append(f"hit_growth_should_pass:{exc}")
    try:
        validate_retrieval_hit_multiset_monotonic_extension_v1(hits_b, hits_a)
    except RetrievalDegradationTaxonomyError:
        pass
    else:
        errors.append("hit_shrink_should_fail")
    om_a = [{"retrieval_omission_class": "RD-CAP-HITS"}]
    om_b = om_a + [{"retrieval_omission_class": "RD-TCRE-GAP"}]
    try:
        validate_retrieval_omission_multiset_monotonic_extension_v1(om_a, om_b)
    except RetrievalDegradationTaxonomyError as exc:
        errors.append(f"omission_growth_should_pass:{exc}")
    try:
        validate_retrieval_omission_multiset_monotonic_extension_v1(om_b, om_a)
    except RetrievalDegradationTaxonomyError:
        pass
    else:
        errors.append("omission_shrink_should_fail")
    return _deg_tax_meta(GP07_DEG02_GATE_ID_V1, "gp07_deg02_monotonicity", errors)


def verify_gp07_deg03_propagation_table_static() -> dict[str, Any]:
    """Substrate propagation table rows use registered ``RD-*`` codes."""
    errors: list[str] = []
    pack = build_retrieval_policy_pack_default_v1()
    for row in RETRIEVAL_SUBSTRATE_PROPAGATION_ROWS_V1:
        code = row["consequence_code"]
        if code not in RETRIEVAL_RD_CODES_REGISTRY_V1:
            errors.append(f"unregistered_consequence:{code}")
    triggers = propagate_upstream_triggers_to_rd_omissions_v1(
        {
            "reconstruction_coverage_gap": True,
            "orphan_artifacts": True,
            "traversal_never_executed": True,
        },
        pack=pack,
    )
    codes = {r["retrieval_omission_class"] for r in triggers}
    if "RD-TCRE-GAP" not in codes or "RD-GRAPH-ORPHAN" not in codes:
        errors.append(f"propagation_missing_codes:{codes}")
    chain = build_degradation_propagation_chain_v1(
        upstream_triggers={"orphan_artifacts": True},
    )
    if not chain or chain[0].get("consequence_code") != "RD-GRAPH-ORPHAN":
        errors.append("chain_orphan_missing")
    try:
        build_lawful_missing_data_omission_v1(
            case="artifact_never_existed",
            rd_code="RD-LINEAGE-GAP",
        )
    except RetrievalDegradationTaxonomyError as exc:
        errors.append(f"lawful_gap:{exc}")
    return _deg_tax_meta(GP07_DEG03_GATE_ID_V1, "gp07_deg03_propagation_table", errors)


def verify_gp07_deg04_completeness_registry_static() -> dict[str, Any]:
    """Completeness projections must only cite registry ``RD-*`` codes."""
    errors: list[str] = []
    try:
        validate_retrieval_completeness_uses_rd_registry_v1(
            {
                "omission_classes": {"RD-CAP-HITS": 1},
                "rd_rows": [{"retrieval_omission_class": "RD-TCRE-GAP"}],
                "propagation_chain": [{"consequence_code": "RD-GRAPH-ORPHAN"}],
            }
        )
    except RetrievalDegradationTaxonomyError as exc:
        errors.append(f"valid_completeness_rejected:{exc}")
    try:
        validate_retrieval_completeness_uses_rd_registry_v1(
            {"omission_classes": {"RD-NOT-REGISTERED": 1}}
        )
    except RetrievalDegradationTaxonomyError:
        pass
    else:
        errors.append("unknown_rd_should_fail")
    cat = build_retrieval_degradation_topology_catalog_v1()
    if len(cat.get("substrate_propagation_table") or []) < 5:
        errors.append("propagation_table_too_small")
    return _deg_tax_meta(GP07_DEG01_GATE_ID_V1, "gp07_deg04_completeness_registry", errors)

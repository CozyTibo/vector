"""Phase 08 P08-18 — synthesis degradation taxonomy propagation (**G-P08-DEG-02**).

Normative: ``DOCS/cortex/synthesis/phase-08-failure-degradation-taxonomy.md`` §Propagation.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.synthesis.phase_boundaries import (
    _RD_TO_SD_PRIMARY_V1,
    build_sd_row_from_rd_omission_v1,
    map_rd_code_to_sd_code_v1,
    propagate_retrieval_omissions_to_sd_rows_v1,
)
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    GP08_DEG01_GATE_ID_V1,
    SYNTHESIS_BOUNDED_CAPS_SPEC_REF_V1,
    SYNTHESIS_DEGRADATION_POSTURES_V1,
    SYNTHESIS_SD_CODES_REGISTRY_V1,
    SYNTHESIS_SUBSTRATE_HEALTH_STATES_V1,
    SynthesisBoundedCapsError,
    _sd_code_from_row,
    build_synthesis_omission_histogram_v1,
    classify_synthesis_degradation_posture_v1,
    classify_synthesis_substrate_health_v1,
    normalize_sorted_sd_codes_v1,
    normalize_synthesis_omission_law_rows_v1,
    record_synthesis_omissions_to_histogram_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import synthesis_policy_pack_digest_v1
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1

PHASE08_SYNTHESIS_DEGRADATION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_DEG02_GATE_ID_V1: Final[str] = "G-P08-DEG-02"

SYNTHESIS_DEGRADATION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-failure-degradation-taxonomy.md"
)


class SynthesisDegradationError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def build_rd_to_sd_propagation_matrix_v1(
    *,
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Deterministic RD→SD propagation matrix (policy pack + primary map)."""
    pack_body = pack or load_synthesis_policy_pack_v1()
    matrix: dict[str, str] = dict(_RD_TO_SD_PRIMARY_V1)
    for rule in pack_body.get("rd_to_sd_propagation") or []:
        if not isinstance(rule, Mapping):
            continue
        rd = str(rule.get("rd_code") or "").strip()
        sd = str(rule.get("sd_code") or "").strip()
        if rd and sd:
            matrix[rd] = sd
    return [
        {"rd_code": rd, "sd_code": sd}
        for rd, sd in sorted(matrix.items())
    ]


def map_rd_to_sd_via_matrix_v1(rd_code: str, *, pack: Mapping[str, Any] | None = None) -> str:
    """Resolve SD code for an RD code using the closed propagation matrix."""
    code = rd_code.strip()
    for row in build_rd_to_sd_propagation_matrix_v1(pack=pack):
        if row["rd_code"] == code:
            return row["sd_code"]
    return map_rd_code_to_sd_code_v1(code)


def propagate_rd_omissions_via_matrix_v1(
    retrieval_omission_rows: Sequence[Mapping[str, Any]] | None,
    *,
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Propagate Phase 07 omissions through the RD→SD matrix (doctrine table)."""
    _ = pack
    return propagate_retrieval_omissions_to_sd_rows_v1(retrieval_omission_rows)


def normalize_synthesis_sd_multiset_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> Counter[str]:
    codes: list[str] = []
    for row in omissions:
        if not isinstance(row, Mapping):
            continue
        sd = _sd_code_from_row(row)
        if sd:
            codes.extend([sd] * max(1, int(row.get("trigger_count", 1))))
    return Counter(codes)


def validate_synthesis_sd_multiset_monotonic_extension_v1(
    before: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, Any]],
) -> None:
    """**G-P08-DEG-02** — upstream growth must not shrink the SD omission multiset."""
    before_ms = normalize_synthesis_sd_multiset_v1(before)
    after_ms = normalize_synthesis_sd_multiset_v1(after)
    for sd, count in before_ms.items():
        if after_ms.get(sd, 0) < count:
            raise SynthesisDegradationError(
                "sd_multiset_regression",
                detail={"sd_code": sd, "before": count, "after": after_ms.get(sd, 0)},
            )


def build_synthesis_sd_rollup_v1(
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """SD-* rollup for artifacts, receipts, and admin topology."""
    normalized = normalize_synthesis_omission_law_rows_v1(synthesis_omission_rows)
    counts = normalize_synthesis_sd_multiset_v1(normalized)
    sd_sorted = normalize_sorted_sd_codes_v1(normalized)
    posture = classify_synthesis_degradation_posture_v1(normalized)
    return {
        "sd_codes_sorted": sd_sorted,
        "sd_code_counts": dict(sorted(counts.items())),
        "sd_code_total": sum(counts.values()),
        "omission_histogram": {sd: counts[sd] for sd in sd_sorted},
        "synthesis_degradation_posture": posture,
        "synthesis_omission_row_count": len(normalized),
    }


def apply_synthesis_degradation_taxonomy_v1(
    *,
    synthesis_omission_rows: Sequence[Mapping[str, Any]],
    retrieval_ingress: Mapping[str, Any] | None = None,
    synthesis_legality_class: str = "synthesis_partial",
    synthesis_workload_class: str = "",
    upstream_triggers: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge upstream rollup + RD→SD propagation + posture + substrate health."""
    pack = load_synthesis_policy_pack_v1()
    default_workloads = pack.get("pipeline_default_workloads")
    is_default_wl = (
        isinstance(default_workloads, list)
        and str(synthesis_workload_class) in default_workloads
    )
    upstream_rollup: dict[str, Any] = {}
    if isinstance(retrieval_ingress, Mapping):
        raw_rollup = retrieval_ingress.get("retrieval_degradation_rollup")
        if isinstance(raw_rollup, Mapping):
            upstream_rollup = dict(raw_rollup)
    retrieval_rows = retrieval_ingress.get("retrieval_omission_rows") if isinstance(
        retrieval_ingress,
        Mapping,
    ) else None
    propagated = propagate_rd_omissions_via_matrix_v1(
        retrieval_rows if isinstance(retrieval_rows, list) else [],
        pack=pack,
    )
    trigger_rows: list[dict[str, Any]] = []
    if isinstance(upstream_triggers, Mapping):
        for trigger, active in upstream_triggers.items():
            if not active:
                continue
            trigger_rows.append(
                {
                    "sd_code": "SD-UPSTREAM-RD",
                    "synthesis_omission_class": "SD-UPSTREAM-RD",
                    "omission_semantics": "omitted_upstream",
                    "upstream_trigger": str(trigger),
                    "reason": "upstream_substrate_trigger",
                },
            )
    merged_raw: list[Mapping[str, Any]] = [
        *propagated,
        *[row for row in synthesis_omission_rows if isinstance(row, Mapping)],
        *trigger_rows,
    ]
    normalized = normalize_synthesis_omission_law_rows_v1(merged_raw)
    record_synthesis_omissions_to_histogram_v1(normalized)
    posture = classify_synthesis_degradation_posture_v1(normalized)
    health = classify_synthesis_substrate_health_v1(
        omissions=normalized,
        synthesis_legality_class=synthesis_legality_class,
        is_pipeline_default_workload=is_default_wl,
    )
    rollup = build_synthesis_sd_rollup_v1(normalized)
    rollup["substrate_health_state"] = health
    return {
        "synthesis_omission_rows": normalized,
        "upstream_rollup": upstream_rollup,
        "synthesis_degradation_posture": posture,
        "substrate_health_state": health,
        "sd_codes_sorted": rollup["sd_codes_sorted"],
        "synthesis_degradation_rollup": rollup,
        "rd_to_sd_propagation_matrix": build_rd_to_sd_propagation_matrix_v1(pack=pack),
    }


def apply_synthesis_degradation_to_artifact_v1(
    artifact: dict[str, Any],
    *,
    retrieval_ingress: Mapping[str, Any] | None = None,
    upstream_triggers: Mapping[str, Any] | None = None,
    synthesis_legality_class: str | None = None,
    synthesis_workload_class: str = "",
) -> dict[str, Any]:
    """Attach propagation rollup fields to ``SynthesisIntelligenceArtifactV1`` (§Propagation)."""
    legality = synthesis_legality_class or str(
        artifact.get("synthesis_legality_class") or "synthesis_partial",
    )
    tax = apply_synthesis_degradation_taxonomy_v1(
        synthesis_omission_rows=list(artifact.get("synthesis_omission_rows") or []),
        retrieval_ingress=retrieval_ingress,
        synthesis_legality_class=legality,
        synthesis_workload_class=synthesis_workload_class,
        upstream_triggers=upstream_triggers,
    )
    artifact["synthesis_omission_rows"] = list(tax["synthesis_omission_rows"])
    artifact["synthesis_degradation_rollup"] = dict(tax["synthesis_degradation_rollup"])
    artifact["upstream_rollup"] = dict(tax.get("upstream_rollup") or {})
    return artifact


def build_synthesis_degradation_topology_catalog_v1(
    *,
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Admin degradation topology — RD→SD matrix, health states, rollups."""
    pack = load_synthesis_policy_pack_v1()
    matrix = build_rd_to_sd_propagation_matrix_v1(pack=pack)
    return {
        "surface_kind": "synthesis_degradation_topology",
        "tenant_id": tenant_id or "",
        "phase08_synthesis_degradation_runtime_schema_version": (
            PHASE08_SYNTHESIS_DEGRADATION_RUNTIME_SCHEMA_VERSION
        ),
        "gate_ids": [GP08_DEG01_GATE_ID_V1, GP08_DEG02_GATE_ID_V1],
        "synthesis_policy_pack_id": pack.get("synthesis_policy_pack_id"),
        "synthesis_policy_pack_digest": synthesis_policy_pack_digest_v1(),
        "sd_codes_registry": sorted(SYNTHESIS_SD_CODES_REGISTRY_V1),
        "rd_to_sd_propagation_matrix": matrix,
        "rd_to_sd_primary_map": dict(_RD_TO_SD_PRIMARY_V1),
        "policy_pack_rd_to_sd": list(pack.get("rd_to_sd_propagation") or []),
        "substrate_health_states": sorted(SYNTHESIS_SUBSTRATE_HEALTH_STATES_V1),
        "degradation_postures": sorted(SYNTHESIS_DEGRADATION_POSTURES_V1),
        "omission_histogram": build_synthesis_omission_histogram_v1(),
        "rules": [
            {
                "id": "SYN-DEG-01",
                "text": "Closed SD-* registry; never collapse into silent claim removal",
            },
            {
                "id": "SYN-DEG-02",
                "text": "RD→SD propagation matrix is deterministic; SD multiset must not regress",
            },
        ],
        "doctrine_anchors": [
            SYNTHESIS_DEGRADATION_SPEC_REF_V1,
            SYNTHESIS_BOUNDED_CAPS_SPEC_REF_V1,
        ],
    }


def _deg_meta(gate_id: str, name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": gate_id,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "errors": errors,
            "phase08_synthesis_degradation_runtime_schema_version": (
                PHASE08_SYNTHESIS_DEGRADATION_RUNTIME_SCHEMA_VERSION
            ),
        },
    }


def verify_gp08_deg02_rd_to_sd_matrix_static() -> dict[str, Any]:
    errors: list[str] = []
    matrix = build_rd_to_sd_propagation_matrix_v1()
    by_rd = {row["rd_code"]: row["sd_code"] for row in matrix}
    if by_rd.get("RD-REPLAY-TWIN") != "SD-REPLAY-TWIN":
        errors.append("rd_replay_twin_mapping")
    if by_rd.get("RD-REPLAY-UNSAFE") != "SD-UPSTREAM-LEG":
        errors.append("rd_replay_unsafe_mapping")
    sample_rd = build_sd_row_from_rd_omission_v1(
        {"retrieval_omission_class": "RD-TCRE-GAP"},
    )
    if sample_rd.get("sd_code") != "SD-UPSTREAM-RD" and sample_rd.get("synthesis_omission_class") != "SD-UPSTREAM-RD":
        errors.append("rd_tcre_gap_propagation")
    return _deg_meta(GP08_DEG02_GATE_ID_V1, "gp08_deg02_rd_to_sd_matrix", errors)


def verify_gp08_deg02_sd_multiset_monotonic_static() -> dict[str, Any]:
    errors: list[str] = []
    before = [{"sd_code": "SD-CITE-GAP"}]
    after = before + [{"sd_code": "SD-UPSTREAM-RD"}]
    try:
        validate_synthesis_sd_multiset_monotonic_extension_v1(before, after)
    except SynthesisDegradationError as exc:
        errors.append(f"growth_should_pass:{exc}")
    try:
        validate_synthesis_sd_multiset_monotonic_extension_v1(after, before)
    except SynthesisDegradationError:
        pass
    else:
        errors.append("shrink_should_fail")
    return _deg_meta(GP08_DEG02_GATE_ID_V1, "gp08_deg02_sd_multiset_monotonic", errors)


def verify_gp08_deg02_artifact_taxonomy_apply_static() -> dict[str, Any]:
    errors: list[str] = []
    artifact = {
        "synthesis_legality_class": "synthesis_degraded",
        "synthesis_omission_rows": [{"sd_code": "SD-CITE-GAP"}],
        "claims": [{"claim_kind": "observation", "omitted_reason": "SD-CITE-GAP"}],
    }
    ingress = {
        "retrieval_degradation_rollup": {"rd_code_counts": {"RD-TCRE-GAP": 1}},
        "retrieval_omission_rows": [{"retrieval_omission_class": "RD-TCRE-GAP"}],
    }
    out = apply_synthesis_degradation_to_artifact_v1(
        artifact,
        retrieval_ingress=ingress,
        synthesis_workload_class="degradation_brief",
    )
    rollup = out.get("synthesis_degradation_rollup")
    if not isinstance(rollup, Mapping):
        errors.append("missing_rollup")
    elif "SD-UPSTREAM-RD" not in (rollup.get("sd_codes_sorted") or []):
        errors.append("expected_upstream_rd_propagation")
    if not out.get("upstream_rollup"):
        errors.append("missing_upstream_rollup_copy")
    try:
        normalize_synthesis_omission_law_rows_v1([{"sd_code": "SD-NOT-REAL"}])
    except SynthesisBoundedCapsError:
        pass
    else:
        errors.append("unknown_sd_should_fail")
    return _deg_meta(GP08_DEG02_GATE_ID_V1, "gp08_deg02_artifact_taxonomy_apply", errors)

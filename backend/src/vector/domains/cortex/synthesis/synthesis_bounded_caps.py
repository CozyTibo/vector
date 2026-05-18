"""Phase 08 P08-13 — bounded caps + **SD-*** omission law (**G-P08-DEG-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-failure-degradation-taxonomy.md``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import load_synthesis_policy_pack_v1

PHASE08_SYNTHESIS_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_DEG01_GATE_ID_V1: Final[str] = "G-P08-DEG-01"

SYNTHESIS_BOUNDED_CAPS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-failure-degradation-taxonomy.md"
)

SD_CAP_CLAIMS_V1: Final[str] = "SD-CAP-CLAIMS"
SD_CAP_RETRIEVAL_V1: Final[str] = "SD-CAP-RETRIEVAL"
SD_CAP_LLM_V1: Final[str] = "SD-CAP-LLM"
SD_CITE_GAP_V1: Final[str] = "SD-CITE-GAP"
SD_SCOPE_EMPTY_V1: Final[str] = "SD-SCOPE-EMPTY"
SD_UPSTREAM_RD_V1: Final[str] = "SD-UPSTREAM-RD"
SD_UPSTREAM_LEG_V1: Final[str] = "SD-UPSTREAM-LEG"
SD_LLM_TIMEOUT_V1: Final[str] = "SD-LLM-TIMEOUT"
SD_LLM_SCHEMA_V1: Final[str] = "SD-LLM-SCHEMA"
SD_LLM_POLICY_V1: Final[str] = "SD-LLM-POLICY"
SD_REPLAY_TWIN_V1: Final[str] = "SD-REPLAY-TWIN"
SD_REPLAY_DRIFT_V1: Final[str] = "SD-REPLAY-DRIFT"
SD_POLICY_MISMATCH_V1: Final[str] = "SD-POLICY-MISMATCH"
SD_PUBLISH_BLOCKED_V1: Final[str] = "SD-PUBLISH-BLOCKED"
SD_PIPELINE_GAP_V1: Final[str] = "SD-PIPELINE-GAP"
SD_TEMPORAL_PIN_V1: Final[str] = "SD-TEMPORAL-PIN"
SD_LINEAGE_GAP_V1: Final[str] = "SD-LINEAGE-GAP"

SYNTHESIS_SD_CODES_REGISTRY_V1: Final[frozenset[str]] = frozenset(
    {
        SD_CAP_CLAIMS_V1,
        SD_CAP_RETRIEVAL_V1,
        SD_CAP_LLM_V1,
        SD_CITE_GAP_V1,
        SD_SCOPE_EMPTY_V1,
        SD_UPSTREAM_RD_V1,
        SD_UPSTREAM_LEG_V1,
        SD_LLM_TIMEOUT_V1,
        SD_LLM_SCHEMA_V1,
        SD_LLM_POLICY_V1,
        SD_REPLAY_TWIN_V1,
        SD_REPLAY_DRIFT_V1,
        SD_POLICY_MISMATCH_V1,
        SD_PUBLISH_BLOCKED_V1,
        SD_PIPELINE_GAP_V1,
        SD_TEMPORAL_PIN_V1,
        SD_LINEAGE_GAP_V1,
    }
)

SYNTHESIS_OMISSION_SEMANTICS_BY_SD_V1: Final[dict[str, str]] = {
    SD_CAP_CLAIMS_V1: "omitted_cap",
    SD_CAP_RETRIEVAL_V1: "omitted_cap",
    SD_CAP_LLM_V1: "omitted_cap",
    SD_CITE_GAP_V1: "omitted_evidence",
    SD_SCOPE_EMPTY_V1: "omitted_empty_scope",
    SD_UPSTREAM_RD_V1: "omitted_upstream",
    SD_UPSTREAM_LEG_V1: "omitted_upstream_legality",
    SD_LLM_TIMEOUT_V1: "omitted_llm",
    SD_LLM_SCHEMA_V1: "omitted_llm",
    SD_LLM_POLICY_V1: "omitted_llm",
    SD_REPLAY_TWIN_V1: "omitted_replay",
    SD_REPLAY_DRIFT_V1: "omitted_replay",
    SD_POLICY_MISMATCH_V1: "omitted_policy",
    SD_PUBLISH_BLOCKED_V1: "omitted_publish",
    SD_PIPELINE_GAP_V1: "omitted_pipeline",
    SD_TEMPORAL_PIN_V1: "omitted_temporal",
    SD_LINEAGE_GAP_V1: "omitted_lineage",
}

SYNTHESIS_SUBSTRATE_HEALTH_STATES_V1: Final[frozenset[str]] = frozenset(
    {
        "healthy",
        "degraded",
        "critical",
        "unresolved",
        "replay_conflicted",
    }
)

SYNTHESIS_DEGRADATION_POSTURES_V1: Final[frozenset[str]] = frozenset(
    {"stable", "degraded", "critical", "unresolved"},
)

SYNTHESIS_POLICY_PACK_DEFAULT_CAPS_V1: Final[dict[str, int]] = {
    "max_claims": 64,
    "max_retrieval_subqueries": 8,
    "max_llm_tokens": 8192,
    "max_wall_ms": 120_000,
    "max_artifact_json_bytes": 524_288,
}

_CAP_CEILING_KEYS_V1: Final[tuple[str, ...]] = (
    "max_claims",
    "max_retrieval_subqueries",
    "max_llm_tokens",
    "max_wall_ms",
    "max_artifact_json_bytes",
)

_SYNTHESIS_OMISSION_HISTOGRAM_V1: dict[str, int] = defaultdict(int)


class SynthesisBoundedCapsError(ValueError):
    def __init__(
        self,
        code: str,
        *,
        http_status: int = 400,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def synthesis_policy_pack_caps_v1(pack: Mapping[str, Any] | None = None) -> dict[str, int]:
    body = dict(pack or load_synthesis_policy_pack_v1())
    raw = body.get("caps")
    if not isinstance(raw, dict):
        return dict(SYNTHESIS_POLICY_PACK_DEFAULT_CAPS_V1)
    out: dict[str, int] = dict(SYNTHESIS_POLICY_PACK_DEFAULT_CAPS_V1)
    for key in _CAP_CEILING_KEYS_V1:
        if key in raw:
            out[key] = int(raw[key])
    return out


def enforce_synthesis_cap_ceilings_not_bypassed_v1(
    selection_policy: Mapping[str, Any],
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Caps MUST NOT exceed ``SynthesisPolicyPackV1`` ceilings."""
    ceilings = synthesis_policy_pack_caps_v1(pack or load_synthesis_policy_pack_v1())
    out: dict[str, Any] = dict(selection_policy)
    for key in _CAP_CEILING_KEYS_V1:
        ceiling = ceilings.get(key)
        if ceiling is None:
            continue
        if key in out and key != "llm_simulate":
            try:
                requested = int(out[key])
            except (TypeError, ValueError) as exc:
                raise SynthesisBoundedCapsError(
                    "invalid_selection_cap",
                    detail={"key": key, "value": out[key]},
                ) from exc
            if requested > ceiling:
                raise SynthesisBoundedCapsError(
                    "selection_policy_cap_ceiling_exceeded",
                    detail={"key": key, "requested": requested, "ceiling": ceiling},
                )
            out[key] = requested
        elif key not in out:
            out[key] = ceiling
    pack_body = pack or load_synthesis_policy_pack_v1()
    out.setdefault("synthesis_policy_pack_id", str(pack_body.get("synthesis_policy_pack_id") or ""))
    return out


def apply_synthesis_policy_pack_caps_v1(
    workload_class: str,
    selection_policy: Mapping[str, Any] | None,
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge policy-pack caps into workload selection policy (Step **13** law)."""
    from vector.domains.cortex.synthesis.synthesis_job_contract import (
        selection_policy_caps_for_synthesis_workload_v1,
    )

    merged: dict[str, Any] = dict(selection_policy_caps_for_synthesis_workload_v1(workload_class))
    if isinstance(selection_policy, Mapping):
        merged.update(dict(selection_policy))
    pack_body = pack or load_synthesis_policy_pack_v1()
    for key, val in synthesis_policy_pack_caps_v1(pack_body).items():
        merged.setdefault(key, val)
    return enforce_synthesis_cap_ceilings_not_bypassed_v1(merged, pack=pack_body)


def validate_sd_code_registered_v1(sd_code: str) -> None:
    if sd_code not in SYNTHESIS_SD_CODES_REGISTRY_V1:
        raise SynthesisBoundedCapsError(
            "unknown_synthesis_omission_class",
            detail={"synthesis_omission_class": sd_code},
        )


def _sd_code_from_row(row: Mapping[str, Any]) -> str:
    return str(
        row.get("sd_code") or row.get("synthesis_omission_class") or "",
    ).strip().upper()


def normalize_synthesis_omission_law_row_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    """Validate omission rows against closed ``SD-*`` registry."""
    sd = _sd_code_from_row(row)
    validate_sd_code_registered_v1(sd)
    semantics = str(row.get("omission_semantics") or "").strip()
    if not semantics:
        semantics = SYNTHESIS_OMISSION_SEMANTICS_BY_SD_V1.get(sd, "omitted_upstream")
    out: dict[str, Any] = {
        "synthesis_omission_class": sd,
        "sd_code": sd,
        "omission_semantics": semantics,
        "reason": str(row.get("reason") or ""),
        "trigger_count": int(row.get("trigger_count", 1)),
    }
    if row.get("upstream_rd"):
        out["upstream_rd"] = str(row["upstream_rd"])
    if row.get("upstream_trigger"):
        out["upstream_trigger"] = str(row["upstream_trigger"])
    if row.get("claim_id"):
        out["claim_id"] = str(row["claim_id"])
    if row.get("model_route_id"):
        out["model_route_id"] = str(row["model_route_id"])
    detail = row.get("detail")
    if isinstance(detail, Mapping):
        out["detail"] = dict(detail)
    return out


def normalize_synthesis_omission_law_rows_v1(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [normalize_synthesis_omission_law_row_v1(row) for row in rows if isinstance(row, Mapping)]


def build_sd_cap_claims_row_v1(
    *,
    accepted_claim_count: int,
    max_claims: int,
) -> dict[str, Any]:
    return {
        "synthesis_omission_class": SD_CAP_CLAIMS_V1,
        "sd_code": SD_CAP_CLAIMS_V1,
        "omission_semantics": SYNTHESIS_OMISSION_SEMANTICS_BY_SD_V1[SD_CAP_CLAIMS_V1],
        "reason": "max_claims_exceeded",
        "accepted_claim_count": accepted_claim_count,
        "max_claims": max_claims,
    }


def list_synthesis_claim_cap_violations_v1(
    *,
    accepted_claim_count: int,
    max_claims: int,
) -> list[dict[str, Any]]:
    if accepted_claim_count <= max_claims:
        return []
    return [build_sd_cap_claims_row_v1(accepted_claim_count=accepted_claim_count, max_claims=max_claims)]


def normalize_sorted_sd_codes_v1(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """Sorted unique SD codes for replay twin multiset pin."""
    codes = {_sd_code_from_row(row) for row in rows if isinstance(row, Mapping)}
    return sorted(c for c in codes if c in SYNTHESIS_SD_CODES_REGISTRY_V1)


def classify_synthesis_degradation_posture_v1(
    omissions: Sequence[Mapping[str, Any]],
) -> str:
    """``stable`` | ``degraded`` | ``critical`` | ``unresolved``."""
    codes = {_sd_code_from_row(row) for row in omissions if isinstance(row, Mapping)}
    if SD_PUBLISH_BLOCKED_V1 in codes or SD_LLM_SCHEMA_V1 in codes:
        return "critical"
    if codes & {
        SD_UPSTREAM_RD_V1,
        SD_UPSTREAM_LEG_V1,
        SD_REPLAY_TWIN_V1,
        SD_REPLAY_DRIFT_V1,
        SD_PIPELINE_GAP_V1,
        SD_LLM_TIMEOUT_V1,
        SD_LLM_POLICY_V1,
    }:
        return "degraded"
    if SD_SCOPE_EMPTY_V1 in codes:
        return "unresolved"
    if codes:
        return "degraded"
    return "stable"


def classify_synthesis_substrate_health_v1(
    *,
    omissions: Sequence[Mapping[str, Any]],
    synthesis_legality_class: str,
    is_pipeline_default_workload: bool = False,
) -> str:
    codes = {_sd_code_from_row(row) for row in omissions if isinstance(row, Mapping)}
    if SD_REPLAY_DRIFT_V1 in codes:
        return "replay_conflicted"
    if SD_PUBLISH_BLOCKED_V1 in codes or SD_LLM_SCHEMA_V1 in codes:
        return "critical"
    if SD_SCOPE_EMPTY_V1 in codes and is_pipeline_default_workload:
        return "unresolved"
    if codes & {SD_UPSTREAM_RD_V1, SD_UPSTREAM_LEG_V1, SD_REPLAY_TWIN_V1}:
        return "degraded"
    if synthesis_legality_class == "synthesis_forbidden":
        return "critical"
    if not codes and synthesis_legality_class == "synthesis_replay_safe":
        return "healthy"
    return "degraded"


def record_synthesis_omissions_to_histogram_v1(rows: Sequence[Mapping[str, Any]]) -> None:
    for row in rows:
        sd = _sd_code_from_row(row)
        if not sd:
            continue
        count = int(row.get("trigger_count", 1))
        _SYNTHESIS_OMISSION_HISTOGRAM_V1[sd] += max(count, 1)


def build_synthesis_omission_histogram_v1() -> dict[str, int]:
    return dict(sorted(_SYNTHESIS_OMISSION_HISTOGRAM_V1.items()))


def reset_synthesis_omission_histogram_v1() -> None:
    _SYNTHESIS_OMISSION_HISTOGRAM_V1.clear()


def estimate_json_byte_size_v1(body: Mapping[str, Any]) -> int:
    return len(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


def assert_synthesis_artifact_under_byte_cap_v1(
    body: Mapping[str, Any],
    *,
    max_artifact_json_bytes: int,
) -> None:
    size = estimate_json_byte_size_v1(body)
    if size > int(max_artifact_json_bytes):
        raise SynthesisBoundedCapsError(
            "synthesis_artifact_too_large",
            http_status=413,
            detail={"bytes": size, "max_artifact_json_bytes": int(max_artifact_json_bytes)},
        )


def assert_synthesis_wall_budget_v1(
    *,
    elapsed_ms: float,
    max_wall_ms: int,
) -> None:
    if elapsed_ms > float(max_wall_ms):
        raise SynthesisBoundedCapsError(
            "synthesis_timeout",
            http_status=503,
            detail={"elapsed_ms": elapsed_ms, "max_wall_ms": int(max_wall_ms)},
        )


def build_synthesis_omission_explorer_catalog_v1() -> dict[str, Any]:
    pack = load_synthesis_policy_pack_v1()
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_sd_omission_explorer_v1",
        "phase08_synthesis_bounded_caps_runtime_schema_version": (
            PHASE08_SYNTHESIS_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_DEG01_GATE_ID_V1,
        "spec_ref": SYNTHESIS_BOUNDED_CAPS_SPEC_REF_V1,
        "synthesis_policy_pack_id": pack.get("synthesis_policy_pack_id"),
        "default_caps": synthesis_policy_pack_caps_v1(pack),
        "sd_codes_registry": sorted(SYNTHESIS_SD_CODES_REGISTRY_V1),
        "omission_semantics_by_sd": dict(SYNTHESIS_OMISSION_SEMANTICS_BY_SD_V1),
        "substrate_health_states": sorted(SYNTHESIS_SUBSTRATE_HEALTH_STATES_V1),
        "degradation_postures": sorted(SYNTHESIS_DEGRADATION_POSTURES_V1),
        "omission_histogram": build_synthesis_omission_histogram_v1(),
        "rd_to_sd_propagation": list(pack.get("rd_to_sd_propagation") or []),
        "rules": [
            {"id": "SYN-DEG-01", "text": "Closed SD-* registry; new codes need amendment"},
            {"id": "SYN-DEG-02", "text": "Never collapse SD-* into silent claim removal"},
        ],
        "http_behaviors": {
            "synthesis_artifact_too_large": 413,
            "synthesis_timeout": 503,
        },
    }


def _deg_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_DEG01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_deg01_sd_registry_closed_static() -> dict[str, Any]:
    errors: list[str] = []
    pack = load_synthesis_policy_pack_v1()
    pack_codes = pack.get("sd_codes")
    if not isinstance(pack_codes, list):
        errors.append("fixture_sd_codes_missing")
    else:
        fixture_set = {str(c) for c in pack_codes}
        if fixture_set != SYNTHESIS_SD_CODES_REGISTRY_V1:
            missing = SYNTHESIS_SD_CODES_REGISTRY_V1 - fixture_set
            extra = fixture_set - SYNTHESIS_SD_CODES_REGISTRY_V1
            if missing:
                errors.append(f"fixture_missing_sd:{sorted(missing)}")
            if extra:
                errors.append(f"fixture_extra_sd:{sorted(extra)}")
    try:
        normalize_synthesis_omission_law_row_v1(
            {"sd_code": SD_CAP_CLAIMS_V1, "reason": "test"},
        )
    except SynthesisBoundedCapsError as exc:
        errors.append(f"known_row_rejected:{exc}")
    try:
        normalize_synthesis_omission_law_row_v1({"sd_code": "SD-NOT-REAL"})
    except SynthesisBoundedCapsError:
        pass
    else:
        errors.append("unknown_sd_should_fail")
    caps = apply_synthesis_policy_pack_caps_v1("degradation_brief", {"max_claims": 32})
    if caps.get("max_claims") != 32:
        errors.append("cap_merge_failed")
    try:
        apply_synthesis_policy_pack_caps_v1("degradation_brief", {"max_claims": 10_000})
    except SynthesisBoundedCapsError:
        pass
    else:
        errors.append("bypass_should_raise")
    reset_synthesis_omission_histogram_v1()
    record_synthesis_omissions_to_histogram_v1([{"sd_code": SD_CITE_GAP_V1, "trigger_count": 2}])
    hist = build_synthesis_omission_histogram_v1()
    if hist.get(SD_CITE_GAP_V1) != 2:
        errors.append("histogram_count")
    reset_synthesis_omission_histogram_v1()
    from vector.domains.cortex.synthesis.synthesis_degradation import (
        apply_synthesis_degradation_taxonomy_v1,
    )

    tax = apply_synthesis_degradation_taxonomy_v1(
        synthesis_omission_rows=[{"sd_code": SD_REPLAY_TWIN_V1}],
        synthesis_legality_class="synthesis_degraded",
    )
    if tax["synthesis_degradation_posture"] != "degraded":
        errors.append("posture_degraded")
    if tax["substrate_health_state"] != "degraded":
        errors.append("substrate_health")
    if SD_REPLAY_TWIN_V1 not in tax["sd_codes_sorted"]:
        errors.append("sd_multiset_missing")
    try:
        assert_synthesis_artifact_under_byte_cap_v1({"x": "y" * 1000}, max_artifact_json_bytes=10)
    except SynthesisBoundedCapsError as exc:
        if exc.http_status != 413:
            errors.append("wrong_413_status")
    else:
        errors.append("413_should_raise")
    try:
        assert_synthesis_wall_budget_v1(elapsed_ms=200_000, max_wall_ms=120_000)
    except SynthesisBoundedCapsError as exc:
        if exc.http_status != 503:
            errors.append("wrong_503_status")
    else:
        errors.append("503_should_raise")
    cat = build_synthesis_omission_explorer_catalog_v1()
    if cat["gate_id"] != GP08_DEG01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _deg_meta("gp08_deg01_sd_registry_closed", errors)

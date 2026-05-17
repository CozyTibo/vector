"""Phase 07 P07-13 — bounded caps + omission law (**RET-DEG-01/02**).

Normative: ``phase-07-query-contract-doctrine.md`` §6;
``phase-07-retrieval-degradation-taxonomy.md``.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)

PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_DEG01_GATE_ID_V1: Final[str] = "G-P07-DEG-01"

RETRIEVAL_BOUNDED_CAPS_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-degradation-taxonomy.md"
)

RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1: Final[str] = "RetrievalPolicyPackV1_Default"

RETRIEVAL_POLICY_PACK_DEFAULT_CAPS_V1: Final[dict[str, int]] = {
    "max_hits": 100,
    "max_chronology_rows": 500,
    "max_edges": 200,
    "max_lineage_hops": 64,
    "max_wall_ms": 30_000,
    "max_response_json_bytes": 262_144,
}

RETRIEVAL_RD_TRAVERSAL_IDLE_V1: Final[str] = "RD-TRAVERSAL-IDLE"

RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1: Final[str] = "RD-TRAVERSAL-BLOCKED"

RETRIEVAL_RD_GRAPH_ORPHAN_V1: Final[str] = "RD-GRAPH-ORPHAN"

RETRIEVAL_RD_LINEAGE_GAP_V1: Final[str] = "RD-LINEAGE-GAP"

RETRIEVAL_RD_CODES_REGISTRY_V1: Final[frozenset[str]] = frozenset(
    {
        "RD-CAP-HITS",
        "RD-CAP-CHRON",
        "RD-CAP-EDGE",
        "RD-CAP-LINEAGE",
        "RD-TCRE-GAP",
        "RD-GRAPH-ORPHAN",
        "RD-TRAVERSAL-IDLE",
        "RD-TRAVERSAL-BLOCKED",
        "RD-LINEAGE-GAP",
        "RD-REPLAY-UNSAFE",
        "RD-REPLAY-TWIN",
        "RD-INDEX-STALE",
        "RD-POLICY-MISMATCH",
        "RD-ADDRESSING-UNRESOLVED",
        "RD-TEMPORAL-FUTURE",
        "RD-TEMPORAL-PIN",
    }
)

RETRIEVAL_OMISSION_SEMANTICS_BY_RD_V1: Final[dict[str, str]] = {
    "RD-CAP-HITS": "omitted_cap",
    "RD-CAP-CHRON": "omitted_cap",
    "RD-CAP-EDGE": "omitted_cap",
    "RD-CAP-LINEAGE": "omitted_cap",
    "RD-TCRE-GAP": "omitted_upstream_gap",
    "RD-GRAPH-ORPHAN": "omitted_upstream_gap",
    "RD-TRAVERSAL-IDLE": "omitted_upstream_gap",
    "RD-TRAVERSAL-BLOCKED": "omitted_upstream_gap",
    "RD-LINEAGE-GAP": "omitted_upstream_gap",
    "RD-REPLAY-UNSAFE": "omitted_replay_unsafe",
    "RD-REPLAY-TWIN": "omitted_replay_unsafe",
    "RD-INDEX-STALE": "omitted_upstream_gap",
    "RD-POLICY-MISMATCH": "omitted_legality",
    "RD-ADDRESSING-UNRESOLVED": "omitted_addressing_partial",
    "RD-TEMPORAL-FUTURE": "omitted_temporal_future",
    "RD-TEMPORAL-PIN": "omitted_upstream_gap",
}

RETRIEVAL_SUBSTRATE_HEALTH_STATES_V1: Final[frozenset[str]] = frozenset(
    {
        "healthy",
        "degraded",
        "critical",
        "unresolved",
        "replay_conflicted",
    }
)

_CAP_CEILING_KEYS_V1: Final[tuple[str, ...]] = (
    "max_hits",
    "max_chronology_rows",
    "max_edges",
    "max_lineage_hops",
    "max_wall_ms",
    "max_response_json_bytes",
)

_RETRIEVAL_OMISSION_HISTOGRAM_V1: dict[str, int] = defaultdict(int)


class RetrievalBoundedCapsError(ValueError):
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


def retrieval_policy_pack_fixture_path_v1() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "RetrievalPolicyPackV1_Default.json"


def load_retrieval_policy_pack_v1(
    path: Path | None = None,
) -> dict[str, Any]:
    fixture_path = path or retrieval_policy_pack_fixture_path_v1()
    body = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise RetrievalBoundedCapsError("policy_pack_invalid")
    return body


def build_retrieval_policy_pack_default_v1() -> dict[str, Any]:
    return load_retrieval_policy_pack_v1()


def retrieval_policy_pack_digest_v1(pack: Mapping[str, Any] | None = None) -> str:
    body = dict(pack or build_retrieval_policy_pack_default_v1())
    return hash_reasoning_canonical_json_sha256_v1(body)


def policy_pack_caps_v1(pack: Mapping[str, Any]) -> dict[str, int]:
    raw = pack.get("caps")
    if not isinstance(raw, dict):
        return dict(RETRIEVAL_POLICY_PACK_DEFAULT_CAPS_V1)
    out: dict[str, int] = dict(RETRIEVAL_POLICY_PACK_DEFAULT_CAPS_V1)
    for key in _CAP_CEILING_KEYS_V1:
        if key in raw:
            out[key] = int(raw[key])
    return out


def enforce_cap_ceilings_not_bypassed_v1(
    selection_policy: Mapping[str, Any],
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Caps MUST NOT exceed policy-pack ceilings (**legality: no bypass**)."""
    ceilings = policy_pack_caps_v1(pack or build_retrieval_policy_pack_default_v1())
    out: dict[str, Any] = dict(selection_policy)
    for key in _CAP_CEILING_KEYS_V1:
        ceiling = ceilings.get(key)
        if ceiling is None:
            continue
        if key in out:
            try:
                requested = int(out[key])
            except (TypeError, ValueError) as exc:
                raise RetrievalBoundedCapsError(
                    "invalid_selection_cap",
                    detail={"key": key, "value": out[key]},
                ) from exc
            if requested > ceiling:
                raise RetrievalBoundedCapsError(
                    "selection_policy_cap_ceiling_exceeded",
                    detail={"key": key, "requested": requested, "ceiling": ceiling},
                )
            out[key] = requested
        else:
            out[key] = ceiling
    pack_body = pack or build_retrieval_policy_pack_default_v1()
    out.setdefault(
        "selection_policy_profile_id",
        str(pack_body.get("selection_policy_profile_id") or ""),
    )
    out.setdefault("retrieval_policy_pack_id", str(pack_body.get("retrieval_policy_pack_id") or ""))
    return out


def apply_retrieval_policy_pack_defaults_v1(
    workload_class: str,
    selection_policy: Mapping[str, Any] | None,
    *,
    pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge ``RetrievalPolicyPackV1_Default`` caps into workload selection policy."""
    from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
        normalize_retrieval_selection_policy_v1,
    )

    pack_body = pack or build_retrieval_policy_pack_default_v1()
    merged = normalize_retrieval_selection_policy_v1(
        workload_class,
        selection_policy,
    )
    ceilings = policy_pack_caps_v1(pack_body)
    for key, val in ceilings.items():
        merged.setdefault(key, val)
    merged["retrieval_policy_pack_id"] = str(
        pack_body.get("retrieval_policy_pack_id") or RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1
    )
    merged["retrieval_policy_pack_version"] = int(
        pack_body.get("retrieval_policy_pack_version") or 1
    )
    return enforce_cap_ceilings_not_bypassed_v1(merged, pack=pack_body)


def validate_rd_code_registered_v1(rd_code: str) -> None:
    if rd_code not in RETRIEVAL_RD_CODES_REGISTRY_V1:
        raise RetrievalBoundedCapsError(
            "unknown_retrieval_omission_class",
            detail={"retrieval_omission_class": rd_code},
        )


def normalize_retrieval_omission_law_row_v1(row: Mapping[str, Any]) -> dict[str, Any]:
    rd = str(
        row.get("retrieval_omission_class") or row.get("rd_code") or ""
    ).strip()
    validate_rd_code_registered_v1(rd)
    semantics = str(row.get("omission_semantics") or "").strip()
    if not semantics:
        semantics = RETRIEVAL_OMISSION_SEMANTICS_BY_RD_V1.get(rd, "omitted_upstream_gap")
    return {
        "retrieval_omission_class": rd,
        "omission_semantics": semantics,
        "upstream_trigger": str(row.get("upstream_trigger") or ""),
        "trigger_count": int(row.get("trigger_count", 1)),
    }


def normalize_retrieval_omission_law_rows_v1(
    rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Validate omission rows against closed ``RD-*`` registry (**RET-DEG-01**)."""
    return [normalize_retrieval_omission_law_row_v1(row) for row in rows]


def record_retrieval_omissions_to_histogram_v1(
    rows: Sequence[Mapping[str, Any]],
) -> None:
    for row in rows:
        rd = str(row.get("retrieval_omission_class") or "").strip()
        if not rd:
            continue
        count = int(row.get("trigger_count", 1))
        _RETRIEVAL_OMISSION_HISTOGRAM_V1[rd] += max(count, 1)


def build_retrieval_omission_histogram_v1() -> dict[str, int]:
    return dict(sorted(_RETRIEVAL_OMISSION_HISTOGRAM_V1.items()))


def reset_retrieval_omission_histogram_v1() -> None:
    _RETRIEVAL_OMISSION_HISTOGRAM_V1.clear()


def classify_substrate_health_v1(
    *,
    omissions: Sequence[Mapping[str, Any]],
    retrieval_legality_class: str,
) -> str:
    codes = {
        str(o.get("retrieval_omission_class") or "")
        for o in omissions
        if o.get("retrieval_omission_class")
    }
    if "RD-REPLAY-UNSAFE" in codes or retrieval_legality_class == "retrieval_unverifiable":
        return "replay_conflicted"
    if "RD-ADDRESSING-UNRESOLVED" in codes:
        return "unresolved"
    cap_hits = sum(1 for c in codes if c.startswith("RD-CAP-"))
    if retrieval_legality_class == "retrieval_forbidden":
        return "critical"
    if cap_hits > 0 or retrieval_legality_class in ("retrieval_degraded", "retrieval_partial"):
        return "degraded"
    if not omissions and retrieval_legality_class == "retrieval_replay_safe":
        return "healthy"
    return "degraded"


def build_degradation_propagation_chain_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    pack: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Human-readable propagation chain (P07-19 taxonomy module)."""
    from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
        build_degradation_propagation_chain_v1 as _build_chain_v1,
    )

    return _build_chain_v1(upstream_triggers=upstream_triggers, pack=pack)


def estimate_json_byte_size_v1(body: Mapping[str, Any]) -> int:
    return len(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )


def assert_retrieval_response_under_byte_cap_v1(
    result: Mapping[str, Any],
    *,
    max_response_json_bytes: int,
) -> None:
    """413 ``retrieval_response_too_large`` when canonical JSON exceeds cap."""
    size = estimate_json_byte_size_v1(result)
    if size > int(max_response_json_bytes):
        raise RetrievalBoundedCapsError(
            "retrieval_response_too_large",
            http_status=413,
            detail={"bytes": size, "max_response_json_bytes": int(max_response_json_bytes)},
        )


def assert_retrieval_wall_budget_v1(
    *,
    elapsed_ms: float,
    max_wall_ms: int,
) -> None:
    """503 ``retrieval_timeout`` when wall budget exceeded."""
    if elapsed_ms > float(max_wall_ms):
        raise RetrievalBoundedCapsError(
            "retrieval_timeout",
            http_status=503,
            detail={"elapsed_ms": elapsed_ms, "max_wall_ms": int(max_wall_ms)},
        )


def enforce_retrieval_bounded_response_law_v1(
    result: Mapping[str, Any],
    *,
    caps: Mapping[str, Any],
    elapsed_ms: float,
) -> None:
    assert_retrieval_wall_budget_v1(
        elapsed_ms=elapsed_ms,
        max_wall_ms=int(caps.get("max_wall_ms", RETRIEVAL_POLICY_PACK_DEFAULT_CAPS_V1["max_wall_ms"])),
    )
    assert_retrieval_response_under_byte_cap_v1(
        result,
        max_response_json_bytes=int(
            caps.get(
                "max_response_json_bytes",
                RETRIEVAL_POLICY_PACK_DEFAULT_CAPS_V1["max_response_json_bytes"],
            )
        ),
    )


def build_retrieval_omission_explorer_catalog_v1() -> dict[str, Any]:
    pack = build_retrieval_policy_pack_default_v1()
    return {
        "retrieval_bounded_caps_runtime_schema_version": (
            PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_DEG01_GATE_ID_V1,
        "retrieval_policy_pack_id": pack.get("retrieval_policy_pack_id"),
        "retrieval_policy_pack_digest": retrieval_policy_pack_digest_v1(pack),
        "default_caps": policy_pack_caps_v1(pack),
        "rd_codes_registry": sorted(RETRIEVAL_RD_CODES_REGISTRY_V1),
        "omission_semantics_by_rd": dict(RETRIEVAL_OMISSION_SEMANTICS_BY_RD_V1),
        "substrate_health_states": sorted(RETRIEVAL_SUBSTRATE_HEALTH_STATES_V1),
        "omission_histogram": build_retrieval_omission_histogram_v1(),
        "degradation_propagation": list(pack.get("degradation_propagation") or []),
        "rules": [
            {"id": "RET-DEG-01", "text": "Closed RD-* registry; new codes need amendment"},
            {
                "id": "RET-DEG-02",
                "text": "Upstream growth must not remove authoritative hits (monotonicity)",
            },
        ],
        "http_behaviors": {
            "retrieval_response_too_large": 413,
            "retrieval_timeout": 503,
        },
        "doctrine_anchor": RETRIEVAL_BOUNDED_CAPS_SPEC_REF_V1,
    }


def _deg_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_DEG01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_deg01_rd_registry_closed_static() -> dict[str, Any]:
    errors: list[str] = []
    pack = build_retrieval_policy_pack_default_v1()
    pack_codes = pack.get("rd_codes")
    if not isinstance(pack_codes, list):
        errors.append("fixture_rd_codes_missing")
    else:
        for code in pack_codes:
            if code not in RETRIEVAL_RD_CODES_REGISTRY_V1:
                errors.append(f"fixture_unknown_rd:{code}")
    if len(RETRIEVAL_RD_CODES_REGISTRY_V1) < 10:
        errors.append("registry_too_small")
    try:
        normalize_retrieval_omission_law_row_v1(
            {"retrieval_omission_class": "RD-CAP-HITS", "upstream_trigger": "max_hits"}
        )
    except RetrievalBoundedCapsError as exc:
        errors.append(f"known_row_rejected:{exc}")
    try:
        normalize_retrieval_omission_law_row_v1({"retrieval_omission_class": "RD-UNKNOWN"})
    except RetrievalBoundedCapsError:
        pass
    else:
        errors.append("unknown_rd_should_fail")
    caps = apply_retrieval_policy_pack_defaults_v1("causal_chain", {"max_hits": 50})
    if caps.get("max_hits") != 50:
        errors.append("cap_merge_failed")
    try:
        apply_retrieval_policy_pack_defaults_v1("causal_chain", {"max_hits": 10_000})
    except RetrievalBoundedCapsError:
        pass
    else:
        errors.append("bypass_should_raise")
    reset_retrieval_omission_histogram_v1()
    record_retrieval_omissions_to_histogram_v1(
        [{"retrieval_omission_class": "RD-CAP-HITS", "trigger_count": 2}]
    )
    hist = build_retrieval_omission_histogram_v1()
    if hist.get("RD-CAP-HITS") != 2:
        errors.append("histogram_count")
    reset_retrieval_omission_histogram_v1()
    health = classify_substrate_health_v1(
        omissions=[{"retrieval_omission_class": "RD-CAP-HITS"}],
        retrieval_legality_class="retrieval_degraded",
    )
    if health != "degraded":
        errors.append("substrate_health_degraded")
    big = {"hits": ["x" * 300_000]}
    try:
        assert_retrieval_response_under_byte_cap_v1(big, max_response_json_bytes=100)
    except RetrievalBoundedCapsError as exc:
        if exc.http_status != 413:
            errors.append("wrong_413_status")
    else:
        errors.append("413_should_raise")
    try:
        assert_retrieval_wall_budget_v1(elapsed_ms=40_000, max_wall_ms=30_000)
    except RetrievalBoundedCapsError as exc:
        if exc.http_status != 503:
            errors.append("wrong_503_status")
    else:
        errors.append("503_should_raise")
    cat = build_retrieval_omission_explorer_catalog_v1()
    if cat["gate_id"] != GP07_DEG01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _deg_meta("gp07_deg01_rd_registry_closed", errors)

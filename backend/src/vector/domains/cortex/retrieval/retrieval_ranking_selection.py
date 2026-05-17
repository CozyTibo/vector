"""Phase 07 P07-12 — deterministic ranking + selection (**RET-RANK-01/02**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-ranking-selection-doctrine.md``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Final

PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_RANK01_GATE_ID_V1: Final[str] = "G-P07-RANK-01"

RETRIEVAL_RANKING_SELECTION_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-ranking-selection-doctrine.md"
)

RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1: Final[str] = (
    "RetrievalSelectionPolicyProfileV1_Default"
)

RETRIEVAL_SELECTION_POLICY_PROFILE_IDS_V1: Final[frozenset[str]] = frozenset(
    {
        RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
        "RetrievalSelectionPolicyProfileV1_LegalityFirst",
    }
)

RETRIEVAL_RD_CAP_HITS_V1: Final[str] = "RD-CAP-HITS"
RETRIEVAL_RD_CAP_CHRON_V1: Final[str] = "RD-CAP-CHRON"
RETRIEVAL_RD_CAP_EDGE_V1: Final[str] = "RD-CAP-EDGE"
RETRIEVAL_RD_CAP_LINEAGE_V1: Final[str] = "RD-CAP-LINEAGE"

RETRIEVAL_CAP_OMISSION_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        RETRIEVAL_RD_CAP_HITS_V1,
        RETRIEVAL_RD_CAP_CHRON_V1,
        RETRIEVAL_RD_CAP_EDGE_V1,
        RETRIEVAL_RD_CAP_LINEAGE_V1,
    }
)

_RANKING_DIMENSIONS_V1: Final[tuple[str, ...]] = (
    "provenance_integrity_rank",
    "replay_stability_rank",
    "chronology_legality_rank",
    "continuity_confidence_rank",
    "degradation_severity_rank",
    "traversal_coverage_rank",
    "recency_legality_rank",
    "evidence_completeness_rank",
    "tie_break_key",
)

_PROFILE_DIMENSION_ORDER_V1: Final[dict[str, tuple[str, ...]]] = {
    RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1: _RANKING_DIMENSIONS_V1,
    "RetrievalSelectionPolicyProfileV1_LegalityFirst": (
        "provenance_integrity_rank",
        "chronology_legality_rank",
        "replay_stability_rank",
        "continuity_confidence_rank",
        "degradation_severity_rank",
        "traversal_coverage_rank",
        "recency_legality_rank",
        "evidence_completeness_rank",
        "tie_break_key",
    ),
}

_RANK01_FORBIDDEN_KEY_PATTERN_V1: Final[re.Pattern[str]] = re.compile(
    r"(score|weight|similarity|embedding)",
    re.IGNORECASE,
)

_EVIDENCE_LEGALITY_RANK_V1: Final[dict[str, int]] = {
    "evidence_authoritative": 0,
    "evidence_degraded": 1,
    "evidence_candidate_only": 2,
    "evidence_replay_conflict": 3,
    "evidence_unverifiable": 4,
}

_REPLAY_POSTURE_RANK_V1: Final[dict[str, int]] = {
    "stable": 0,
    "partial": 1,
    "unsafe": 2,
}

_CHRONOLOGY_LEGALITY_RANK_V1: Final[dict[str, int]] = {
    "strict": 0,
    "chronology_degraded": 1,
    "degraded": 2,
    "illegal": 3,
    "unverifiable": 4,
}

_CONTINUITY_POSTURE_RANK_V1: Final[dict[str, int]] = {
    "stable": 0,
    "degraded": 1,
    "unverifiable": 2,
}

_CAP_FIELD_TO_RD_V1: Final[dict[str, str]] = {
    "max_hits": RETRIEVAL_RD_CAP_HITS_V1,
    "max_chronology_rows": RETRIEVAL_RD_CAP_CHRON_V1,
    "max_edges": RETRIEVAL_RD_CAP_EDGE_V1,
    "max_lineage_hops": RETRIEVAL_RD_CAP_LINEAGE_V1,
}

_RETRIEVAL_CAP_OVERFLOW_TOTAL_V1: dict[str, int] = defaultdict(int)


class RetrievalRankingSelectionError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_cap_overflow_totals_v1() -> dict[str, int]:
    return dict(_RETRIEVAL_CAP_OVERFLOW_TOTAL_V1)


def record_retrieval_cap_overflow_v1(rd_code: str, *, count: int = 1) -> None:
    if count > 0:
        _RETRIEVAL_CAP_OVERFLOW_TOTAL_V1[rd_code] += int(count)


def list_rank01_forbidden_selection_policy_keys_v1(
    selection_policy: Mapping[str, Any],
) -> list[str]:
    """**G-P07-RANK-01** / **RET-RANK-02** — reject float-score smuggling keys."""
    hits: list[str] = []
    for key in selection_policy:
        if not isinstance(key, str):
            continue
        if _RANK01_FORBIDDEN_KEY_PATTERN_V1.search(key):
            hits.append(key)
    return hits


def enforce_selection_policy_rank01_v1(selection_policy: Mapping[str, Any]) -> None:
    forbidden = list_rank01_forbidden_selection_policy_keys_v1(selection_policy)
    if forbidden:
        raise RetrievalRankingSelectionError(
            "selection_policy_forbidden_rank_keys",
            detail={"forbidden_keys": forbidden, "gate_id": GP07_RANK01_GATE_ID_V1},
        )
    for key, val in selection_policy.items():
        if isinstance(val, float):
            raise RetrievalRankingSelectionError(
                "selection_policy_float_coefficient_forbidden",
                detail={"key": key, "gate_id": GP07_RANK01_GATE_ID_V1},
            )


def resolve_selection_policy_profile_id_v1(raw: object | None) -> str:
    profile = str(raw or RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1).strip()
    if profile not in RETRIEVAL_SELECTION_POLICY_PROFILE_IDS_V1:
        raise RetrievalRankingSelectionError(
            "unknown_selection_policy_profile_id",
            detail={"profile_id": profile, "allowed": sorted(RETRIEVAL_SELECTION_POLICY_PROFILE_IDS_V1)},
        )
    return profile


def normalize_retrieval_selection_policy_v1(
    workload_class: str,
    selection_policy: Mapping[str, Any] | None,
    *,
    base_caps: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Merge workload caps + profile id; enforce **RET-RANK-01/02**."""
    from vector.domains.cortex.retrieval.query_contract import (
        selection_policy_caps_for_workload_v1,
    )

    caps: dict[str, Any] = dict(base_caps or selection_policy_caps_for_workload_v1(workload_class))
    raw = dict(selection_policy or {})
    enforce_selection_policy_rank01_v1(raw)
    profile_id = resolve_selection_policy_profile_id_v1(
        raw.get("selection_policy_profile_id")
    )
    for key, val in raw.items():
        if key == "selection_policy_profile_id":
            continue
        if key.startswith("max_"):
            try:
                caps[key] = int(val)
            except (TypeError, ValueError) as exc:
                raise RetrievalRankingSelectionError(
                    "invalid_selection_cap",
                    detail={"key": key, "value": val},
                ) from exc
        elif key.startswith("rank_priority_"):
            raise RetrievalRankingSelectionError(
                "selection_policy_coefficient_forbidden",
                detail={"key": key},
            )
    caps["selection_policy_profile_id"] = profile_id
    return caps


def _rank_from_map(value: str | None, table: Mapping[str, int], *, default: int = 9) -> int:
    if not value:
        return default
    return table.get(str(value).strip().lower(), default)


def compute_hit_rank_components_v1(
    hit: Mapping[str, Any],
    *,
    row: Any | None = None,
    temporal_scope: Mapping[str, Any] | None = None,
) -> dict[str, int | str]:
    prov_raw = hit.get("provenance")
    prov: dict[str, Any] = dict(prov_raw) if isinstance(prov_raw, dict) else {}
    row_chron = getattr(row, "chronology_legality_class", None) if row is not None else None
    row_continuity = getattr(row, "continuity_posture", None) if row is not None else None
    chron = str(prov.get("chronology_legality_class") or row_chron or "")
    continuity = str(prov.get("continuity_posture") or row_continuity or "")
    degradation_classes = prov.get("degradation_classes")
    deg_count = len(degradation_classes) if isinstance(degradation_classes, list) else 0
    missing = hit.get("ret_prov01_missing_digests")
    missing_count = len(missing) if isinstance(missing, list) else 0
    ref_raw = hit.get("artifact_ref")
    ref: dict[str, Any] = dict(ref_raw) if isinstance(ref_raw, dict) else {}
    if row is not None and not ref:
        row_ref = getattr(row, "artifact_ref_json", None)
        ref = dict(row_ref) if isinstance(row_ref, dict) else {}
    scope = temporal_scope or {}
    t_as_of = scope.get("t_as_of_unix_ns") or scope.get("graph_as_of_unix_ns")
    recency = 0
    if t_as_of is not None:
        observed = ref.get("materialization_observed_at_unix_ns") or ref.get(
            "canonical_processed_at_unix_ns"
        )
        if observed is not None:
            try:
                recency = max(0, int(observed) - int(t_as_of))
            except (TypeError, ValueError):
                recency = 0
    hop_count = 0
    if row is not None:
        summary = dict(getattr(row, "omission_summary", None) or {})
        hop_count = int(summary.get("traversal_hop_count") or summary.get("hop_count") or 0)
    tie = str(
        hit.get("retrieval_lookup_id")
        or ref.get("materialization_id")
        or ref.get("causal_chain_id")
        or ref.get("edge_id")
        or ref.get("walk_id")
        or ""
    )
    return {
        "provenance_integrity_rank": _rank_from_map(
            str(hit.get("evidence_legality_class", "")), _EVIDENCE_LEGALITY_RANK_V1
        ),
        "replay_stability_rank": _rank_from_map(
            str(prov.get("replay_posture", "")), _REPLAY_POSTURE_RANK_V1
        ),
        "chronology_legality_rank": _rank_from_map(chron, _CHRONOLOGY_LEGALITY_RANK_V1),
        "continuity_confidence_rank": _rank_from_map(continuity, _CONTINUITY_POSTURE_RANK_V1),
        "degradation_severity_rank": deg_count,
        "traversal_coverage_rank": hop_count,
        "recency_legality_rank": recency,
        "evidence_completeness_rank": missing_count,
        "tie_break_key": tie,
    }


def build_hit_ranking_tuple_v1(
    components: Mapping[str, int | str],
    *,
    dimension_order: Sequence[str],
) -> tuple[int | str, ...]:
    return tuple(components[d] for d in dimension_order)


def sort_hits_deterministically_v1(
    hits: Sequence[Mapping[str, Any]],
    *,
    profile_id: str,
    row: Any | None = None,
    temporal_scope: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """**RET-RANK-01** — integer tuple sort; lower rank tuple sorts first."""
    order = _PROFILE_DIMENSION_ORDER_V1[profile_id]
    keyed: list[tuple[tuple[int | str, ...], dict[str, Any], dict[str, int | str]]] = []
    for hit in hits:
        row_hit = dict(hit)
        components = compute_hit_rank_components_v1(
            row_hit, row=row, temporal_scope=temporal_scope
        )
        ranking_tuple = build_hit_ranking_tuple_v1(components, dimension_order=order)
        row_hit["_ranking_components"] = components
        row_hit["_ranking_tuple"] = list(ranking_tuple)
        keyed.append((ranking_tuple, row_hit, components))
    keyed.sort(key=lambda item: item[0])
    return [item[1] for item in keyed]


def list_cap_truncation_omissions_v1(
    *,
    cap_key: str,
    before_count: int,
    after_count: int,
) -> list[dict[str, Any]]:
    overflow = before_count - after_count
    if overflow <= 0:
        return []
    rd = _CAP_FIELD_TO_RD_V1.get(cap_key)
    if not rd:
        return []
    record_retrieval_cap_overflow_v1(rd, count=overflow)
    return [
        {
            "retrieval_omission_class": rd,
            "omission_semantics": "omitted_cap",
            "upstream_trigger": cap_key,
            "trigger_count": overflow,
        }
    ]


def apply_hit_metadata_caps_v1(
    hits: Sequence[Mapping[str, Any]],
    caps: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Emit ``RD-CAP-*`` when per-hit metadata counters exceed policy caps."""
    omissions: list[dict[str, Any]] = []
    for cap_key, meta_field in (
        ("max_chronology_rows", "chronology_row_count"),
        ("max_edges", "edge_count"),
        ("max_lineage_hops", "lineage_hop_count"),
    ):
        limit = int(caps.get(cap_key, 0) or 0)
        if limit < 1:
            continue
        total = sum(int(h.get(meta_field, 0) or 0) for h in hits)
        if total > limit:
            omissions.extend(
                list_cap_truncation_omissions_v1(
                    cap_key=cap_key,
                    before_count=total,
                    after_count=limit,
                )
            )
    return omissions


def apply_retrieval_selection_caps_v1(
    hits: Sequence[Mapping[str, Any]],
    caps: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Bounded caps after sort → ``RD-CAP-*`` omissions."""
    max_hits = int(caps.get("max_hits", 100))
    if max_hits < 1:
        raise RetrievalRankingSelectionError("invalid_max_hits_cap")
    sorted_hits = [dict(h) for h in hits]
    omissions: list[dict[str, Any]] = []
    if len(sorted_hits) > max_hits:
        omissions.extend(
            list_cap_truncation_omissions_v1(
                cap_key="max_hits",
                before_count=len(sorted_hits),
                after_count=max_hits,
            )
        )
        sorted_hits = sorted_hits[:max_hits]
    omissions.extend(apply_hit_metadata_caps_v1(sorted_hits, caps))
    return sorted_hits, omissions


def build_selection_sort_trace_v1(
    hits: Sequence[Mapping[str, Any]],
    *,
    profile_id: str,
) -> dict[str, Any]:
    """Admin query-debugger sort trace."""
    order = list(_PROFILE_DIMENSION_ORDER_V1[profile_id])
    ranked: list[dict[str, Any]] = []
    for idx, hit in enumerate(hits):
        components = hit.get("_ranking_components")
        if not isinstance(components, dict):
            components = {}
        ranked.append(
            {
                "ordinal": idx,
                "retrieval_lookup_id": hit.get("retrieval_lookup_id"),
                "ranking_tuple": hit.get("_ranking_tuple") or [],
                "ranking_components": dict(components),
            }
        )
    return {
        "selection_policy_profile_id": profile_id,
        "dimension_order": order,
        "ranked_hits": ranked,
    }


def strip_internal_ranking_fields_v1(hits: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for hit in hits:
        row = {k: v for k, v in dict(hit).items() if not k.startswith("_ranking")}
        out.append(row)
    return out


def apply_retrieval_ranking_and_selection_v1(
    *,
    hits: Sequence[Mapping[str, Any]],
    caps: Mapping[str, Any],
    row: Any | None = None,
    temporal_scope: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Sort hits deterministically then apply caps (**RET-RANK-01**, query contract §6)."""
    profile_id = resolve_selection_policy_profile_id_v1(
        caps.get("selection_policy_profile_id")
    )
    sorted_hits = sort_hits_deterministically_v1(
        hits,
        profile_id=profile_id,
        row=row,
        temporal_scope=temporal_scope,
    )
    sort_trace = build_selection_sort_trace_v1(sorted_hits, profile_id=profile_id)
    capped_hits, cap_omissions = apply_retrieval_selection_caps_v1(sorted_hits, caps)
    public_hits = strip_internal_ranking_fields_v1(capped_hits)
    return {
        "hits": public_hits,
        "omissions": cap_omissions,
        "selection_sort_trace": sort_trace,
        "selection_policy_profile_id": profile_id,
        "cap_overflow_totals": get_retrieval_cap_overflow_totals_v1(),
    }


def build_retrieval_ranking_selection_catalog_v1() -> dict[str, Any]:
    return {
        "retrieval_ranking_selection_runtime_schema_version": (
            PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_RANK01_GATE_ID_V1,
        "selection_policy_profile_ids": sorted(RETRIEVAL_SELECTION_POLICY_PROFILE_IDS_V1),
        "default_profile_id": RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
        "ranking_dimensions": list(_RANKING_DIMENSIONS_V1),
        "profile_dimension_orders": {
            k: list(v) for k, v in sorted(_PROFILE_DIMENSION_ORDER_V1.items())
        },
        "cap_omission_classes": sorted(RETRIEVAL_CAP_OMISSION_CLASSES_V1),
        "cap_overflow_totals": get_retrieval_cap_overflow_totals_v1(),
        "rules": [
            {"id": "RET-RANK-01", "text": "Integer tuple sort only; profiles reorder dimensions"},
            {
                "id": "RET-RANK-02",
                "text": "Forbidden keys: score, weight, similarity, embedding",
            },
        ],
        "doctrine_anchor": RETRIEVAL_RANKING_SELECTION_SPEC_REF_V1,
    }


def _rank_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_RANK01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_rank01_no_float_scores_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        enforce_selection_policy_rank01_v1({"similarity_score": 1})
    except RetrievalRankingSelectionError:
        pass
    else:
        errors.append("forbidden_key_not_rejected")
    try:
        enforce_selection_policy_rank01_v1({"max_hits": 10, "blend_weight": 0.5})
    except RetrievalRankingSelectionError:
        pass
    else:
        errors.append("float_coefficient_not_rejected")
    hits = [
        {
            "retrieval_lookup_id": "sha256:" + "b" * 64,
            "evidence_legality_class": "evidence_degraded",
            "provenance": {"replay_posture": "partial", "chronology_legality_class": "strict"},
        },
        {
            "retrieval_lookup_id": "sha256:" + "a" * 64,
            "evidence_legality_class": "evidence_authoritative",
            "provenance": {"replay_posture": "stable", "chronology_legality_class": "strict"},
        },
    ]
    sorted_once = sort_hits_deterministically_v1(
        hits, profile_id=RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1
    )
    sorted_twice = sort_hits_deterministically_v1(
        list(reversed(hits)),
        profile_id=RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
    )
    ids_a = [h["retrieval_lookup_id"] for h in sorted_once]
    ids_b = [h["retrieval_lookup_id"] for h in sorted_twice]
    if ids_a != ids_b:
        errors.append("sort_not_deterministic")
    caps = normalize_retrieval_selection_policy_v1(
        "causal_chain",
        {"max_hits": 1, "selection_policy_profile_id": RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1},
    )
    out = apply_retrieval_ranking_and_selection_v1(hits=sorted_once, caps=caps)
    if not any(
        o.get("retrieval_omission_class") == RETRIEVAL_RD_CAP_HITS_V1 for o in out["omissions"]
    ):
        errors.append("cap_hits_omission_missing")
    if len(out["hits"]) != 1:
        errors.append("cap_hits_not_applied")
    cat = build_retrieval_ranking_selection_catalog_v1()
    if cat["gate_id"] != GP07_RANK01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _rank_meta("gp07_rank01_no_float_scores", errors)

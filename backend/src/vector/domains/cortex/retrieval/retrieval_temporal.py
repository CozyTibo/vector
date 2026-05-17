"""Phase 07 P07-11 — temporal retrieval model (**RET-TEMP-01..04**).

Normative: ``DOCS/cortex/retrieval/phase-07-temporal-retrieval-doctrine.md``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_TEMPORAL_SCOPE_SCHEMA_VERSION_V1: Final[int] = 1

GP07_TEMP01_GATE_ID_V1: Final[str] = "G-P07-TEMP-01"

RETRIEVAL_TEMPORAL_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-temporal-retrieval-doctrine.md"
)

RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1: Final[frozenset[str]] = frozenset(
    {
        "t_as_of_unix_ns",
        "window_start_ns",
        "window_end_ns",
        "replay_epoch",
        "export_sequence",
        "graph_as_of_unix_ns",
    }
)

RETRIEVAL_RD_TEMPORAL_FUTURE_V1: Final[str] = "RD-TEMPORAL-FUTURE"

RETRIEVAL_RD_TEMPORAL_PIN_V1: Final[str] = "RD-TEMPORAL-PIN"

RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1: Final[str] = "omitted_temporal_future"

_TEMPORAL_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {
        "materialization_as_of",
        "chronology_window",
        "degradation_survey",
        "ownership_continuity",
        "replay_equivalence",
    }
)

_TCRE_TEMPORAL_READ_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {
        "execution_continuity",
        "chronology_window",
        "causal_chain",
        "causal_edge",
        "degradation_survey",
        "dependency_propagation",
        "replay_divergence",
        "replay_equivalence",
        "materialization_as_of",
        "ownership_continuity",
    }
)


class RetrievalTemporalError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def normalize_retrieval_temporal_scope_v1(
    temporal_scope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Canonical ``temporal_scope_v1`` (sorted keys, coerced numerics)."""
    if not temporal_scope:
        return {"schema_version": RETRIEVAL_TEMPORAL_SCOPE_SCHEMA_VERSION_V1}
    out: dict[str, Any] = {"schema_version": RETRIEVAL_TEMPORAL_SCOPE_SCHEMA_VERSION_V1}
    for key in sorted(temporal_scope):
        if key not in RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1:
            continue
        val = temporal_scope[key]
        if val is None or (isinstance(val, str) and not val.strip()):
            continue
        if key in ("t_as_of_unix_ns", "window_start_ns", "window_end_ns", "graph_as_of_unix_ns"):
            out[key] = int(val)
        else:
            out[key] = str(val).strip()
    return out


def validate_retrieval_temporal_scope_v1(
    temporal_scope: Mapping[str, Any],
    *,
    workload_class: str,
    replay_pins: Mapping[str, Any] | None = None,
) -> None:
    """Freeze ``temporal_scope_v1`` schema + workload-required fields."""
    unknown = [
        k
        for k in temporal_scope
        if k not in RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1
        and k != "schema_version"
    ]
    if unknown:
        raise RetrievalTemporalError(
            "temporal_scope_unknown_fields",
            detail={"unknown": unknown},
        )
    for ns_key in ("t_as_of_unix_ns", "window_start_ns", "window_end_ns", "graph_as_of_unix_ns"):
        if ns_key not in temporal_scope:
            continue
        try:
            ns_val = int(temporal_scope[ns_key])
        except (TypeError, ValueError) as exc:
            raise RetrievalTemporalError(
                "temporal_scope_invalid_ns_field",
                detail={"field": ns_key},
            ) from exc
        if ns_val < 0:
            raise RetrievalTemporalError(
                "temporal_scope_negative_ns",
                detail={"field": ns_key, "value": ns_val},
            )
    start = temporal_scope.get("window_start_ns")
    end = temporal_scope.get("window_end_ns")
    if start is not None and end is not None:
        if int(start) >= int(end):
            raise RetrievalTemporalError(
                "temporal_scope_invalid_window",
                detail={"window_start_ns": start, "window_end_ns": end},
            )
    if workload_class in _TEMPORAL_SCOPED_WORKLOADS_V1:
        _assert_workload_temporal_requirements_v1(
            temporal_scope,
            workload_class=workload_class,
            replay_pins=replay_pins,
        )


def _assert_workload_temporal_requirements_v1(
    temporal_scope: Mapping[str, Any],
    *,
    workload_class: str,
    replay_pins: Mapping[str, Any] | None = None,
) -> None:
    if workload_class == "materialization_as_of":
        if "t_as_of_unix_ns" not in temporal_scope and "graph_as_of_unix_ns" not in temporal_scope:
            raise RetrievalTemporalError(
                "temporal_scope_missing_t_as_of",
                detail={"workload_class": workload_class},
            )
    if workload_class == "chronology_window":
        has_window = "window_start_ns" in temporal_scope and "window_end_ns" in temporal_scope
        if not has_window:
            raise RetrievalTemporalError(
                "temporal_scope_missing_window",
                detail={"workload_class": workload_class},
            )
    if workload_class == "degradation_survey":
        if "window_start_ns" not in temporal_scope or "window_end_ns" not in temporal_scope:
            raise RetrievalTemporalError(
                "temporal_scope_missing_window",
                detail={"workload_class": workload_class},
            )
    if workload_class == "ownership_continuity":
        if "t_as_of_unix_ns" not in temporal_scope:
            raise RetrievalTemporalError(
                "temporal_scope_missing_t_as_of",
                detail={"workload_class": workload_class},
            )
    if workload_class == "replay_equivalence":
        pins = replay_pins if isinstance(replay_pins, dict) else {}
        has_epoch = "replay_epoch" in temporal_scope or bool(
            str(pins.get("index_epoch") or temporal_scope.get("replay_epoch") or "").strip()
        )
        if not has_epoch:
            raise RetrievalTemporalError(
                "temporal_scope_missing_replay_epoch",
                detail={"workload_class": workload_class},
            )


def workload_requires_temporal_scope_v1(workload_class: str) -> bool:
    return workload_class in _TEMPORAL_SCOPED_WORKLOADS_V1


def temporal_scope_has_meaningful_fields_v1(temporal_scope: Mapping[str, Any]) -> bool:
    return any(k for k in temporal_scope if k != "schema_version")


def artifact_valid_at_t_as_of_v1(
    *,
    t_as_of_unix_ns: int,
    artifact_observed_at_unix_ns: int | None,
) -> bool:
    """**RET-TEMP-01** — selection only; never rewrite history."""
    if artifact_observed_at_unix_ns is None:
        return True
    return int(artifact_observed_at_unix_ns) <= int(t_as_of_unix_ns)


def list_ret_temp02_pin_violations_v1(
    replay_pins: Mapping[str, Any] | None,
    *,
    workload_class: str,
    temporal_scope: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """**RET-TEMP-02** — TCRE reads require pinned ``tcre_policy_bundle_digest``."""
    if workload_class not in _TCRE_TEMPORAL_READ_WORKLOADS_V1:
        return []
    scope = temporal_scope or {}
    if not temporal_scope_has_meaningful_fields_v1(scope) and workload_class not in _TEMPORAL_SCOPED_WORKLOADS_V1:
        return []
    pins = replay_pins if isinstance(replay_pins, dict) else {}
    if str(pins.get("tcre_policy_bundle_digest") or "").strip():
        return []
    return [
        {
            "retrieval_omission_class": RETRIEVAL_RD_TEMPORAL_PIN_V1,
            "omission_semantics": "omitted_upstream_gap",
            "upstream_trigger": "ret_temp02_missing_tcre_policy_pin",
            "trigger_count": 1,
        }
    ]


def list_ret_temp03_future_materialization_omissions_v1(
    *,
    temporal_scope: Mapping[str, Any],
    artifact_ref: Mapping[str, Any] | None,
    omission_summary: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """**RET-TEMP-03** — late arrivals after ``t_as_of`` → ``omitted_temporal_future``."""
    t_as_of = temporal_scope.get("t_as_of_unix_ns")
    if t_as_of is None:
        t_as_of = temporal_scope.get("graph_as_of_unix_ns")
    if t_as_of is None:
        return []
    ref = artifact_ref if isinstance(artifact_ref, dict) else {}
    summary = omission_summary if isinstance(omission_summary, dict) else {}
    observed_keys = (
        "materialization_observed_at_unix_ns",
        "canonical_processed_at_unix_ns",
        "observed_at_unix_ns",
    )
    future_count = 0
    for key in observed_keys:
        raw = ref.get(key) or summary.get(key)
        if raw is None:
            continue
        try:
            observed = int(raw)
        except (TypeError, ValueError):
            continue
        if observed > int(t_as_of):
            future_count += 1
    if future_count == 0:
        return []
    return [
        {
            "retrieval_omission_class": RETRIEVAL_RD_TEMPORAL_FUTURE_V1,
            "omission_semantics": RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1,
            "upstream_trigger": "late_arrival_after_t_as_of",
            "trigger_count": future_count,
        }
    ]


def extract_upstream_skew_flags_v1(
    *,
    row: Any | None = None,
    artifact_ref: Mapping[str, Any] | None = None,
    omission_summary: Mapping[str, Any] | None = None,
) -> list[str]:
    flags: list[str] = []
    ref = artifact_ref if isinstance(artifact_ref, dict) else {}
    summary = omission_summary if isinstance(omission_summary, dict) else {}
    if row is not None:
        ref = dict(getattr(row, "artifact_ref_json", None) or ref or {})
        summary = dict(getattr(row, "omission_summary", None) or summary or {})
    for container in (ref, summary):
        raw = container.get("skew_flags") or container.get("chronology_skew_flags")
        if isinstance(raw, list):
            for item in raw:
                s = str(item).strip()
                if s and s not in flags:
                    flags.append(s)
        elif isinstance(raw, dict):
            for key in sorted(raw):
                if raw[key] and key not in flags:
                    flags.append(key)
    return sorted(flags)


def apply_skew_copy_through_to_hits_v1(
    hits: Sequence[Mapping[str, Any]],
    *,
    skew_flags: Sequence[str],
) -> list[dict[str, Any]]:
    """**RET-TEMP-04** — copy Phase 06 skew flags into hit provenance (no recompute)."""
    if not skew_flags:
        return [dict(h) for h in hits]
    out: list[dict[str, Any]] = []
    for hit in hits:
        row_hit = dict(hit)
        prov = dict(row_hit.get("provenance") or {})
        prov["skew_flags"] = list(skew_flags)
        prov["skew_copy_through"] = True
        row_hit["provenance"] = prov
        out.append(row_hit)
    return out


def assess_temporal_legality_envelope_v1(
    *,
    chronology_legality_classes: Sequence[str],
    replay_conflict: bool = False,
) -> dict[str, Any]:
    """Temporal legality aggregate (floors query legality)."""
    classes = [str(c) for c in chronology_legality_classes if c]
    if replay_conflict:
        floor = "retrieval_unverifiable"
        reason = "replay_conflict_in_window"
    elif any(c == "chronology_degraded" for c in classes):
        floor = "retrieval_degraded"
        reason = "chronology_degraded_in_window"
    elif classes and all(c == "strict" for c in classes):
        floor = "retrieval_replay_safe"
        reason = "all_chronology_strict"
    elif not classes:
        floor = "retrieval_degraded"
        reason = "no_chronology_evidence"
    else:
        floor = "retrieval_degraded"
        reason = "mixed_chronology_legality"
    return {
        "temporal_legality_floor": floor,
        "chronology_legality_classes": classes,
        "replay_conflict": replay_conflict,
        "reason": reason,
    }


def build_temporal_skew_audit_v1(
    *,
    skew_flags: Sequence[str],
    temporal_scope: Mapping[str, Any],
    ret_temp02_violations: Sequence[Mapping[str, Any]],
    ret_temp03_omissions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "skew_flags": list(skew_flags),
        "temporal_scope": dict(temporal_scope),
        "ret_temp02_pin_violations": len(ret_temp02_violations),
        "ret_temp03_future_omissions": len(ret_temp03_omissions),
        "skew_copy_through": bool(skew_flags),
    }


def apply_retrieval_temporal_law_to_query_v1(
    *,
    envelope: Mapping[str, Any],
    temporal_scope: Mapping[str, Any],
    row: Any,
    hits: Sequence[Mapping[str, Any]],
    omissions: Sequence[Mapping[str, Any]],
    replay_pins: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply **RET-TEMP-01..04** to hits + omissions; return temporal envelope + audit."""
    wl = str(envelope.get("workload_class", ""))
    pins = replay_pins if isinstance(replay_pins, dict) else {}
    out_omissions = [dict(o) for o in omissions]
    out_omissions.extend(
        list_ret_temp02_pin_violations_v1(
            pins, workload_class=wl, temporal_scope=temporal_scope
        )
    )
    ref = dict(getattr(row, "artifact_ref_json", None) or {})
    summary = dict(getattr(row, "omission_summary", None) or {})
    out_omissions.extend(
        list_ret_temp03_future_materialization_omissions_v1(
            temporal_scope=temporal_scope,
            artifact_ref=ref,
            omission_summary=summary,
        )
    )
    skew_flags = extract_upstream_skew_flags_v1(row=row)
    out_hits = apply_skew_copy_through_to_hits_v1(hits, skew_flags=skew_flags)
    chron_classes = [str(getattr(row, "chronology_legality_class", ""))]
    for hit in out_hits:
        prov = hit.get("provenance")
        if isinstance(prov, dict) and prov.get("chronology_legality_class"):
            chron_classes.append(str(prov["chronology_legality_class"]))
    replay_conflict = bool(
        (envelope.get("upstream_triggers") or {}).get("replay_conflicted_identity")
    )
    temporal_envelope = assess_temporal_legality_envelope_v1(
        chronology_legality_classes=chron_classes,
        replay_conflict=replay_conflict,
    )
    temp02_rows = [
        o
        for o in out_omissions
        if str(o.get("retrieval_omission_class")) == RETRIEVAL_RD_TEMPORAL_PIN_V1
    ]
    temp03_rows = [
        o
        for o in out_omissions
        if str(o.get("retrieval_omission_class")) == RETRIEVAL_RD_TEMPORAL_FUTURE_V1
    ]
    skew_audit = build_temporal_skew_audit_v1(
        skew_flags=skew_flags,
        temporal_scope=temporal_scope,
        ret_temp02_violations=temp02_rows,
        ret_temp03_omissions=temp03_rows,
    )
    return {
        "hits": out_hits,
        "omissions": out_omissions,
        "temporal_legality_envelope": temporal_envelope,
        "temporal_skew_audit": skew_audit,
        "temporal_legality_floor": temporal_envelope["temporal_legality_floor"],
    }


def build_retrieval_temporal_explorer_catalog_v1() -> dict[str, Any]:
    """Admin temporal explorer — schema + rules (**G-P07-TEMP-01**)."""
    return {
        "retrieval_temporal_runtime_schema_version": (
            PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_TEMP01_GATE_ID_V1,
        "temporal_scope_schema_version": RETRIEVAL_TEMPORAL_SCOPE_SCHEMA_VERSION_V1,
        "temporal_scope_fields": sorted(RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1),
        "temporal_scoped_workloads": sorted(_TEMPORAL_SCOPED_WORKLOADS_V1),
        "tcre_temporal_read_workloads": sorted(_TCRE_TEMPORAL_READ_WORKLOADS_V1),
        "query_patterns": [
            {
                "pattern": "execution_state_as_of",
                "workload_class": "materialization_as_of",
            },
            {"pattern": "continuity_evolution", "workload_class": "chronology_window"},
            {"pattern": "degradation_over_time", "workload_class": "degradation_survey"},
            {
                "pattern": "ownership_transitions",
                "workload_class": "ownership_continuity",
            },
            {"pattern": "replay_epoch_compare", "workload_class": "replay_equivalence"},
        ],
        "rules": [
            {
                "id": "RET-TEMP-01",
                "text": "t_as_of selects valid-at-T artifacts only; never rewrites history",
            },
            {
                "id": "RET-TEMP-02",
                "text": "Pin tcre_policy_bundle_digest when reading TCRE temporal artifacts",
            },
            {
                "id": "RET-TEMP-03",
                "text": "Late materializations after t_as_of → omitted_temporal_future",
            },
            {
                "id": "RET-TEMP-04",
                "text": "Copy Phase 06 skew flags into provenance; do not recompute",
            },
        ],
        "omission_classes": {
            RETRIEVAL_RD_TEMPORAL_FUTURE_V1: RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1,
            RETRIEVAL_RD_TEMPORAL_PIN_V1: "omitted_upstream_gap",
        },
        "doctrine_anchor": RETRIEVAL_TEMPORAL_SPEC_REF_V1,
    }


def _temp_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_TEMP01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_temp01_temporal_scope_schema_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1) < 5:
        errors.append("temporal_scope_field_count")
    scope = normalize_retrieval_temporal_scope_v1(
        {
            "t_as_of_unix_ns": 100,
            "window_start_ns": 1,
            "window_end_ns": 10,
            "replay_epoch": "epoch-a",
        }
    )
    try:
        validate_retrieval_temporal_scope_v1(scope, workload_class="causal_chain")
    except RetrievalTemporalError as exc:
        errors.append(f"causal_chain_scope_rejected:{exc}")
    try:
        validate_retrieval_temporal_scope_v1(
            {"window_start_ns": 10, "window_end_ns": 5},
            workload_class="causal_chain",
        )
    except RetrievalTemporalError as exc:
        if exc.code != "temporal_scope_invalid_window":
            errors.append(f"window_check:{exc.code}")
    else:
        errors.append("invalid_window_should_fail")
    try:
        validate_retrieval_temporal_scope_v1(
            normalize_retrieval_temporal_scope_v1(
                {"window_start_ns": 1, "window_end_ns": 100}
            ),
            workload_class="chronology_window",
        )
    except RetrievalTemporalError as exc:
        errors.append(f"chronology_window_valid:{exc}")
    future = list_ret_temp03_future_materialization_omissions_v1(
        temporal_scope={"t_as_of_unix_ns": 50},
        artifact_ref={"materialization_observed_at_unix_ns": 99},
    )
    if not future or future[0].get("omission_semantics") != RETRIEVAL_OMISSION_SEMANTICS_TEMPORAL_FUTURE_V1:
        errors.append("ret_temp03_future_omission")
    if artifact_valid_at_t_as_of_v1(t_as_of_unix_ns=50, artifact_observed_at_unix_ns=99):
        errors.append("ret_temp01_future_should_be_invalid")
    if artifact_valid_at_t_as_of_v1(t_as_of_unix_ns=50, artifact_observed_at_unix_ns=40) is not True:
        errors.append("ret_temp01_should_allow_past")
    env = assess_temporal_legality_envelope_v1(
        chronology_legality_classes=["strict", "strict"],
        replay_conflict=False,
    )
    if env.get("temporal_legality_floor") != "retrieval_replay_safe":
        errors.append("temporal_envelope_strict")
    degraded = assess_temporal_legality_envelope_v1(
        chronology_legality_classes=["strict", "chronology_degraded"],
    )
    if degraded.get("temporal_legality_floor") != "retrieval_degraded":
        errors.append("temporal_envelope_degraded")
    cat = build_retrieval_temporal_explorer_catalog_v1()
    if cat["gate_id"] != GP07_TEMP01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _temp_meta("gp07_temp01_temporal_scope_schema", errors)

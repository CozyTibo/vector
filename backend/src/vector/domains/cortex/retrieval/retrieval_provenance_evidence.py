"""Phase 07 P07-10 — retrieval provenance + evidence envelopes (**RET-PROV-01/02**).

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-provenance-evidence-doctrine.md``.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import (
    format_retrieval_lookup_id_v1,
)

PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_PROVENANCE_ENVELOPE_SCHEMA_VERSION_V1: Final[int] = 1

GP07_PROV01_GATE_ID_V1: Final[str] = "G-P07-PROV-01"

RETRIEVAL_PROVENANCE_EVIDENCE_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-provenance-evidence-doctrine.md"
)

RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "evidence_authoritative",
        "evidence_degraded",
        "evidence_candidate_only",
        "evidence_replay_conflict",
        "evidence_unverifiable",
    }
)

RETRIEVAL_OMISSION_SEMANTICS_CLASSES_V1: Final[frozenset[str]] = frozenset(
    {
        "omitted_cap",
        "omitted_upstream_gap",
        "omitted_legality",
        "omitted_replay_unsafe",
        "omitted_exploration_partition",
        "omitted_addressing_partial",
        "omitted_temporal_future",
    }
)

RETRIEVAL_PROVENANCE_UPSTREAM_DIGEST_KEYS_V1: Final[frozenset[str]] = frozenset(
    {
        "raw_record_digest",
        "canonical_materialization_digest",
        "org_link_digest",
        "walk_result_hash",
        "tcre_policy_bundle_digest",
        "chronology_receipt_digest",
        "causal_chain_id",
        "retrieval_index_entry_digest",
    }
)

RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "provenance_envelope_id",
        "tenant_id",
        "replay_posture",
        "omission_state",
        "evidence_legality_class",
        "upstream_digests",
        "degradation_classes",
    }
)

_RD_TO_OMISSION_SEMANTICS_V1: Final[dict[str, str]] = {
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
    "RD-INDEX-STALE": "omitted_upstream_gap",
    "RD-POLICY-MISMATCH": "omitted_legality",
    "RD-ADDRESSING-UNRESOLVED": "omitted_addressing_partial",
    "RD-TEMPORAL-FUTURE": "omitted_temporal_future",
    "RD-TEMPORAL-PIN": "omitted_upstream_gap",
}

_WORKLOAD_REQUIRED_UPSTREAM_DIGESTS_V1: Final[dict[str, frozenset[str]]] = {
    "causal_chain": frozenset({"causal_chain_id", "retrieval_index_entry_digest"}),
    "causal_edge": frozenset({"causal_chain_id", "retrieval_index_entry_digest"}),
    "chronology_window": frozenset({"retrieval_index_entry_digest"}),
    "materialization_as_of": frozenset({"retrieval_index_entry_digest"}),
    "traversal_lineage": frozenset({"walk_result_hash", "retrieval_index_entry_digest"}),
    "replay_equivalence": frozenset({"retrieval_index_entry_digest"}),
    "lineage_explorer": frozenset({"retrieval_index_entry_digest"}),
}


class RetrievalProvenanceEvidenceError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def hash_provenance_envelope_id_v1(envelope_body: Mapping[str, Any]) -> str:
    """Content-addressed ``provenance_envelope_id`` (sha256 hex)."""
    return hash_reasoning_canonical_json_sha256_v1(envelope_body)


def classify_evidence_legality_class_v1(
    *,
    chronology_legality_class: str,
    causal_legality_class: str,
    replay_posture: str,
    execution_partition: str,
    link_authority: str | None = None,
    replay_identity_match: bool = True,
    prov01_degraded_floor: bool = False,
) -> str:
    if not replay_identity_match or replay_posture == "unsafe":
        return "evidence_replay_conflict"
    if chronology_legality_class in ("illegal", "unverifiable") or causal_legality_class in (
        "illegal",
        "unverifiable",
    ):
        return "evidence_unverifiable"
    if execution_partition == "authoritative" and link_authority == "candidate":
        return RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
    if prov01_degraded_floor:
        return "evidence_degraded"
    if (
        chronology_legality_class not in ("strict",)
        or causal_legality_class not in ("verified",)
        or replay_posture != "stable"
    ):
        return "evidence_degraded"
    return "evidence_authoritative"


def list_ret_prov01_missing_upstream_digests_v1(
    *,
    workload_class: str,
    upstream_digests: Mapping[str, Any],
) -> list[str]:
    """**RET-PROV-01** — required digests for workload must be present."""
    required = _WORKLOAD_REQUIRED_UPSTREAM_DIGESTS_V1.get(workload_class, frozenset())
    missing: list[str] = []
    for key in sorted(required):
        val = upstream_digests.get(key)
        if val is None or not str(val).strip():
            missing.append(key)
    return missing


def build_upstream_digests_for_index_hit_v1(
    *,
    row: Any,
    retrieval_lookup_id: str,
    replay_pins: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    artifact_ref = dict(getattr(row, "artifact_ref_json", None) or {})
    entry_body = {
        "retrieval_lookup_id": retrieval_lookup_id,
        "index_kind": row.index_kind,
        "index_key": row.index_key,
        "replay_identity": row.replay_identity,
        "traversal_epoch": row.traversal_epoch,
        "chronology_legality_class": row.chronology_legality_class,
        "causal_legality_class": row.causal_legality_class,
        "retrieval_policy_digest": row.retrieval_policy_digest,
    }
    digests: dict[str, str] = {
        "retrieval_index_entry_digest": hash_reasoning_canonical_json_sha256_v1(entry_body),
    }
    chain_id = artifact_ref.get("causal_chain_id")
    if chain_id:
        digests["causal_chain_id"] = str(chain_id)
    pins = replay_pins if isinstance(replay_pins, dict) else {}
    tcre = pins.get("tcre_policy_bundle_digest")
    if tcre:
        digests["tcre_policy_bundle_digest"] = str(tcre)
    walk_hash = pins.get("walk_result_hash")
    if walk_hash:
        digests["walk_result_hash"] = str(walk_hash)
    return digests


def build_retrieval_provenance_envelope_v1(
    *,
    tenant_id: uuid.UUID | str,
    replay_posture: str,
    evidence_legality_class: str,
    upstream_digests: Mapping[str, Any],
    omission_state: str = "none",
    chronology_legality_class: str | None = None,
    causal_legality_class: str | None = None,
    continuity_posture: str | None = None,
    lineage_coverage: str | None = None,
    traversal_binding_state: str | None = None,
    degradation_classes: Sequence[str] | None = None,
    artifact_kind: str | None = None,
    provenance_class: str | None = None,
    index_epoch: str | None = None,
) -> dict[str, Any]:
    """Build ``RetrievalProvenanceEnvelopeV1`` with content-addressed id."""
    deg = sorted({str(c) for c in (degradation_classes or []) if str(c).strip()})
    body: dict[str, Any] = {
        "schema_version": RETRIEVAL_PROVENANCE_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "replay_posture": replay_posture,
        "omission_state": omission_state,
        "evidence_legality_class": evidence_legality_class,
        "upstream_digests": {k: str(v) for k, v in upstream_digests.items() if v is not None},
        "degradation_classes": deg,
    }
    if chronology_legality_class:
        body["chronology_legality_class"] = chronology_legality_class
    if causal_legality_class:
        body["causal_legality_class"] = causal_legality_class
    if continuity_posture:
        body["continuity_posture"] = continuity_posture
    if lineage_coverage:
        body["lineage_coverage"] = lineage_coverage
    if traversal_binding_state:
        body["traversal_binding_state"] = traversal_binding_state
    if artifact_kind:
        body["artifact_kind"] = artifact_kind
    if provenance_class:
        body["provenance_class"] = provenance_class
    if index_epoch:
        body["index_epoch"] = index_epoch
    envelope_id = hash_provenance_envelope_id_v1(body)
    body["provenance_envelope_id"] = envelope_id
    return body


def validate_retrieval_provenance_envelope_v1(envelope: Mapping[str, Any]) -> None:
    missing = [f for f in RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1 if f not in envelope]
    if missing:
        raise RetrievalProvenanceEvidenceError(
            "provenance_envelope_missing_fields",
            detail={"missing": missing},
        )
    ev = str(envelope.get("evidence_legality_class", ""))
    if ev not in RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1:
        raise RetrievalProvenanceEvidenceError("invalid_evidence_legality_class")
    upstream = envelope.get("upstream_digests")
    if not isinstance(upstream, dict):
        raise RetrievalProvenanceEvidenceError("upstream_digests_required")
    for key in upstream:
        if key not in RETRIEVAL_PROVENANCE_UPSTREAM_DIGEST_KEYS_V1:
            raise RetrievalProvenanceEvidenceError(
                "unknown_upstream_digest_key",
                detail={"key": key},
            )


def build_retrieval_evidence_hit_v1(
    *,
    tenant_id: uuid.UUID | str,
    retrieval_lookup_id: str,
    row: Any,
    replay_posture: str,
    workload_class: str,
    execution_partition: str,
    replay_pins: Mapping[str, Any] | None = None,
    replay_identity_match: bool = True,
    partial_addressing: bool = False,
    lineage_coverage: str = "unknown",
) -> dict[str, Any]:
    upstream = build_upstream_digests_for_index_hit_v1(
        row=row,
        retrieval_lookup_id=retrieval_lookup_id,
        replay_pins=replay_pins,
    )
    missing = list_ret_prov01_missing_upstream_digests_v1(
        workload_class=workload_class,
        upstream_digests=upstream,
    )
    evidence_class = classify_evidence_legality_class_v1(
        chronology_legality_class=row.chronology_legality_class,
        causal_legality_class=row.causal_legality_class,
        replay_posture=replay_posture,
        execution_partition=execution_partition,
        replay_identity_match=replay_identity_match,
        prov01_degraded_floor=bool(missing),
    )
    omission_state = "partial" if partial_addressing or missing else "none"
    degradation_classes = list(missing)
    if missing:
        degradation_classes.append("RD-PROV-01-MISSING-DIGEST")
    provenance = build_retrieval_provenance_envelope_v1(
        tenant_id=tenant_id,
        replay_posture=replay_posture,
        evidence_legality_class=evidence_class,
        upstream_digests=upstream,
        omission_state=omission_state,
        chronology_legality_class=row.chronology_legality_class,
        causal_legality_class=row.causal_legality_class,
        continuity_posture=row.continuity_posture,
        lineage_coverage=lineage_coverage,
        traversal_binding_state="bound" if row.traversal_epoch else "stale_epoch",
        degradation_classes=degradation_classes,
        artifact_kind="retrieval_index",
        provenance_class="derived",
        index_epoch=row.traversal_epoch,
    )
    validate_retrieval_provenance_envelope_v1(provenance)
    return {
        "retrieval_lookup_id": format_retrieval_lookup_id_v1(retrieval_lookup_id)
        if not str(retrieval_lookup_id).startswith("sha256:")
        else str(retrieval_lookup_id),
        "upstream_digest": upstream.get("retrieval_index_entry_digest", ""),
        "evidence_legality_class": evidence_class,
        "provenance": provenance,
        "ret_prov01_missing_digests": missing,
    }


def map_rd_code_to_omission_semantics_v1(rd_code: str) -> str:
    return _RD_TO_OMISSION_SEMANTICS_V1.get(rd_code, "omitted_upstream_gap")


def normalize_retrieval_omission_rows_v1(
    raw_omissions: Sequence[Mapping[str, Any]],
    *,
    partial_addressing: bool = False,
) -> list[dict[str, Any]]:
    """**RET-PROV-02** — explicit omission rows with semantics (never silent drop)."""
    rows: list[dict[str, Any]] = []
    for item in raw_omissions:
        rd = str(
            item.get("retrieval_omission_class")
            or item.get("rd_code")
            or ""
        ).strip()
        if not rd:
            continue
        semantics = map_rd_code_to_omission_semantics_v1(rd)
        rows.append(
            {
                "retrieval_omission_class": rd,
                "omission_semantics": semantics,
                "upstream_trigger": str(item.get("upstream_trigger") or ""),
                "trigger_count": int(item.get("trigger_count", 1)),
            }
        )
    if partial_addressing:
        rows.append(
            {
                "retrieval_omission_class": "RD-ADDRESSING-UNRESOLVED",
                "omission_semantics": "omitted_addressing_partial",
                "upstream_trigger": "partial_addressing",
                "trigger_count": 1,
            }
        )
    return rows


def build_retrieval_evidence_hits_from_index_v1(
    *,
    tenant_id: uuid.UUID | str,
    retrieval_lookup_id: str,
    row: Any,
    replay_posture: str,
    workload_class: str,
    execution_partition: str,
    replay_pins: Mapping[str, Any] | None = None,
    replay_identity_match: bool = True,
    partial_addressing: bool = False,
) -> list[dict[str, Any]]:
    hit = build_retrieval_evidence_hit_v1(
        tenant_id=tenant_id,
        retrieval_lookup_id=retrieval_lookup_id,
        row=row,
        replay_posture=replay_posture,
        workload_class=workload_class,
        execution_partition=execution_partition,
        replay_pins=replay_pins,
        replay_identity_match=replay_identity_match,
        partial_addressing=partial_addressing,
    )
    return [hit]


def compute_provenance_coverage_percent_v1(hits: Sequence[Mapping[str, Any]]) -> int:
    """Observability: percent of hits with full provenance envelope + authoritative evidence."""
    if not hits:
        return 0
    full = 0
    for hit in hits:
        prov = hit.get("provenance")
        if not isinstance(prov, dict):
            continue
        if prov.get("provenance_envelope_id") and hit.get("evidence_legality_class") in (
            "evidence_authoritative",
            "evidence_degraded",
        ):
            full += 1
    return int(round(100.0 * full / len(hits)))


def build_retrieval_provenance_inspector_catalog_v1() -> dict[str, Any]:
    """Admin provenance inspector — field checklist + enums (**G-P07-PROV-01**)."""
    return {
        "retrieval_provenance_evidence_runtime_schema_version": (
            PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_PROV01_GATE_ID_V1,
        "provenance_envelope_schema_version": RETRIEVAL_PROVENANCE_ENVELOPE_SCHEMA_VERSION_V1,
        "required_fields": sorted(RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1),
        "upstream_digest_keys": sorted(RETRIEVAL_PROVENANCE_UPSTREAM_DIGEST_KEYS_V1),
        "evidence_legality_classes": sorted(RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1),
        "omission_semantics_classes": sorted(RETRIEVAL_OMISSION_SEMANTICS_CLASSES_V1),
        "workload_required_upstream_digests": {
            k: sorted(v) for k, v in sorted(_WORKLOAD_REQUIRED_UPSTREAM_DIGESTS_V1.items())
        },
        "rules": [
            {"id": "RET-PROV-01", "text": "Missing digest for declared artifact → degraded floor"},
            {"id": "RET-PROV-02", "text": "Omissions explicit in RetrievalOmissionRowV1[]"},
        ],
        "doctrine_anchor": RETRIEVAL_PROVENANCE_EVIDENCE_SPEC_REF_V1,
    }


def _prov_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_PROV01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_prov01_provenance_field_checklist_static() -> dict[str, Any]:
    errors: list[str] = []
    if len(RETRIEVAL_PROVENANCE_ENVELOPE_REQUIRED_FIELDS_V1) < 7:
        errors.append("required_fields_count")
    sample = build_retrieval_provenance_envelope_v1(
        tenant_id=uuid.UUID(int=0),
        replay_posture="stable",
        evidence_legality_class="evidence_authoritative",
        upstream_digests={"retrieval_index_entry_digest": "a" * 64},
    )
    try:
        validate_retrieval_provenance_envelope_v1(sample)
    except RetrievalProvenanceEvidenceError as exc:
        errors.append(f"sample_envelope_invalid:{exc}")
    if "provenance_envelope_id" not in sample:
        errors.append("missing_provenance_envelope_id")
    missing = list_ret_prov01_missing_upstream_digests_v1(
        workload_class="causal_chain",
        upstream_digests={"retrieval_index_entry_digest": "b" * 64},
    )
    if "causal_chain_id" not in missing:
        errors.append("prov01_should_flag_missing_causal_chain_id")
    rows = normalize_retrieval_omission_rows_v1(
        [{"retrieval_omission_class": "RD-CAP-HITS", "upstream_trigger": "policy"}]
    )
    if not rows or rows[0].get("omission_semantics") != "omitted_cap":
        errors.append("omission_semantics_mapping")
    cat = build_retrieval_provenance_inspector_catalog_v1()
    if cat["gate_id"] != GP07_PROV01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _prov_meta("gp07_prov01_provenance_field_checklist", errors)

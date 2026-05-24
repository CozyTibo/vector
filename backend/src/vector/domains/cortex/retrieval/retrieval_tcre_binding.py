"""Phase 07 P07-15 — TCRE / chronology / edge bindings.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md`` §TCRE.
**RET-TCRE-01** read stored artifacts only; **RET-TCRE-02** RUNTIME-02 handoff → lookup id map.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.phase_boundaries import (
    RETRIEVAL_RD_TCRE_GAP_V1,
    TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1,
    build_rd_tcre_gap_omission_row_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_entry_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import (
    derive_retrieval_lookup_id_v1,
    format_retrieval_lookup_id_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_artifact import (
    CortexTcreReconstructionArtifact,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_TCRE01_GATE_ID_V1: Final[str] = "G-P07-TCRE-01"

RETRIEVAL_TCRE_BINDING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md"
)

RET_TCRE01_RULE_ID_V1: Final[str] = "RET-TCRE-01"

RET_TCRE02_RULE_ID_V1: Final[str] = "RET-TCRE-02"

DEFAULT_MAX_TCRE_CAUSAL_EDGES_PER_EPOCH_V1: Final[int] = 500


def retrieval_index_tcre_causal_edges_enabled_v1() -> bool:
    """When false, skip writing ``index_kind=causal_edge`` rows (S2.4 rollback)."""
    raw = os.environ.get("CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES", "1")
    return raw.strip().lower() not in ("0", "false", "no", "off")


def max_tcre_causal_edges_per_epoch_v1(*, max_materializations: int) -> int:
    return max(1, min(int(max_materializations), DEFAULT_MAX_TCRE_CAUSAL_EDGES_PER_EPOCH_V1))

_TCRE_ARTIFACT_CHRONOLOGY_V1: Final[str] = "chronology_receipt"
_TCRE_ARTIFACT_EDGE_V1: Final[str] = "causal_edge"
_TCRE_ARTIFACT_CHAIN_V1: Final[str] = "causal_chain"

_TCRE_BINDING_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
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

_RUNTIME02_REF_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_lookup_id",
        "retrieval_chain_ref",
        "chronology_window_ref",
        "materialization_id",
        "tcre_causal_edge_id",
        "causal_chain_id",
    }
)

_RETRIEVAL_TCRE_BIND_FAILURES_TOTAL_V1: int = 0


class RetrievalTcreBindingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_tcre_bind_failures_total_v1() -> int:
    return _RETRIEVAL_TCRE_BIND_FAILURES_TOTAL_V1


def record_retrieval_tcre_bind_failure_v1(
    *,
    tenant_id: str,
    reason: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    global _RETRIEVAL_TCRE_BIND_FAILURES_TOTAL_V1
    _RETRIEVAL_TCRE_BIND_FAILURES_TOTAL_V1 += 1
    return {
        "event": "retrieval_tcre_bind_failure",
        "tenant_id": tenant_id,
        "reason": reason,
        "tcre_reconstruction_job_id": job_id,
    }


def parse_runtime02_operator_retrieval_ref_v1(ref: str) -> tuple[str, str] | None:
    """Parse RUNTIME-02 operator ``chronology:`` / ``edge:`` shorthand refs."""
    raw = str(ref or "").strip()
    if not raw:
        return None
    if raw.startswith("sha256:") and len(raw) == 71:
        return ("retrieval_lookup_id", raw)
    for prefix, kind in (
        ("chronology:", "materialization_id"),
        ("edge:", "tcre_causal_edge_id"),
        ("chain:", "causal_chain_id"),
    ):
        if raw.startswith(prefix):
            return (kind, raw[len(prefix) :])
    return None


def map_runtime02_ref_to_retrieval_lookup_id_v1(
    *,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
) -> str:
    """**RET-TCRE-02** — map Phase 06 RUNTIME-02 stable refs → index ``retrieval_lookup_id``."""
    kind = str(ref_kind).strip()
    value = str(ref_value).strip()
    if not value:
        raise RetrievalTcreBindingError("runtime02_ref_value_required")
    if kind == "retrieval_lookup_id":
        return format_retrieval_lookup_id_v1(value)
    if kind in ("chronology_window_ref", "materialization_id"):
        return derive_retrieval_lookup_id_v1(
            index_kind="materialization",
            index_key=f"materialization:{value}",
            replay_identity=replay_identity,
        )
    if kind == "tcre_causal_edge_id":
        return derive_retrieval_lookup_id_v1(
            index_kind="causal_edge",
            index_key=f"causal_edge:{value}",
            replay_identity=replay_identity,
        )
    if kind in ("causal_chain_id", "retrieval_chain_ref"):
        chain_id = value[6:] if value.startswith("chain:") else value
        return derive_retrieval_lookup_id_v1(
            index_kind="causal_chain",
            index_key=f"causal_chain:{chain_id}",
            replay_identity=replay_identity,
        )
    raise RetrievalTcreBindingError("runtime02_ref_kind_unknown", detail={"ref_kind": kind})


def build_runtime02_handoff_entry_v1(
    *,
    ref_kind: str,
    ref_value: str,
    replay_identity: str,
    chronology_legality_class: str | None = None,
    causal_legality_class: str | None = None,
    artifact_digest: str | None = None,
) -> dict[str, Any]:
    lookup_id = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind=ref_kind,
        ref_value=ref_value,
        replay_identity=replay_identity,
    )
    entry: dict[str, Any] = {
        "ref_kind": ref_kind,
        "ref_value": ref_value,
        "retrieval_lookup_id": lookup_id,
    }
    if ref_kind in ("materialization_id", "chronology_window_ref"):
        entry["chronology_window_ref"] = ref_value
    if ref_kind == "causal_chain_id":
        entry["retrieval_chain_ref"] = f"chain:{ref_value}"
    if chronology_legality_class:
        entry["chronology_legality_class"] = chronology_legality_class
    if causal_legality_class:
        entry["causal_legality_class"] = causal_legality_class
    if artifact_digest:
        entry["artifact_digest"] = artifact_digest
    return entry


def load_tcre_reconstruction_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID | str,
) -> CortexTcreReconstructionJob | None:
    jid = job_id if isinstance(job_id, uuid.UUID) else uuid.UUID(str(job_id))
    return session.scalar(
        select(CortexTcreReconstructionJob)
        .where(
            CortexTcreReconstructionJob.id == jid,
            CortexTcreReconstructionJob.tenant_id == tenant_id,
        )
        .options(selectinload(CortexTcreReconstructionJob.artifacts))
    )


def _worst_causal_legality_v1(classes: Sequence[str]) -> str:
    order = (
        "causal_unverifiable",
        "causal_replay_degraded",
        "causal_replay_equivalent",
        "verified",
    )
    present = {str(c) for c in classes if c}
    if not present:
        return "verified"
    for leg in order:
        if leg in present:
            return leg
    return sorted(present)[0]


def _worst_chronology_legality_v1(classes: Sequence[str]) -> str:
    if any(c == "chronology_degraded" for c in classes):
        return "chronology_degraded"
    if any(c == "chronology_unverifiable" for c in classes):
        return "chronology_unverifiable"
    return "chronology_strict"


def map_tcre_chronology_legality_to_index_v1(tcre_class: str) -> str:
    raw = str(tcre_class or "").strip()
    if raw.startswith("chronology_"):
        raw = raw[len("chronology_") :]
    if raw in ("strict", "degraded", "unverifiable", "illegal"):
        return raw
    return "strict"


def map_tcre_causal_legality_to_index_v1(tcre_class: str) -> str:
    raw = str(tcre_class or "").strip()
    if raw.startswith("causal_"):
        raw = raw[len("causal_") :]
    mapping = {
        "replay_equivalent": "verified",
        "replay_degraded": "degraded",
        "unverifiable": "unverifiable",
        "illegal": "illegal",
        "verified": "verified",
        "degraded": "degraded",
    }
    return mapping.get(raw, "verified")


def build_tcre_replay_artifact_pins_v1(
    job: CortexTcreReconstructionJob,
    artifacts: Sequence[CortexTcreReconstructionArtifact],
) -> list[dict[str, str]]:
    """Replay pins from persisted job artifacts (no inline reducer)."""
    pins: list[dict[str, str]] = []
    for art in artifacts:
        pins.append(
            {
                "artifact_kind": str(art.artifact_kind),
                "artifact_key": str(art.artifact_key),
                "artifact_digest": str(art.artifact_digest),
            }
        )
    pins.append(
        {
            "artifact_kind": "tcre_policy_bundle",
            "artifact_key": str(job.tcre_policy_bundle_digest),
            "artifact_digest": str(job.tcre_policy_bundle_digest),
        }
    )
    pins.sort(key=lambda r: (r["artifact_kind"], r["artifact_key"]))
    return pins


def build_tcre_handoff_lookup_map_v1(
    *,
    job: CortexTcreReconstructionJob,
    artifacts: Sequence[CortexTcreReconstructionArtifact],
    replay_identity: str,
) -> dict[str, Any]:
    """Lookup id map from RUNTIME-02 handoff refs (**RET-TCRE-02**)."""
    by_materialization: dict[str, dict[str, Any]] = {}
    by_edge: dict[str, dict[str, Any]] = {}
    by_chain: dict[str, dict[str, Any]] = {}
    handoff_rows: list[dict[str, Any]] = []
    chronology_classes: list[str] = []
    causal_classes: list[str] = []
    chain_body: dict[str, Any] | None = None

    for art in artifacts:
        key = str(art.artifact_key)
        digest = str(art.artifact_digest)
        body = dict(art.body_json or {})
        if art.artifact_kind == _TCRE_ARTIFACT_CHRONOLOGY_V1:
            leg = str(body.get("chronology_legality_class") or "strict")
            chronology_classes.append(leg)
            entry = build_runtime02_handoff_entry_v1(
                ref_kind="materialization_id",
                ref_value=key,
                replay_identity=replay_identity,
                chronology_legality_class=leg,
                artifact_digest=digest,
            )
            entry["runtime02_retrieval_lookup_id"] = f"chronology:{key}"
            by_materialization[key] = entry
            handoff_rows.append(entry)
        elif art.artifact_kind == _TCRE_ARTIFACT_EDGE_V1:
            leg = str(body.get("causal_legality_class") or "causal_replay_equivalent")
            causal_classes.append(leg)
            entry = build_runtime02_handoff_entry_v1(
                ref_kind="tcre_causal_edge_id",
                ref_value=key,
                replay_identity=replay_identity,
                causal_legality_class=leg,
                artifact_digest=digest,
            )
            entry["runtime02_retrieval_lookup_id"] = f"edge:{key}"
            by_edge[key] = entry
            handoff_rows.append(entry)
        elif art.artifact_kind == _TCRE_ARTIFACT_CHAIN_V1:
            chain_body = body
            chain_body["causal_chain_id"] = key
            leg = str(body.get("causal_legality_class") or _worst_causal_legality_v1(causal_classes))
            entry = build_runtime02_handoff_entry_v1(
                ref_kind="causal_chain_id",
                ref_value=key,
                replay_identity=replay_identity,
                causal_legality_class=leg,
                artifact_digest=digest,
            )
            entry["runtime02_retrieval_lookup_id"] = f"chain:{key}"
            entry["retrieval_chain_ref"] = f"chain:{key}"
            by_chain[key] = entry
            handoff_rows.append(entry)

    chron_floor = _worst_chronology_legality_v1(chronology_classes)
    causal_floor = _worst_causal_legality_v1(
        causal_classes + ([str(chain_body.get("causal_legality_class") or "")] if chain_body else [])
    )
    return {
        "schema_version": PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION,
        "tcre_reconstruction_job_id": str(job.id),
        "tcre_policy_bundle_digest": str(job.tcre_policy_bundle_digest),
        "job_status": str(job.status),
        "handoff_ref_keys": sorted(TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1),
        "lookup_entries": handoff_rows,
        "by_materialization_id": by_materialization,
        "by_tcre_causal_edge_id": by_edge,
        "by_causal_chain_id": by_chain,
        "chronology_legality_class": chron_floor,
        "causal_legality_class": causal_floor,
        "replay_artifact_pins": build_tcre_replay_artifact_pins_v1(job, artifacts),
        "lookup_map_digest": hash_reasoning_canonical_json_sha256_v1(
            {
                "job_id": str(job.id),
                "entries": sorted(
                    (r["ref_kind"], r["ref_value"], r["retrieval_lookup_id"]) for r in handoff_rows
                ),
            }
        ),
    }


def list_tcre_coverage_gap_omissions_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    job: CortexTcreReconstructionJob | None,
    bind_required: bool,
) -> list[dict[str, Any]]:
    omissions: list[dict[str, Any]] = []
    triggers = dict(upstream_triggers or {})
    if triggers.get("reconstruction_coverage_gap"):
        omissions.append(build_rd_tcre_gap_omission_row_v1())
    if bind_required and job is None:
        omissions.append(
            build_rd_tcre_gap_omission_row_v1(
                trigger="tcre_job_not_found",
                detail={"reason": "missing_tcre_reconstruction_job"},
            )
        )
    elif job is not None and str(job.status) != "completed":
        omissions.append(
            build_rd_tcre_gap_omission_row_v1(
                trigger="tcre_job_incomplete",
                detail={"job_status": str(job.status)},
            )
        )
    elif job is not None:
        summary = dict(job.summary_json or {})
        if summary.get("reconstruction_coverage_gap") or summary.get("coverage_gap"):
            omissions.append(build_rd_tcre_gap_omission_row_v1())
    return omissions


def copy_tcre_legality_to_hits_v1(
    hits: list[dict[str, Any]],
    *,
    lookup_map: Mapping[str, Any],
    row_chronology: str,
    row_causal: str,
) -> list[dict[str, Any]]:
    """**RET-TCRE-01** — copy chronology/causal legality from TCRE artifacts (no recompute)."""
    chron_floor = str(lookup_map.get("chronology_legality_class") or row_chronology)
    causal_floor = str(lookup_map.get("causal_legality_class") or row_causal)
    by_mat = lookup_map.get("by_materialization_id") or {}
    by_edge = lookup_map.get("by_tcre_causal_edge_id") or {}
    out: list[dict[str, Any]] = []
    for hit in hits:
        h = dict(hit)
        prov = dict(h.get("provenance") or {})
        prov.setdefault("chronology_legality_class", chron_floor)
        prov.setdefault("causal_legality_class", causal_floor)
        mat = str(prov.get("materialization_id") or h.get("materialization_id") or "")
        edge = str(prov.get("tcre_causal_edge_id") or h.get("tcre_causal_edge_id") or "")
        if mat and mat in by_mat:
            prov["chronology_legality_class"] = by_mat[mat].get(
                "chronology_legality_class", prov["chronology_legality_class"]
            )
        if edge and edge in by_edge:
            prov["causal_legality_class"] = by_edge[edge].get(
                "causal_legality_class", prov["causal_legality_class"]
            )
        h["provenance"] = prov
        out.append(h)
    return out


def materialize_retrieval_index_from_tcre_job_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job: CortexTcreReconstructionJob,
    replay_identity: str,
    index_epoch: str,
    max_materializations: int = 500,
    auto_publish: bool = True,
) -> dict[str, Any]:
    """Materialize index rows for chain + bounded chronology/edge refs from a completed job."""
    if str(job.status) != "completed":
        raise RetrievalTcreBindingError(
            "tcre_job_not_completed", detail={"status": str(job.status)}
        )
    artifacts = list(job.artifacts)
    lookup_map = build_tcre_handoff_lookup_map_v1(
        job=job, artifacts=artifacts, replay_identity=replay_identity
    )
    materialized: list[str] = []
    chron_index = map_tcre_chronology_legality_to_index_v1(
        str(lookup_map.get("chronology_legality_class") or "chronology_strict")
    )
    causal_index = map_tcre_causal_legality_to_index_v1(
        str(lookup_map.get("causal_legality_class") or "causal_replay_equivalent")
    )
    for cid, entry in (lookup_map.get("by_causal_chain_id") or {}).items():
        row = materialize_retrieval_index_entry_v1(
            session,
            tenant_id=tenant_id,
            causal_chain_id=cid,
            replay_identity=replay_identity,
            index_epoch=index_epoch,
            chronology_legality_class=chron_index,
            causal_legality_class=causal_index,
            artifact_ref={
                "causal_chain_id": cid,
                "tcre_reconstruction_job_id": str(job.id),
                "tcre_policy_bundle_digest": str(job.tcre_policy_bundle_digest),
            },
            omission_summary={},
            auto_publish=auto_publish,
        )
        materialized.append(row.retrieval_lookup_id)
        entry["index_materialized"] = True
    mat_count = 0
    for mid, entry in (lookup_map.get("by_materialization_id") or {}).items():
        if mat_count >= max_materializations:
            break
        chron = map_tcre_chronology_legality_to_index_v1(
            str(entry.get("chronology_legality_class") or "chronology_strict")
        )
        row = materialize_retrieval_index_entry_v1(
            session,
            tenant_id=tenant_id,
            replay_identity=replay_identity,
            index_epoch=index_epoch,
            index_kind="materialization",
            index_key=f"materialization:{mid}",
            chronology_legality_class=chron,
            causal_legality_class="verified",
            artifact_ref={
                "materialization_id": mid,
                "tcre_reconstruction_job_id": str(job.id),
            },
            omission_summary={},
            auto_publish=auto_publish,
        )
        materialized.append(row.retrieval_lookup_id)
        entry["index_materialized"] = True
        mat_count += 1

    edge_count = 0
    if retrieval_index_tcre_causal_edges_enabled_v1():
        max_edges = max_tcre_causal_edges_per_epoch_v1(max_materializations=max_materializations)
        for eid, entry in sorted((lookup_map.get("by_tcre_causal_edge_id") or {}).items()):
            if edge_count >= max_edges:
                break
            causal_edge_index = map_tcre_causal_legality_to_index_v1(
                str(entry.get("causal_legality_class") or "causal_replay_equivalent")
            )
            row = materialize_retrieval_index_entry_v1(
                session,
                tenant_id=tenant_id,
                replay_identity=replay_identity,
                index_epoch=index_epoch,
                index_kind="causal_edge",
                index_key=f"causal_edge:{eid}",
                chronology_legality_class=chron_index,
                causal_legality_class=causal_edge_index,
                artifact_ref={
                    "tcre_causal_edge_id": eid,
                    "tcre_reconstruction_job_id": str(job.id),
                    "tcre_policy_bundle_digest": str(job.tcre_policy_bundle_digest),
                },
                omission_summary={},
                auto_publish=auto_publish,
            )
            materialized.append(row.retrieval_lookup_id)
            entry["index_materialized"] = True
            edge_count += 1

    return {
        "materialized_lookup_ids": materialized,
        "lookup_map": lookup_map,
        "index_epoch": index_epoch,
        "causal_edges_materialized": edge_count,
        "causal_edge_indexing_enabled": retrieval_index_tcre_causal_edges_enabled_v1(),
    }


def _tcre_job_id_from_envelope_v1(envelope: Mapping[str, Any], pins: Mapping[str, Any]) -> str | None:
    for key in (
        "tcre_reconstruction_job_id",
        "tcre_job_id",
        "reconstruction_job_id",
    ):
        raw = pins.get(key) or envelope.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    addressing = envelope.get("addressing")
    if isinstance(addressing, dict):
        raw = addressing.get("tcre_reconstruction_job_id") or addressing.get("tcre_job_id")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def apply_retrieval_tcre_binding_to_query_v1(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    workload_class: str,
    hits: list[dict[str, Any]],
    omissions: list[dict[str, Any]],
    replay_pins: Mapping[str, Any],
    row: Any,
) -> dict[str, Any]:
    """Bind TCRE job artifacts to query hits; propagate ``RD-TCRE-GAP`` on coverage gaps."""
    wl = str(workload_class)
    bind_required = wl in _TCRE_BINDING_WORKLOADS_V1 or bool(
        _tcre_job_id_from_envelope_v1(envelope, replay_pins)
    )
    replay_id = str(
        replay_pins.get("replay_identity")
        or replay_pins.get("retrieval_replay_identity")
        or getattr(row, "replay_identity", "")
        or ""
    ).strip()
    job_id_raw = _tcre_job_id_from_envelope_v1(envelope, replay_pins)
    job: CortexTcreReconstructionJob | None = None
    if job_id_raw:
        try:
            job = load_tcre_reconstruction_job_v1(
                session, tenant_id=tenant_id, job_id=job_id_raw
            )
        except (ValueError, TypeError):
            job = None
    gap_omissions = list_tcre_coverage_gap_omissions_v1(
        upstream_triggers=envelope.get("upstream_triggers")
        if isinstance(envelope.get("upstream_triggers"), dict)
        else None,
        job=job,
        bind_required=bind_required and bool(job_id_raw),
    )
    out_omissions = list(omissions)
    out_omissions.extend(gap_omissions)

    lookup_map: dict[str, Any] = {
        "schema_version": PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION,
        "bind_state": "skipped",
        "tcre_reconstruction_job_id": job_id_raw,
        "handoff_ref_keys": sorted(TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1),
    }
    if job is not None and str(job.status) == "completed" and replay_id:
        lookup_map = build_tcre_handoff_lookup_map_v1(
            job=job, artifacts=list(job.artifacts), replay_identity=replay_id
        )
        lookup_map["bind_state"] = "bound"
        out_hits = copy_tcre_legality_to_hits_v1(
            hits,
            lookup_map=lookup_map,
            row_chronology=str(getattr(row, "chronology_legality_class", "strict")),
            row_causal=str(getattr(row, "causal_legality_class", "verified")),
        )
        setattr(
            row,
            "chronology_legality_class",
            map_tcre_chronology_legality_to_index_v1(
                str(lookup_map.get("chronology_legality_class") or "chronology_strict")
            ),
        )
        setattr(
            row,
            "causal_legality_class",
            map_tcre_causal_legality_to_index_v1(
                str(lookup_map.get("causal_legality_class") or "causal_replay_equivalent")
            ),
        )
    elif bind_required and job_id_raw and job is None:
        record_retrieval_tcre_bind_failure_v1(
            tenant_id=str(tenant_id), reason="job_not_found", job_id=job_id_raw
        )
        lookup_map["bind_state"] = "failed"
        out_hits = list(hits)
    else:
        out_hits = list(hits)

    if gap_omissions:
        lookup_map["bind_state"] = "degraded"
    return {
        "hits": out_hits,
        "omissions": out_omissions,
        "tcre_binding_envelope": lookup_map,
        "chronology_legality_class": str(getattr(row, "chronology_legality_class", "strict")),
        "causal_legality_class": str(getattr(row, "causal_legality_class", "verified")),
    }


def build_retrieval_tcre_binding_catalog_v1() -> dict[str, Any]:
    """Admin TCRE binding panel catalog."""
    return {
        "retrieval_tcre_binding_runtime_schema_version": (
            PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_TCRE01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_TCRE_BINDING_SPEC_REF_V1,
        "rules": [
            {
                "id": RET_TCRE01_RULE_ID_V1,
                "text": "Read cortex_tcre_reconstruction_jobs + artifacts as stored; no inline reducer",
            },
            {
                "id": RET_TCRE02_RULE_ID_V1,
                "text": "Map materialization_id, tcre_causal_edge_id, causal_chain_id → retrieval_lookup_id",
            },
        ],
        "handoff_ref_keys": sorted(TCRE_RETRIEVAL_HANDOFF_REF_KEYS_V1),
        "runtime02_ref_kinds": sorted(_RUNTIME02_REF_KINDS_V1),
        "tcre_binding_workloads": sorted(_TCRE_BINDING_WORKLOADS_V1),
        "rd_tcre_gap_code": RETRIEVAL_RD_TCRE_GAP_V1,
        "artifact_kinds": [
            _TCRE_ARTIFACT_CHRONOLOGY_V1,
            _TCRE_ARTIFACT_EDGE_V1,
            _TCRE_ARTIFACT_CHAIN_V1,
        ],
        "observability": {
            "metric": "retrieval_tcre_bind_failures_total",
            "getter": "get_retrieval_tcre_bind_failures_total_v1",
            "causal_edge_indexing": {
                "shipped_in": "S2.4_S3.1",
                "env_flag": "CORTEX_RETRIEVAL_INDEX_TCRE_CAUSAL_EDGES",
                "default_enabled": True,
            },
        },
    }


def _tcre_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_TCRE01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_tcre01_runtime02_lookup_map_static() -> dict[str, Any]:
    """**G-P07-TCRE-01** — RUNTIME-02 handoff refs resolve to stable lookup ids."""
    errors: list[str] = []
    replay = "replay-static-test"
    mid = "00000000-0000-4000-8000-000000000099"
    eid = "edge-hash-abc"
    cid = "chain-hash-xyz"
    lid_m = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind="materialization_id", ref_value=mid, replay_identity=replay
    )
    lid_e = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind="tcre_causal_edge_id", ref_value=eid, replay_identity=replay
    )
    lid_c = map_runtime02_ref_to_retrieval_lookup_id_v1(
        ref_kind="causal_chain_id", ref_value=cid, replay_identity=replay
    )
    if not lid_m.startswith("sha256:"):
        errors.append("materialization_lookup_id_format")
    if derive_retrieval_lookup_id_v1(
        index_kind="materialization",
        index_key=f"materialization:{mid}",
        replay_identity=replay,
    ) != lid_m:
        errors.append("materialization_lookup_id_deterministic")
    parsed = parse_runtime02_operator_retrieval_ref_v1(f"chronology:{mid}")
    if parsed != ("materialization_id", mid):
        errors.append("parse_chronology_ref")
    entry = build_runtime02_handoff_entry_v1(
        ref_kind="chronology_window_ref",
        ref_value=mid,
        replay_identity=replay,
        chronology_legality_class="chronology_strict",
    )
    if not entry.get("retrieval_lookup_id"):
        errors.append("handoff_missing_retrieval_lookup_id")
    if entry.get("chronology_window_ref") != mid:
        errors.append("handoff_chronology_window_ref")
    chain_entry = build_runtime02_handoff_entry_v1(
        ref_kind="causal_chain_id",
        ref_value=cid,
        replay_identity=replay,
    )
    if chain_entry.get("retrieval_chain_ref") != f"chain:{cid}":
        errors.append("handoff_retrieval_chain_ref")
    gaps = list_tcre_coverage_gap_omissions_v1(
        upstream_triggers={"reconstruction_coverage_gap": True},
        job=None,
        bind_required=False,
    )
    if not gaps or gaps[0].get("retrieval_omission_class") != RETRIEVAL_RD_TCRE_GAP_V1:
        errors.append("coverage_gap_omission")
    if lid_e == lid_c:
        errors.append("edge_chain_lookup_ids_must_differ")
    cat = build_retrieval_tcre_binding_catalog_v1()
    if cat["gate_id"] != GP07_TCRE01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _tcre_meta("gp07_tcre01_runtime02_lookup_map", errors)

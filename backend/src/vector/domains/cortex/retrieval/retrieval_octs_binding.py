"""Phase 07 P07-16 — OCTS walk + traversal bindings.

Normative: ``DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md`` §OCTS.
**RET-OCTS-01** durable walk reads; **RET-OCTS-02** ``retrieval_walk_ref`` law;
**RET-OCTS-03** exploration partition isolation.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import build_retrieval_walk_ref_body_v1
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
    RETRIEVAL_RD_TRAVERSAL_IDLE_V1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    materialize_retrieval_index_entry_v1,
)
from vector.domains.cortex.retrieval.retrieval_lookup_projection import derive_retrieval_lookup_id_v1
from vector.domains.cortex.traversal.exploration_mode_contract import EXECUTION_PARTITION_EXPLORATION
from vector.domains.cortex.traversal.runtime.durable_walk_store import (
    extract_walk_replay_metadata_v1,
    resolve_octs_walk_store_v1,
)
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord

PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP07_OCTS01_GATE_ID_V1: Final[str] = "G-P07-OCTS-01"

RETRIEVAL_OCTS_BINDING_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/retrieval/phase-07-retrieval-runtime-architecture.md"
)

RET_OCTS01_RULE_ID_V1: Final[str] = "RET-OCTS-01"

RET_OCTS02_RULE_ID_V1: Final[str] = "RET-OCTS-02"

RET_OCTS03_RULE_ID_V1: Final[str] = "RET-OCTS-03"

_WALK_SCOPED_WORKLOADS_V1: Final[frozenset[str]] = frozenset(
    {"traversal_lineage", "replay_equivalence"}
)

_WALK_SCOPE_QUERY_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "walk_by_id",
        "walk_by_hash_and_epoch",
        "tenant_completed_walk_inventory",
        "graph_eligible_idle_probe",
    }
)

_BLOCKED_WALK_STATUSES_V1: Final[frozenset[str]] = frozenset(
    {"queued", "running", "failed", "cancelled"}
)

_RETRIEVAL_WALK_BIND_FAILURES_TOTAL_V1: int = 0


class RetrievalOctsBindingError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_retrieval_walk_bind_failures_total_v1() -> int:
    return _RETRIEVAL_WALK_BIND_FAILURES_TOTAL_V1


def record_retrieval_walk_bind_failure_v1(
    *,
    tenant_id: str,
    reason: str,
    walk_id: str | None = None,
) -> dict[str, Any]:
    global _RETRIEVAL_WALK_BIND_FAILURES_TOTAL_V1
    _RETRIEVAL_WALK_BIND_FAILURES_TOTAL_V1 += 1
    return {
        "event": "retrieval_walk_bind_failure",
        "tenant_id": tenant_id,
        "reason": reason,
        "walk_id": walk_id,
    }


def build_retrieval_walk_ref_v1(
    *,
    walk_id: str,
    walk_result_hash: str,
    traversal_epoch: str,
) -> dict[str, Any]:
    """**RET-OCTS-02** — canonical ``retrieval_walk_ref`` from walk hash + epoch."""
    wid = str(walk_id).strip()
    wh = str(walk_result_hash).strip()
    epoch = str(traversal_epoch).strip()
    if not wid or not wh or not epoch:
        raise RetrievalOctsBindingError("retrieval_walk_ref_fields_required")
    return build_retrieval_walk_ref_body_v1(
        walk_id=wid,
        walk_result_hash=wh,
        traversal_epoch=epoch,
    )


def map_walk_to_retrieval_lookup_id_v1(
    *,
    walk_id: str,
    replay_identity: str,
) -> str:
    return derive_retrieval_lookup_id_v1(
        index_kind="walk",
        index_key=f"walk:{str(walk_id).strip()}",
        replay_identity=replay_identity,
    )


def build_rd_traversal_omission_row_v1(
    *,
    omission_class: str,
    upstream_trigger: str,
    detail: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "retrieval_omission_class": omission_class,
        "upstream_trigger": upstream_trigger,
        "detail": dict(detail or {}),
    }


def load_durable_walk_record_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID | str,
) -> WalkApiRecordV1 | None:
    """**RET-OCTS-01** — read stored walk via ``resolve_octs_walk_store_v1``."""
    try:
        wid = walk_id if isinstance(walk_id, uuid.UUID) else uuid.UUID(str(walk_id))
    except (ValueError, TypeError) as exc:
        raise RetrievalOctsBindingError("invalid_walk_id", detail={"walk_id": str(walk_id)}) from exc
    store = resolve_octs_walk_store_v1(session)
    return store.get(tenant_id, wid)


def durable_row_from_walk_record_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    walk_id: uuid.UUID,
) -> CortexOctsDurableWalkRecord | None:
    row = session.get(CortexOctsDurableWalkRecord, walk_id)
    if row is None or row.tenant_id != tenant_id:
        return None
    return row


def extract_walk_result_hash_from_record_v1(record: WalkApiRecordV1) -> str | None:
    payload = record.walk_payload or {}
    wr = payload.get("walk_result") or {}
    raw = wr.get("walk_result_hash")
    return str(raw).strip() if raw else None


def walk_request_exploration_partition_v1(request_body: Mapping[str, Any]) -> str:
    if bool(request_body.get("exploration_mode")):
        return EXECUTION_PARTITION_EXPLORATION
    return "authoritative"


def assert_walk_exploration_partition_matches_v1(
    *,
    execution_partition: str,
    walk_request_body: Mapping[str, Any],
) -> bool:
    """**RET-OCTS-03** — walk partition must match query execution partition."""
    walk_part = walk_request_exploration_partition_v1(walk_request_body)
    query_part = (
        EXECUTION_PARTITION_EXPLORATION
        if execution_partition.strip().lower() == "exploration"
        else "authoritative"
    )
    return walk_part == query_part


def list_walk_result_hash_pin_violations_v1(
    *,
    replay_pins: Mapping[str, Any],
    walk_result_hash: str | None,
    workload_class: str,
) -> list[dict[str, Any]]:
    wl = str(workload_class)
    if wl not in _WALK_SCOPED_WORKLOADS_V1:
        return []
    pinned = str(replay_pins.get("walk_result_hash") or "").strip()
    actual = str(walk_result_hash or "").strip()
    if not pinned:
        return [
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
                upstream_trigger="walk_result_hash_pin_missing",
                detail={"workload_class": wl},
            )
        ]
    if actual and pinned != actual:
        return [
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
                upstream_trigger="walk_result_hash_pin_mismatch",
                detail={"pinned": pinned, "actual": actual},
            )
        ]
    return []


def list_traversal_idle_omissions_v1(
    *,
    upstream_triggers: Mapping[str, Any] | None,
    graph_eligible: bool,
    walk_count: int,
    bind_required: bool,
) -> list[dict[str, Any]]:
    triggers = dict(upstream_triggers or {})
    if triggers.get("traversal_never_executed"):
        return [
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_IDLE_V1,
                upstream_trigger="traversal_never_executed",
            )
        ]
    if bind_required and graph_eligible and walk_count == 0:
        return [
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_IDLE_V1,
                upstream_trigger="graph_eligible_zero_walks",
            )
        ]
    return []


def list_traversal_blocked_omissions_v1(
    *,
    record: WalkApiRecordV1 | None,
    exploration_mismatch: bool,
) -> list[dict[str, Any]]:
    omissions: list[dict[str, Any]] = []
    if exploration_mismatch:
        omissions.append(
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
                upstream_trigger="exploration_partition_mismatch",
            )
        )
    if record is None:
        return omissions
    if str(record.status) in _BLOCKED_WALK_STATUSES_V1:
        omissions.append(
            build_rd_traversal_omission_row_v1(
                omission_class=RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
                upstream_trigger="walk_not_completed",
                detail={"status": str(record.status)},
            )
        )
    return omissions


def query_walk_scope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    scope_kind: str,
    walk_id: str | None = None,
    walk_result_hash: str | None = None,
    traversal_epoch: str | None = None,
    graph_eligible: bool = False,
) -> dict[str, Any]:
    """Walk scope queries (**done when** registry defined)."""
    kind = str(scope_kind).strip()
    if kind not in _WALK_SCOPE_QUERY_KINDS_V1:
        raise RetrievalOctsBindingError("walk_scope_kind_unknown", detail={"scope_kind": kind})
    store = resolve_octs_walk_store_v1(session)
    if kind == "walk_by_id":
        if not walk_id:
            raise RetrievalOctsBindingError("walk_id_required")
        rec = load_durable_walk_record_v1(session, tenant_id=tenant_id, walk_id=walk_id)
        return {"scope_kind": kind, "walk_count": 1 if rec else 0, "walk": rec}
    if kind == "walk_by_hash_and_epoch":
        target_hash = str(walk_result_hash or "").strip()
        target_epoch = str(traversal_epoch or "").strip()
        matches: list[WalkApiRecordV1] = []
        for rec in store.list_walk_records_for_tenant_v1(tenant_id):
            if extract_walk_result_hash_from_record_v1(rec) != target_hash:
                continue
            if target_epoch:
                row = durable_row_from_walk_record_v1(
                    session, tenant_id=tenant_id, walk_id=rec.walk_id
                )
                if row is None or str(row.traversal_epoch or "") != target_epoch:
                    continue
            matches.append(rec)
        return {"scope_kind": kind, "walk_count": len(matches), "walks": matches}
    if kind == "tenant_completed_walk_inventory":
        records = [
            r
            for r in store.list_walk_records_for_tenant_v1(tenant_id)
            if str(r.status) == "completed"
        ]
        return {"scope_kind": kind, "walk_count": len(records), "walks": records}
    # graph_eligible_idle_probe
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    completed = sum(1 for r in records if str(r.status) == "completed")
    idle = graph_eligible and completed == 0
    return {
        "scope_kind": kind,
        "graph_eligible": graph_eligible,
        "completed_walk_count": completed,
        "idle_eligible": idle,
    }


def build_walk_handoff_binding_v1(
    *,
    record: WalkApiRecordV1,
    durable_row: CortexOctsDurableWalkRecord | None,
    replay_identity: str,
) -> dict[str, Any]:
    walk_hash = extract_walk_result_hash_from_record_v1(record) or str(
        durable_row.walk_hash if durable_row else ""
    )
    epoch = str(durable_row.traversal_epoch if durable_row else "") or ""
    if not walk_hash or not epoch:
        meta = extract_walk_replay_metadata_v1(
            request_body=dict(record.request_body or {}),
            walk_payload=dict(record.walk_payload or {}),
            replay_lineage=None,
        )
        walk_hash = walk_hash or str(meta.get("walk_hash") or "")
        epoch = epoch or str(meta.get("traversal_epoch") or "")
    walk_ref = build_retrieval_walk_ref_v1(
        walk_id=str(record.walk_id),
        walk_result_hash=walk_hash,
        traversal_epoch=epoch,
    )
    lookup_id = map_walk_to_retrieval_lookup_id_v1(
        walk_id=str(record.walk_id),
        replay_identity=replay_identity,
    )
    return {
        "schema_version": PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION,
        "retrieval_walk_ref": walk_ref,
        "retrieval_lookup_id": lookup_id,
        "walk_id": str(record.walk_id),
        "walk_result_hash": walk_hash,
        "traversal_epoch": epoch,
        "walk_replay_identity": str(durable_row.replay_identity if durable_row else ""),
        "replay_legality_posture": str(durable_row.replay_legality_posture if durable_row else ""),
        "traversal_receipt_digest": str(
            durable_row.traversal_receipt_digest if durable_row else ""
        ),
        "walk_scope_queries": sorted(_WALK_SCOPE_QUERY_KINDS_V1),
    }


def materialize_retrieval_index_from_walk_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    record: WalkApiRecordV1,
    replay_identity: str,
    index_epoch: str,
    auto_publish: bool = True,
) -> dict[str, Any]:
    """Materialize index row for a completed durable walk."""
    if str(record.status) != "completed":
        raise RetrievalOctsBindingError(
            "walk_not_completed", detail={"status": str(record.status)}
        )
    durable_row = durable_row_from_walk_record_v1(
        session, tenant_id=tenant_id, walk_id=record.walk_id
    )
    binding = build_walk_handoff_binding_v1(
        record=record,
        durable_row=durable_row,
        replay_identity=replay_identity,
    )
    walk_ref = binding["retrieval_walk_ref"]
    degradation = "degraded" if binding.get("replay_legality_posture") == "degraded" else "stable"
    row = materialize_retrieval_index_entry_v1(
        session,
        tenant_id=tenant_id,
        replay_identity=replay_identity,
        index_epoch=index_epoch,
        index_kind="walk",
        index_key=f"walk:{record.walk_id}",
        chronology_legality_class="strict",
        causal_legality_class="verified",
        degradation_posture=degradation,
        artifact_ref={
            "walk_id": str(record.walk_id),
            "walk_result_hash": binding["walk_result_hash"],
            "traversal_epoch": binding["traversal_epoch"],
        },
        omission_summary={},
        auto_publish=auto_publish,
    )
    return {"retrieval_index_entry": row, "binding": binding, "walk_ref": walk_ref}


def _walk_id_from_envelope_v1(envelope: Mapping[str, Any], pins: Mapping[str, Any]) -> str | None:
    addressing = envelope.get("addressing")
    if isinstance(addressing, dict):
        walk_ref = addressing.get("retrieval_walk_ref")
        if isinstance(walk_ref, dict) and walk_ref.get("walk_id"):
            return str(walk_ref["walk_id"]).strip()
        if addressing.get("walk_id"):
            return str(addressing["walk_id"]).strip()
        if addressing.get("retrieval_walk_ref") and not isinstance(walk_ref, dict):
            return str(addressing["retrieval_walk_ref"]).strip()
    for key in ("octs_walk_id", "walk_id"):
        raw = pins.get(key) or envelope.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def _graph_eligible_from_envelope_v1(envelope: Mapping[str, Any]) -> bool:
    triggers = envelope.get("upstream_triggers")
    if isinstance(triggers, dict) and triggers.get("graph_eligible"):
        return True
    scope = envelope.get("ingress_scope")
    if isinstance(scope, dict) and scope.get("graph_eligible"):
        return True
    return bool(envelope.get("graph_eligible"))


def apply_retrieval_octs_binding_to_query_v1(
    *,
    session: Session,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    workload_class: str,
    execution_partition: str,
    hits: list[dict[str, Any]],
    omissions: list[dict[str, Any]],
    replay_pins: Mapping[str, Any],
    row: Any,
) -> dict[str, Any]:
    """Bind durable OCTS walks; propagate ``RD-TRAVERSAL-*``; emit ``retrieval_walk_ref``."""
    wl = str(workload_class)
    bind_required = wl in _WALK_SCOPED_WORKLOADS_V1 or bool(_walk_id_from_envelope_v1(envelope, replay_pins))
    walk_id_raw = _walk_id_from_envelope_v1(envelope, replay_pins)
    replay_id = str(
        replay_pins.get("replay_identity")
        or replay_pins.get("retrieval_replay_identity")
        or getattr(row, "replay_identity", "")
        or ""
    ).strip()
    graph_eligible = _graph_eligible_from_envelope_v1(envelope)
    store = resolve_octs_walk_store_v1(session)
    completed_count = sum(
        1
        for r in store.list_walk_records_for_tenant_v1(tenant_id)
        if str(r.status) == "completed"
    )

    out_omissions = list(omissions)
    out_omissions.extend(
        list_traversal_idle_omissions_v1(
            upstream_triggers=envelope.get("upstream_triggers")
            if isinstance(envelope.get("upstream_triggers"), dict)
            else None,
            graph_eligible=graph_eligible,
            walk_count=completed_count,
            bind_required=bind_required,
        )
    )

    record: WalkApiRecordV1 | None = None
    if walk_id_raw:
        try:
            record = load_durable_walk_record_v1(
                session, tenant_id=tenant_id, walk_id=walk_id_raw
            )
        except RetrievalOctsBindingError:
            record = None
        if record is None:
            record_retrieval_walk_bind_failure_v1(
                tenant_id=str(tenant_id),
                reason="walk_not_found",
                walk_id=walk_id_raw,
            )

    exploration_mismatch = False
    if record is not None:
        exploration_mismatch = not assert_walk_exploration_partition_matches_v1(
            execution_partition=execution_partition,
            walk_request_body=dict(record.request_body or {}),
        )

    out_omissions.extend(
        list_traversal_blocked_omissions_v1(
            record=record,
            exploration_mismatch=exploration_mismatch,
        )
    )
    if record is not None and str(record.status) == "completed":
        walk_hash = extract_walk_result_hash_from_record_v1(record)
        out_omissions.extend(
            list_walk_result_hash_pin_violations_v1(
                replay_pins=replay_pins,
                walk_result_hash=walk_hash,
                workload_class=wl,
            )
        )

    binding_envelope: dict[str, Any] = {
        "schema_version": PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION,
        "bind_state": "skipped",
        "walk_id": walk_id_raw,
        "walk_scope_queries": sorted(_WALK_SCOPE_QUERY_KINDS_V1),
    }
    retrieval_walk_ref: dict[str, Any] | None = None
    out_hits = list(hits)

    if record is not None and str(record.status) == "completed" and replay_id and not exploration_mismatch:
        durable_row = durable_row_from_walk_record_v1(
            session, tenant_id=tenant_id, walk_id=record.walk_id
        )
        handoff = build_walk_handoff_binding_v1(
            record=record,
            durable_row=durable_row,
            replay_identity=replay_id,
        )
        binding_envelope = {
            **handoff,
            "bind_state": "bound",
            "tcre_policy_bundle_digest": replay_pins.get("tcre_policy_bundle_digest"),
        }
        retrieval_walk_ref = handoff["retrieval_walk_ref"]
        if durable_row and durable_row.traversal_epoch:
            setattr(row, "traversal_epoch", durable_row.traversal_epoch)
            if getattr(row, "index_epoch", None) in (None, ""):
                setattr(row, "index_epoch", durable_row.traversal_epoch)
        for hit in out_hits:
            prov = dict(hit.get("provenance") or {})
            prov["traversal_binding_state"] = "bound"
            prov["walk_result_hash"] = handoff["walk_result_hash"]
            prov["traversal_epoch"] = handoff["traversal_epoch"]
            hit["provenance"] = prov
    elif bind_required and walk_id_raw and record is None:
        binding_envelope["bind_state"] = "failed"
    elif exploration_mismatch or any(
        str(o.get("retrieval_omission_class")) == RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1
        for o in out_omissions
        if isinstance(o, dict)
    ):
        binding_envelope["bind_state"] = "blocked"
    elif any(
        str(o.get("retrieval_omission_class")) == RETRIEVAL_RD_TRAVERSAL_IDLE_V1
        for o in out_omissions
        if isinstance(o, dict)
    ):
        binding_envelope["bind_state"] = "idle"

    return {
        "hits": out_hits,
        "omissions": out_omissions,
        "traversal_binding_envelope": binding_envelope,
        "retrieval_walk_ref": retrieval_walk_ref,
    }


def build_retrieval_traversal_binding_catalog_v1() -> dict[str, Any]:
    """Admin traversal binding panel catalog."""
    return {
        "retrieval_octs_binding_runtime_schema_version": (
            PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP07_OCTS01_GATE_ID_V1,
        "spec_ref": RETRIEVAL_OCTS_BINDING_SPEC_REF_V1,
        "rules": [
            {
                "id": RET_OCTS01_RULE_ID_V1,
                "text": "Read durable walks via resolve_octs_walk_store_v1 only",
            },
            {
                "id": RET_OCTS02_RULE_ID_V1,
                "text": "retrieval_walk_ref from walk_result_hash + traversal_epoch",
            },
            {
                "id": RET_OCTS03_RULE_ID_V1,
                "text": "Exploration partition on walk must match query execution_partition",
            },
        ],
        "walk_scope_query_kinds": sorted(_WALK_SCOPE_QUERY_KINDS_V1),
        "walk_scoped_workloads": sorted(_WALK_SCOPED_WORKLOADS_V1),
        "rd_traversal_codes": [
            RETRIEVAL_RD_TRAVERSAL_IDLE_V1,
            RETRIEVAL_RD_TRAVERSAL_BLOCKED_V1,
        ],
        "observability": {
            "metric": "retrieval_walk_bind_failures_total",
            "getter": "get_retrieval_walk_bind_failures_total_v1",
        },
    }


def _octs_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP07_OCTS01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_octs01_walk_ref_and_scope_queries_static() -> dict[str, Any]:
    """**G-P07-OCTS-01** — walk ref law + walk scope query registry."""
    errors: list[str] = []
    if len(_WALK_SCOPE_QUERY_KINDS_V1) < 4:
        errors.append("walk_scope_query_kind_count")
    ref = build_retrieval_walk_ref_v1(
        walk_id="00000000-0000-4000-8000-000000000001",
        walk_result_hash="sha256:" + "a" * 64,
        traversal_epoch="epoch-test-1",
    )
    if ref.get("walk_id") != "00000000-0000-4000-8000-000000000001":
        errors.append("walk_ref_walk_id")
    if not ref.get("walk_result_hash", "").startswith("sha256:"):
        errors.append("walk_ref_hash")
    lid = map_walk_to_retrieval_lookup_id_v1(
        walk_id="00000000-0000-4000-8000-000000000001",
        replay_identity="replay-scope-test",
    )
    if not lid.startswith("sha256:"):
        errors.append("walk_lookup_id_format")
    idle = list_traversal_idle_omissions_v1(
        upstream_triggers=None,
        graph_eligible=True,
        walk_count=0,
        bind_required=True,
    )
    if not idle or idle[0].get("retrieval_omission_class") != RETRIEVAL_RD_TRAVERSAL_IDLE_V1:
        errors.append("rd_traversal_idle")
    blocked = list_traversal_blocked_omissions_v1(record=None, exploration_mismatch=True)
    if not blocked:
        errors.append("exploration_mismatch_blocked")
    req = {"exploration_mode": True}
    if not assert_walk_exploration_partition_matches_v1(
        execution_partition="exploration", walk_request_body=req
    ):
        errors.append("exploration_match_expected")
    if assert_walk_exploration_partition_matches_v1(
        execution_partition="authoritative", walk_request_body=req
    ):
        errors.append("exploration_mismatch_expected")
    cat = build_retrieval_traversal_binding_catalog_v1()
    if cat["gate_id"] != GP07_OCTS01_GATE_ID_V1:
        errors.append("catalog_gate_id")
    return _octs_meta("gp07_octs01_walk_ref_and_scope_queries", errors)

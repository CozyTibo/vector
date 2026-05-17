"""Phase 07 P07-06 — lawful query envelope + deterministic execution FSM.

Normative: ``DOCS/cortex/retrieval/phase-07-query-contract-doctrine.md`` §3–4.
``RET-QC-02`` addressing resolution; ``RET-QC-03`` fixed phase order.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.anti_goals import (
    enforce_retrieval_query_envelope_anti_goals_v1,
    validate_retrieval_authoritative_output_algebra_v1,
)
from vector.domains.cortex.retrieval.phase_boundaries import (
    enforce_retrieval_envelope_phase06_boundary_v1,
    merge_upstream_triggers_into_retrieval_omissions_v1,
    validate_retrieval_response_phase_boundaries_v1,
)
from vector.domains.cortex.retrieval.query_contract import (
    RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
    RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
    addressing_has_resolvable_ref_v1,
    resolve_retrieval_workload_and_intent_v1,
    validate_retrieval_intent_v1,
    validate_retrieval_workload_class_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    aggregate_query_legality_class_v1,
    build_retrieval_legality_posture_v1,
    classify_upstream_index_legality_v1,
    max_retrieval_legality_class_v1,
    run_retrieval_r_leg_precheck_v1,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    RetrievalIngressError,
    enforce_retrieval_ingress_scope_v1,
    validate_retrieval_derived_index_read_v1,
    validate_retrieval_ingress_artifact_kind_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RetrievalLegalityError,
    assert_retrieval_query_lawful_v1,
    retrieval_policy_digest_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import (
    RetrievalAddressingError,
    resolve_retrieval_addressing_v1,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    RetrievalBoundedCapsError,
    apply_retrieval_policy_pack_defaults_v1,
    assert_retrieval_wall_budget_v1,
    normalize_retrieval_omission_law_rows_v1,
    retrieval_policy_pack_digest_v1,
    assert_retrieval_response_under_byte_cap_v1,
)
from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
    RetrievalRankingSelectionError,
)
from vector.domains.cortex.retrieval.retrieval_temporal import (
    RetrievalTemporalError,
    apply_retrieval_temporal_law_to_query_v1,
    normalize_retrieval_temporal_scope_v1,
    validate_retrieval_temporal_scope_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    RETRIEVAL_RD_POLICY_MISMATCH_V1,
    RetrievalReplayEquivalenceError,
    build_retrieval_query_replay_pins_v1,
    build_retrieval_replay_equivalence_twin_diff_v1,
    compare_gp07_replay_01_double_run_v1,
    compute_retrieval_query_replay_identity_v1,
    list_retrieval_replay_pin_violations_v1,
    record_retrieval_replay_divergence_v1,
)
from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
    apply_retrieval_degradation_taxonomy_to_query_result_v1,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs import (
    retrieval_replay_omissions_from_twin_diff_v1,
)

PHASE07_QUERY_EXECUTION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_QUERY_RECEIPT_SCHEMA_VERSION_V1: Final[int] = 1

RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1: Final[str] = "addressing_unresolved"

RETRIEVAL_QUERY_EXECUTION_PHASES_V1: Final[tuple[str, ...]] = (
    "VALIDATE",
    "RESOLVE",
    "BOUND",
    "PROVENANCE",
    "CLASSIFY",
    "RECEIPT",
)

_EXECUTION_PARTITIONS_V1: Final[frozenset[str]] = frozenset({"authoritative", "exploration"})

class RetrievalQueryExecutionError(ValueError):
    """Raised when envelope validation or FSM execution fails."""

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


def _parse_tenant_id(raw: object) -> uuid.UUID:
    if isinstance(raw, uuid.UUID):
        return raw
    try:
        return uuid.UUID(str(raw))
    except (ValueError, TypeError) as exc:
        raise RetrievalQueryExecutionError(
            "invalid_tenant_id",
            detail={"tenant_id": raw},
        ) from exc


def normalize_retrieval_query_envelope_v1(
    body: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Validate and normalize ``RetrievalQueryEnvelopeV1`` (§3)."""
    schema_version = body.get("schema_version")
    if schema_version != RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1:
        raise RetrievalQueryExecutionError(
            "invalid_schema_version",
            detail={"schema_version": schema_version},
        )
    env_tenant = _parse_tenant_id(body.get("tenant_id"))
    if env_tenant != tenant_id:
        raise RetrievalQueryExecutionError(
            "tenant_id_scope_mismatch",
            detail={"envelope_tenant_id": str(env_tenant), "auth_tenant_id": str(tenant_id)},
        )
    wl = validate_retrieval_workload_class_v1(str(body.get("workload_class", "")))
    temporal_scope_raw = body.get("temporal_scope")
    if temporal_scope_raw is not None and not isinstance(temporal_scope_raw, dict):
        raise RetrievalQueryExecutionError("invalid_temporal_scope")
    temporal_scope = normalize_retrieval_temporal_scope_v1(
        temporal_scope_raw if isinstance(temporal_scope_raw, dict) else None
    )
    replay_pins_raw = body.get("replay_pins")
    if replay_pins_raw is not None and not isinstance(replay_pins_raw, dict):
        raise RetrievalQueryExecutionError("invalid_replay_pins")
    try:
        validate_retrieval_temporal_scope_v1(
            temporal_scope,
            workload_class=wl,
            replay_pins=replay_pins_raw if isinstance(replay_pins_raw, dict) else None,
        )
    except RetrievalTemporalError as exc:
        raise RetrievalQueryExecutionError(exc.code, detail=exc.detail) from exc
    it = validate_retrieval_intent_v1(str(body.get("intent", "")))
    partition = str(body.get("execution_partition") or "authoritative").strip().lower()
    if partition not in _EXECUTION_PARTITIONS_V1:
        raise RetrievalQueryExecutionError(
            "invalid_execution_partition",
            detail={"execution_partition": partition},
        )
    addressing = body.get("addressing")
    if not isinstance(addressing, dict):
        raise RetrievalQueryExecutionError("addressing_required")
    if not addressing_has_resolvable_ref_v1(addressing) and it != "audit":
        raise RetrievalQueryExecutionError(
            RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1,
            http_status=400,
            detail={"addressing": dict(addressing), "rd_code": RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1},
        )
    selection_policy = body.get("selection_policy")
    if selection_policy is not None and not isinstance(selection_policy, dict):
        raise RetrievalQueryExecutionError("invalid_selection_policy")
    try:
        caps = apply_retrieval_policy_pack_defaults_v1(
            wl,
            selection_policy if isinstance(selection_policy, dict) else None,
        )
    except (RetrievalRankingSelectionError, RetrievalBoundedCapsError) as exc:
        http_status = getattr(exc, "http_status", 400)
        raise RetrievalQueryExecutionError(
            exc.code, http_status=http_status, detail=getattr(exc, "detail", None)
        ) from exc
    idempotency_key = body.get("idempotency_key")
    if idempotency_key is not None and not str(idempotency_key).strip():
        raise RetrievalQueryExecutionError("invalid_idempotency_key")
    return {
        "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "workload_class": wl,
        "intent": it,
        "execution_partition": partition,
        "temporal_scope": dict(temporal_scope),
        "addressing": dict(addressing),
        "selection_policy": caps,
        "replay_pins": dict(replay_pins_raw or {}),
        "idempotency_key": str(idempotency_key).strip() if idempotency_key else None,
        "upstream_triggers": dict(body["upstream_triggers"])
        if isinstance(body.get("upstream_triggers"), dict)
        else {},
        "policy_override_exploration": bool(body.get("policy_override_exploration")),
        "ingress_scope": dict(body["ingress_scope"]) if isinstance(body.get("ingress_scope"), dict) else {},
    }


def coerce_body_to_retrieval_query_envelope_v1(
    body: Mapping[str, Any],
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Accept full envelope or minimal admin body (``retrieval_lookup_id`` only)."""
    if body.get("schema_version") == RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1 and isinstance(
        body.get("addressing"), dict
    ):
        return normalize_retrieval_query_envelope_v1(body, tenant_id=tenant_id)
    lookup_id = str(body.get("retrieval_lookup_id") or "").strip()
    if not lookup_id and isinstance(body.get("addressing"), dict):
        lookup_id = str(body["addressing"].get("retrieval_lookup_id") or "").strip()
    wl, it = resolve_retrieval_workload_and_intent_v1(body)
    addressing: dict[str, Any] = dict(body.get("addressing") or {"retrieval_lookup_id": lookup_id})
    minimal = {
        "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "workload_class": wl,
        "intent": it,
        "execution_partition": str(body.get("execution_partition") or "authoritative"),
        "temporal_scope": dict(body.get("temporal_scope") or {}),
        "addressing": addressing,
        "selection_policy": dict(body.get("selection_policy") or {}),
        "replay_pins": dict(body.get("replay_pins") or {}),
        "idempotency_key": body.get("idempotency_key"),
        "upstream_triggers": body.get("upstream_triggers"),
        "policy_override_exploration": body.get("policy_override_exploration"),
        "ingress_scope": body.get("ingress_scope"),
        "expected_replay_identity": body.get("expected_replay_identity"),
        "index_epoch": body.get("index_epoch"),
    }
    if not lookup_id and not addressing_has_resolvable_ref_v1(addressing):
        raise RetrievalQueryExecutionError(
            RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1,
            http_status=400,
        )
    return normalize_retrieval_query_envelope_v1(minimal, tenant_id=tenant_id)


def resolve_retrieval_lookup_id_from_addressing_v1(
    envelope: Mapping[str, Any],
    *,
    expected_replay_identity: str | None = None,
) -> str:
    """RESOLVE phase — map addressing → ``retrieval_lookup_id`` (**RET-ADDR-01**)."""
    tenant_raw = envelope.get("tenant_id")
    tid = uuid.UUID(str(tenant_raw)) if tenant_raw else uuid.UUID(int=0)
    try:
        return resolve_retrieval_addressing_v1(
            envelope,
            tenant_id=tid,
            expected_replay_identity=expected_replay_identity,
        ).retrieval_lookup_id
    except RetrievalAddressingError as exc:
        raise RetrievalQueryExecutionError(
            RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1
            if exc.code == "addressing_unresolved"
            else exc.code,
            http_status=400,
            detail=exc.detail,
        ) from exc


def build_retrieval_query_receipt_v1(
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    retrieval_lookup_id: str,
    retrieval_legality_class: str,
    execution_trace: list[dict[str, Any]],
    replay_posture: str,
    retrieval_query_replay_identity: str | None = None,
) -> dict[str, Any]:
    """Emit ``RetrievalQueryReceiptV1`` with canonical digest (RECEIPT phase)."""
    body_for_digest: dict[str, Any] = {
        "schema_version": RETRIEVAL_QUERY_RECEIPT_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "workload_class": envelope["workload_class"],
        "intent": envelope["intent"],
        "execution_partition": envelope["execution_partition"],
        "retrieval_lookup_id": retrieval_lookup_id,
        "retrieval_legality_class": retrieval_legality_class,
        "replay_posture": replay_posture,
        "execution_phases": [row["phase"] for row in execution_trace],
        "retrieval_policy_digest": retrieval_policy_digest_v1(),
    }
    if retrieval_query_replay_identity:
        body_for_digest[PHASE07_REPLAY_IDENTITY_FIELD_V1] = retrieval_query_replay_identity
    return {
        "schema_version": RETRIEVAL_QUERY_RECEIPT_SCHEMA_VERSION_V1,
        "receipt_digest": hash_reasoning_canonical_json_sha256_v1(body_for_digest),
        "receipt_body": body_for_digest,
    }


def _trace_phase(
    trace: list[dict[str, Any]],
    *,
    phase: str,
    started: float,
    extra: Mapping[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {
        "phase": phase,
        "status": "ok",
        "duration_ms": max(0, int((time.perf_counter() - started) * 1000)),
    }
    if extra:
        row.update(dict(extra))
    trace.append(row)


def _assert_fsm_phase_order_v1(trace: list[dict[str, Any]]) -> None:
    phases = [row["phase"] for row in trace]
    if phases != list(RETRIEVAL_QUERY_EXECUTION_PHASES_V1):
        msg = f"fsm_phase_order_violation:{phases}"
        raise RetrievalQueryExecutionError("fsm_phase_order_violation", detail={"phases": phases})


def execute_retrieval_query_envelope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    body: Mapping[str, Any],
    expected_replay_identity: str | None = None,
    _twin_inner: bool = False,
) -> dict[str, Any]:
    """Run full query FSM: VALIDATE → RESOLVE → BOUND → PROVENANCE → CLASSIFY → RECEIPT."""
    if not _twin_inner:
        pre = coerce_body_to_retrieval_query_envelope_v1(body, tenant_id=tenant_id)
        if str(pre.get("workload_class")) == "replay_equivalence":
            run_a = execute_retrieval_query_envelope_v1(
                session,
                tenant_id=tenant_id,
                body=body,
                expected_replay_identity=expected_replay_identity,
                _twin_inner=True,
            )
            run_b = execute_retrieval_query_envelope_v1(
                session,
                tenant_id=tenant_id,
                body=body,
                expected_replay_identity=expected_replay_identity,
                _twin_inner=True,
            )
            twin = build_retrieval_replay_equivalence_twin_diff_v1(run_a, run_b)
            try:
                compare_gp07_replay_01_double_run_v1(run_a, run_b)
            except RetrievalReplayEquivalenceError:
                twin["gp07_replay_01_passed"] = False
                twin["divergence_event"] = record_retrieval_replay_divergence_v1(
                    tenant_id=str(tenant_id),
                    retrieval_query_replay_identity_a=str(
                        run_a.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or ""
                    ),
                    retrieval_query_replay_identity_b=str(
                        run_b.get(PHASE07_REPLAY_IDENTITY_FIELD_V1) or ""
                    ),
                    detail=dict(twin),
                )
                from vector.domains.cortex.retrieval.retrieval_observability import (
                    note_retrieval_replay_divergence_observed_v1,
                )

                note_retrieval_replay_divergence_observed_v1()
            if not twin.get("gp07_replay_01_passed"):
                twin_omissions = retrieval_replay_omissions_from_twin_diff_v1(twin)
                existing = run_a.get("omissions")
                merged: list[Any] = list(existing) if isinstance(existing, list) else []
                merged.extend(twin_omissions)
                run_a["omissions"] = merged
                om_sum = run_a.get("omission_summary")
                if isinstance(om_sum, dict):
                    rd_rows = list(om_sum.get("rd_rows") or [])
                    rd_rows.extend(twin_omissions)
                    om_sum["rd_rows"] = rd_rows
                run_a["retrieval_legality_class"] = max_retrieval_legality_class_v1(
                    str(run_a.get("retrieval_legality_class") or "retrieval_replay_safe"),
                    "retrieval_degraded",
                )
                run_a["replay_posture"] = "partial"
            run_a["replay_equivalence_twin"] = twin
            return run_a

    trace: list[dict[str, Any]] = []
    t0 = time.perf_counter()

    # VALIDATE
    envelope = coerce_body_to_retrieval_query_envelope_v1(body, tenant_id=tenant_id)
    enforce_retrieval_query_envelope_anti_goals_v1(envelope)
    enforce_retrieval_envelope_phase06_boundary_v1(envelope)
    if envelope.get("ingress_scope"):
        enforce_retrieval_ingress_scope_v1(envelope["ingress_scope"])
    r_leg = run_retrieval_r_leg_precheck_v1(envelope)
    if not r_leg["R-LEG-01"]:
        from vector.domains.cortex.retrieval.retrieval_observability import (
            record_retrieval_legality_failure_v1,
        )

        record_retrieval_legality_failure_v1(reason="R-LEG-01")
        raise RetrievalQueryExecutionError("retrieval_forbidden", http_status=403)
    _trace_phase(trace, phase="VALIDATE", started=t0, extra={"r_leg": r_leg})

    # RESOLVE
    t1 = time.perf_counter()
    pins = envelope.get("replay_pins") or {}
    assert isinstance(pins, dict)
    exp_replay = expected_replay_identity or pins.get("expected_replay_identity")
    try:
        resolution = resolve_retrieval_addressing_v1(
            envelope,
            tenant_id=tenant_id,
            expected_replay_identity=exp_replay,
        )
    except RetrievalAddressingError as exc:
        raise RetrievalQueryExecutionError(
            RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1
            if exc.code == "addressing_unresolved"
            else exc.code,
            http_status=400,
            detail=exc.detail,
        ) from exc
    lookup_id = resolution.retrieval_lookup_id
    from sqlalchemy import select

    from vector.infrastructure.db.models.cortex_retrieval_index_entry import (
        CortexRetrievalIndexEntry,
    )

    row = session.scalar(
        select(CortexRetrievalIndexEntry).where(
            CortexRetrievalIndexEntry.tenant_id == tenant_id,
            CortexRetrievalIndexEntry.retrieval_lookup_id == lookup_id,
        )
    )
    if row is None:
        raise RetrievalLegalityError("retrieval_lookup_not_found")
    _trace_phase(
        trace,
        phase="RESOLVE",
        started=t1,
        extra={
            "retrieval_lookup_id": lookup_id,
            "resolution_path": resolution.resolution_path,
            "partial_addressing": resolution.partial_addressing,
        },
    )

    # BOUND
    t2 = time.perf_counter()
    caps = dict(envelope["selection_policy"])
    hits: list[dict[str, Any]] = []
    omissions = merge_upstream_triggers_into_retrieval_omissions_v1(
        envelope.get("upstream_triggers") if isinstance(envelope.get("upstream_triggers"), dict) else None
    )
    policy_digest = retrieval_policy_digest_v1()
    omissions.extend(
        list_retrieval_replay_pin_violations_v1(
            pins,
            actual_policy_digest=policy_digest,
            execution_partition=str(envelope.get("execution_partition") or "authoritative"),
        )
    )
    max_hits = int(caps.get("max_hits", 100))
    if max_hits < 1:
        raise RetrievalQueryExecutionError("invalid_max_hits_cap")
    _trace_phase(trace, phase="BOUND", started=t2, extra={"caps": caps, "hit_count": len(hits)})

    wl = str(envelope["workload_class"])
    it = str(envelope["intent"])
    partition = str(envelope["execution_partition"])

    # PROVENANCE (RET-QC-03 — MUST NOT skip)
    t3 = time.perf_counter()
    try:
        validate_retrieval_ingress_artifact_kind_v1("retrieval_index")
        index_epoch = (
            pins.get("index_epoch")
            or envelope.get("index_epoch")
            or body.get("index_epoch")
        )
        from vector.domains.cortex.retrieval.retrieval_index_materialization import (
            assert_index_epoch_published_for_read_v1,
        )

        row_epoch = row.index_epoch or row.traversal_epoch
        assert_index_epoch_published_for_read_v1(
            session,
            tenant_id=tenant_id,
            index_epoch_on_row=row_epoch,
            pinned_index_epoch=str(index_epoch) if index_epoch else None,
        )
    except RetrievalIngressError as exc:
        raise RetrievalLegalityError(exc.code, detail=exc.detail) from exc
    from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
        compute_provenance_coverage_percent_v1,
        normalize_retrieval_omission_rows_v1,
    )
    from vector.domains.cortex.retrieval.runtime.reconstruction import apply_reconstruction_to_query_v1

    replay_match_early = exp_replay is None or row.replay_identity == exp_replay
    reconstruction_receipt: dict[str, Any] | None = None
    if not hits:
        recon = apply_reconstruction_to_query_v1(
            session=session,
            tenant_id=tenant_id,
            envelope=envelope,
            row=row,
            retrieval_lookup_id=lookup_id,
            workload_class=wl,
            execution_partition=partition,
            replay_pins=pins,
            replay_identity_match=replay_match_early,
            partial_addressing=resolution.partial_addressing,
        )
        hits = recon["hits"]
        omissions.extend(recon.get("omissions") or [])
        reconstruction_receipt = recon.get("reconstruction_receipt")
        if reconstruction_receipt:
            if trace:
                extra = trace[-1].get("extra")
                if isinstance(extra, dict):
                    extra["reconstruction_receipt_digest"] = recon["reconstruction_receipt"].get(
                        "reconstruction_receipt_digest"
                    )
    ingress_provenance = hits[0]["provenance"] if hits else {}
    omissions = normalize_retrieval_omission_rows_v1(
        omissions,
        partial_addressing=resolution.partial_addressing,
    )
    provenance_coverage_percent = compute_provenance_coverage_percent_v1(hits)
    _trace_phase(
        trace,
        phase="PROVENANCE",
        started=t3,
        extra={"hit_count": len(hits), "provenance_coverage_percent": provenance_coverage_percent},
    )

    from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
        apply_retrieval_tcre_binding_to_query_v1,
    )

    tcre_binding = apply_retrieval_tcre_binding_to_query_v1(
        session=session,
        tenant_id=tenant_id,
        envelope=envelope,
        workload_class=wl,
        hits=hits,
        omissions=omissions,
        replay_pins=pins,
        row=row,
    )
    hits = tcre_binding["hits"]
    omissions = normalize_retrieval_omission_rows_v1(
        tcre_binding["omissions"],
        partial_addressing=resolution.partial_addressing,
    )
    tcre_binding_envelope = tcre_binding["tcre_binding_envelope"]
    if trace:
        extra = trace[-1].get("extra")
        if isinstance(extra, dict):
            extra["tcre_bind_state"] = tcre_binding_envelope.get("bind_state")
            extra["tcre_job_id"] = tcre_binding_envelope.get("tcre_reconstruction_job_id")

    from vector.domains.cortex.retrieval.retrieval_octs_binding import (
        apply_retrieval_octs_binding_to_query_v1,
    )

    octs_binding = apply_retrieval_octs_binding_to_query_v1(
        session=session,
        tenant_id=tenant_id,
        envelope=envelope,
        workload_class=wl,
        execution_partition=partition,
        hits=hits,
        omissions=omissions,
        replay_pins=pins,
        row=row,
    )
    hits = octs_binding["hits"]
    omissions = normalize_retrieval_omission_rows_v1(
        octs_binding["omissions"],
        partial_addressing=resolution.partial_addressing,
    )
    traversal_binding_envelope = octs_binding["traversal_binding_envelope"]
    retrieval_walk_ref = octs_binding.get("retrieval_walk_ref")
    if trace:
        extra = trace[-1].get("extra")
        if isinstance(extra, dict):
            extra["octs_bind_state"] = traversal_binding_envelope.get("bind_state")
            extra["walk_id"] = traversal_binding_envelope.get("walk_id")

    temporal_scope = normalize_retrieval_temporal_scope_v1(envelope.get("temporal_scope"))

    from vector.domains.cortex.retrieval.retrieval_graph_binding import (
        apply_retrieval_graph_binding_to_query_v1,
    )

    graph_binding = apply_retrieval_graph_binding_to_query_v1(
        session=session,
        tenant_id=tenant_id,
        envelope=envelope,
        workload_class=wl,
        execution_partition=partition,
        hits=hits,
        omissions=omissions,
        replay_pins=pins,
        temporal_scope=temporal_scope,
        row=row,
    )
    hits = graph_binding["hits"]
    omissions = normalize_retrieval_omission_rows_v1(
        graph_binding["omissions"],
        partial_addressing=resolution.partial_addressing,
    )
    graph_binding_envelope = graph_binding["graph_binding_envelope"]
    graph_scope = graph_binding.get("graph_scope") or {}
    if trace:
        extra = trace[-1].get("extra")
        if isinstance(extra, dict):
            extra["graph_bind_state"] = graph_binding_envelope.get("bind_state")
            extra["org_entity_id"] = graph_binding_envelope.get("org_entity_id")

    from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
        apply_retrieval_lineage_binding_to_query_v1,
    )

    lineage_binding = apply_retrieval_lineage_binding_to_query_v1(
        session=session,
        tenant_id=tenant_id,
        envelope=envelope,
        workload_class=wl,
        execution_partition=partition,
        hits=hits,
        omissions=omissions,
        replay_pins=pins,
        retrieval_lookup_id=lookup_id,
        row=row,
        caps=caps,
    )
    hits = lineage_binding["hits"]
    omissions = normalize_retrieval_omission_rows_v1(
        lineage_binding["omissions"],
        partial_addressing=resolution.partial_addressing,
    )
    lineage_binding_envelope = lineage_binding["lineage_binding_envelope"]
    lineage_chain = lineage_binding["lineage_chain"]
    explain = lineage_binding["lineage_explainability"]
    if trace:
        extra = trace[-1].get("extra")
        if isinstance(extra, dict):
            extra["lineage_coverage"] = lineage_binding_envelope.get("lineage_coverage")
            extra["lineage_chain_digest"] = lineage_binding_envelope.get("lineage_chain_digest")

    temporal_law = apply_retrieval_temporal_law_to_query_v1(
        envelope=envelope,
        temporal_scope=temporal_scope,
        row=row,
        hits=hits,
        omissions=omissions,
        replay_pins=pins,
    )
    hits = temporal_law["hits"]
    omissions = normalize_retrieval_omission_rows_v1(
        temporal_law["omissions"],
        partial_addressing=resolution.partial_addressing,
    )
    temporal_legality_envelope = temporal_law["temporal_legality_envelope"]
    temporal_skew_audit = temporal_law["temporal_skew_audit"]

    from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
        apply_retrieval_ranking_and_selection_v1,
    )

    ranking = apply_retrieval_ranking_and_selection_v1(
        hits=hits,
        caps=caps,
        row=row,
        temporal_scope=temporal_scope,
    )
    hits = ranking["hits"]
    omissions.extend(
        normalize_retrieval_omission_rows_v1(
            ranking["omissions"],
            partial_addressing=resolution.partial_addressing,
        )
    )
    selection_sort_trace = ranking["selection_sort_trace"]
    selection_policy_profile_id = ranking["selection_policy_profile_id"]
    cap_overflow_totals = ranking["cap_overflow_totals"]

    # CLASSIFY
    t4 = time.perf_counter()
    replay_match = exp_replay is None or row.replay_identity == exp_replay
    replay_posture = "stable" if replay_match else "unsafe"
    if hits:
        replay_posture = str(hits[0].get("provenance", {}).get("replay_posture", replay_posture))
    upstream_legality = classify_upstream_index_legality_v1(
        replay_identity_match=replay_match,
        chronology_legality_class=row.chronology_legality_class,
        causal_legality_class=row.causal_legality_class,
        degradation_posture=row.degradation_posture,
        continuity_posture=row.continuity_posture,
        traversal_degraded=row.degradation_posture == "degraded",
    )
    hit_evidence = [
        str(h.get("evidence_legality_class", h.get("evidence_legality", "")))
        for h in hits
        if isinstance(h, dict)
        and (h.get("evidence_legality_class") or h.get("evidence_legality"))
    ]
    legality = aggregate_query_legality_class_v1(
        r_leg=r_leg,
        upstream_row_legality=upstream_legality,
        intent=it,
        hit_evidence_legalities=hit_evidence,
    )
    if any(
        str(o.get("retrieval_omission_class")) == RETRIEVAL_RD_POLICY_MISMATCH_V1
        for o in omissions
        if isinstance(o, dict)
    ):
        legality = max_retrieval_legality_class_v1(legality, "retrieval_degraded")
    legality = max_retrieval_legality_class_v1(
        legality,
        str(temporal_legality_envelope.get("temporal_legality_floor", legality)),
    )
    if legality == "retrieval_replay_safe" and replay_match:
        replay_posture = "stable"
    elif legality in ("retrieval_partial", "retrieval_degraded"):
        replay_posture = "partial"
    elif not replay_match:
        replay_posture = "unsafe"
    legality_posture = build_retrieval_legality_posture_v1(
        legality_class=legality,
        intent=it,
        execution_partition=partition,
        r_leg=r_leg,
    )
    assert_retrieval_query_lawful_v1(
        legality_class=legality,
        replay_posture=replay_posture,
        intent=it,
        execution_partition=partition,
    )
    _trace_phase(
        trace,
        phase="CLASSIFY",
        started=t4,
        extra={"retrieval_legality_class": legality, "legality_posture": legality_posture},
    )

    from vector.domains.cortex.retrieval.retrieval_degradation_projection import (
        build_retrieval_degradation_envelope_v1,
    )

    degradation = build_retrieval_degradation_envelope_v1(
        degradation_posture=row.degradation_posture,
        omission_summary=dict(row.omission_summary or {}),
        retrieval_legality_class=legality,
        r_leg_violations=legality_posture.get("r_leg_violations"),
    )
    omission_summary = dict(row.omission_summary or {})
    if omissions:
        omission_summary["rd_rows"] = omissions

    result: dict[str, Any] = {
        "schema_version": RETRIEVAL_QUERY_ENVELOPE_SCHEMA_VERSION_V1,
        "retrieval_lookup_id": row.retrieval_lookup_id,
        "retrieval_policy_digest": row.retrieval_policy_digest,
        "retrieval_replay_identity": row.replay_identity,
        "chronology_legality_class": row.chronology_legality_class,
        "causal_legality_class": row.causal_legality_class,
        "upstream_chronology_legality_class": row.chronology_legality_class,
        "upstream_causal_legality_class": row.causal_legality_class,
        "tcre_binding_envelope": tcre_binding_envelope,
        "tcre_replay_artifact_pins": tcre_binding_envelope.get("replay_artifact_pins") or [],
        "traversal_binding_envelope": traversal_binding_envelope,
        "retrieval_walk_ref": retrieval_walk_ref,
        "graph_binding_envelope": graph_binding_envelope,
        "graph_scope": graph_scope,
        "lineage_binding_envelope": lineage_binding_envelope,
        "lineage_chain_digest": lineage_binding_envelope.get("lineage_chain_digest"),
        "retrieval_legality_class": legality,
        "degradation_posture": row.degradation_posture,
        "continuity_posture": row.continuity_posture,
        "omission_summary": omission_summary,
        "replay_posture": replay_posture,
        "artifact_ref": dict(row.artifact_ref_json or {}),
        "ingress_provenance": ingress_provenance,
        "retrieval_evidence_hits": hits,
        "retrieval_omission_rows": omissions,
        "provenance_coverage_percent": provenance_coverage_percent,
        "temporal_scope": temporal_scope,
        "temporal_legality_envelope": temporal_legality_envelope,
        "temporal_skew_audit": temporal_skew_audit,
        "selection_sort_trace": selection_sort_trace,
        "selection_policy_profile_id": selection_policy_profile_id,
        "cap_overflow_totals": cap_overflow_totals,
        "workload_class": wl,
        "intent": it,
        "selection_policy": caps,
        "query_replay_identity_scope": build_retrieval_query_replay_pins_v1(
            workload_class=wl,
            intent=it,
            tenant_id=str(tenant_id),
            replay_pins=pins,
        ),
        "degradation_envelope": degradation,
        "lineage": explain,
        "reconstruction_receipt": reconstruction_receipt,
        "hits": hits,
        "omissions": omissions,
        "r_leg_precheck": r_leg,
        "retrieval_legality_posture": legality_posture,
        "addressing_resolution": {
            "resolution_path": resolution.resolution_path,
            "partial_addressing": resolution.partial_addressing,
            "missing_fields": list(resolution.missing_fields),
        },
        "execution_trace": trace,
    }
    if partition == "exploration":
        result["non_authoritative"] = True

    fallback_upstream = (
        str(hits[0].get("upstream_digest", ""))
        if hits
        else hash_reasoning_canonical_json_sha256_v1(ingress_provenance)
    )
    query_replay_identity = compute_retrieval_query_replay_identity_v1(
        envelope=envelope,
        retrieval_policy_digest=policy_digest,
        hits=hits,
        omissions=omissions,
        fallback_lookup_id=lookup_id,
        fallback_upstream_digest=fallback_upstream,
    )
    result[PHASE07_REPLAY_IDENTITY_FIELD_V1] = query_replay_identity

    omissions = normalize_retrieval_omission_law_rows_v1(omissions)
    result["retrieval_omission_rows"] = omissions
    result["omissions"] = omissions
    result["retrieval_policy_pack_id"] = str(caps.get("retrieval_policy_pack_id") or "")
    result["retrieval_policy_pack_digest"] = retrieval_policy_pack_digest_v1()
    apply_retrieval_degradation_taxonomy_to_query_result_v1(
        result,
        upstream_triggers=envelope.get("upstream_triggers")
        if isinstance(envelope.get("upstream_triggers"), dict)
        else None,
    )
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        compute_index_lag_epochs_v1,
        get_published_index_epoch_v1,
    )

    result["published_index_epoch"] = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    result["index_lag_epochs"] = compute_index_lag_epochs_v1(session, tenant_id=tenant_id)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    try:
        assert_retrieval_wall_budget_v1(
            elapsed_ms=elapsed_ms,
            max_wall_ms=int(caps.get("max_wall_ms", 30_000)),
        )
    except RetrievalBoundedCapsError as exc:
        raise RetrievalQueryExecutionError(
            exc.code, http_status=exc.http_status, detail=exc.detail
        ) from exc
    try:
        assert_retrieval_response_under_byte_cap_v1(
            result,
            max_response_json_bytes=int(caps.get("max_response_json_bytes", 262_144)),
        )
    except RetrievalBoundedCapsError as exc:
        raise RetrievalQueryExecutionError(
            exc.code, http_status=exc.http_status, detail=exc.detail
        ) from exc

    validate_retrieval_authoritative_output_algebra_v1(result, execution_partition=partition)
    validate_retrieval_response_phase_boundaries_v1(
        result,
        execution_partition=partition,
        upstream_triggers=envelope.get("upstream_triggers")
        if isinstance(envelope.get("upstream_triggers"), dict)
        else None,
        policy_override_exploration=bool(envelope.get("policy_override_exploration")),
    )

    # RECEIPT
    t5 = time.perf_counter()
    receipt = build_retrieval_query_receipt_v1(
        tenant_id=tenant_id,
        envelope=envelope,
        retrieval_lookup_id=lookup_id,
        retrieval_legality_class=legality,
        execution_trace=trace,
        replay_posture=replay_posture,
        retrieval_query_replay_identity=query_replay_identity,
    )
    result["retrieval_query_receipt"] = receipt
    _trace_phase(trace, phase="RECEIPT", started=t5, extra={"receipt_digest": receipt["receipt_digest"]})
    result["execution_trace"] = trace
    _assert_fsm_phase_order_v1(trace)
    from vector.domains.cortex.retrieval.retrieval_observability import (
        record_retrieval_query_observability_v1,
    )

    operator_user_id = envelope.get("operator_user_id") or body.get("operator_user_id")
    obs = record_retrieval_query_observability_v1(
        session,
        tenant_id=tenant_id,
        envelope=envelope,
        result=result,
        duration_ms=int(elapsed_ms),
        operator_user_id=operator_user_id,
    )
    result["retrieval_query_log"] = obs.get("query_log")
    return result


def verify_gp07_qc02_addressing_resolution_static() -> dict[str, Any]:
    errors: list[str] = []
    tid = uuid.UUID(int=0)
    try:
        normalize_retrieval_query_envelope_v1(
            {
                "schema_version": 1,
                "tenant_id": str(tid),
                "workload_class": "causal_chain",
                "intent": "inspect",
                "execution_partition": "authoritative",
                "addressing": {},
            },
            tenant_id=tid,
        )
    except RetrievalQueryExecutionError as exc:
        if exc.code != RETRIEVAL_QUERY_ADDRESSING_UNRESOLVED_CODE_V1:
            errors.append(f"wrong_code:{exc.code}")
    else:
        errors.append("expected_addressing_unresolved")
    try:
        env = normalize_retrieval_query_envelope_v1(
            {
                "schema_version": 1,
                "tenant_id": str(tid),
                "workload_class": "causal_chain",
                "intent": "inspect",
                "addressing": {"retrieval_lookup_id": "sha256:00"},
            },
            tenant_id=tid,
        )
        lid = resolve_retrieval_lookup_id_from_addressing_v1(env)
        if lid != "sha256:00":
            errors.append("resolve_lookup_mismatch")
    except RetrievalQueryExecutionError as exc:
        errors.append(f"unexpected_rejection:{exc}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-QC-02",
        "name": "retrieval_addressing_resolution",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_qc03_fsm_phase_order_static() -> dict[str, Any]:
    errors: list[str] = []
    if list(RETRIEVAL_QUERY_EXECUTION_PHASES_V1) != [
        "VALIDATE",
        "RESOLVE",
        "BOUND",
        "PROVENANCE",
        "CLASSIFY",
        "RECEIPT",
    ]:
        errors.append("phase_tuple_mismatch")
    trace = [{"phase": p} for p in RETRIEVAL_QUERY_EXECUTION_PHASES_V1]
    try:
        _assert_fsm_phase_order_v1(trace)
    except RetrievalQueryExecutionError as exc:
        errors.append(f"unexpected_order_rejection:{exc}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-QC-03",
        "name": "retrieval_fsm_phase_order",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

"""Phase 08 P08-06 — synthesis job envelope execution FSM (skeleton).

Normative: ``DOCS/cortex/synthesis/phase-08-synthesis-law-system.md`` §FSM,
``phase-08-synthesis-runtime-architecture.md`` §Orchestrator.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.normative import PHASE07_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.anti_goals import (
    SynthesisAntiGoalViolationError,
    enforce_synthesis_job_envelope_anti_goals_v1,
)
from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_ingress import (
    SynthesisIngressError,
    build_retrieval_evidence_ingress_v1,
    compute_retrieval_ingress_digest_v1,
    enforce_retrieval_evidence_ingress_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (
    SynthesisJobContractError,
    build_synthesis_job_replay_identity_scope_v1,
)
from vector.domains.cortex.synthesis.synthesis_legality_matrix import (
    SynthesisLegalityError,
    assert_synthesis_job_lawful_v1,
    classify_synthesis_legality_for_job_v1,
)
from vector.domains.cortex.synthesis.synthesis_evidence_binding import (
    SynthesisEvidenceBindingError,
    bind_synthesis_evidence_v1,
    normalize_retrieval_hits_v1,
)
from vector.domains.cortex.synthesis.synthesis_llm_router import (
    SynthesisLlmRouterError,
    execute_synthesis_llm_phase_v1,
)
from vector.domains.cortex.synthesis.synthesis_artifact_materialization import (
    SynthesisArtifactMaterializationError,
    get_synthesis_artifact_by_job_id_v1,
    materialize_synthesis_artifact_for_job_v1,
)
from vector.domains.cortex.synthesis.synthesis_bindings import SynthesisBindingsError
from vector.domains.cortex.synthesis.synthesis_lineage import SynthesisLineageError
from vector.domains.cortex.synthesis.synthesis_bounded_caps import (
    SynthesisBoundedCapsError,
    assert_synthesis_wall_budget_v1,
    classify_synthesis_substrate_health_v1,
    list_synthesis_claim_cap_violations_v1,
    synthesis_policy_pack_caps_v1,
)
from vector.domains.cortex.synthesis.synthesis_degradation import (
    apply_synthesis_degradation_taxonomy_v1,
)
from vector.domains.cortex.synthesis.synthesis_prompt_assembly import (
    SynthesisPromptAssemblyError,
    assemble_synthesis_prompts_for_job_v1,
)
from vector.domains.cortex.synthesis.synthesis_query_plan import (
    SynthesisQueryPlanError,
    build_synthesis_retrieval_plan_v1,
    build_retrieval_subquery_receipt_row_v1,
    execute_synthesis_retrieval_plan_v1,
    load_synthesis_policy_pack_v1,
)
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    SynthesisReplayEquivalenceError,
    apply_syn_rep02_retrieval_twin_legality_floor_v1,
    build_synthesis_job_receipt_v1,
    compute_synthesis_job_replay_identity_v1,
    enforce_synthesis_expected_replay_identity_v1,
)
from vector.domains.cortex.synthesis.synthesis_observability import (
    record_synthesis_job_observability_v1,
    record_synthesis_legality_failure_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_envelope import (
    PHASE08_SYNTHESIS_JOB_ENVELOPE_RUNTIME_SCHEMA_VERSION,
    SynthesisJobEnvelopeError,
    coerce_body_to_synthesis_job_envelope_v1,
    compute_synthesis_job_envelope_digest_v1,
    synthesis_policy_pack_digest_v1,
)
from vector.domains.cortex.synthesis.synthesis_repository import (
    create_synthesis_job_row_v1,
    envelope_json_for_persistence_v1,
    find_idempotent_synthesis_job_v1,
    persist_synthesis_job_receipt_row_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_synthesis_job_receipt import CortexSynthesisJobReceipt

PHASE08_SYNTHESIS_ORCHESTRATOR_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_ORCHESTRATOR_BUILD_ID_V1: Final[str] = "syn-orchestrator-v1-stub"

SYNTHESIS_JOB_RECEIPT_SCHEMA_VERSION_V1: Final[int] = 1

GP08_FSM01_GATE_ID_V1: Final[str] = "G-P08-FSM-01"

SYNTHESIS_JOB_EXECUTION_PHASES_V1: Final[tuple[str, ...]] = (
    "INGRESS",
    "PLAN",
    "RETRIEVE",
    "BIND",
    "ASSEMBLE",
    "LLM",
    "CLASSIFY",
    "RECEIPT",
    "PUBLISH",
)

class SynthesisOrchestratorError(ValueError):
    """Raised when synthesis FSM execution fails."""

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


def _trace_phase(
    trace: list[dict[str, Any]],
    *,
    phase: str,
    started: float,
    extra: Mapping[str, Any] | None = None,
    status: str = "ok",
) -> None:
    row: dict[str, Any] = {
        "phase": phase,
        "status": status,
        "duration_ms": max(0, int((time.perf_counter() - started) * 1000)),
        "started_at_ms": int(started * 1000),
    }
    if extra:
        row.update(dict(extra))
    trace.append(row)


def _assert_fsm_phase_order_v1(trace: list[dict[str, Any]]) -> None:
    phases = [row["phase"] for row in trace]
    if phases != list(SYNTHESIS_JOB_EXECUTION_PHASES_V1):
        raise SynthesisOrchestratorError(
            "fsm_phase_order_violation",
            detail={"phases": phases, "expected": list(SYNTHESIS_JOB_EXECUTION_PHASES_V1)},
        )


def _assert_execution_trace_monotonic_v1(trace: list[dict[str, Any]]) -> None:
    prev = -1
    for row in trace:
        ts = int(row.get("started_at_ms", 0))
        if ts < prev:
            raise SynthesisOrchestratorError(
                "execution_trace_non_monotonic",
                detail={"phase": row.get("phase"), "started_at_ms": ts, "previous": prev},
            )
        prev = ts


def build_synthesis_job_run_result_v1(
    job: CortexSynthesisJob,
    *,
    execution_trace: list[dict[str, Any]],
    receipt: Mapping[str, Any],
    synthesis_legality_class: str,
    synthesis_job_replay_identity: str,
    retrieval_ingress_digest: str | None,
    synthesis_legality_posture: Mapping[str, Any] | None = None,
    idempotent_replay: bool = False,
    llm_invocations: Sequence[Mapping[str, Any]] | None = None,
    llm_trace_refs: Sequence[Mapping[str, Any]] | None = None,
    prompt_assemblies: Sequence[Mapping[str, Any]] | None = None,
    prompt_hashes: Sequence[str] | None = None,
) -> dict[str, Any]:
    receipt_dict = dict(receipt)
    inv = list(llm_invocations or receipt_dict.get("llm_invocations") or [])
    traces = list(llm_trace_refs or receipt_dict.get("llm_trace_refs") or [])
    assemblies = list(prompt_assemblies or receipt_dict.get("prompt_assemblies") or [])
    hashes = list(prompt_hashes or receipt_dict.get("prompt_hashes") or [])
    return {
        "surface_kind": "synthesis_job_run",
        "phase08_synthesis_orchestrator_runtime_schema_version": (
            PHASE08_SYNTHESIS_ORCHESTRATOR_RUNTIME_SCHEMA_VERSION
        ),
        "job_id": str(job.id),
        "tenant_id": str(job.tenant_id),
        "status": job.status,
        "synthesis_workload_class": job.synthesis_workload_class,
        "synthesis_intent": job.synthesis_intent,
        "execution_partition": job.execution_partition,
        "synthesis_legality_class": synthesis_legality_class,
        "synthesis_legality_posture": dict(synthesis_legality_posture or {}),
        "synthesis_job_replay_identity": synthesis_job_replay_identity,
        "retrieval_ingress_digest": retrieval_ingress_digest,
        "synthesis_orchestrator_build_id": job.synthesis_orchestrator_build_id,
        "execution_trace": list(execution_trace),
        "synthesis_job_receipt": receipt_dict,
        "idempotent_replay": idempotent_replay,
        "execution_phases": list(SYNTHESIS_JOB_EXECUTION_PHASES_V1),
        "retrieval_subqueries": list(job.retrieval_subqueries_json or []),
        "llm_invocations": inv,
        "llm_trace_refs": traces,
        "prompt_assemblies": assemblies,
        "prompt_hashes": hashes,
        "artifact_id": receipt_dict.get("artifact_id"),
        "artifact_digest": receipt_dict.get("artifact_digest"),
    }


def execute_synthesis_job_envelope_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    body: Mapping[str, Any],
    job_id: uuid.UUID | None = None,
    _twin_inner: bool = False,
) -> dict[str, Any]:
    """Run synthesis FSM: INGRESS → … → PUBLISH (artifact materialization)."""
    envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
    if not _twin_inner:
        from vector.domains.cortex.synthesis.synthesis_replay_equivalence_proofs import (
            execute_synthesis_inline_replay_proof_v1,
            synthesis_inline_twin_required_v1,
        )

        if synthesis_inline_twin_required_v1(envelope):
            return execute_synthesis_inline_replay_proof_v1(
                session,
                tenant_id=tenant_id,
                body=body,
                job_id=job_id,
            )
    envelope_digest = compute_synthesis_job_envelope_digest_v1(envelope)
    idem_key = envelope.get("idempotency_key")
    if idem_key:
        existing = find_idempotent_synthesis_job_v1(
            session,
            tenant_id=tenant_id,
            idempotency_key=str(idem_key),
            envelope_digest=envelope_digest,
        )
        if existing is not None and existing.receipt_digest:
            existing_trace = list(existing.execution_trace_json or [])
            receipt_body = dict(existing.receipt_json or {})
            run = build_synthesis_job_run_result_v1(
                existing,
                execution_trace=existing_trace,
                receipt=receipt_body,
                synthesis_legality_class=str(
                    existing.synthesis_legality_class
                    or (receipt_body.get("receipt_body") or {}).get(
                        "synthesis_legality_class",
                        "synthesis_partial",
                    ),
                ),
                synthesis_job_replay_identity=str(existing.synthesis_job_replay_identity or ""),
                retrieval_ingress_digest=existing.retrieval_ingress_digest,
                synthesis_legality_posture={},
                idempotent_replay=True,
            )
            run["claims"] = list(receipt_body.get("claims") or [])
            run["synthesis_citation_envelope"] = dict(
                receipt_body.get("synthesis_citation_envelope") or {},
            )
            art = get_synthesis_artifact_by_job_id_v1(
                session,
                tenant_id=tenant_id,
                job_id=existing.id,
            )
            if art is not None:
                run["artifact_id"] = str(art.id)
                run["artifact_digest"] = art.artifact_digest
            return run

    if job_id is not None:
        job = session.get(CortexSynthesisJob, job_id)
        if job is None or job.tenant_id != tenant_id:
            raise SynthesisOrchestratorError("synthesis_job_not_found")
        if job.status not in {"queued", "running"}:
            raise SynthesisOrchestratorError(
                "synthesis_job_not_runnable",
                detail={"status": job.status},
            )
        job.envelope_json = envelope_json_for_persistence_v1(envelope)
        job.envelope_digest = envelope_digest
    else:
        job = create_synthesis_job_row_v1(
            session,
            tenant_id=tenant_id,
            envelope=envelope,
            envelope_digest=envelope_digest,
        )

    job.status = "running"
    job.started_at = datetime.now(UTC)
    trace: list[dict[str, Any]] = []
    retrieval_ingress_digest: str | None = None
    retrieval_subqueries: list[dict[str, Any]] = []
    retrieval_ingress_snapshot: dict[str, Any] = {}
    synthesis_legality_posture: dict[str, Any] = {}
    synthesis_legality_class = "synthesis_replay_safe"
    claim_slots: list[dict[str, Any]] = []
    accepted_claims: list[dict[str, Any]] = []
    synthesis_citation_envelope: dict[str, Any] = {}
    llm_invocations: list[dict[str, Any]] = []
    llm_trace_refs: list[dict[str, Any]] = []
    prompt_assemblies: list[dict[str, Any]] = []
    prompt_hashes: list[str] = []
    synthesis_degradation_rollup: dict[str, Any] = {}
    substrate_health_state = "healthy"
    synthesis_degradation_posture = "stable"
    llm_schema_failed = False
    job_started_perf = time.perf_counter()

    try:
        # INGRESS
        t0 = time.perf_counter()
        enforce_synthesis_job_envelope_anti_goals_v1(envelope)
        _trace_phase(
            trace,
            phase="INGRESS",
            started=t0,
            extra={
                "synthesis_policy_pack_digest": envelope.get("_synthesis_policy_pack_digest"),
            },
        )

        # PLAN
        t1 = time.perf_counter()
        plan = build_synthesis_retrieval_plan_v1(envelope)
        _trace_phase(trace, phase="PLAN", started=t1, extra={"retrieval_plan_count": len(plan)})

        # RETRIEVE
        t2 = time.perf_counter()
        pinned = envelope.get("pinned_retrieval_receipt")
        if isinstance(pinned, dict):
            retrieval_response = dict(pinned.get("retrieval_response") or pinned)
            enforce_retrieval_evidence_ingress_v1(
                retrieval_response,
                job_envelope=envelope,
            )
            ingress = build_retrieval_evidence_ingress_v1(
                retrieval_response,
                job_execution_partition=str(envelope["execution_partition"]),
            )
            retrieval_ingress_snapshot = dict(ingress)
            retrieval_ingress_snapshot["retrieval_evidence_hits"] = normalize_retrieval_hits_v1(
                retrieval_response,
            )
            envelope["_retrieval_response_source"] = dict(retrieval_response)
            retrieval_ingress_digest = compute_retrieval_ingress_digest_v1(ingress)
            retrieval_subqueries = [
                build_retrieval_subquery_receipt_row_v1(
                    plan_item=plan[0] if plan else {"plan_index": 0, "role": "primary"},
                    retrieval_response=retrieval_response,
                    retrieval_ingress_digest=retrieval_ingress_digest or "",
                ),
            ]
            job.retrieval_subqueries_json = retrieval_subqueries
            session.flush()
            _trace_phase(
                trace,
                phase="RETRIEVE",
                started=t2,
                extra={
                    "mode": "pinned_receipt",
                    "retrieval_ingress_digest": retrieval_ingress_digest,
                    "retrieval_subquery_count": len(retrieval_subqueries),
                },
            )
        else:
            retrieve_out = execute_synthesis_retrieval_plan_v1(
                session,
                tenant_id=tenant_id,
                envelope=envelope,
                plan=plan,
                job_envelope=envelope,
            )
            retrieval_subqueries = list(retrieve_out["retrieval_subqueries"])
            retrieval_ingress_snapshot = dict(retrieve_out["retrieval_ingress"])
            merged_response = retrieve_out.get("retrieval_response")
            if isinstance(merged_response, Mapping):
                envelope["_retrieval_response_source"] = dict(merged_response)
            retrieval_ingress_digest = str(retrieve_out["retrieval_ingress_digest"])
            job.retrieval_subqueries_json = retrieval_subqueries
            session.flush()
            _trace_phase(
                trace,
                phase="RETRIEVE",
                started=t2,
                extra={
                    "mode": "live_retrieval_plan",
                    "retrieval_ingress_digest": retrieval_ingress_digest,
                    "retrieval_subquery_count": len(retrieval_subqueries),
                    "merged_subquery_count": retrieval_ingress_snapshot.get("retrieval_evidence_hit_count"),
                },
            )
        job.retrieval_ingress_digest = retrieval_ingress_digest

        # BIND
        t3 = time.perf_counter()
        binding = bind_synthesis_evidence_v1(
            envelope=envelope,
            retrieval_hits=normalize_retrieval_hits_v1(retrieval_ingress_snapshot),
        )
        claim_slots = list(binding["claim_slots"])
        accepted_claims = list(binding["claims"])
        synthesis_citation_envelope = dict(binding["synthesis_citation_envelope"])
        existing_sd = list(retrieval_ingress_snapshot.get("synthesis_omission_rows") or [])
        retrieval_ingress_snapshot["synthesis_omission_rows"] = existing_sd + list(
            binding["synthesis_omission_rows"],
        )
        pack_caps = synthesis_policy_pack_caps_v1()
        claim_cap_rows = list_synthesis_claim_cap_violations_v1(
            accepted_claim_count=len(accepted_claims),
            max_claims=int(
                (envelope.get("selection_policy") or {}).get("max_claims", pack_caps["max_claims"]),
            ),
        )
        if claim_cap_rows:
            retrieval_ingress_snapshot["synthesis_omission_rows"] = list(
                retrieval_ingress_snapshot.get("synthesis_omission_rows") or [],
            ) + claim_cap_rows
        evidence_scope_summary = dict(binding["evidence_scope_summary"])
        evidence_scope_summary["skeleton"] = not bool(
            retrieval_ingress_snapshot.get("retrieval_evidence_hits"),
        )
        _trace_phase(
            trace,
            phase="BIND",
            started=t3,
            extra={
                "evidence_scope_summary": evidence_scope_summary,
                "citation_envelope_digest": synthesis_citation_envelope.get("citation_envelope_digest"),
            },
        )

        # ASSEMBLE
        t4 = time.perf_counter()
        prompt_assemblies = assemble_synthesis_prompts_for_job_v1(
            envelope=envelope,
            claim_slots=claim_slots,
            synthesis_omission_rows=list(retrieval_ingress_snapshot.get("synthesis_omission_rows") or []),
            retrieval_ingress=retrieval_ingress_snapshot,
        )
        prompt_hashes = sorted(
            str(row.get("prompt_hash") or "")
            for row in prompt_assemblies
            if row.get("prompt_hash")
        )
        _trace_phase(
            trace,
            phase="ASSEMBLE",
            started=t4,
            extra={
                "claim_slot_count": len(claim_slots),
                "accepted_claim_count": len(accepted_claims),
                "citation_count": synthesis_citation_envelope.get("citation_count", 0),
                "prompt_assembly_count": len(prompt_assemblies),
                "prompt_hashes": prompt_hashes,
            },
        )

        # LLM
        t5 = time.perf_counter()
        llm_out = execute_synthesis_llm_phase_v1(
            envelope=envelope,
            retrieval_ingress=retrieval_ingress_snapshot,
            claim_slots=claim_slots,
            claims=accepted_claims,
            synthesis_omission_rows=list(retrieval_ingress_snapshot.get("synthesis_omission_rows") or []),
            synthesis_citation_envelope=synthesis_citation_envelope,
            prompt_assemblies=prompt_assemblies,
        )
        llm_invocations = list(llm_out.get("llm_invocations") or [])
        llm_trace_refs = list(llm_out.get("llm_trace_refs") or [])
        llm_schema_failed = bool(llm_out.get("llm_schema_failed"))
        accepted_claims = list(llm_out.get("claims") or accepted_claims)
        llm_sd = list(llm_out.get("synthesis_omission_rows") or [])
        if llm_sd:
            existing_sd = list(retrieval_ingress_snapshot.get("synthesis_omission_rows") or [])
            retrieval_ingress_snapshot["synthesis_omission_rows"] = existing_sd + llm_sd
        llm_status = "skipped" if llm_out.get("skipped") else "ok"
        _trace_phase(
            trace,
            phase="LLM",
            started=t5,
            status=llm_status,
            extra={
                "skip_reason": llm_out.get("skip_reason") or "",
                "llm_invocation_count": len(llm_invocations),
                "tokens_used_total": llm_out.get("tokens_used_total", 0),
                "llm_schema_failed": llm_schema_failed,
            },
        )

        # CLASSIFY (after full SD taxonomy merge)
        t6 = time.perf_counter()
        taxonomy = apply_synthesis_degradation_taxonomy_v1(
            synthesis_omission_rows=list(
                retrieval_ingress_snapshot.get("synthesis_omission_rows") or [],
            ),
            retrieval_ingress=retrieval_ingress_snapshot,
            synthesis_legality_class="synthesis_partial",
            synthesis_workload_class=str(envelope["synthesis_workload_class"]),
        )
        retrieval_ingress_snapshot["synthesis_omission_rows"] = list(
            taxonomy["synthesis_omission_rows"],
        )
        synthesis_degradation_rollup = dict(taxonomy.get("synthesis_degradation_rollup") or {})
        substrate_health_state = str(taxonomy.get("substrate_health_state") or "degraded")
        synthesis_degradation_posture = str(taxonomy.get("synthesis_degradation_posture") or "stable")
        sd_codes_sorted = list(taxonomy.get("sd_codes_sorted") or [])
        hit_legalities: list[str] = []
        if isinstance(retrieval_ingress_snapshot.get("retrieval_evidence_hits"), list):
            for hit in retrieval_ingress_snapshot["retrieval_evidence_hits"]:
                if isinstance(hit, Mapping) and hit.get("evidence_legality"):
                    hit_legalities.append(str(hit["evidence_legality"]))
        synthesis_legality_class, synthesis_legality_posture = classify_synthesis_legality_for_job_v1(
            envelope=envelope,
            retrieval_ingress=retrieval_ingress_snapshot,
            hit_evidence_legalities=hit_legalities,
            llm_schema_failed=llm_schema_failed,
        )
        assert_synthesis_job_lawful_v1(
            legality_class=synthesis_legality_class,
            synthesis_intent=str(envelope["synthesis_intent"]),
            execution_partition=str(envelope["execution_partition"]),
        )
        job.synthesis_legality_class = synthesis_legality_class
        pack = load_synthesis_policy_pack_v1(
            policy_pack_id=str(envelope.get("synthesis_policy_pack_id") or ""),
        )
        default_wl = pack.get("pipeline_default_workloads") or []
        substrate_health_state = classify_synthesis_substrate_health_v1(
            omissions=retrieval_ingress_snapshot.get("synthesis_omission_rows") or [],
            synthesis_legality_class=synthesis_legality_class,
            is_pipeline_default_workload=str(envelope["synthesis_workload_class"]) in default_wl,
        )
        _trace_phase(
            trace,
            phase="CLASSIFY",
            started=t6,
            extra={
                "synthesis_legality_class": synthesis_legality_class,
                "s_leg_violations": synthesis_legality_posture.get("s_leg_violations", []),
                "synthesis_degradation_posture": synthesis_degradation_posture,
                "substrate_health_state": substrate_health_state,
            },
        )

        # RECEIPT
        t7 = time.perf_counter()
        synthesis_job_replay_identity = compute_synthesis_job_replay_identity_v1(
            envelope=envelope,
            retrieval_ingress_digest=retrieval_ingress_digest,
            retrieval_subqueries=retrieval_subqueries,
            retrieval_ingress=retrieval_ingress_snapshot,
            claim_slots=claim_slots,
            llm_invocations=llm_invocations,
            sd_codes_sorted=sd_codes_sorted,
        )
        enforce_synthesis_expected_replay_identity_v1(
            envelope,
            computed_identity=synthesis_job_replay_identity,
        )
        receipt = build_synthesis_job_receipt_v1(
            tenant_id=str(tenant_id),
            job_id=str(job.id),
            envelope=envelope,
            execution_trace=trace,
            synthesis_legality_class=synthesis_legality_class,
            synthesis_job_replay_identity=synthesis_job_replay_identity,
            retrieval_ingress_digest=retrieval_ingress_digest,
            retrieval_subqueries=retrieval_subqueries,
            retrieval_ingress=retrieval_ingress_snapshot,
            claim_slots=claim_slots,
            llm_invocations=llm_invocations,
            sd_codes_sorted=sd_codes_sorted,
            synthesis_degradation_rollup=synthesis_degradation_rollup,
        )
        gp08_replay_01_passed = True
        synthesis_legality_class = apply_syn_rep02_retrieval_twin_legality_floor_v1(
            synthesis_legality_class,
            gp08_replay_01_passed=gp08_replay_01_passed,
        )
        job.synthesis_legality_class = synthesis_legality_class
        _trace_phase(
            trace,
            phase="RECEIPT",
            started=t7,
            extra={"receipt_digest": receipt["receipt_digest"]},
        )
        job.synthesis_job_replay_identity = synthesis_job_replay_identity
        job.receipt_digest = str(receipt["receipt_digest"])
        receipt_out = dict(receipt)
        receipt_out["synthesis_citation_envelope"] = synthesis_citation_envelope
        receipt_out["claims"] = accepted_claims
        receipt_out["llm_trace_refs"] = llm_trace_refs
        receipt_out["prompt_assemblies"] = prompt_assemblies
        receipt_out["prompt_hashes"] = prompt_hashes
        receipt_out["synthesis_degradation_rollup"] = synthesis_degradation_rollup
        receipt_out["substrate_health_state"] = substrate_health_state
        receipt_out["synthesis_degradation_posture"] = synthesis_degradation_posture
        job.receipt_json = receipt_out

        wall_ms = int((time.perf_counter() - job_started_perf) * 1000)
        max_wall = int((envelope.get("selection_policy") or {}).get("max_wall_ms", 120_000))
        assert_synthesis_wall_budget_v1(elapsed_ms=wall_ms, max_wall_ms=max_wall)

        # PUBLISH — persist SynthesisIntelligenceArtifactV1 (unpublished; epoch Step 18)
        t8 = time.perf_counter()
        pub = materialize_synthesis_artifact_for_job_v1(
            session,
            tenant_id=tenant_id,
            job=job,
            envelope=envelope,
            synthesis_legality_class=synthesis_legality_class,
            synthesis_job_replay_identity=synthesis_job_replay_identity,
            synthesis_legality_posture=synthesis_legality_posture,
            retrieval_ingress=retrieval_ingress_snapshot,
            retrieval_subqueries=retrieval_subqueries,
            claims=accepted_claims,
            synthesis_citation_envelope=synthesis_citation_envelope,
            synthesis_omission_rows=list(
                retrieval_ingress_snapshot.get("synthesis_omission_rows") or [],
            ),
            synthesis_degradation_rollup=synthesis_degradation_rollup,
            llm_trace_refs=llm_trace_refs,
            evidence_scope_summary=evidence_scope_summary,
        )
        publish_status = str(pub.get("publish_status") or "materialized")
        _trace_phase(
            trace,
            phase="PUBLISH",
            started=t8,
            status="ok",
            extra={
                "artifact_id": pub.get("artifact_id"),
                "artifact_digest": pub.get("artifact_digest"),
                "published": pub.get("published"),
                "publish_barrier_passed": (pub.get("publish_barrier") or {}).get(
                    "publish_barrier_passed",
                ),
                "publish_status": publish_status,
            },
        )
        receipt_out["artifact_id"] = pub.get("artifact_id")
        receipt_out["artifact_digest"] = pub.get("artifact_digest")
        job.execution_trace_json = list(trace)

        _assert_fsm_phase_order_v1(trace)
        _assert_execution_trace_monotonic_v1(trace)

        persist_synthesis_job_receipt_row_v1(
            session,
            job=job,
            receipt=receipt_out,
            execution_trace=trace,
        )
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        session.flush()

        run_result = build_synthesis_job_run_result_v1(
            job,
            execution_trace=trace,
            receipt=receipt_out,
            synthesis_legality_class=synthesis_legality_class,
            synthesis_job_replay_identity=synthesis_job_replay_identity,
            retrieval_ingress_digest=retrieval_ingress_digest,
            synthesis_legality_posture=synthesis_legality_posture,
            llm_invocations=llm_invocations,
            llm_trace_refs=llm_trace_refs,
            prompt_assemblies=prompt_assemblies,
            prompt_hashes=prompt_hashes,
        )
        run_result["claims"] = accepted_claims
        run_result["synthesis_citation_envelope"] = synthesis_citation_envelope
        run_result["retrieval_subqueries"] = retrieval_subqueries
        run_result["llm_invocations"] = llm_invocations
        run_result["llm_trace_refs"] = llm_trace_refs
        run_result["prompt_assemblies"] = prompt_assemblies
        run_result["prompt_hashes"] = prompt_hashes
        run_result["artifact_id"] = pub.get("artifact_id")
        run_result["artifact_digest"] = pub.get("artifact_digest")
        run_result["synthesis_intelligence_artifact"] = pub.get("artifact_body")
        twin_on_receipt = receipt_out.get("replay_equivalence_twin")
        if isinstance(twin_on_receipt, Mapping) and twin_on_receipt:
            run_result["replay_equivalence_twin"] = dict(twin_on_receipt)
        twin_passed: bool | None = None
        if isinstance(twin_on_receipt, Mapping):
            raw_twin = twin_on_receipt.get("gp08_replay_proof_passed")
            if isinstance(raw_twin, bool):
                twin_passed = raw_twin
        omission_rows = list(synthesis_degradation_rollup.get("synthesis_omission_rows") or [])
        obs = record_synthesis_job_observability_v1(
            tenant_id=tenant_id,
            job_id=job.id,
            envelope=envelope,
            status="completed",
            synthesis_legality_class=synthesis_legality_class,
            duration_ms=wall_ms,
            synthesis_job_replay_identity=synthesis_job_replay_identity,
            receipt_digest=str(receipt_out.get("receipt_digest") or ""),
            synthesis_omission_rows=omission_rows,
            llm_invocations=llm_invocations,
            artifact_id=str(pub.get("artifact_id")) if pub.get("artifact_id") else None,
            replay_twin_passed=twin_passed,
        )
        run_result["synthesis_job_log"] = obs["job_log"]
        run_result["synthesis_observability_metrics"] = obs["metrics"]
        return run_result
    except (
        SynthesisJobEnvelopeError,
        SynthesisJobContractError,
        SynthesisAntiGoalViolationError,
        SynthesisIngressError,
        SynthesisLegalityError,
        SynthesisEvidenceBindingError,
        SynthesisQueryPlanError,
        SynthesisLlmRouterError,
        SynthesisPromptAssemblyError,
        SynthesisBoundedCapsError,
        SynthesisArtifactMaterializationError,
        SynthesisBindingsError,
        SynthesisLineageError,
        SynthesisReplayEquivalenceError,
        SynthesisOrchestratorError,
    ) as exc:
        job.status = "failed"
        job.error_detail = getattr(exc, "code", str(exc))
        job.completed_at = datetime.now(UTC)
        job.execution_trace_json = list(trace)
        session.flush()
        fail_ms = int((time.perf_counter() - job_started_perf) * 1000)
        if isinstance(exc, SynthesisLegalityError) and getattr(exc, "code", "") == "synthesis_forbidden":
            record_synthesis_legality_failure_v1(reason="synthesis_forbidden")
        record_synthesis_job_observability_v1(
            tenant_id=tenant_id,
            job_id=job.id,
            envelope=envelope,
            status="failed",
            synthesis_legality_class=str(job.synthesis_legality_class or "synthesis_forbidden"),
            duration_ms=fail_ms,
            synthesis_job_replay_identity=str(job.synthesis_job_replay_identity or ""),
            receipt_digest=str(job.receipt_digest or ""),
            synthesis_omission_rows=list(synthesis_degradation_rollup.get("synthesis_omission_rows") or []),
            llm_invocations=llm_invocations,
        )
        if isinstance(exc, SynthesisOrchestratorError):
            raise
        if isinstance(
            exc,
            (
                SynthesisLegalityError,
                SynthesisReplayEquivalenceError,
                SynthesisEvidenceBindingError,
                SynthesisQueryPlanError,
                SynthesisLlmRouterError,
                SynthesisPromptAssemblyError,
                SynthesisBoundedCapsError,
                SynthesisArtifactMaterializationError,
                SynthesisBindingsError,
                SynthesisLineageError,
            ),
        ):
            raise SynthesisOrchestratorError(
                exc.code,
                http_status=exc.http_status,
                detail=exc.detail,
            ) from exc
        http_status = getattr(exc, "http_status", 400)
        raise SynthesisOrchestratorError(
            getattr(exc, "code", "synthesis_job_failed"),
            http_status=http_status,
            detail=getattr(exc, "detail", None),
        ) from exc


def get_synthesis_job_detail_v1(session: Session, *, tenant_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
    job = session.get(CortexSynthesisJob, job_id)
    if job is None or job.tenant_id != tenant_id:
        raise SynthesisOrchestratorError("synthesis_job_not_found", http_status=404)
    return {
        "surface_kind": "synthesis_job_detail",
        "job_id": str(job.id),
        "tenant_id": str(job.tenant_id),
        "status": job.status,
        "synthesis_workload_class": job.synthesis_workload_class,
        "synthesis_intent": job.synthesis_intent,
        "execution_partition": job.execution_partition,
        "envelope_json": dict(job.envelope_json or {}),
        "envelope_digest": job.envelope_digest,
        "retrieval_ingress_digest": job.retrieval_ingress_digest,
        "synthesis_job_replay_identity": job.synthesis_job_replay_identity,
        "synthesis_legality_class": job.synthesis_legality_class,
        "receipt_digest": job.receipt_digest,
        "execution_trace": list(job.execution_trace_json or []),
        "synthesis_job_receipt": dict(job.receipt_json or {}),
        "error_detail": job.error_detail,
        "celery_task_id": job.celery_task_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "retrieval_subqueries": list(job.retrieval_subqueries_json or []),
    }


def verify_gp08_fsm01_synthesis_phase_order_static() -> dict[str, Any]:
    """``G-P08-FSM-01`` — closed FSM phase order matches runtime architecture."""
    errors: list[str] = []
    expected = (
        "INGRESS",
        "PLAN",
        "RETRIEVE",
        "BIND",
        "ASSEMBLE",
        "LLM",
        "CLASSIFY",
        "RECEIPT",
        "PUBLISH",
    )
    if SYNTHESIS_JOB_EXECUTION_PHASES_V1 != expected:
        errors.append("phase_tuple_mismatch")
    if len(SYNTHESIS_JOB_EXECUTION_PHASES_V1) != 9:
        errors.append(f"phase_count:{len(SYNTHESIS_JOB_EXECUTION_PHASES_V1)}")
    trace: list[dict[str, Any]] = []
    t = time.perf_counter()
    for phase in SYNTHESIS_JOB_EXECUTION_PHASES_V1:
        _trace_phase(trace, phase=phase, started=t)
        t += 0.001
    try:
        _assert_fsm_phase_order_v1(trace)
        _assert_execution_trace_monotonic_v1(trace)
    except SynthesisOrchestratorError as exc:
        errors.append(exc.code)
    return {
        "id": GP08_FSM01_GATE_ID_V1,
        "name": "synthesis_fsm_phase_order",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {
            "phase08_synthesis_orchestrator_runtime_schema_version": (
                PHASE08_SYNTHESIS_ORCHESTRATOR_RUNTIME_SCHEMA_VERSION
            ),
            "phases": list(SYNTHESIS_JOB_EXECUTION_PHASES_V1),
            "errors": errors,
        },
    }


def verify_gp08_schema01_synthesis_job_envelope_execution_static() -> dict[str, Any]:
    """``G-P08-SCHEMA-01`` — envelope normalization rejects forbidden cognition keys."""
    errors: list[str] = []
    tid = uuid.UUID(int=0)
    try:
        coerce_body_to_synthesis_job_envelope_v1(
            {
                "schema_version": 1,
                "tenant_id": str(tid),
                "synthesis_workload_class": "pipeline_default",
                "synthesis_intent": "inspect",
                "execution_partition": "authoritative",
            },
            tenant_id=tid,
        )
    except Exception as exc:
        errors.append(f"legal_envelope_rejected:{exc}")
    try:
        from vector.domains.cortex.synthesis.synthesis_job_envelope import (
            normalize_synthesis_job_envelope_v1,
        )

        normalize_synthesis_job_envelope_v1(
            {
                "schema_version": 1,
                "tenant_id": str(tid),
                "synthesis_workload_class": "pipeline_default",
                "synthesis_intent": "inspect",
                "execution_partition": "authoritative",
                "natural_language_query": "forbidden",
            },
            tenant_id=tid,
        )
    except Exception:
        pass
    else:
        errors.append("expected_forbidden_key_rejection")
    digest = synthesis_policy_pack_digest_v1()
    if len(digest) < 32:
        errors.append("policy_digest_format")
    return {
        "id": "G-P08-SCHEMA-01",
        "name": "synthesis_job_envelope_execution",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

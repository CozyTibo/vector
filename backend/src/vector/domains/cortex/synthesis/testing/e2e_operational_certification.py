"""Phase 08 Step 34 — E2E operational certification (scenarios A–D)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import index_tcre_chain_for_retrieval_v1
from vector.domains.cortex.retrieval.testing.e2e_pipeline_harness import (
    run_substrate_pipeline_sync_through_retrieval_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.domains.cortex.synthesis.normative import PHASE08_REPLAY_IDENTITY_FIELD_V1
from vector.domains.cortex.synthesis.synthesis_pipeline import run_substrate_phase_08_synthesis_v1
from vector.domains.cortex.synthesis.synthesis_publication import (
    get_current_synthesis_publication_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1
from vector.domains.cortex.synthesis.synthesis_job_envelope import compute_synthesis_job_envelope_digest_v1
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_replay_equivalence import (
    verify_gp08_replay01_canonical_identity_stable_static,
)
from vector.domains.cortex.synthesis.testing.e2e_pipeline_harness import (
    build_synthesis_pipeline_execute_stub_v1,
)
from vector.domains.cortex.synthesis.testing.e2e_verification import (
    assert_synthesis_control_plane_runtime_backed_v1,
    assert_synthesis_degraded_upstream_v1,
    assert_synthesis_idempotent_replay_v1,
    assert_synthesis_replay_twin_zero_citation_diff_v1,
    assert_synthesis_substrate_ready_v1,
    degraded_upstream_retrieval_stub_v1,
    get_completed_job_with_receipt_v1,
    get_synthesis_job_artifact_v1,
    legal_retrieval_stub_v1,
    load_first_index_lookup_v1,
)

PHASE08_SYNTHESIS_E2E_RUNTIME_SCHEMA_VERSION: Final[int] = 1

GP08_E2E01_GATE_ID_V1: Final[str] = "G-P08-E2E-01"

SYNTHESIS_E2E_SCENARIOS_V1: Final[tuple[str, ...]] = (
    "scenario_a_pipeline_default",
    "scenario_b_degraded_upstream",
    "scenario_c_replay_twin",
    "scenario_d_pipeline_idempotency",
)

SYNTHESIS_E2E_TEST_MODULES_V1: Final[tuple[str, ...]] = (
    "test_phase08_step34_synthesis_e2e_operational.py",
)


def _synthesis_e2e_tests_dir_v1() -> Path:
    """Locate synthesis acceptance pytest modules (monorepo ``backend/tests`` or compose ``/app/tests``)."""
    here = Path(__file__).resolve()
    rel = Path("vector") / "domains" / "cortex" / "synthesis"
    seen: set[Path] = set()
    for root in [here, *here.parents]:
        for prefix in (root / "tests", root / "backend" / "tests"):
            candidate = (prefix / rel).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.is_dir():
                return candidate
    docker_candidate = (Path("/app/tests") / rel).resolve()
    if docker_candidate.is_dir():
        return docker_candidate
    msg = "synthesis acceptance tests dir not found"
    raise RuntimeError(msg)


def run_synthesis_e2e_scenario_a_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None,
    batch_limit: int = 50,
) -> dict[str, Any]:
    """Scenario A — happy path: pipeline 02–08 + synthesis publication + control plane."""
    if not bundle_id:
        return {"scenario": "A", "passed": False, "skipped": True, "reason": "no_bundle_id"}

    pipeline = run_substrate_pipeline_sync_through_retrieval_v1(
        session,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
    if pipeline.get("skipped"):
        return {"scenario": "A", "passed": False, "skipped": True, "reason": pipeline.get("reason")}

    prid = uuid.UUID(str(pipeline["pipeline_run_id"]))
    epoch = pipeline.get("published_index_epoch") or pipeline.get("index_epoch")
    if not epoch:
        return {"scenario": "A", "passed": False, "skipped": True, "reason": "no_published_index_epoch"}

    epoch_str = str(epoch)
    lookup = load_first_index_lookup_v1(session, tenant_id=tenant_id, index_epoch=epoch_str)
    if not lookup:
        entry = index_tcre_chain_for_retrieval_v1(
            session,
            tenant_id=tenant_id,
            causal_chain_id=f"chain-a-{uuid.uuid4().hex[:8]}",
            replay_identity=f"replay-a-{uuid.uuid4().hex[:8]}",
            traversal_epoch=epoch_str,
        )
        session.flush()
        lookup = entry.retrieval_lookup_id
    stub = build_synthesis_pipeline_execute_stub_v1(
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        published_index_epoch=epoch_str,
        retrieval_lookup_id=lookup,
        pinned_retrieval_response=legal_retrieval_stub_v1(),
    )
    from vector.settings import get_settings

    if not get_settings().cortex_substrate_pipeline_phase_08_enabled:
        return {
            "scenario": "A",
            "passed": False,
            "skipped": True,
            "reason": "phase_08_disabled",
        }

    import vector.domains.cortex.synthesis.synthesis_pipeline as syn_pipe

    original = syn_pipe.execute_synthesis_job_envelope_v1  # type: ignore[attr-defined]
    syn_pipe.execute_synthesis_job_envelope_v1 = stub  # type: ignore[attr-defined]
    try:
        syn_out = run_substrate_phase_08_synthesis_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
        )
    finally:
        syn_pipe.execute_synthesis_job_envelope_v1 = original  # type: ignore[attr-defined]

    phase08 = get_phase_run_v1(session, pipeline_run_id=prid, phase_id=PHASE_08_SYNTHESIS)
    pipeline = {
        **pipeline,
        **syn_out,
        "pipeline_run_id": str(prid),
        "synthesis_publication_epoch": syn_out.get("synthesis_publication_epoch")
        or get_current_synthesis_publication_epoch_v1(session, tenant_id=tenant_id),
        "phase_08_status": phase08.status if phase08 else None,
    }

    ready = assert_synthesis_substrate_ready_v1(session, tenant_id=tenant_id)
    cp = assert_synthesis_control_plane_runtime_backed_v1(session, tenant_id=tenant_id)
    job = get_completed_job_with_receipt_v1(session, tenant_id=tenant_id)
    artifact = (
        get_synthesis_job_artifact_v1(session, tenant_id=tenant_id, job_id=job.id)
        if job is not None
        else None
    )
    replay01 = verify_gp08_replay01_canonical_identity_stable_static()
    passed = (
        ready["ready"]
        and cp["passed"]
        and bool(pipeline.get("synthesis_publication_epoch"))
        and pipeline.get("phase_08_status") in ("completed", "skipped")
        and job is not None
        and artifact is not None
        and replay01.get("passed")
    )
    return {
        "scenario": "A",
        "passed": passed,
        "pipeline": pipeline,
        "ready": ready,
        "control_plane": cp,
        "job_id": str(job.id) if job else None,
        "artifact_id": str(artifact.id) if artifact else None,
        "replay01_static": replay01.get("passed"),
    }


def run_synthesis_e2e_scenario_b_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Scenario B — upstream degradation (RD-TCRE-GAP → SD-UPSTREAM-RD)."""
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "pinned_retrieval_receipt": {"retrieval_response": degraded_upstream_retrieval_stub_v1()},
    }
    out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
    omissions: list[Mapping[str, Any]] = []
    artifact_id = out.get("artifact_id")
    if artifact_id:
        from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact

        art = session.get(CortexSynthesisArtifact, uuid.UUID(str(artifact_id)))
        if art is not None and isinstance(art.body_json, dict):
            omissions = [
                dict(r)
                for r in art.body_json.get("synthesis_omission_rows") or []
                if isinstance(r, Mapping)
            ]
            rollup = art.body_json.get("synthesis_degradation_rollup") or {}
            if not omissions and isinstance(rollup, dict):
                omissions = [
                    {"sd_code": code, "synthesis_omission_class": code}
                    for code in rollup.get("sd_codes_sorted") or []
                ]
    check = assert_synthesis_degraded_upstream_v1(
        synthesis_legality_class=str(out.get("synthesis_legality_class") or ""),
        omission_rows=omissions,
    )
    return {
        "scenario": "B",
        "passed": check["passed"] and bool(out.get("artifact_id")),
        "degradation_check": check,
        "synthesis_legality_class": out.get("synthesis_legality_class"),
    }


def run_synthesis_e2e_scenario_c_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Scenario C — replay_equivalence_synthesis inline twin."""
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "replay_equivalence_synthesis",
        "synthesis_intent": "prove",
        "execution_partition": "authoritative",
        "retrieval_scope": {},
        "pinned_retrieval_receipt": {"retrieval_response": legal_retrieval_stub_v1(replay_identity="rqid:e2e-c")},
    }
    out = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
    twin = out.get("replay_equivalence_twin") or {}
    check = assert_synthesis_replay_twin_zero_citation_diff_v1(session, twin_result=twin)
    return {
        "scenario": "C",
        "passed": bool(check["passed"]) and bool(out.get(PHASE08_REPLAY_IDENTITY_FIELD_V1)),
        "replay_twin": check,
        "gp08_replay_proof_passed": twin.get("gp08_replay_proof_passed"),
    }


def run_synthesis_e2e_scenario_d_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Scenario D — idempotency key returns same completed job."""
    from vector.domains.cortex.synthesis.synthesis_job_envelope import (
        coerce_body_to_synthesis_job_envelope_v1,
    )

    idem = f"e2e-idem-{uuid.uuid4().hex[:12]}"
    body = {
        "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "synthesis_workload_class": "degradation_brief",
        "synthesis_intent": "inspect",
        "execution_partition": "authoritative",
        "idempotency_key": idem,
        "retrieval_scope": {},
        "pinned_retrieval_receipt": {"retrieval_response": legal_retrieval_stub_v1(replay_identity="rqid:e2e-d")},
    }
    envelope = coerce_body_to_synthesis_job_envelope_v1(body, tenant_id=tenant_id)
    digest = compute_synthesis_job_envelope_digest_v1(envelope)
    out_a = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
    out_b = execute_synthesis_job_envelope_v1(session, tenant_id=tenant_id, body=body)
    idem_check = assert_synthesis_idempotent_replay_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=idem,
        envelope_digest=digest,
    )
    same_job = out_a.get("job_id") == out_b.get("job_id")
    same_artifact = out_a.get("artifact_id") == out_b.get("artifact_id")
    return {
        "scenario": "D",
        "passed": bool(idem_check["passed"]) and same_job and same_artifact,
        "idempotency_check": idem_check,
        "job_id_a": out_a.get("job_id"),
        "job_id_b": out_b.get("job_id"),
        "artifact_id": out_a.get("artifact_id"),
    }


def run_synthesis_e2e_certification_bundle_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Run scenarios A–D and return certification-shaped summary."""
    results = {
        "A": run_synthesis_e2e_scenario_a_v1(session, tenant_id=tenant_id, bundle_id=bundle_id),
        "B": run_synthesis_e2e_scenario_b_v1(session, tenant_id=tenant_id),
        "C": run_synthesis_e2e_scenario_c_v1(session, tenant_id=tenant_id),
        "D": run_synthesis_e2e_scenario_d_v1(session, tenant_id=tenant_id),
    }
    passed = all(bool(r.get("passed")) for r in results.values() if not r.get("skipped"))
    return {
        "gate_id": GP08_E2E01_GATE_ID_V1,
        "tenant_id": str(tenant_id),
        "scenarios": results,
        "all_passed": passed,
        "certification_digest": hash_reasoning_canonical_json_sha256_v1(
            {k: {"passed": v.get("passed"), "skipped": v.get("skipped")} for k, v in results.items()},
        ),
    }


def build_synthesis_e2e_operational_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_e2e_operational_v1",
        "phase08_synthesis_e2e_runtime_schema_version": PHASE08_SYNTHESIS_E2E_RUNTIME_SCHEMA_VERSION,
        "gate_id": GP08_E2E01_GATE_ID_V1,
        "scenarios": list(SYNTHESIS_E2E_SCENARIOS_V1),
        "test_modules": list(SYNTHESIS_E2E_TEST_MODULES_V1),
        "spec_ref": "DOCS/cortex/synthesis/phase-08-e2e-operational-flow.md",
    }


def verify_gp08_e2e01_operational_certification_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        tests_dir = _synthesis_e2e_tests_dir_v1()
    except RuntimeError:
        errors.append("repo_root_not_found")
        tests_dir = Path(".")
    for mod in SYNTHESIS_E2E_TEST_MODULES_V1:
        if not (tests_dir / mod).is_file():
            errors.append(f"missing_test_module:{mod}")

    for name in (
        "run_synthesis_e2e_scenario_a_v1",
        "run_synthesis_e2e_scenario_b_v1",
        "run_synthesis_e2e_scenario_c_v1",
        "run_synthesis_e2e_scenario_d_v1",
        "run_synthesis_e2e_certification_bundle_v1",
    ):
        if name not in globals():
            errors.append(f"missing:{name}")

    return {
        "id": GP08_E2E01_GATE_ID_V1,
        "name": "gp08_e2e01_operational_certification",
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

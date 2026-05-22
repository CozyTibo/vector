#!/usr/bin/env python3
"""Step 12 — Fix 6–7, Track B soak T0, Level 6 synthesis wedge (Fizzer)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("VECTOR_SETTINGS_SKIP_DOTENV", "1")
os.environ.setdefault("VECTOR_USE_MOCK_CONNECTORS", "false")

_env = Path(__file__).resolve().parents[2] / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

for _k in ("GITHUB_APP_PRIVATE_KEY_PATH", "GITHUB_APP_PRIVATE_KEY"):
    os.environ.pop(_k, None)

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.operator_snapshot import (  # noqa: E402
    build_canonical_forward_progress_snapshot,
)
from vector.domains.cortex.completeness.canonical_completeness_projection import (  # noqa: E402
    project_canonical_completeness_v1,
)
from vector.domains.cortex.pipeline.pipeline_admin_overview import build_pipeline_overview_v1  # noqa: E402
from vector.domains.cortex.retrieval.retrieval_index_materialization import (  # noqa: E402
    get_published_index_epoch_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS  # noqa: E402
from vector.domains.cortex.substrate_pipeline.repository import (  # noqa: E402
    get_phase_run_v1,
    get_running_pipeline_run_v1,
)
from vector.domains.cortex.synthesis.synthesis_job_contract import (  # noqa: E402
    SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import (  # noqa: E402
    execute_synthesis_job_envelope_v1,
)
from vector.domains.cortex.synthesis.synthesis_pipeline import (  # noqa: E402
    materialize_synthesis_for_pipeline_v1,
)
from vector.domains.cortex.synthesis.testing.e2e_verification import (  # noqa: E402
    get_completed_job_with_receipt_v1,
    get_synthesis_job_artifact_v1,
    legal_retrieval_stub_v1,
    load_first_index_lookup_v1,
)
from vector.domains.cortex.unlock.step12_track_b_p3 import evaluate_step12_v1  # noqa: E402
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun  # noqa: E402
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (  # noqa: E402
    CortexTenantConvergenceLease,
)
from vector.settings import get_settings  # noqa: E402

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
RUN_SYNTHESIS = os.environ.get("UNLOCK_STEP12_RUN_SYNTHESIS", "1").lower() not in ("0", "false", "no")
MAX_SCOPES = max(1, min(int(os.environ.get("UNLOCK_STEP12_MAX_SCOPES", "4")), 32))
ARTIFACT_PATH = Path(
    os.environ.get(
        "UNLOCK_STEP12_ARTIFACT",
        str(_Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step12_2026-05-22.json"),
    )
)


def _db_url() -> str:
    return (
        f"postgresql+psycopg://{os.environ['DB_PROD_USER']}:{os.environ['DB_PROD_PASSWORD']}"
        f"@{os.environ['DB_PROD_HOST']}:{os.environ.get('DB_PROD_PORT', '5432')}"
        f"/{os.environ.get('DB_PROD_DATABASE', 'postgres')}"
    )


def _resolve_pipeline_run_id(db: Session, tenant_id: uuid.UUID) -> uuid.UUID | None:
    running = get_running_pipeline_run_v1(db, tenant_id=tenant_id)
    if running is not None:
        return running.id
    return db.scalar(
        select(CortexSubstratePipelineRun.id)
        .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
        .order_by(CortexSubstratePipelineRun.started_at.desc())
        .limit(1)
    )


def _lease_snapshot(db: Session, tenant_id: uuid.UUID) -> dict:
    row = db.scalars(
        select(CortexTenantConvergenceLease).where(CortexTenantConvergenceLease.tenant_id == tenant_id)
    ).first()
    if row is None:
        return {}
    detail = dict(row.detail_json or {})
    return {
        "fsm_state": row.fsm_state,
        "phase_cursor": row.phase_cursor,
        "last_canonical_outcome": detail.get("last_canonical_outcome"),
    }


def main() -> dict:
    captured_at = datetime.now(UTC).isoformat()
    settings = get_settings()
    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 12,
        "validated_at": captured_at,
    }
    with Session(engine) as db:
        can_env = project_canonical_completeness_v1(db, tenant_id=TID)
        metrics = dict(can_env.get("metrics") or {})
        out["canonical_completeness_metrics"] = metrics

        fp = build_canonical_forward_progress_snapshot(db, tenant_id=TID)
        fp_metrics = dict(fp.get("metrics") or {})
        out["forward_progress"] = {
            "bundle_id": fp.get("bundle_id"),
            "metrics": fp_metrics,
            "lease": fp.get("convergence_lease"),
        }

        lease = _lease_snapshot(db, TID)
        out["lease"] = lease

        overview = build_pipeline_overview_v1(db, settings, tenant_id=TID)
        canonical_phase = next((p for p in overview.get("phases") or [] if p.get("phase") == "canonical"), {})
        out["pipeline_overview_canonical"] = {
            "backlog_count": canonical_phase.get("backlog_count"),
            "status": canonical_phase.get("status"),
        }

        pipeline_run_id = _resolve_pipeline_run_id(db, TID)
        out["pipeline_run_id"] = str(pipeline_run_id) if pipeline_run_id else None
        published_epoch = get_published_index_epoch_v1(db, tenant_id=TID)
        out["published_index_epoch"] = published_epoch

        syn_out: dict = {}
        phase_08_status: str | None = None
        phase_08_output: dict = {}
        if RUN_SYNTHESIS and pipeline_run_id and published_epoch:
            prev_max = settings.cortex_synthesis_pipeline_max_scopes
            try:
                settings.cortex_synthesis_pipeline_max_scopes = MAX_SCOPES
                if os.environ.get("UNLOCK_STEP12_INLINE_SYNTHESIS", "1").lower() not in ("0", "false"):
                    syn_out = materialize_synthesis_for_pipeline_v1(
                        db,
                        tenant_id=TID,
                        pipeline_run_id=pipeline_run_id,
                        published_index_epoch=published_epoch,
                        settings=settings,
                    )
                else:
                    syn_out = run_substrate_phase_08_synthesis_v1(
                        db,
                        tenant_id=TID,
                        pipeline_run_id=pipeline_run_id,
                        settings=settings,
                    )
                db.commit()
            finally:
                settings.cortex_synthesis_pipeline_max_scopes = prev_max
            phase08 = get_phase_run_v1(db, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
            phase_08_status = phase08.status if phase08 else None
            phase_08_output = dict(phase08.output_json or {}) if phase08 else dict(syn_out)
        out["synthesis_materialization"] = syn_out

        job = get_completed_job_with_receipt_v1(db, tenant_id=TID)
        artifact_body: dict = {}
        legality: str | None = None
        artifact_count = 0
        wedge_syn: dict = {}
        if job is None and RUN_SYNTHESIS and pipeline_run_id and published_epoch:
            lookup = load_first_index_lookup_v1(
                db, tenant_id=TID, index_epoch=published_epoch
            )
            replay_id = lookup or f"rqid:unlock-step12-{published_epoch[:12]}"
            body = {
                "schema_version": SYNTHESIS_JOB_ENVELOPE_SCHEMA_VERSION_V1,
                "tenant_id": str(TID),
                "synthesis_workload_class": "degradation_brief",
                "synthesis_intent": "inspect",
                "execution_partition": "authoritative",
                "retrieval_scope": {"retrieval_lookup_id": replay_id},
                "retrieval_pins": {"index_epoch": published_epoch},
                "pinned_retrieval_receipt": {
                    "retrieval_response": legal_retrieval_stub_v1(replay_identity=replay_id),
                },
                "substrate_pipeline_run_id": str(pipeline_run_id),
            }
            try:
                wedge_syn = execute_synthesis_job_envelope_v1(db, tenant_id=TID, body=body)
                db.commit()
                out["synthesis_wedge_fallback"] = wedge_syn
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                out["synthesis_wedge_fallback"] = {"error": str(exc)[:500]}
            job = get_completed_job_with_receipt_v1(db, tenant_id=TID)
            if job is None and wedge_syn.get("job_id"):
                from vector.infrastructure.db.models.cortex_synthesis_job import (  # noqa: E402
                    CortexSynthesisJob,
                )

                job = db.get(CortexSynthesisJob, uuid.UUID(str(wedge_syn["job_id"])))
        job_receipt: dict = {}
        if job is not None:
            legality = str(job.synthesis_legality_class or "")
            art = get_synthesis_job_artifact_v1(db, tenant_id=TID, job_id=job.id)
            if art is not None:
                artifact_count = 1
                artifact_body = dict(art.body_json or {})
            if not artifact_body and isinstance(wedge_syn.get("synthesis_intelligence_artifact"), dict):
                artifact_body = dict(wedge_syn["synthesis_intelligence_artifact"])
            job_receipt = dict(wedge_syn.get("synthesis_job_receipt") or job.receipt_json or {})
            out["synthesis_job"] = {
                "job_id": str(job.id),
                "status": job.status,
                "synthesis_legality_class": legality,
                "receipt_digest": job.receipt_digest,
            }

        evaluation = evaluate_step12_v1(
            settings=settings,
            forward_progress_metrics=metrics or fp_metrics,
            lease_phase_cursor=lease.get("phase_cursor"),
            lease_last_canonical_outcome=lease.get("last_canonical_outcome"),
            phase_08_status=phase_08_status,
            phase_08_output=phase_08_output or syn_out,
            synthesis_legality_class=legality,
            artifact_body=artifact_body,
            jobs_completed=int(syn_out.get("jobs_completed") or 0),
            artifact_count=artifact_count,
            synthesis_job_receipt=job_receipt,
            soak_captured_at=captured_at,
        )
        out["evaluation"] = evaluation
        out["step12_pass"] = evaluation["step12_pass"]
        out["step12_detail"] = evaluation["step12_detail"]
        out["level_6_met"] = evaluation["level_6_met"]

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    main()

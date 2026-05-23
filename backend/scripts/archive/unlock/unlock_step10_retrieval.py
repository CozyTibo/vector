#!/usr/bin/env python3
"""Step 10 — prod RETRIEVAL wedge for evidence recovery (Fizzer A6)."""

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

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.admin_commands import restart_execution_from_phase_v1  # noqa: E402
from vector.domains.cortex.retrieval.retrieval_index_materialization import (  # noqa: E402
    bootstrap_retrieval_index_from_upstream_v1,
    get_published_index_epoch_v1,
    materialize_retrieval_index_for_pipeline_v1,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (  # noqa: E402
    RET_SKIP_GRAPH_DISCONNECTED_V1,
    normalize_skip_reasons_from_stats_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL  # noqa: E402
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1  # noqa: E402
from vector.domains.cortex.traversal.runtime.durable_walk_store import (  # noqa: E402
    resolve_octs_walk_store_v1,
)
from vector.domains.cortex.unlock.step10_retrieval import (  # noqa: E402
    evaluate_a6_evidence_recovery_v1,
    summarize_ret_skip_codes_v1,
)
from vector.infrastructure.db.models.cortex_retrieval_materialization_report import (  # noqa: E402
    CortexRetrievalMaterializationReport,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (  # noqa: E402
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (  # noqa: E402
    CortexTcreReconstructionJob,
)

TENANT = os.environ.get("PROOF_TENANT_ID", "c08ef32b-f89a-40f6-9566-e19b5329436f")
TID = uuid.UUID(TENANT)
RUN_RESTART = os.environ.get("UNLOCK_STEP10_RUN_RESTART", "1").lower() not in ("0", "false", "no")
MAX_GRAPH_LINKS = max(1, min(int(os.environ.get("UNLOCK_STEP10_MAX_GRAPH_LINKS", "200")), 500))
USE_BOOTSTRAP = os.environ.get("UNLOCK_STEP10_USE_BOOTSTRAP", "1").lower() not in ("0", "false", "no")


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


def _count_completed_walks(db: Session, tenant_id: uuid.UUID) -> int:
    store = resolve_octs_walk_store_v1(db)
    return sum(
        1
        for r in store.list_walk_records_for_tenant_v1(tenant_id)
        if str(r.status) == "completed" and r.walk_payload
    )


def _count_completed_tcre_jobs(db: Session, tenant_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        )
        or 0
    )


def _latest_materialization_report(db: Session, tenant_id: uuid.UUID) -> dict[str, object] | None:
    row = db.scalars(
        select(CortexRetrievalMaterializationReport)
        .where(CortexRetrievalMaterializationReport.tenant_id == tenant_id)
        .order_by(CortexRetrievalMaterializationReport.created_at.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    return {
        "id": str(row.id),
        "accepted_rows": int(row.accepted_rows or 0),
        "skipped_rows": int(row.skipped_rows or 0),
        "tcre_candidates": int(row.tcre_candidates or 0),
        "walks_candidates": int(row.walks_candidates or 0),
        "org_link_candidates": int(row.org_link_candidates or 0),
        "skip_reasons": list(row.skip_reasons_json or []),
        "retrieval_epoch": row.retrieval_epoch,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _recent_phase07_runs(db: Session, tenant_id: uuid.UUID, *, limit: int = 3) -> list[dict]:
    rows = db.execute(
        select(
            CortexSubstratePhaseRun.status,
            CortexSubstratePhaseRun.output_json,
            CortexSubstratePhaseRun.started_at,
        )
        .join(
            CortexSubstratePipelineRun,
            CortexSubstratePipelineRun.id == CortexSubstratePhaseRun.pipeline_run_id,
        )
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == PHASE_07_RETRIEVAL,
        )
        .order_by(CortexSubstratePhaseRun.started_at.desc())
        .limit(limit)
    ).all()
    out: list[dict] = []
    for status, output_json, started_at in rows:
        oj = output_json if isinstance(output_json, dict) else {}
        out.append(
            {
                "status": str(status),
                "entries_materialized": oj.get("entries_materialized"),
                "entry_count": oj.get("entry_count"),
                "retrieval_outcome": oj.get("retrieval_outcome"),
                "build_state": oj.get("build_state"),
                "started_at": started_at.isoformat() if started_at else None,
            }
        )
    return out


def main() -> dict:
    from vector.domains.cortex.substrate_pipeline.continuity_cleanup_freeze import (
        WedgeScriptBannedDuringHoldError,
        assert_wedge_script_allowed_v1,
    )

    try:
        assert_wedge_script_allowed_v1(__file__, repo_root=_Path(__file__).resolve().parents[2])
    except WedgeScriptBannedDuringHoldError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    engine = create_engine(_db_url())
    out: dict = {
        "tenant_id": TENANT,
        "step": 10,
        "validated_at": datetime.now(UTC).isoformat(),
    }
    with Session(engine) as db:
        out["completed_walks"] = _count_completed_walks(db, TID)
        out["completed_tcre_jobs"] = _count_completed_tcre_jobs(db, TID)
        out["published_index_epoch_before"] = get_published_index_epoch_v1(db, tenant_id=TID)
        out["materialization_report_before"] = _latest_materialization_report(db, TID)

        if RUN_RESTART:
            try:
                restart_out = restart_execution_from_phase_v1(
                    db,
                    tenant_id=TID,
                    from_phase="RETRIEVAL",
                    force=True,
                )
                db.commit()
                out["execution_restart"] = restart_out
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                out["execution_restart"] = {"restarted": False, "error": str(exc)}

        pipeline_run_id = _resolve_pipeline_run_id(db, TID)
        out["pipeline_run_id"] = str(pipeline_run_id) if pipeline_run_id else None

        mat: dict
        if pipeline_run_id is not None:
            mat = materialize_retrieval_index_for_pipeline_v1(
                db,
                tenant_id=TID,
                pipeline_run_id=pipeline_run_id,
            )
        elif USE_BOOTSTRAP:
            mat = bootstrap_retrieval_index_from_upstream_v1(
                db,
                tenant_id=TID,
                max_graph_links=MAX_GRAPH_LINKS,
            )
        else:
            mat = {"ok": False, "reason": "no_pipeline_run_and_bootstrap_disabled"}
        db.commit()
        out["retrieval_materialization"] = mat

        skip_raw = list(mat.get("skip_reasons") or [])
        skip_counts = summarize_ret_skip_codes_v1(skip_raw)
        out["ret_skip_code_counts"] = skip_counts
        out["ret_skip_codes_normalized"] = normalize_skip_reasons_from_stats_v1(skip_raw)
        out["graph_disconnect_dominated"] = (
            bool(skip_counts)
            and not {k for k in skip_counts if k != RET_SKIP_GRAPH_DISCONNECTED_V1}
            and RET_SKIP_GRAPH_DISCONNECTED_V1 in skip_counts
        )

        entries = int(mat.get("entries_materialized") or mat.get("entry_count") or 0)
        accepted = int(mat.get("entry_count") or entries)
        a6_ok, a6_detail = evaluate_a6_evidence_recovery_v1(
            entries_materialized=entries,
            skip_code_counts=skip_counts,
            materialization_attempts=1,
            accepted_rows=accepted,
        )
        out["A6_pass"] = a6_ok
        out["A6_detail"] = a6_detail
        out["published_index_epoch_after"] = get_published_index_epoch_v1(db, tenant_id=TID)
        out["materialization_report_after"] = _latest_materialization_report(db, TID)
        out["phase_07_recent"] = _recent_phase07_runs(db, TID)

        if int(out.get("completed_walks") or 0) < 1:
            out["A6_pass"] = False
            out["A6_detail"] = "completed_walks=0 (prerequisite for A6 after step 9)"

    return out


if __name__ == "__main__":
    payload = main()
    text = json.dumps(payload, indent=2, default=str)
    out_path = _Path(__file__).resolve().parents[2] / "DOCS/audits/baselines/fizzer_step10_2026-05-22.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(text)
    if not payload.get("A6_pass"):
        raise SystemExit(1)

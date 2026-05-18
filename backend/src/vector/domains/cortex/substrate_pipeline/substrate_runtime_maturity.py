"""Tenant runtime maturity stages (structural legality vs operational aliveness)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

STAGE_0_IDLE: Final[str] = "STAGE_0_IDLE"
STAGE_1_INGESTING: Final[str] = "STAGE_1_INGESTING"
STAGE_2_PIPELINE_RUNNING: Final[str] = "STAGE_2_PIPELINE_RUNNING"
STAGE_3_TCRE_ACTIVE: Final[str] = "STAGE_3_TCRE_ACTIVE"
STAGE_4_RETRIEVAL_PUBLISHED: Final[str] = "STAGE_4_RETRIEVAL_PUBLISHED"
STAGE_5_SYNTHESIS_ACTIVE: Final[str] = "STAGE_5_SYNTHESIS_ACTIVE"
STAGE_6_CONTINUOUSLY_OPERATIONAL: Final[str] = "STAGE_6_CONTINUOUSLY_OPERATIONAL"

MATURITY_STAGES_ORDER_V1: Final[tuple[str, ...]] = (
    STAGE_0_IDLE,
    STAGE_1_INGESTING,
    STAGE_2_PIPELINE_RUNNING,
    STAGE_3_TCRE_ACTIVE,
    STAGE_4_RETRIEVAL_PUBLISHED,
    STAGE_5_SYNTHESIS_ACTIVE,
    STAGE_6_CONTINUOUSLY_OPERATIONAL,
)


def evaluate_tenant_runtime_maturity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Classify tenant operational maturity from durable runtime signals."""
    recent_ingestion = session.scalar(
        select(func.count())
        .select_from(IngestionRun)
        .where(IngestionRun.tenant_id == tenant_id)
    )
    running_pipeline = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running_pipeline.id)
        if running_pipeline
        else None
    )
    tcre_active = int(
        session.scalar(
            select(func.count())
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status.in_(("queued", "running")),
            )
        )
        or 0
    )
    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    eligible = int(scope.get("eligible_scopes") or 0)
    synth_completed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
            )
        )
        or 0
    )

    stage = STAGE_0_IDLE
    if int(recent_ingestion or 0) > 0:
        stage = STAGE_1_INGESTING
    if running_pipeline is not None:
        stage = STAGE_2_PIPELINE_RUNNING
    if continuation is not None and continuation.continuation_status == CONTINUATION_STATUS_WAITING:
        stage = STAGE_3_TCRE_ACTIVE
    elif tcre_active > 0:
        stage = STAGE_3_TCRE_ACTIVE
    if published and eligible > 0:
        stage = STAGE_4_RETRIEVAL_PUBLISHED
    if synth_completed > 0:
        stage = STAGE_5_SYNTHESIS_ACTIVE
    if published and eligible > 0 and synth_completed > 0:
        stage = STAGE_6_CONTINUOUSLY_OPERATIONAL

    return {
        "tenant_id": str(tenant_id),
        "maturity_stage": stage,
        "maturity_stage_ordinal": MATURITY_STAGES_ORDER_V1.index(stage),
        "signals": {
            "ingestion_runs": int(recent_ingestion or 0),
            "pipeline_running": running_pipeline is not None,
            "tcre_active_jobs": tcre_active,
            "published_index_epoch": published,
            "eligible_scopes": eligible,
            "completed_synthesis_jobs": synth_completed,
            "continuation_waiting": (
                continuation.continuation_status == CONTINUATION_STATUS_WAITING
                if continuation
                else False
            ),
        },
        "structurally_legal_but_idle": eligible == 0 and published is not None,
        "operationally_alive": stage
        in (STAGE_5_SYNTHESIS_ACTIVE, STAGE_6_CONTINUOUSLY_OPERATIONAL),
    }

"""Cortex substrate pipeline orchestration (ingestion → retrieval closure)."""

from vector.domains.cortex.substrate_pipeline.orchestrator import (
    schedule_substrate_pipeline_v1,
    substrate_pipeline_celery_task_id,
)

__all__ = [
    "schedule_substrate_pipeline_v1",
    "substrate_pipeline_celery_task_id",
]

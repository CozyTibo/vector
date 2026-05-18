"""Cortex substrate pipeline phase identifiers and orchestration constants."""

from __future__ import annotations

from typing import Final

SUBSTRATE_PIPELINE_SCHEMA_VERSION: Final[int] = 1

PHASE_01_INGESTION: Final[str] = "phase_01_ingestion"
PHASE_02_CANONICAL: Final[str] = "phase_02_canonical"
PHASE_03_IDENTITY: Final[str] = "phase_03_identity"
PHASE_04_GRAPH: Final[str] = "phase_04_graph"
PHASE_05_TRAVERSAL: Final[str] = "phase_05_traversal"
PHASE_06_TCRE: Final[str] = "phase_06_tcre"
PHASE_07_RETRIEVAL: Final[str] = "phase_07_retrieval"
PHASE_08_SYNTHESIS: Final[str] = "phase_08_synthesis"

SUBSTRATE_PIPELINE_PHASE_ORDER: Final[tuple[str, ...]] = (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)

PHASE_STATUS_QUEUED: Final[str] = "queued"
PHASE_STATUS_RUNNING: Final[str] = "running"
PHASE_STATUS_COMPLETED: Final[str] = "completed"
PHASE_STATUS_FAILED: Final[str] = "failed"
PHASE_STATUS_SKIPPED: Final[str] = "skipped"

PIPELINE_STATUS_QUEUED: Final[str] = "queued"
PIPELINE_STATUS_RUNNING: Final[str] = "running"
PIPELINE_STATUS_COMPLETED: Final[str] = "completed"
PIPELINE_STATUS_FAILED: Final[str] = "failed"
PIPELINE_STATUS_PARTIAL: Final[str] = "partial"

PIPELINE_TRIGGER_POST_INGESTION: Final[str] = "post_ingestion"
PIPELINE_TRIGGER_FLUSH_RERUN: Final[str] = "flush_rerun"
PIPELINE_TRIGGER_MANUAL: Final[str] = "manual"

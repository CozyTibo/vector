"""Cortex Phase 01 — ingestion lifecycle (runs, raw rows, checkpoints)."""

from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync

__all__ = ["execute_connector_sync"]

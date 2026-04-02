"""Metrics for Linear projection drain."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LinearProjectionMetrics:
    raw_rows_processed: int = 0
    batches_committed: int = 0

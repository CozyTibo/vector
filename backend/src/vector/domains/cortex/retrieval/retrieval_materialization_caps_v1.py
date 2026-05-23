"""Wave S3 — per-epoch materialization caps (orchestration; mix gate uses separate thresholds)."""

from __future__ import annotations

from typing import Final

RETRIEVAL_MATERIALIZATION_CAPS_SCHEMA_VERSION: Final[int] = 1


def get_retrieval_max_org_link_entries_per_epoch_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_retrieval_max_org_link_entries_per_epoch))
    except Exception:  # noqa: BLE001
        return 500


def get_retrieval_max_canonical_materializations_per_epoch_v1() -> int:
    try:
        from vector.settings import get_settings

        return max(1, int(get_settings().cortex_retrieval_max_canonical_materializations_per_epoch))
    except Exception:  # noqa: BLE001
        return 800

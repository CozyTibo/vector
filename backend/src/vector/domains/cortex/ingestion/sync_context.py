"""Phase 01 Step 3 — live vs replay execution context (checkpoint namespaces, lineage)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

SCOPE_DEFAULT = "default"

_ALLOWED_SYNC_MODES = frozenset({"live", "replay"})


@dataclass(frozen=True)
class IngestionSyncContext:
    """Carries sync mode and replay lineage for one executor invocation.

    Live runs use ``scope_key=default`` checkpoints. Replay runs use a separate
    ``replay:<replay_job_id>`` scope so live cursors are never advanced from replay work.

    ``backfill_lane`` selects the checkpoint backfill writer without a separate top-level
    sync mode (live | replay only).
    """

    sync_mode: str
    replay_job_id: uuid.UUID | None
    replay_version: int
    backfill_lane: bool = False

    @property
    def replay_mode(self) -> bool:
        return self.sync_mode == "replay"

    @property
    def writes_backfill_lane(self) -> bool:
        return self.backfill_lane and not self.replay_mode

    @property
    def checkpoint_sync_mode(self) -> str:
        """Checkpoint lane for merge_monotonic_connector_state (incremental vs backfill)."""
        if self.replay_mode:
            return "incremental"
        return "backfill" if self.backfill_lane else "incremental"

    def checkpoint_scope_key(self) -> str:
        if self.replay_mode and self.replay_job_id is not None:
            return f"replay:{self.replay_job_id}"
        return SCOPE_DEFAULT

    def validate(self) -> None:
        if self.sync_mode not in _ALLOWED_SYNC_MODES:
            msg = f"sync_mode must be one of {sorted(_ALLOWED_SYNC_MODES)}"
            raise ValueError(msg)
        if self.sync_mode == "replay" and self.replay_job_id is None:
            msg = "replay_job_id is required when sync_mode is replay"
            raise ValueError(msg)
        if self.replay_version < 1:
            msg = "replay_version must be >= 1"
            raise ValueError(msg)

    @staticmethod
    def live_incremental() -> IngestionSyncContext:
        return IngestionSyncContext(
            sync_mode="live",
            replay_job_id=None,
            replay_version=1,
            backfill_lane=False,
        )

    @staticmethod
    def replay(*, replay_job_id: uuid.UUID, replay_version: int = 1) -> IngestionSyncContext:
        return IngestionSyncContext(
            sync_mode="replay",
            replay_job_id=replay_job_id,
            replay_version=replay_version,
            backfill_lane=False,
        )

    @staticmethod
    def backfill() -> IngestionSyncContext:
        return IngestionSyncContext(
            sync_mode="live",
            replay_job_id=None,
            replay_version=1,
            backfill_lane=True,
        )

"""Optional org-link replay lane runners registered by downstream packages (no CESP import)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob

LAWFUL_EDGE_PROMOTION_JOB_KIND_V1: Final[str] = "lawful_edge_promotion"

_LawfulEdgePromotionRunner = Callable[[Session, CortexOrgLinkReplayJob], None]

_lawful_edge_promotion_runner_v1: _LawfulEdgePromotionRunner | None = None


def register_lawful_edge_promotion_runner_v1(runner: _LawfulEdgePromotionRunner) -> None:
    global _lawful_edge_promotion_runner_v1
    _lawful_edge_promotion_runner_v1 = runner


def run_lawful_edge_promotion_lane_v1(db: Session, job: CortexOrgLinkReplayJob) -> None:
    if _lawful_edge_promotion_runner_v1 is None:
        from vector.domains.cortex.identity.org_link_replay_runtime import OrgLinkReplayError

        raise OrgLinkReplayError("lawful_edge_promotion_runner_not_registered")
    _lawful_edge_promotion_runner_v1(db, job)

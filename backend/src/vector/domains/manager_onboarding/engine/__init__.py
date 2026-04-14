"""Manager Slack onboarding engine (LLM turn + validate + merge)."""

from vector.domains.manager_onboarding.engine.requirements import (
    missing_requirements,
    primary_requirement,
)
from vector.domains.manager_onboarding.engine.turn import EngineTurnResult, run_engine_turn

__all__ = [
    "EngineTurnResult",
    "missing_requirements",
    "primary_requirement",
    "run_engine_turn",
]

"""§6 Step 42 — learning demotion for ``prioritize_decisions`` (after Step 27 base tuple).

**Sort contract (Steps 27–28):** ``prioritize_decisions`` uses a combined gap key
``gap_type_rank * STRIDE + learning_demotion`` (see ``prioritize_decisions``) so large
demotions (e.g. ``suppress``) can move a gap later **across** nominal gap-type bands while
zero demotion preserves legacy Step 27 ordering.

**Formula (deterministic, capped):**

- ``policy_fp = min(500, 50 * fp_count)`` where ``fp_count`` is ``false_positive_count`` on the
  **latest** ``window_start`` policy row for ``dimension == f"gap_type:{gap_type}"`` in the
  fetch window ``[as_of - window_days, as_of]`` (see repo helper).
- ``outcome_fp = min(300, 30 * n_fp)`` where ``n_fp`` counts ``manager_insight_outcomes`` rows
  with ``false_positive IS TRUE``, ``observed_at`` in the same window, joined to persisted
  decisions for ``gap_type``.
- ``suppress = 10_000`` if **any** policy row for that ``gap_type`` in the window has
  ``suppress_until > as_of``; else ``0``.
- ``learning_demotion = policy_fp + outcome_fp + suppress`` (missing aggregates → 0).

When no DB context is passed (``learning is None``), demotion is **0** for every row — identical
ordering to Step 27-only behavior.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from vector.domains.manager_insights.data_reliability import default_window
from vector.infrastructure.db.repositories.manager_insight_outcomes import (
    fetch_gap_type_false_positive_outcome_counts_for_sort,
    fetch_gap_type_policy_for_decision_sort,
)

# Caps keep sort stable and avoid dominating Step 27 ordering except explicit suppression.
_POLICY_FP_WEIGHT = 50
_POLICY_FP_CAP = 500
_OUTCOME_FP_WEIGHT = 30
_OUTCOME_FP_CAP = 300
_SUPPRESS_DEMOTION = 10_000


@dataclass(frozen=True)
class DecisionSortLearning:
    """Precomputed §6 Step 42 demotion per coordination ``gap_type``."""

    _demotion_by_gap_type: dict[str, int]

    @staticmethod
    def empty() -> DecisionSortLearning:
        return DecisionSortLearning(_demotion_by_gap_type={})

    def demotion_for_gap_type(self, gap_type: str) -> int:
        return self._demotion_by_gap_type.get(gap_type, 0)

    def gap_demotions_for_qa(self) -> dict[str, int]:
        """Copy of per-``gap_type`` demotion totals for ``perception_qa`` (admin JSON)."""
        return dict(self._demotion_by_gap_type)

    @classmethod
    def from_policy_and_outcome_maps(
        cls,
        *,
        policy_by_gap: Mapping[str, tuple[int, bool]],
        outcome_fp_by_gap: Mapping[str, int],
    ) -> DecisionSortLearning:
        keys = set(policy_by_gap) | set(outcome_fp_by_gap)
        dem: dict[str, int] = {}
        for gt in keys:
            fp_count, suppressed = policy_by_gap.get(gt, (0, False))
            n_fp = int(outcome_fp_by_gap.get(gt, 0))
            policy_fp = min(_POLICY_FP_CAP, _POLICY_FP_WEIGHT * max(0, int(fp_count)))
            outcome_fp = min(_OUTCOME_FP_CAP, _OUTCOME_FP_WEIGHT * max(0, n_fp))
            suppress = _SUPPRESS_DEMOTION if suppressed else 0
            total = policy_fp + outcome_fp + suppress
            if total:
                dem[gt] = total
        return DecisionSortLearning(_demotion_by_gap_type=dem)


def load_decision_sort_learning(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    as_of: datetime,
    window_days: int,
) -> DecisionSortLearning:
    """Load aggregates from PostgreSQL and build §6 Step 42 demotion map."""
    window_start, window_end = default_window(window_days=window_days, as_of=as_of)
    policy = fetch_gap_type_policy_for_decision_sort(
        session,
        tenant_id=tenant_id,
        window_start=window_start,
        as_of=window_end,
    )
    outcomes = fetch_gap_type_false_positive_outcome_counts_for_sort(
        session,
        tenant_id=tenant_id,
        window_start=window_start,
        as_of=window_end,
    )
    return DecisionSortLearning.from_policy_and_outcome_maps(
        policy_by_gap=policy,
        outcome_fp_by_gap=outcomes,
    )


__all__ = [
    "DecisionSortLearning",
    "load_decision_sort_learning",
]

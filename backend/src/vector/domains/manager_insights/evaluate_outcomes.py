"""§6 Step 41 — deterministic ``ground_truth`` enrichment for persisted outcomes (no ML).

Rules are versioned under ``ground_truth["rule_version"]`` so callers can skip already-evaluated
rows unless ``reset=True``. ``ground_truth["rules_applied"]`` lists rule ids cumulatively.

``step41_v0`` rules (see ``compute_ground_truth_patch``):

- ``stamp`` — ``rule_version``, ``evaluated_at`` (ISO-8601 UTC).
- ``orphan_outcome`` — no matching decision row ⇒ ``decision_row_missing`` = **true**.
- ``coherence_dismissed`` — ``dismissed`` outcome vs decision ``status``.
- ``coherence_apply_success`` — ``applied_success`` vs ``completed`` + ``receipt.ok``.
- ``apply_non_terminal_note`` — ``applied_partial`` / ``apply_failed`` review hint.
- ``false_positive_note`` — ``false_positive is True`` flag recorded.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.infrastructure.db.models.manager_insight_decision import ManagerInsightDecision
from vector.infrastructure.db.repositories.manager_insight_decisions import (
    get_manager_insight_decision_for_tenant,
)
from vector.infrastructure.db.repositories.manager_insight_outcomes import (
    list_manager_insight_outcomes_chronological,
)

RULE_VERSION = "step41_v0"


def _receipt_ok(receipt: dict[str, Any] | None) -> bool:
    if not receipt or not isinstance(receipt, dict):
        return False
    return receipt.get("ok") is True


def _merge_rule_ids(existing_applied: Any, new_rules: list[str]) -> list[str]:
    base: list[str] = []
    if isinstance(existing_applied, list):
        base = [str(x) for x in existing_applied if isinstance(x, str)]
    seen = set(base)
    out = list(base)
    for r in new_rules:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


def compute_ground_truth_patch(
    *,
    decision: ManagerInsightDecision | None,
    outcome_type: str,
    false_positive: bool | None,
    existing_ground_truth: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Return ``(patch merged onto existing, rule ids fired this pass)``."""
    applied: list[str] = []
    patch: dict[str, Any] = {}
    before_rules = existing_ground_truth.get("rules_applied")

    now = datetime.now(tz=UTC).isoformat().replace("+00:00", "Z")
    patch["rule_version"] = RULE_VERSION
    patch["evaluated_at"] = now
    applied.append("stamp")

    if decision is None:
        patch["decision_row_missing"] = True
        applied.append("orphan_outcome")
    else:
        st = decision.status
        if outcome_type == "dismissed":
            patch["decision_outcome_coherent"] = st == "dismissed"
            applied.append("coherence_dismissed")
        if outcome_type == "applied_success":
            patch["apply_outcome_matches_lifecycle"] = (
                st == "completed" and _receipt_ok(decision.receipt)
            )
            applied.append("coherence_apply_success")
        if outcome_type in ("applied_partial", "apply_failed"):
            patch["apply_terminal_review"] = "suggested"
            applied.append("apply_non_terminal_note")

    if false_positive is True:
        patch["flagged_false_positive_recorded"] = True
        applied.append("false_positive_note")

    patch["rules_applied"] = _merge_rule_ids(before_rules, applied)
    return patch, applied


@dataclass(frozen=True)
class EvaluateOutcomeRowResult:
    outcome_id: uuid.UUID
    decision_id: uuid.UUID
    rules_applied: list[str]
    ground_truth_before: dict[str, Any]
    ground_truth_after: dict[str, Any]


def run_evaluate_outcomes_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    reset: bool,
    scan_cap: int = 800,
) -> tuple[int, int, int, list[EvaluateOutcomeRowResult]]:
    """Update up to ``limit`` outcomes; returns ``(processed, skipped, scanned, items)``."""
    candidates = list_manager_insight_outcomes_chronological(
        session,
        tenant_id=tenant_id,
        scan_limit=scan_cap,
    )
    processed = 0
    skipped = 0
    scanned = 0
    items: list[EvaluateOutcomeRowResult] = []

    for outcome in candidates:
        if processed >= limit:
            break
        scanned += 1
        before = dict(outcome.ground_truth or {})
        if not reset and before.get("rule_version") == RULE_VERSION:
            skipped += 1
            continue

        decision = get_manager_insight_decision_for_tenant(
            session,
            tenant_id=tenant_id,
            decision_id=outcome.decision_id,
        )
        patch, rules = compute_ground_truth_patch(
            decision=decision,
            outcome_type=outcome.outcome_type,
            false_positive=outcome.false_positive,
            existing_ground_truth=before,
        )
        after = {**before, **patch}
        outcome.ground_truth = after
        session.flush()
        processed += 1
        items.append(
            EvaluateOutcomeRowResult(
                outcome_id=outcome.id,
                decision_id=outcome.decision_id,
                rules_applied=list(rules),
                ground_truth_before=before,
                ground_truth_after=after,
            ),
        )

    return processed, skipped, scanned, items


__all__ = [
    "RULE_VERSION",
    "EvaluateOutcomeRowResult",
    "compute_ground_truth_patch",
    "run_evaluate_outcomes_for_tenant",
]

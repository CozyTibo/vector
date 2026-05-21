"""TRUE P0C — canonical drain uses deterministic pass rotation only."""

from __future__ import annotations

from vector.domains.cortex.canonical.forward_progress.pass_fairness import resolve_fair_pass_cursor
from vector.domains.cortex.execution.scheduling import verify_canonical_deterministic_selection_v1


def test_verify_canonical_deterministic_selection() -> None:
    assert verify_canonical_deterministic_selection_v1() == []


def test_resolve_fair_pass_cursor_fixed_rotation() -> None:
    c1, rt1, pk1, n1, sk1 = resolve_fair_pass_cursor(0)
    c2, rt2, pk2, n2, sk2 = resolve_fair_pass_cursor(n1)
    assert (c1, rt1) != (c2, rt2) or pk1 != pk2 or n1 != n2
    assert sk1 is False and sk2 is False

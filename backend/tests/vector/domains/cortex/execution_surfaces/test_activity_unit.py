"""Activity stream helpers."""

from vector.domains.cortex.execution_surfaces.activity import _stable_event_id


def test_stable_event_id_deterministic() -> None:
    a = _stable_event_id("relationship_observed", "id-1", "2026-01-01T00:00:00+00:00")
    b = _stable_event_id("relationship_observed", "id-1", "2026-01-01T00:00:00+00:00")
    assert a == b
    assert len(a) == 32

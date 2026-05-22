"""War-room step 7 — graph density promotion (alive criterion A2)."""

from __future__ import annotations

A2_WEDGE_MIN_AUTHORITATIVE_LINKS = 1
A2_PROMOTION_PASS_MAX_EXPECTED = 200


def evaluate_a2_authoritative_links_v1(
    *,
    authoritative_links_active: int,
    promoted_count: int | None = None,
) -> tuple[bool, str]:
    """Return (passed, detail) for alive criterion A2 after lawful promotion pass."""
    active = int(authoritative_links_active)
    promoted = int(promoted_count) if promoted_count is not None else None
    if active >= A2_PROMOTION_PASS_MAX_EXPECTED:
        return (
            True,
            f"authoritative_links_active={active} at_pass_cap>={A2_PROMOTION_PASS_MAX_EXPECTED}",
        )
    if active >= A2_WEDGE_MIN_AUTHORITATIVE_LINKS:
        if promoted is not None and promoted > 0:
            return (
                True,
                f"authoritative_links_active={active}>={A2_WEDGE_MIN_AUTHORITATIVE_LINKS}:promoted={promoted}",
            )
        return True, f"authoritative_links_active={active}>={A2_WEDGE_MIN_AUTHORITATIVE_LINKS}"
    if promoted is not None and promoted > 0:
        return (
            False,
            f"promoted_count={promoted} but authoritative_links_active={active}",
        )
    return (
        False,
        f"authoritative_links_active={active} below wedge minimum {A2_WEDGE_MIN_AUTHORITATIVE_LINKS}",
    )

"""Unit tests for tenant slug helpers."""

from __future__ import annotations

from vector.domains.identity_access.slug import base_slug_from_domain, unique_slug


def test_base_slug_from_domain() -> None:
    assert base_slug_from_domain("ACME.Corp") == "acme-corp"


def test_base_slug_fallback() -> None:
    assert base_slug_from_domain("...") == "org"


def test_unique_slug_no_collision() -> None:
    assert unique_slug(lambda _s: None, "acme.io") == "acme-io"


def test_unique_slug_with_collision() -> None:
    def first(slug: str) -> object | None:
        return object() if slug == "acme-io" else None

    out = unique_slug(first, "acme.io")
    assert out.startswith("acme-io-")
    assert len(out) > len("acme-io")

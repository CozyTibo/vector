"""Unit tests for email domain parsing."""

from __future__ import annotations

import pytest

from vector.domains.identity_access.email_domain import email_domain_from_address


def test_email_domain_from_address_ok() -> None:
    assert email_domain_from_address("User@Example.COM") == "example.com"


@pytest.mark.parametrize(
    "raw",
    ["", "nope", "@only.com", "only@"],
)
def test_email_domain_invalid(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid email"):
        email_domain_from_address(raw)

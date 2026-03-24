"""Password policy and hashing."""

from __future__ import annotations

import pytest

from vector.domains.identity_access.errors import WeakPasswordError
from vector.domains.identity_access.services.passwords import (
    hash_password,
    validate_password_policy,
    verify_password,
)


def test_validate_too_short() -> None:
    with pytest.raises(WeakPasswordError):
        validate_password_policy("short")


def test_hash_and_verify_roundtrip() -> None:
    h = hash_password("good-long-pass")
    assert verify_password(h, "good-long-pass")
    assert not verify_password(h, "wrong-password-here")


def test_empty_verify_fails() -> None:
    h = hash_password("another-good-pass-here")
    assert not verify_password(h, "")

"""Password hashing (Argon2id)."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from vector.domains.identity_access.errors import WeakPasswordError

_MIN_LEN = 8
_MAX_LEN = 128

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def validate_password_policy(plain: str) -> None:
    if len(plain) < _MIN_LEN:
        raise WeakPasswordError(f"password must be at least {_MIN_LEN} characters")
    if len(plain) > _MAX_LEN:
        raise WeakPasswordError(f"password must be at most {_MAX_LEN} characters")


def hash_password(plain: str) -> str:
    validate_password_policy(plain)
    return _hasher.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain)
    except VerifyMismatchError:
        return False

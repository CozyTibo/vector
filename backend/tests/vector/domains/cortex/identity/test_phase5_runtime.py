from __future__ import annotations

from vector.domains.cortex.identity.resolver_version import (
    IDENTITY_RESOLVER_VERSION,
    effective_identity_resolver_version,
    get_identity_resolver_version,
)


def test_resolver_version_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_IDENTITY_RESOLVER_VERSION", "7")
    assert get_identity_resolver_version(override=3) == 3


def test_resolver_version_env_fallback(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_IDENTITY_RESOLVER_VERSION", "4")
    assert get_identity_resolver_version() == 4


def test_effective_resolver_version_never_below_code_baseline() -> None:
    assert effective_identity_resolver_version(override=1) == IDENTITY_RESOLVER_VERSION


from __future__ import annotations

from vector.domains.cortex.identity.resolver_version import get_identity_resolver_version


def test_resolver_version_override_wins(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_IDENTITY_RESOLVER_VERSION", "7")
    assert get_identity_resolver_version(override=3) == 3


def test_resolver_version_env_fallback(monkeypatch) -> None:
    monkeypatch.setenv("CORTEX_IDENTITY_RESOLVER_VERSION", "4")
    assert get_identity_resolver_version() == 4


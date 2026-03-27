"""Post-install redirect allowlist."""

from __future__ import annotations

from vector.domains.connectors.github.return_path import sanitize_github_install_return_to


def test_allows_app_onboarding() -> None:
    assert sanitize_github_install_return_to("/app/onboarding") == "/app/onboarding"


def test_strips_query() -> None:
    assert sanitize_github_install_return_to("/app/foo?x=1") == "/app/foo"


def test_rejects_external() -> None:
    assert sanitize_github_install_return_to("https://evil.test/app/x") is None


def test_rejects_double_slash() -> None:
    assert sanitize_github_install_return_to("//evil.test/app/x") is None


def test_rejects_non_app() -> None:
    assert sanitize_github_install_return_to("/admin") is None

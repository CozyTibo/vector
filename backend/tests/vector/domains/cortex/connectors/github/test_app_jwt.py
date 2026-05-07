"""GitHub App JWT (RS256)."""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from vector.domains.cortex.connectors.github.app_jwt import create_github_app_jwt
from vector.settings import get_settings


def _generate_rsa_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode()


@pytest.fixture(autouse=True)
def _minimal_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://vector:vector@127.0.0.1:5432/vector",
        ),
    )
    # Compose/.env often sets PATH; these tests must sign with the monkeypatched PEM only.
    monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PATH", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_github_app_jwt_iss_prefers_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    pem = _generate_rsa_pem()
    monkeypatch.setenv("GITHUB_APP_ID", "99999")
    monkeypatch.setenv("GITHUB_CLIENT_ID", "Iv23.clientidtest")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", pem)
    get_settings.cache_clear()
    settings = get_settings()
    token = create_github_app_jwt(settings)
    priv = cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(pem.encode(), password=None),
    )
    public = priv.public_key()
    payload = jwt.decode(
        token,
        public,
        algorithms=["RS256"],
        options={"require": ["exp", "iat", "iss"]},
    )
    assert payload["iss"] == "Iv23.clientidtest"


def test_github_app_jwt_iss_falls_back_to_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    pem = _generate_rsa_pem()
    monkeypatch.setenv("GITHUB_APP_ID", "12345")
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", pem)
    get_settings.cache_clear()
    settings = get_settings()
    token = create_github_app_jwt(settings)
    priv = cast(
        RSAPrivateKey,
        serialization.load_pem_private_key(pem.encode(), password=None),
    )
    payload = jwt.decode(
        token,
        priv.public_key(),
        algorithms=["RS256"],
        options={"require": ["exp", "iat", "iss"]},
    )
    assert payload["iss"] == "12345"

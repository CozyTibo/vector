"""Unit tests for connector install JSON vs redirect."""

from __future__ import annotations

import json

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from vector.api.http.routes.connectors.install_response import install_redirect_or_json


def test_install_redirect_or_json_defaults_to_redirect() -> None:
    r = install_redirect_or_json("https://example.com/oauth", install_response=None)
    assert isinstance(r, RedirectResponse)
    assert r.headers["location"] == "https://example.com/oauth"


def test_install_redirect_or_json_json_body() -> None:
    r = install_redirect_or_json("https://example.com/oauth", install_response="json")
    assert isinstance(r, JSONResponse)
    body = json.loads(r.body.decode())
    assert body == {"url": "https://example.com/oauth"}


def test_install_redirect_or_json_rejects_unknown() -> None:
    with pytest.raises(HTTPException) as exc_info:
        install_redirect_or_json("https://example.com/oauth", install_response="xml")
    assert exc_info.value.status_code == 400

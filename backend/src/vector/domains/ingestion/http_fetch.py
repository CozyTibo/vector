"""HTTP fetch with retries (429 / transient errors)."""

from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

_logger = logging.getLogger("app")


class FetchTransientError(Exception):
    """Retryable failure (rate limit, 5xx, network)."""


class FetchFatalError(Exception):
    """Non-retryable HTTP failure."""


def _sleep_backoff(attempt: int, retry_after: float | None) -> None:
    if retry_after is not None and retry_after > 0:
        time.sleep(min(retry_after, 60.0))
        return
    base = min(2**attempt, 30.0)
    jitter = random.uniform(0, 0.5)
    time.sleep(base + jitter)


class FetchExecutor:
    """Thin httpx wrapper with conservative retries."""

    def __init__(
        self,
        *,
        timeout_s: float = 60.0,
        max_retries: int = 6,
    ) -> None:
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._client = httpx.Client(timeout=timeout_s, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                resp = self._client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                )
            except httpx.RequestError as e:
                last_exc = e
                _logger.warning(
                    "http request error %s %s attempt=%s",
                    method,
                    url,
                    attempt,
                    exc_info=True,
                )
                if attempt + 1 >= self._max_retries:
                    raise FetchTransientError(str(e)) from e
                _sleep_backoff(attempt, None)
                continue

            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After")
                retry_s = float(ra) if ra and ra.isdigit() else None
                if attempt + 1 >= self._max_retries:
                    raise FetchTransientError(f"http 429 {url}") from None
                _sleep_backoff(attempt, retry_s)
                continue

            if 500 <= resp.status_code < 600:
                if attempt + 1 >= self._max_retries:
                    raise FetchTransientError(f"http {resp.status_code} {url}") from None
                _sleep_backoff(attempt, None)
                continue

            return resp

        msg = "exhausted retries"
        raise FetchTransientError(msg) from last_exc


def raise_for_github_status(resp: httpx.Response, *, allow_404: bool = False) -> None:
    if resp.status_code == 404 and allow_404:
        return
    if resp.status_code in (401, 403):
        raise FetchFatalError(f"github auth error http {resp.status_code}")
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:300]
        raise FetchFatalError(f"github http {resp.status_code}: {snippet}")

"""Verify Slack signing secret (Events API + Interactivity)."""

from __future__ import annotations

import hashlib
import hmac
import time


def verify_slack_signature(
    *,
    signing_secret: str,
    timestamp_header: str,
    raw_body: bytes,
    signature_header: str,
    max_age_seconds: int = 60 * 5,
) -> bool:
    """Return True if the request is authentic and fresh enough."""
    if not signing_secret.strip() or not timestamp_header or not signature_header:
        return False
    try:
        ts = int(timestamp_header)
    except ValueError:
        return False
    if abs(int(time.time()) - ts) > max_age_seconds:
        return False
    basestring = f"v0:{timestamp_header}:{raw_body.decode('utf-8')}"
    digest = hmac.new(
        signing_secret.encode("utf-8"),
        basestring.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    expected = f"v0={digest}"
    return hmac.compare_digest(expected, signature_header)

"""Normalize Redis URLs for TLS (ElastiCache ``rediss://``)."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Celery accepts CERT_* spellings in URLs; redis-py 6+ only accepts ``none`` / ``optional`` / ``required``.
_CELERY_SSL_TO_REDIS_PY = {
    "cert_none": "none",
    "cert_optional": "optional",
    "cert_required": "required",
}


def normalize_rediss_url(url: str) -> str:
    """Ensure ``ssl_cert_reqs`` works for redis-py ``from_url`` (and Celery still accepts it).

    redis-py expects lowercase strings ``none``, ``optional``, ``required`` — not ``CERT_NONE``.
    Celery maps both spellings to the same ssl constants (see celery.backends.redis).
    """
    stripped = url.strip()
    if not stripped.lower().startswith("rediss://"):
        return stripped

    parts = urlsplit(stripped)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    qdict = dict(pairs)

    req = qdict.get("ssl_cert_reqs")
    if req is not None:
        normalized_key = req.strip().lower()
        if normalized_key in _CELERY_SSL_TO_REDIS_PY:
            qdict["ssl_cert_reqs"] = _CELERY_SSL_TO_REDIS_PY[normalized_key]
        elif normalized_key in ("none", "optional", "required"):
            qdict["ssl_cert_reqs"] = normalized_key
        else:
            qdict["ssl_cert_reqs"] = req
    else:
        qdict["ssl_cert_reqs"] = "none"

    new_query = urlencode(sorted(qdict.items()))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

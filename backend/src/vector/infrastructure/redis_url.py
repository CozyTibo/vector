"""Normalize Redis URLs for TLS (ElastiCache ``rediss://``)."""


def normalize_rediss_url(url: str) -> str:
    """Append ``ssl_cert_reqs=CERT_NONE`` when missing so redis-py/Celery match ElastiCache TLS."""
    stripped = url.strip()
    if not stripped.lower().startswith("rediss://"):
        return stripped
    if "ssl_cert_reqs=" in stripped.lower():
        return stripped
    sep = "&" if "?" in stripped else "?"
    return f"{stripped}{sep}ssl_cert_reqs=CERT_NONE"

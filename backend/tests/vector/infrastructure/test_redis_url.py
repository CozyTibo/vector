from vector.infrastructure.redis_url import normalize_rediss_url


def test_normalize_rediss_appends_none() -> None:
    u = "rediss://host:6379/0"
    out = normalize_rediss_url(u)
    assert "ssl_cert_reqs=none" in out
    assert out.startswith("rediss://host:6379/0?")


def test_normalize_rediss_rewrites_celery_cert_none() -> None:
    u = "rediss://host:6379/0?ssl_cert_reqs=CERT_NONE"
    assert normalize_rediss_url(u) == "rediss://host:6379/0?ssl_cert_reqs=none"


def test_non_tls_unchanged() -> None:
    assert normalize_rediss_url("redis://127.0.0.1:6379/0") == "redis://127.0.0.1:6379/0"

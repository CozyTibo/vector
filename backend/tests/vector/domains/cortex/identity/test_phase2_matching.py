from __future__ import annotations

from vector.domains.cortex.identity.materialize import _local_part_token, same_local_part_with_tenant_domain


def test_same_local_part_with_tenant_domain_true() -> None:
    assert (
        same_local_part_with_tenant_domain(
            left_email="Tibo@Example.com",
            right_email="tibo@example.com",
            tenant_domain="example.com",
        )
        is True
    )


def test_same_local_part_with_tenant_domain_false_when_domain_differs() -> None:
    assert (
        same_local_part_with_tenant_domain(
            left_email="tibo@example.com",
            right_email="tibo@other.com",
            tenant_domain="example.com",
        )
        is False
    )


def test_local_part_token_removes_non_alnum() -> None:
    assert _local_part_token("julien.siauvaud+eng@fizzer.com") == "juliensiauvaudeng"


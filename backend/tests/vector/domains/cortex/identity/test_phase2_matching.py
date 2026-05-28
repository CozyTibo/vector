from __future__ import annotations

from vector.domains.cortex.identity.materialize import (
    _handle_matches_email_local_part,
    _local_part_token,
    _name_token,
    _significant_handle_overlap,
    same_local_part_with_tenant_domain,
)


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


def test_handle_matches_email_local_part_rejects_short_first_names() -> None:
    assert not _handle_matches_email_local_part({"julien", "julienmaitre"}, "julien")
    assert _handle_matches_email_local_part({"julienpeyruchat"}, "julienpeyruchat")


def test_significant_handle_overlap_ignores_short_shared_handles() -> None:
    assert not _significant_handle_overlap({"julien", "julienmaitre"}, {"julien", "juliendurieux"})
    assert _significant_handle_overlap({"julienpeyruchat"}, {"julienpeyruchat", "julien"})


def test_name_token_normalizes_accents_and_separators() -> None:
    assert _name_token("Cyril Clément") == "cyrilclement"


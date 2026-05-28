from __future__ import annotations

import uuid

from vector.domains.cortex.identity.materialize import (
    _cross_actor_match_handles,
    _edit_distance_at_most_one,
    _handle_matches_email_local_part,
    _local_part_token,
    _matches_initial_plus_surname_suffix,
    _name_token,
    _significant_handle_overlap,
    _significant_handles_edit_distance_one,
    _surname_suffixes_from_email_local,
    same_local_part_with_tenant_domain,
)
from vector.domains.cortex.identity.signals import ActorSignal


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


def test_surname_suffix_links_github_initial_login() -> None:
    local = _local_part_token("cecile@fizzer.com")
    assert local == "cecile"
    handles = {"cecileveneziani"}
    suffixes = _surname_suffixes_from_email_local(local or "", handles)
    assert suffixes == {"veneziani"}
    assert _matches_initial_plus_surname_suffix("cveneziani", local or "", suffixes)
    assert not _matches_initial_plus_surname_suffix("juliendurieux", local or "", suffixes)


def test_edit_distance_one_on_long_handles() -> None:
    assert _edit_distance_at_most_one("cecileveneziani", "ccileveneziani")
    assert not _edit_distance_at_most_one("cecileveneziani", "cveneziani")
    assert _significant_handles_edit_distance_one({"ccileveneziani"}, {"cecileveneziani"})


def test_cross_actor_match_handles_use_provider_login_only() -> None:
    maitre = ActorSignal(
        canon_entity_id=uuid.uuid4(),
        connector="slack",
        connection_id=uuid.uuid4(),
        entity_key="k",
        primary_handle="julienmaitre",
    )
    maitre.handles = {"julien", "julienmaitre", "julienphotoweb"}
    durieux = ActorSignal(
        canon_entity_id=uuid.uuid4(),
        connector="slack",
        connection_id=uuid.uuid4(),
        entity_key="k2",
        primary_handle="juliendurieux",
    )
    durieux.handles = {"julien", "juliendurieux"}
    assert not _significant_handle_overlap(_cross_actor_match_handles(maitre), _cross_actor_match_handles(durieux))


def test_name_token_normalizes_accents_and_separators() -> None:
    assert _name_token("Cyril Clément") == "cyrilclement"


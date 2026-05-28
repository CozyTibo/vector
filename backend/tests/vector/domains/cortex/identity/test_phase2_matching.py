from __future__ import annotations

import uuid

from vector.domains.cortex.identity.materialize import (
    _actor_has_tenant_email,
    _cross_actor_match_handles,
    _edit_distance_at_most_one,
    _handle_matches_email_local_part,
    _local_part_token,
    _matches_initial_plus_surname_suffix,
    _name_token,
    _cross_actor_full_display_name_tokens,
    _significant_handle_overlap,
    _significant_handles_edit_distance_one,
    _surname_suffixes_from_email_local,
    _weak_cross_actor_merge_allowed,
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


def test_handle_matches_email_local_part_requires_long_local_part() -> None:
    assert not _handle_matches_email_local_part({"camilleortholand"}, "camille")


def test_significant_handle_overlap_ignores_short_shared_handles() -> None:
    assert not _significant_handle_overlap({"julien", "julienmaitre"}, {"julien", "juliendurieux"})
    assert not _significant_handle_overlap({"julienmaire"}, {"julienpeyruchat"})
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


def test_cross_actor_full_display_name_tokens_reject_bare_first_names() -> None:
    assert _cross_actor_full_display_name_tokens("julien") == set()
    assert _cross_actor_full_display_name_tokens("camille") == set()
    assert "julienpeyruchat" in _cross_actor_full_display_name_tokens("Julien Peyruchat")
    assert "camilleortholand" in _cross_actor_full_display_name_tokens("Camille Ortholand")
    assert "camillechambefort" in _cross_actor_full_display_name_tokens("camille chambefort")
    assert "chambefort" not in _cross_actor_full_display_name_tokens("camille chambefort")


def test_bare_first_name_tokens_do_not_cross_match() -> None:
    left = _cross_actor_full_display_name_tokens("julien")
    right = _cross_actor_full_display_name_tokens("Julien Peyruchat")
    assert not left.intersection(right)


def test_slack_without_email_can_still_match_on_long_shared_handle() -> None:
    uid = uuid.uuid4()
    notion = ActorSignal(
        canon_entity_id=uid,
        connector="notion",
        connection_id=uid,
        entity_key="n",
        primary_handle="julienpeyruchat",
    )
    notion.emails.add("julien@fizzer.com")
    notion.handles = {"julienpeyruchat"}
    slack = ActorSignal(
        canon_entity_id=uid,
        connector="slack",
        connection_id=uid,
        entity_key="s",
        primary_handle="julienpeyruchat",
    )
    slack.handles = {"julien", "julienpeyruchat"}
    assert not _actor_has_tenant_email(slack, "fizzer.com")
    assert not _weak_cross_actor_merge_allowed(slack, "fizzer.com")
    assert _significant_handle_overlap(
        _cross_actor_match_handles(notion),
        _cross_actor_match_handles(slack),
    )


def test_chambefort_does_not_match_ortholand_display_names() -> None:
    orth = _cross_actor_full_display_name_tokens("Camille Ortholand")
    cham = _cross_actor_full_display_name_tokens("camille chambefort") | _cross_actor_full_display_name_tokens(
        "chambefort.camille",
    )
    assert not orth.intersection(cham)


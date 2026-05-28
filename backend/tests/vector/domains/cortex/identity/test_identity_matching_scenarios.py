"""Integration scenarios for identity resolver tiers (prod-shaped Fizzer cases).

Matching tiers (see ``materialize._seed_identity_for_actor``):
  T1 exact_email — same normalized primary email
  T2 local_part_tenant_domain — same local-part on tenant domain
  T3 handle_to_email_local_part — long handle equals email local-part (incoming needs tenant email)
  T3 exact_normalized_handle — shared provider login handle (>=12 chars); Slack email not required
  T3 initial_plus_surname_suffix — e.g. cecile + veneziani (incoming needs tenant email)
  T3 handle_edit_distance_one — fuzzy long handles (incoming needs tenant email)
  T4 exact_normalized_display_name — full collapsed display name (>=11 chars); Slack email not required
  seed — new identity when no match; resolver_split when revoking weak links
"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.resolver_version import IDENTITY_RESOLVER_VERSION
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from tests.vector.domains.cortex.identity.matching_fixtures import (
    NotionActorSpec,
    SlackActorSpec,
    assert_same_identity,
    assert_separate_identities,
    canon_labels_for_identity,
    identity_id_for_email,
    run_full_identity_pass,
    seed_fizzer_actors,
)

pytestmark = pytest.mark.integration


def test_obvious_notion_slack_merge_julien_peyruchat(db_session: Session) -> None:
    """Screenshot regression: Notion email + Slack login without profile email."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(
            NotionActorSpec(
                external_id="notion-jp",
                name="Julien Peyruchat",
                email="julien@fizzer.com",
            ),
        ),
        slack=(
            SlackActorSpec(
                external_id="U-PEYRUCHAT",
                login="julien.peyruchat",
                real_name="Julien Peyruchat",
            ),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    identity_id = assert_same_identity(db_session, tenant_id=tenant_id, label_substrings=("Peyruchat", "julien.peyruchat"))
    labels = canon_labels_for_identity(db_session, tenant_id=tenant_id, identity_id=identity_id)
    assert len(labels) == 2

    assert identity_id_for_email(db_session, tenant_id=tenant_id, email="julien@fizzer.com") == identity_id

    accounts = list(
        db_session.scalars(
            select(IdentityAccount).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    rules = {a.link_rule for a in accounts}
    assert "exact_normalized_handle" in rules
    assert rules <= {"seed_actor", "exact_email", "exact_normalized_handle", "handle_to_email_local_part"}


def test_hugo_bonnome_notion_slack_merge_without_profile_email(db_session: Session) -> None:
    """Prod: hugo@fizzer.com on Notion + Slack login hugo with hugobonnome / hugo bonnome aliases."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-hugo", "Hugo Bonnome", "hugo@fizzer.com"),),
        slack=(
            SlackActorSpec(
                external_id="U-HUGO",
                login="hugo",
                real_name="hugo bonnome",
                display_name="hugo deladata",
            ),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    identity_id = assert_same_identity(
        db_session,
        tenant_id=tenant_id,
        label_substrings=("Bonnome", "hugo"),
    )
    assert identity_id_for_email(db_session, tenant_id=tenant_id, email="hugo@fizzer.com") == identity_id
    assert len(canon_labels_for_identity(db_session, tenant_id=tenant_id, identity_id=identity_id)) == 2

    slack_account = db_session.scalar(
        select(IdentityAccount).where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.identity_entity_id == identity_id,
            IdentityAccount.connector == "slack",
        ),
    )
    assert slack_account is not None
    assert slack_account.link_rule in {
        "exact_normalized_handle",
        "exact_normalized_display_name",
        "handle_edit_distance_one",
    }


def test_obvious_notion_slack_merge_camille_ortholand(db_session: Session) -> None:
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-co", "Camille Ortholand", "camille@fizzer.com"),),
        slack=(
            SlackActorSpec(
                external_id="U-CO-SLACK",
                login="camille.ortholand",
                real_name="Camille Ortholand",
            ),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    identity_id = assert_same_identity(db_session, tenant_id=tenant_id, label_substrings=("Ortholand", "camille.ortholand"))
    assert len(canon_labels_for_identity(db_session, tenant_id=tenant_id, identity_id=identity_id)) == 2


def test_three_distinct_juliens_do_not_merge(db_session: Session) -> None:
    """Screenshot: Julien Peyruchat must not absorb julien.maire / julien.durieux."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-jp", "Julien Peyruchat", "julien@fizzer.com"),),
        slack=(
            SlackActorSpec("U-MAIRE", "julien.maire", "Julien Maire", profile_email=None),
            SlackActorSpec("U-DURIEUX", "julien.durieux", "Julien Durieux"),
            SlackActorSpec("U-PEYRUCHAT", "julien", "Julien Peyruchat"),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    peyruchat_id = identity_id_for_email(db_session, tenant_id=tenant_id, email="julien@fizzer.com")
    assert peyruchat_id is not None
    assert_separate_identities(db_session, tenant_id=tenant_id, left_label="maire", right_label="Peyruchat")
    assert_separate_identities(db_session, tenant_id=tenant_id, left_label="durieux", right_label="Peyruchat")

    identity_count = int(
        db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
        or 0,
    )
    assert identity_count >= 3


def test_camille_ortholand_not_merged_with_chambefort(db_session: Session) -> None:
    """Screenshot: chambefort.camille is a different person from Camille Ortholand."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-co", "Camille Ortholand", "camille@fizzer.com"),),
        slack=(
            SlackActorSpec("U-CHAMBEFORT", "chambefort.camille", "camille chambefort"),
            SlackActorSpec("U-BIGCHEESE", "camille", "camille bigcheese"),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    ortholand_id = identity_id_for_email(db_session, tenant_id=tenant_id, email="camille@fizzer.com")
    assert ortholand_id is not None
    assert_separate_identities(db_session, tenant_id=tenant_id, left_label="chambefort", right_label="Ortholand")

    identity_count = int(
        db_session.scalar(select(func.count()).select_from(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
        or 0,
    )
    assert identity_count >= 3


def test_shirley_two_slack_accounts_same_person(db_session: Session) -> None:
    """Screenshot: two Slack user IDs with same strong handle → one persona is expected."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-st", "Shirley Thiriat", "shirley@fizzer.com"),),
        slack=(
            SlackActorSpec("UF6H0LL0P", "shirley", "Shirley Thiriat"),
            SlackActorSpec("UEFFATL5C", "shirley.thiriat", "shirley"),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    identity_id = assert_same_identity(
        db_session,
        tenant_id=tenant_id,
        label_substrings=("Thiriat", "shirley.thiriat"),
    )
    labels = canon_labels_for_identity(db_session, tenant_id=tenant_id, identity_id=identity_id)
    assert len(labels) == 3
    assert sum(1 for label in labels if "slack" in label.lower() or label.lower() in {"shirley", "shirley.thiriat"}) >= 2


def test_slack_with_tenant_email_can_use_handle_to_email_rule(db_session: Session) -> None:
    """When Slack exposes tenant email, long local-part handle can link (T3 handle_to_email)."""
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-t", "Thibault Hagler", "thibault@fizzer.com"),),
        slack=(
            SlackActorSpec(
                external_id="U-TIBO",
                login="thibaulthagler",
                real_name="Thibault Hagler",
                profile_email="thibault@fizzer.com",
            ),
        ),
    )
    run_full_identity_pass(db_session, tenant_id)

    identity_id = assert_same_identity(db_session, tenant_id=tenant_id, label_substrings=("Hagler", "thibaulthagler"))
    account = db_session.scalar(
        select(IdentityAccount).where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.identity_entity_id == identity_id,
            IdentityAccount.connector == "slack",
        ),
    )
    assert account is not None
    assert account.link_rule in {"exact_normalized_handle", "handle_to_email_local_part", "exact_email"}


def test_entities_run_at_current_resolver_version(db_session: Session) -> None:
    tenant_id = seed_fizzer_actors(
        db_session,
        notion=(NotionActorSpec("notion-v", "Version Check", "version@fizzer.com"),),
    )
    run_full_identity_pass(db_session, tenant_id)
    version = db_session.scalar(
        select(IdentityEntity.resolver_version).where(IdentityEntity.tenant_id == tenant_id).limit(1),
    )
    assert int(version or 0) >= IDENTITY_RESOLVER_VERSION

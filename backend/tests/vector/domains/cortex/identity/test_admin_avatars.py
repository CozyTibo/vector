from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.domains.cortex.identity.admin import pick_identity_avatar_url
from vector.infrastructure.db.models.identity_account import IdentityAccount


def test_pick_identity_avatar_url_prefers_slack_over_github(db_session: Session) -> None:
    tenant_id = uuid.uuid4()
    accounts = [
        IdentityAccount(
            tenant_id=tenant_id,
            identity_entity_id=uuid.uuid4(),
            canon_entity_id=uuid.uuid4(),
            connector="github",
            connection_id=uuid.uuid4(),
            link_tier="T3",
            link_rule="exact_normalized_handle",
            confidence="medium",
            evidence_json={"avatar_url": "https://avatars.githubusercontent.com/u/1"},
        ),
        IdentityAccount(
            tenant_id=tenant_id,
            identity_entity_id=uuid.uuid4(),
            canon_entity_id=uuid.uuid4(),
            connector="slack",
            connection_id=uuid.uuid4(),
            link_tier="T3",
            link_rule="exact_normalized_handle",
            confidence="medium",
            evidence_json={"avatar_url": "https://ca.slack-edge.com/avatar.png"},
        ),
    ]
    url = pick_identity_avatar_url(db_session, tenant_id=tenant_id, accounts=accounts)
    assert url == "https://ca.slack-edge.com/avatar.png"


def test_pick_identity_avatar_url_github_when_no_slack(db_session: Session) -> None:
    tenant_id = uuid.uuid4()
    accounts = [
        IdentityAccount(
            tenant_id=tenant_id,
            identity_entity_id=uuid.uuid4(),
            canon_entity_id=uuid.uuid4(),
            connector="github",
            connection_id=uuid.uuid4(),
            link_tier="T3",
            link_rule="seed_actor",
            confidence="low",
            evidence_json={"avatar_url": "https://avatars.githubusercontent.com/u/99"},
        ),
    ]
    url = pick_identity_avatar_url(db_session, tenant_id=tenant_id, accounts=accounts)
    assert url == "https://avatars.githubusercontent.com/u/99"

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.canonical.constants import RELATION_CONTAINS
from vector.domains.canonical.github_mapper import handle_github_canonical_row
from vector.domains.projections.github.resource_types import RT_PULL_REQUEST, RT_PULL_REQUEST_COMMIT
from vector.infrastructure.db.models.canonical import Relationship
from vector.infrastructure.db.models.github_projection import GithubPullRequest, GithubRepository
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, SOURCE_TRIGGER_POLL


def test_pr_contains_commit_edge(db_session: Session) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    suffix = uuid.uuid4().hex[:8]
    now = datetime.now(tz=UTC)
    repo_github_id = 8_888_888
    full_name = f"testorg/testpr-{suffix}".lower()
    pr_num = 7
    sha = "abcdef1234567890abcdef1234567890abcdef12"

    db_session.add(
        Tenant(
            id=tenant_id,
            company_name=f"T {suffix}",
            primary_email=f"o-{suffix}@example.com",
            email_domain="example.com",
            slug=f"t-{suffix}",
            status="active",
            workspace_access_enabled=True,
        ),
    )
    db_session.add(
        User(
            id=user_id,
            email=f"u-{suffix}@example.com",
            full_name="U",
            password_hash=None,
        ),
    )
    db_session.add(
        TenantConnection(
            id=connection_id,
            tenant_id=tenant_id,
            provider=CONNECTOR_GITHUB,
            status="active",
            connected_by_user_id=user_id,
            display_name="GitHub",
        ),
    )
    db_session.flush()
    db_session.add(
        GithubRepository(
            tenant_id=tenant_id,
            connection_id=connection_id,
            repository_github_id=repo_github_id,
            full_name=full_name,
            name=full_name.split("/", 1)[1],
            owner_login=full_name.split("/", 1)[0],
            last_raw_record_id=1,
            last_observed_at=now,
            last_replay_sequence=1,
        ),
    )
    db_session.add(
        GithubPullRequest(
            tenant_id=tenant_id,
            connection_id=connection_id,
            repository_github_id=repo_github_id,
            pr_number=pr_num,
            repo_full_name=full_name,
            title="Demo PR",
            state="open",
            head_sha=sha[:40],
            last_raw_record_id=1,
            last_observed_at=now,
            last_replay_sequence=1,
        ),
    )
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
        source_trigger=SOURCE_TRIGGER_POLL,
        status="succeeded",
        stats={},
    )
    db_session.add(run)
    db_session.flush()

    pr_payload = {
        "number": pr_num,
        "title": "Demo PR",
        "state": "open",
        "base": {"repo": {"id": repo_github_id, "full_name": full_name}},
        "head": {"sha": sha},
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }
    raw_pr = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
        resource_type=RT_PULL_REQUEST,
        external_id=f"{full_name}#{pr_num}",
        api_endpoint="GET /pulls",
        query_params={},
        payload_body=pr_payload,
        payload_hash=uuid.uuid4().hex,
        http_status=200,
        fetched_at=now,
        run_id=run.id,
        source_trigger=SOURCE_TRIGGER_POLL,
        idempotency_key=f"pr-{suffix}",
    )
    raw_link = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
        resource_type=RT_PULL_REQUEST_COMMIT,
        external_id=f"{full_name}#{pr_num}@{sha}",
        api_endpoint="GET /pulls/commits",
        query_params={},
        payload_body={"sha": sha},
        payload_hash=uuid.uuid4().hex,
        http_status=200,
        fetched_at=now,
        run_id=run.id,
        source_trigger=SOURCE_TRIGGER_POLL,
        idempotency_key=f"prc-{suffix}",
    )
    db_session.add(raw_pr)
    db_session.add(raw_link)
    db_session.flush()

    handle_github_canonical_row(db_session, raw_pr)
    handle_github_canonical_row(db_session, raw_link)
    db_session.flush()

    contains = db_session.scalars(
        select(Relationship).where(
            Relationship.tenant_id == tenant_id,
            Relationship.relation_kind_id == RELATION_CONTAINS,
            Relationship.subject_type == "artifact",
            Relationship.object_type == "artifact",
            Relationship.valid_to.is_(None),
        ),
    ).all()
    assert len(contains) == 1

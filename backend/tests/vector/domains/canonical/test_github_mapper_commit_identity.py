from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.canonical.github_mapper import handle_github_canonical_row
from vector.domains.projections.github.resource_types import RT_COMMIT
from vector.infrastructure.db.models.canonical import Actor, ActorExternalIdentity, Relationship
from vector.infrastructure.db.models.github_projection import GithubCommit, GithubRepository
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_GITHUB, SOURCE_TRIGGER_POLL


def _seed_github_scaffold(db: Session) -> tuple[uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    connection_id = uuid.uuid4()
    suffix = uuid.uuid4().hex[:8]

    db.add(
        Tenant(
            id=tenant_id,
            company_name=f"Vector {suffix}",
            primary_email=f"owner-{suffix}@example.com",
            email_domain="example.com",
            slug=f"vector-{suffix}",
            status="active",
            workspace_access_enabled=True,
        ),
    )
    db.add(
        User(
            id=user_id,
            email=f"user-{suffix}@example.com",
            full_name="Owner",
            password_hash=None,
        ),
    )
    db.add(
        TenantConnection(
            id=connection_id,
            tenant_id=tenant_id,
            provider=CONNECTOR_GITHUB,
            status="active",
            connected_by_user_id=user_id,
            display_name="GitHub",
        ),
    )
    db.flush()
    return tenant_id, connection_id


def _insert_commit_observation(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    repo_github_id: int,
    repo_full_name: str,
    sha: str,
    observed_at: datetime,
    run_id: uuid.UUID,
    ensure_repo: bool,
) -> RawIngestionRecord:
    if ensure_repo:
        db.add(
            GithubRepository(
                tenant_id=tenant_id,
                connection_id=connection_id,
                repository_github_id=repo_github_id,
                full_name=repo_full_name,
                name=repo_full_name.split("/", 1)[1],
                owner_login=repo_full_name.split("/", 1)[0],
                last_raw_record_id=1,
                last_observed_at=observed_at,
                last_replay_sequence=1,
            ),
        )
    db.add(
        GithubCommit(
            tenant_id=tenant_id,
            connection_id=connection_id,
            repository_github_id=repo_github_id,
            commit_sha=sha,
            repo_full_name=repo_full_name,
            message=f"Message {sha[:7]}",
            author_name="Thibault Hagler",
            author_email="thibault.hagler@payflows.io",
            author_github_id=None,
            committer_name="Thibault Hagler",
            committer_email="thibault.hagler@payflows.io",
            committer_github_id=None,
            last_raw_record_id=1,
            last_observed_at=observed_at,
            last_replay_sequence=1,
        ),
    )
    raw = RawIngestionRecord(
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
        resource_type=RT_COMMIT,
        external_id=f"{repo_full_name}@{sha}",
        api_endpoint="GET /repos/{owner}/{repo}/commits",
        query_params={"sha": "main"},
        payload_body={"sha": sha, "repository": {"id": repo_github_id}},
        payload_hash=uuid.uuid4().hex,
        http_status=200,
        fetched_at=observed_at,
        run_id=run_id,
        source_trigger=SOURCE_TRIGGER_POLL,
        idempotency_key=f"raw-{sha}",
    )
    db.add(raw)
    db.flush()
    return raw


def test_commit_without_github_user_creates_synthetic_author_actor(db_session: Session) -> None:
    tenant_id, connection_id = _seed_github_scaffold(db_session)
    now = datetime.now(tz=UTC)
    run = IngestionRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        connection_id=connection_id,
        connector=CONNECTOR_GITHUB,
        source_trigger=SOURCE_TRIGGER_POLL,
        status="succeeded",
        stats={"records_written": 2},
    )
    db_session.add(run)
    db_session.flush()

    raw1 = _insert_commit_observation(
        db_session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        repo_github_id=1190499289,
        repo_full_name="cozytibo/vector",
        sha="f8a3fa197781764b1caacba2bdba4a5338829bbb",
        observed_at=now,
        run_id=run.id,
        ensure_repo=True,
    )
    raw2 = _insert_commit_observation(
        db_session,
        tenant_id=tenant_id,
        connection_id=connection_id,
        repo_github_id=1190499289,
        repo_full_name="cozytibo/vector",
        sha="15e24166653c1fca82bc5a7165c805429b09e8b3",
        observed_at=now,
        run_id=run.id,
        ensure_repo=False,
    )

    handle_github_canonical_row(db_session, raw1)
    handle_github_canonical_row(db_session, raw2)
    db_session.flush()

    synthetic_external_id = "commit_author:thibault.hagler@payflows.io"
    aei_rows = db_session.scalars(
        select(ActorExternalIdentity).where(
            ActorExternalIdentity.tenant_id == tenant_id,
            ActorExternalIdentity.connector == CONNECTOR_GITHUB,
            ActorExternalIdentity.external_id == synthetic_external_id,
        ),
    ).all()
    assert len(aei_rows) == 1

    actor_id = aei_rows[0].actor_id
    actor = db_session.get(Actor, actor_id)
    assert actor is not None
    assert actor.kind == "person"
    assert actor.display_name == "Thibault Hagler"

    authored_links = db_session.scalars(
        select(Relationship).where(
            Relationship.tenant_id == tenant_id,
            Relationship.subject_type == "actor",
            Relationship.subject_id == actor_id,
            Relationship.object_type == "artifact",
            Relationship.relation_kind_id == 1,  # authored_by
            Relationship.valid_to.is_(None),
        ),
    ).all()
    assert len(authored_links) == 2

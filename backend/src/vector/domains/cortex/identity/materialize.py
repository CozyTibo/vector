"""Identity resolution pass runtime (v1)."""

from __future__ import annotations

import uuid
import unicodedata
from typing import Any

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.resolver_version import effective_identity_resolver_version
from vector.domains.cortex.identity.signals import ActorSignal, extract_actor_signal, normalize_email
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_entity import CanonEntity
from vector.infrastructure.db.models.canon_entity_source import CanonEntitySource
from vector.infrastructure.db.models.identity_account import IdentityAccount
from vector.infrastructure.db.models.identity_dirty_queue import IdentityDirtyQueue
from vector.infrastructure.db.models.identity_entity import IdentityEntity
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_suggestion import IdentitySuggestion
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"
BOT_MARKERS = ("[bot]", "-bot", "dependabot", "githubactions", "github-actions", "slackbot")


def same_local_part_with_tenant_domain(
    *,
    left_email: str,
    right_email: str,
    tenant_domain: str | None,
) -> bool:
    domain = (tenant_domain or "").strip().lower()
    if not domain:
        return False
    l = normalize_email(left_email)
    r = normalize_email(right_email)
    if not l or not r:
        return False
    if not l.endswith(f"@{domain}") or not r.endswith(f"@{domain}"):
        return False
    return l.split("@", 1)[0] == r.split("@", 1)[0]


def _local_part_token(email: str) -> str | None:
    norm = normalize_email(email)
    if not norm or "@" not in norm:
        return None
    local = norm.split("@", 1)[0]
    token = "".join(ch for ch in local if ch.isalnum())
    return token or None


def _name_token(raw: str) -> str | None:
    folded = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(ch for ch in folded if ord(ch) < 128)
    token = "".join(ch for ch in ascii_only.lower() if ch.isalnum())
    return token or None


def classify_identity_kind(
    *,
    connector: str,
    handles: set[str],
    display_names: set[str],
    emails: set[str],
    signal_is_bot: bool | None,
    signal_is_inactive: bool | None = None,
) -> tuple[str, str]:
    if signal_is_bot is True:
        return ("bot", "provider_bot_flag")
    has_profile = bool(emails or display_names or handles)
    if signal_is_inactive is True and has_profile:
        return ("inactive_human", "provider_inactive_actor")
    if connector in {"slack", "github", "linear", "notion"}:
        # Provider actor feeds are person-first unless explicit bot flags are present.
        if has_profile:
            merged = " ".join(sorted(handles.union(display_names)))
            if any(m in merged for m in BOT_MARKERS):
                return ("bot", "name_or_handle_bot_marker")
            return ("human", "provider_actor_feed_default")
    merged = " ".join(sorted(handles.union(display_names)))
    if any(m in merged for m in BOT_MARKERS):
        return ("bot", "name_or_handle_bot_marker")
    for email in emails:
        if email.endswith("@users.noreply.github.com"):
            if any("bot" in h for h in handles):
                return ("bot", "github_noreply_bot_pattern")
    if emails or display_names:
        return ("human", "has_human_profile_signals")
    if signal_is_inactive is True:
        return ("inactive_human", "inactive_without_profile")
    return ("unknown", "insufficient_signals")


def _classify_actor_signal(signal: ActorSignal, *, connector: str) -> tuple[str, str]:
    return classify_identity_kind(
        connector=connector,
        handles=signal.handles,
        display_names=signal.display_names,
        emails=signal.emails,
        signal_is_bot=signal.is_bot,
        signal_is_inactive=signal.is_inactive,
    )


def _recompute_identity_kind(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> None:
    """Aggregate kind across all linked accounts (bot > human > inactive_human > unknown)."""
    identity = session.get(IdentityEntity, identity_id)
    if identity is None or identity.tenant_id != tenant_id or identity.status != "active":
        return
    account_rows = list(
        session.scalars(
            select(IdentityAccount.canon_entity_id).where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).all(),
    )
    kinds: list[str] = []
    for canon_entity_id in account_rows:
        row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=canon_entity_id)
        if row is None:
            continue
        canon_entity, source, raw = row
        payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
        signal = extract_actor_signal(
            canon_entity_id=canon_entity.id,
            connector=canon_entity.connector,
            connection_id=canon_entity.connection_id,
            entity_key=canon_entity.entity_key,
            external_id=source.external_id,
            source_revision_key=source.source_revision_key,
            payload_body=payload,
        )
        kind, _ = _classify_actor_signal(signal, connector=canon_entity.connector)
        kinds.append(kind)
    if not kinds:
        return
    if "bot" in kinds:
        identity.kind = "bot"
    elif "human" in kinds:
        identity.kind = "human"
    elif "inactive_human" in kinds:
        identity.kind = "inactive_human"
    else:
        identity.kind = "unknown"


def enqueue_identity_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str,
) -> None:
    existing = session.scalar(
        select(IdentityDirtyQueue.id)
        .where(
            IdentityDirtyQueue.tenant_id == tenant_id,
            IdentityDirtyQueue.canon_entity_id == canon_entity_id,
            IdentityDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        return
    session.add(
        IdentityDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=canon_entity_id,
            reason=reason[:32],
        ),
    )


def enqueue_all_actor_entities(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str,
    limit: int = 50000,
) -> int:
    ids = list(
        session.scalars(
            select(CanonEntity.id)
            .where(CanonEntity.tenant_id == tenant_id, CanonEntity.entity_type == "actor")
            .order_by(CanonEntity.materialized_at.desc())
            .limit(max(1, min(limit, 200000))),
        ).all(),
    )
    for eid in ids:
        enqueue_identity_actor(session, tenant_id=tenant_id, canon_entity_id=eid, reason=reason)
    return len(ids)


def _latest_actor_payload(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
) -> tuple[CanonEntity, CanonEntitySource, RawIngestionRecord] | None:
    row = session.execute(
        select(CanonEntity, CanonEntitySource, RawIngestionRecord)
        .join(CanonEntitySource, CanonEntitySource.canon_entity_id == CanonEntity.id)
        .join(RawIngestionRecord, RawIngestionRecord.id == CanonEntitySource.raw_id)
        .where(
            CanonEntity.tenant_id == tenant_id,
            CanonEntity.id == canon_entity_id,
            CanonEntity.entity_type == "actor",
            CanonEntitySource.is_latest.is_(True),
        )
        .limit(1),
    ).first()
    if row is None:
        return None
    return row


def _seed_identity_for_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity: CanonEntity,
    source: CanonEntitySource,
    raw: RawIngestionRecord,
    resolver_version: int | None = None,
) -> dict[str, Any]:
    existing_row = session.execute(
        select(IdentityAccount, IdentityEntity)
        .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
        .where(
            IdentityAccount.tenant_id == tenant_id,
            IdentityAccount.canon_entity_id == canon_entity.id,
            IdentityAccount.unlinked_at.is_(None),
            IdentityEntity.status == "active",
        )
        .limit(1),
    ).first()

    payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
    signal = extract_actor_signal(
        canon_entity_id=canon_entity.id,
        connector=canon_entity.connector,
        connection_id=canon_entity.connection_id,
        entity_key=canon_entity.entity_key,
        external_id=source.external_id,
        source_revision_key=source.source_revision_key,
        payload_body=payload,
    )
    tenant = session.get(Tenant, tenant_id)
    tenant_domain = tenant.email_domain if tenant is not None else None
    resolved_version = effective_identity_resolver_version(resolver_version)
    existing_account: IdentityAccount | None = None
    existing_identity: IdentityEntity | None = None
    if existing_row is not None:
        existing_account, existing_identity = existing_row
        if (
            existing_identity.resolver_version >= resolved_version
            and existing_account.link_rule != "seed_actor"
        ):
            return {"outcome": "already_linked", "identity_entity_id": str(existing_account.identity_entity_id)}
    emails_sorted = sorted(signal.emails)
    chosen_email = emails_sorted[0] if emails_sorted else None
    kind, kind_reason = _classify_actor_signal(signal, connector=canon_entity.connector)
    link_tier = "seed"
    link_rule = "seed_actor"
    confidence = "low"

    matched_identity: IdentityEntity | None = None
    if chosen_email:
        exact_ids = list(
            session.scalars(
                select(IdentityEntity)
                .where(
                    IdentityEntity.tenant_id == tenant_id,
                    IdentityEntity.status == "active",
                    IdentityEntity.primary_email == chosen_email,
                )
                .order_by(IdentityEntity.resolved_at.asc(), IdentityEntity.id.asc()),
            ).all(),
        )
        if len(exact_ids) == 1:
            matched_identity = exact_ids[0]
            link_tier = "T1"
            link_rule = "exact_email"
            confidence = "certain"
        elif len(exact_ids) == 0 and tenant_domain:
            local_match = list(
                session.scalars(
                    select(IdentityEntity)
                    .where(
                        IdentityEntity.tenant_id == tenant_id,
                        IdentityEntity.status == "active",
                        IdentityEntity.primary_email.is_not(None),
                    ),
                ).all(),
            )
            cands = [
                i
                for i in local_match
                if i.primary_email
                and same_local_part_with_tenant_domain(
                    left_email=chosen_email,
                    right_email=i.primary_email,
                    tenant_domain=tenant_domain,
                )
            ]
            cands.sort(key=lambda i: (i.resolved_at, i.id))
            if len(cands) == 1:
                matched_identity = cands[0]
                link_tier = "T2"
                link_rule = "local_part_tenant_domain"
                confidence = "high"
    if matched_identity is None and signal.handles and tenant_domain:
        handle_to_email_matches: set[uuid.UUID] = set()
        existing = list(
            session.scalars(
                select(IdentityEntity)
                .where(
                    IdentityEntity.tenant_id == tenant_id,
                    IdentityEntity.status == "active",
                    IdentityEntity.primary_email.is_not(None),
                )
                .order_by(IdentityEntity.resolved_at.asc(), IdentityEntity.id.asc()),
            ).all(),
        )
        handle_tokens = {h for h in signal.handles if h}
        for identity in existing:
            if not identity.primary_email:
                continue
            if not identity.primary_email.endswith(f"@{tenant_domain}"):
                continue
            local_tok = _local_part_token(identity.primary_email)
            if local_tok and local_tok in handle_tokens:
                handle_to_email_matches.add(identity.id)
        if len(handle_to_email_matches) == 1:
            target_id = next(iter(handle_to_email_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = "handle_to_email_local_part"
                confidence = "medium"
    if matched_identity is None and signal.handles:
        handle_matches: set[uuid.UUID] = set()
        rows = list(
            session.execute(
                select(IdentityAccount, IdentityEntity)
                .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
                .where(
                    IdentityAccount.tenant_id == tenant_id,
                    IdentityAccount.unlinked_at.is_(None),
                    IdentityEntity.status == "active",
                ),
            ).all(),
        )
        for account, identity in rows:
            evidence = account.evidence_json if isinstance(account.evidence_json, dict) else {}
            prev = evidence.get("handles")
            prev_handles = {str(v).strip().lower() for v in prev} if isinstance(prev, list) else set()
            if prev_handles.intersection(signal.handles):
                handle_matches.add(identity.id)
        if len(handle_matches) == 1:
            target_id = next(iter(handle_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = "exact_normalized_handle"
                confidence = "medium"
    if matched_identity is None and signal.display_names:
        name_matches: set[uuid.UUID] = set()
        incoming_name_tokens = {_name_token(n) for n in signal.display_names}
        incoming_name_tokens.discard(None)
        if incoming_name_tokens:
            rows = list(
                session.execute(
                    select(IdentityAccount, IdentityEntity)
                    .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
                    .where(
                        IdentityAccount.tenant_id == tenant_id,
                        IdentityAccount.unlinked_at.is_(None),
                        IdentityEntity.status == "active",
                    ),
                ).all(),
            )
            for account, identity in rows:
                evidence = account.evidence_json if isinstance(account.evidence_json, dict) else {}
                prev_names = evidence.get("display_names")
                prior_names = {str(v) for v in prev_names} if isinstance(prev_names, list) else set()
                if isinstance(identity.display_name, str) and identity.display_name.strip():
                    prior_names.add(identity.display_name)
                prior_tokens = {_name_token(name) for name in prior_names}
                prior_tokens.discard(None)
                if prior_tokens.intersection(incoming_name_tokens):
                    name_matches.add(identity.id)
            if len(name_matches) == 1:
                target_id = next(iter(name_matches))
                matched_identity = session.get(IdentityEntity, target_id)
                if matched_identity is not None:
                    link_tier = "T4"
                    link_rule = "exact_normalized_display_name"
                    confidence = "medium"

    if matched_identity is None:
        if existing_identity is not None:
            identity = existing_identity
            identity.display_name = canon_entity.display_label[:512]
            if chosen_email is not None:
                identity.primary_email = chosen_email
            if identity.resolver_version < resolved_version:
                identity.resolver_version = resolved_version
            identity.resolved_at = utc_now()
        else:
            identity = IdentityEntity(
                tenant_id=tenant_id,
                kind=kind,
                display_name=canon_entity.display_label[:512],
                primary_email=chosen_email,
                resolver_version=resolved_version,
                status="active",
                resolved_at=utc_now(),
            )
            session.add(identity)
            session.flush()
    else:
        identity = matched_identity
        if identity.primary_email is None and chosen_email is not None:
            identity.primary_email = chosen_email
        if identity.resolver_version < resolved_version:
            identity.resolver_version = resolved_version
            identity.resolved_at = utc_now()
    evidence = {
        "seed": "actor",
        "connector": canon_entity.connector,
        "source_identity_key": source.source_identity_key,
        "emails": emails_sorted,
        "handles": sorted(signal.handles),
        "display_names": sorted(signal.display_names),
        "provider_ids": sorted(signal.provider_ids),
        "bot_reasons": signal.bot_reasons,
        "inactive_reasons": signal.inactive_reasons,
        "tenant_email_domain": tenant_domain,
        "match_tier": link_tier,
        "match_rule": link_rule,
        "kind": kind,
        "kind_reason": kind_reason,
    }
    if existing_account is not None:
        existing_account.identity_entity_id = identity.id
        existing_account.connector = canon_entity.connector
        existing_account.connection_id = canon_entity.connection_id
        existing_account.link_tier = link_tier
        existing_account.link_rule = link_rule
        existing_account.confidence = confidence
        existing_account.evidence_json = evidence
        existing_account.linked_at = utc_now()
        existing_account.unlinked_at = None
        _recompute_identity_kind(session, tenant_id=tenant_id, identity_id=identity.id)
        return {"outcome": "rematched", "identity_entity_id": str(identity.id)}

    account = IdentityAccount(
        tenant_id=tenant_id,
        identity_entity_id=identity.id,
        canon_entity_id=canon_entity.id,
        connector=canon_entity.connector,
        connection_id=canon_entity.connection_id,
        link_tier=link_tier,
        link_rule=link_rule,
        confidence=confidence,
        evidence_json=evidence,
        linked_at=utc_now(),
    )
    session.add(account)
    _recompute_identity_kind(session, tenant_id=tenant_id, identity_id=identity.id)
    return {"outcome": "seeded", "identity_entity_id": str(identity.id)}


def enqueue_periodic_identity_candidates(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    resolver_version: int | None = None,
) -> int:
    """Queue unresolved actors and resolver-bump candidates when dirty queue is empty."""
    limit = max(1, min(limit, 5000))
    queued = 0
    unresolved_actor_ids = list(
        session.scalars(
            select(CanonEntity.id)
            .where(
                CanonEntity.tenant_id == tenant_id,
                CanonEntity.entity_type == "actor",
                ~exists(
                    select(IdentityAccount.id).where(
                        IdentityAccount.tenant_id == tenant_id,
                        IdentityAccount.canon_entity_id == CanonEntity.id,
                        IdentityAccount.unlinked_at.is_(None),
                    ),
                ),
            )
            .order_by(CanonEntity.materialized_at.desc())
            .limit(limit),
        ).all(),
    )
    for eid in unresolved_actor_ids:
        enqueue_identity_actor(
            session,
            tenant_id=tenant_id,
            canon_entity_id=eid,
            reason="periodic_rescan",
        )
        queued += 1
    if queued >= limit:
        return queued

    resolved_version = effective_identity_resolver_version(resolver_version)
    stale_actor_ids = list(
        session.scalars(
            select(IdentityAccount.canon_entity_id)
            .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.unlinked_at.is_(None),
                IdentityEntity.status == "active",
                IdentityEntity.resolver_version < resolved_version,
            )
            .order_by(IdentityEntity.resolved_at.asc())
            .limit(limit - queued),
        ).all(),
    )
    for eid in stale_actor_ids:
        enqueue_identity_actor(
            session,
            tenant_id=tenant_id,
            canon_entity_id=eid,
            reason="resolver_bump",
        )
        queued += 1
    if queued >= limit:
        return queued

    seed_actor_ids = list(
        session.scalars(
            select(IdentityAccount.canon_entity_id)
            .join(IdentityEntity, IdentityEntity.id == IdentityAccount.identity_entity_id)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.unlinked_at.is_(None),
                IdentityAccount.link_rule == "seed_actor",
                IdentityEntity.status == "active",
            )
            .order_by(IdentityEntity.resolved_at.asc())
            .limit(limit - queued),
        ).all(),
    )
    for eid in seed_actor_ids:
        enqueue_identity_actor(
            session,
            tenant_id=tenant_id,
            canon_entity_id=eid,
            reason="seed_rematch",
        )
        queued += 1
    return queued


def execute_identity_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
    max_attempts: int = 5,
    periodic_rescan_limit: int = 200,
    resolver_version: int | None = None,
) -> dict[str, Any]:
    run = IdentityPassRun(
        tenant_id=tenant_id,
        source_trigger=source_trigger,
        status=RUN_RUNNING,
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()
    stats: dict[str, int] = {
        "processed": 0,
        "seeded": 0,
        "already_linked": 0,
        "missing_actor": 0,
        "errors": 0,
    }
    try:
        items = list(
            session.scalars(
                select(IdentityDirtyQueue)
                .where(
                    IdentityDirtyQueue.tenant_id == tenant_id,
                    IdentityDirtyQueue.processed_at.is_(None),
                    IdentityDirtyQueue.attempts < max(1, min(max_attempts, 100)),
                )
                .order_by(IdentityDirtyQueue.enqueued_at.asc())
                .limit(max(1, min(batch_limit, 5000))),
            ).all(),
        )
        if not items:
            if enqueue_periodic_identity_candidates(
                session,
                tenant_id=tenant_id,
                limit=max(1, min(periodic_rescan_limit, 5000)),
                resolver_version=resolver_version,
            ) > 0:
                session.flush()
                items = list(
                    session.scalars(
                        select(IdentityDirtyQueue)
                        .where(
                            IdentityDirtyQueue.tenant_id == tenant_id,
                            IdentityDirtyQueue.processed_at.is_(None),
                            IdentityDirtyQueue.attempts < max(1, min(max_attempts, 100)),
                        )
                        .order_by(IdentityDirtyQueue.enqueued_at.asc())
                        .limit(max(1, min(batch_limit, 5000))),
                    ).all(),
                )
        if not items:
            run.status = RUN_COMPLETED
            run.finished_at = utc_now()
            run.stats = stats
            session.flush()
            return {"status": "completed", "run_id": str(run.id), "stats": stats}
        for item in items:
            stats["processed"] += 1
            row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=item.canon_entity_id)
            if row is None:
                stats["missing_actor"] += 1
                item.processed_at = utc_now()
                item.last_error = "actor_missing"
                continue
            canon_entity, source, raw = row
            try:
                out = _seed_identity_for_actor(
                    session,
                    tenant_id=tenant_id,
                    canon_entity=canon_entity,
                    source=source,
                    raw=raw,
                    resolver_version=resolver_version,
                )
                if out["outcome"] == "seeded":
                    stats["seeded"] += 1
                else:
                    stats["already_linked"] += 1
                item.processed_at = utc_now()
                item.last_error = None
            except Exception as exc:
                stats["errors"] += 1
                item.attempts += 1
                item.last_error = str(exc)[:1000]
        run.status = RUN_COMPLETED
        run.finished_at = utc_now()
        run.stats = stats
        session.flush()
        return {"status": "completed", "run_id": str(run.id), "stats": stats}
    except Exception as exc:
        run.status = RUN_FAILED
        run.finished_at = utc_now()
        run.error_summary = str(exc)[:2000]
        run.stats = stats
        session.flush()
        raise


def rebuild_identities_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str = "manual_rebuild",
    batch_limit: int = 1000,
    resolver_version: int | None = None,
) -> dict[str, Any]:
    session.execute(delete(IdentitySuggestion).where(IdentitySuggestion.tenant_id == tenant_id))
    session.execute(delete(IdentityAccount).where(IdentityAccount.tenant_id == tenant_id))
    session.execute(delete(IdentityEntity).where(IdentityEntity.tenant_id == tenant_id))
    session.execute(delete(IdentityDirtyQueue).where(IdentityDirtyQueue.tenant_id == tenant_id))
    enqueued = enqueue_all_actor_entities(session, tenant_id=tenant_id, reason="rebuild")
    total_stats = {"processed": 0, "seeded": 0, "already_linked": 0, "missing_actor": 0, "errors": 0}
    while True:
        out = execute_identity_pass_for_tenant(
            session,
            tenant_id=tenant_id,
            source_trigger=source_trigger,
            batch_limit=batch_limit,
            resolver_version=resolver_version,
        )
        stats = out.get("stats") if isinstance(out.get("stats"), dict) else {}
        for key in total_stats:
            total_stats[key] += int(stats.get(key, 0))
        if int(stats.get("processed", 0)) <= 0:
            if (
                enqueue_periodic_identity_candidates(
                    session,
                    tenant_id=tenant_id,
                    limit=5000,
                    resolver_version=resolver_version,
                )
                <= 0
            ):
                break
    return {"enqueued": enqueued, "stats": total_stats}


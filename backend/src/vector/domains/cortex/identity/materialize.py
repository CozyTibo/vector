"""Identity resolution pass runtime (v1)."""

from __future__ import annotations

import re
import uuid
import unicodedata
from typing import Any

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.resolver_version import effective_identity_resolver_version
from vector.domains.cortex.identity.signals import (
    ActorSignal,
    extract_actor_signal,
    normalize_email,
    normalize_handle,
)
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
# Provider login handles shorter than this are too ambiguous (e.g. shared first names).
MIN_CROSS_ACTOR_HANDLE_LEN = 12
# Alias handles / collapsed multi-word names (e.g. ``hugobonnome``) may link at 11+ chars.
MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN = 11
# Full collapsed display names must be at least this long for T4 (excludes short names).
MIN_CROSS_ACTOR_FULL_NAME_LEN = MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN
# Isolated name fragments (e.g. surname "chambefort") must not link across actors.
MIN_CROSS_ACTOR_NAME_WORD_LEN = MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN
# Email local-part must be at least this long to derive surname suffixes (e.g. cecile + veneziani).
MIN_EMAIL_LOCAL_FOR_SUFFIX = 5
# Short Slack logins may match email local-part when the anchor has no long handles (zakia@).
MIN_EMAIL_LOCAL_SHORT_LOGIN_MAX = MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN
# Prefix login (melissa -> melissapipolo) requires a longer local-part (excludes julien@).
MIN_EMAIL_LOCAL_PREFIX_LOGIN_LEN = 7
MIN_SURNAME_SUFFIX_LEN = 8
# GitHub-style logins like ``cveneziani`` (9) are below general handle length but safe with surname suffix.
MIN_INITIAL_SUFFIX_LOGIN_LEN = 9
# Auto-links that may be invalidated when resolver rules tighten.
REVOCABLE_WEAK_LINK_RULES = frozenset(
    {
        "handle_to_email_local_part",
        "exact_normalized_handle",
        "exact_normalized_display_name",
        "initial_plus_surname_suffix",
        "handle_edit_distance_one",
        "email_local_short_login",
        "email_local_prefix_login",
    },
)


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


def _significant_handle_tokens(handles: set[str]) -> set[str]:
    return {h for h in handles if h and len(h) >= MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN}


def _handle_matches_email_local_part(handle_tokens: set[str], local_tok: str) -> bool:
    """True only when a normalized handle equals the full email local-part token (not a short prefix)."""
    if not local_tok or len(local_tok) < MIN_CROSS_ACTOR_HANDLE_LEN:
        return False
    return local_tok in handle_tokens


def _cross_actor_match_handles(signal: ActorSignal) -> set[str]:
    """Provider login handle only — not every alias in ``handles`` (avoids first-name bleed)."""
    if signal.primary_handle:
        key = normalize_handle(signal.primary_handle)
        if key and len(key) >= MIN_CROSS_ACTOR_HANDLE_LEN:
            return {key}
    return _significant_handle_tokens(signal.handles)


def _significant_handle_overlap(left: set[str], right: set[str]) -> bool:
    left_s = _significant_handle_tokens(left)
    right_s = _significant_handle_tokens(right)
    shared = left_s.intersection(right_s)
    return any(len(token) >= MIN_CROSS_ACTOR_NAME_WORD_LEN for token in shared)


def _edit_distance_at_most_one(a: str, b: str) -> bool:
    if a == b:
        return False
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la > lb:
        a, b = b, a
        la, lb = lb, la
    if la == lb:
        mismatches = sum(1 for i in range(la) if a[i] != b[i])
        return mismatches == 1
    i = j = 0
    skipped = False
    while i < la and j < lb:
        if a[i] == b[j]:
            i += 1
            j += 1
        elif not skipped:
            skipped = True
            j += 1
        else:
            return False
    return True


def _significant_handles_edit_distance_one(left: set[str], right: set[str]) -> bool:
    left_s = _significant_handle_tokens(left)
    right_s = _significant_handle_tokens(right)
    for a in left_s:
        for b in right_s:
            if _edit_distance_at_most_one(a, b):
                return True
    return False


def _surname_suffixes_from_email_local(local_tok: str, handles: set[str]) -> set[str]:
    if len(local_tok) < MIN_EMAIL_LOCAL_FOR_SUFFIX:
        return set()
    suffixes: set[str] = set()
    for handle in handles:
        if handle.startswith(local_tok) and len(handle) > len(local_tok):
            suffix = handle[len(local_tok) :]
            if len(suffix) >= MIN_SURNAME_SUFFIX_LEN:
                suffixes.add(suffix)
    return suffixes


def _matches_initial_plus_surname_suffix(handle: str, local_tok: str, suffixes: set[str]) -> bool:
    if len(handle) < MIN_INITIAL_SUFFIX_LOGIN_LEN or not suffixes:
        return False
    if len(local_tok) < MIN_EMAIL_LOCAL_FOR_SUFFIX:
        return False
    initial = local_tok[0]
    return any(handle == initial + suffix for suffix in suffixes)


def _initial_suffix_login_handles(signal: ActorSignal) -> set[str]:
    """Provider logins like ``cveneziani`` (9) used only for initial+surname suffix matching."""
    tokens: set[str] = set()
    if signal.primary_handle:
        key = normalize_handle(signal.primary_handle)
        if key and len(key) >= MIN_INITIAL_SUFFIX_LOGIN_LEN:
            tokens.add(key)
    for handle in signal.handles:
        if handle and len(handle) >= MIN_INITIAL_SUFFIX_LOGIN_LEN:
            tokens.add(handle)
    return tokens


def _handles_for_identity_entity(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    identity_id: uuid.UUID,
) -> set[str]:
    handles: set[str] = set()
    rows = list(
        session.execute(
            select(IdentityAccount)
            .where(
                IdentityAccount.tenant_id == tenant_id,
                IdentityAccount.identity_entity_id == identity_id,
                IdentityAccount.unlinked_at.is_(None),
            ),
        ).scalars().all(),
    )
    for account in rows:
        row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=account.canon_entity_id)
        if row is None:
            continue
        entity, source, raw = row
        payload = dict(raw.payload_body) if isinstance(raw.payload_body, dict) else {}
        sig = extract_actor_signal(
            canon_entity_id=entity.id,
            connector=entity.connector,
            connection_id=entity.connection_id,
            entity_key=entity.entity_key,
            external_id=source.external_id,
            source_revision_key=source.source_revision_key,
            payload_body=payload,
        )
        handles.update(_cross_actor_match_handles(sig))
        handles.update(_significant_handle_tokens(sig.handles))
    return handles


def _name_token(raw: str) -> str | None:
    folded = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(ch for ch in folded if ord(ch) < 128)
    token = "".join(ch for ch in ascii_only.lower() if ch.isalnum())
    return token or None


def _cross_actor_full_display_name_tokens(raw: str) -> set[str]:
    """Full collapsed display-name tokens only (no isolated first names or surnames)."""
    full = _name_token(raw)
    if full and len(full) >= MIN_CROSS_ACTOR_FULL_NAME_LEN:
        return {full}
    return set()


def _actor_has_tenant_email(signal: ActorSignal, tenant_domain: str | None) -> bool:
    domain = (tenant_domain or "").strip().lower()
    if not domain:
        return False
    suffix = f"@{domain}"
    return any(email.endswith(suffix) for email in signal.emails)


def _weak_cross_actor_merge_allowed(signal: ActorSignal, tenant_domain: str | None) -> bool:
    """Slack-only actors without a tenant email must not weak-link into email-anchored identities."""
    return _actor_has_tenant_email(signal, tenant_domain)


def _incoming_short_logins(signal: ActorSignal) -> set[str]:
    """Normalized logins between suffix and alias thresholds (e.g. zakia, melissa)."""
    tokens: set[str] = set()
    if signal.primary_handle:
        key = normalize_handle(signal.primary_handle)
        if key and MIN_EMAIL_LOCAL_FOR_SUFFIX <= len(key) < MIN_EMAIL_LOCAL_SHORT_LOGIN_MAX:
            tokens.add(key)
    for handle in signal.handles:
        if MIN_EMAIL_LOCAL_FOR_SUFFIX <= len(handle) < MIN_EMAIL_LOCAL_SHORT_LOGIN_MAX:
            tokens.add(handle)
    return tokens


def _identity_handles_all_short(handles: set[str]) -> bool:
    return not any(len(handle) >= MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN for handle in handles)


def _long_handles_prefixed_by_local(handles: set[str], local_tok: str) -> set[str]:
    return {
        handle
        for handle in handles
        if len(handle) >= MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN
        and handle.startswith(local_tok)
        and len(handle) > len(local_tok)
    }


def _incoming_has_conflicting_long_handle(
    signal: ActorSignal,
    local_tok: str,
    *,
    identity_handles: set[str],
) -> bool:
    """True when incoming exposes a long handle incompatible with this email anchor."""
    allowed_long = _long_handles_prefixed_by_local(identity_handles, local_tok)
    long_handles: set[str] = set()
    if signal.primary_handle:
        primary = normalize_handle(signal.primary_handle)
        if primary and len(primary) >= MIN_CROSS_ACTOR_ALIAS_HANDLE_LEN:
            long_handles.add(primary)
    long_handles.update(_significant_handle_tokens(signal.handles))
    for handle in long_handles:
        if handle in allowed_long:
            continue
        if not handle.startswith(local_tok):
            return True
        # Same first name, different surname in handle (camillebigcheese vs camilleortholand).
        return True
    return False


def _email_local_login_matches(
    *,
    signal: ActorSignal,
    local_tok: str,
    identity_handles: set[str],
    short_logins: set[str],
) -> str | None:
    """Return link_rule when a short Slack login matches a tenant-email anchor (v12)."""
    if local_tok not in short_logins:
        return None
    if _incoming_has_conflicting_long_handle(signal, local_tok, identity_handles=identity_handles):
        return None
    if (
        MIN_EMAIL_LOCAL_FOR_SUFFIX <= len(local_tok) < MIN_EMAIL_LOCAL_SHORT_LOGIN_MAX
        and _identity_handles_all_short(identity_handles)
    ):
        return "email_local_short_login"
    if (
        MIN_EMAIL_LOCAL_PREFIX_LOGIN_LEN <= len(local_tok) < MIN_EMAIL_LOCAL_SHORT_LOGIN_MAX
        and _long_handles_prefixed_by_local(identity_handles, local_tok)
    ):
        return "email_local_prefix_login"
    return None


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


def _actor_has_verified_email(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
) -> bool:
    row = _latest_actor_payload(session, tenant_id=tenant_id, canon_entity_id=canon_entity_id)
    if row is None:
        return False
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
    return bool(signal.emails)


def _sort_dirty_queue_email_first(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    items: list[IdentityDirtyQueue],
) -> list[IdentityDirtyQueue]:
    """Process email-anchored actors before handle-only logins (e.g. GitHub org members)."""
    return sorted(
        items,
        key=lambda item: (
            0 if _actor_has_verified_email(session, tenant_id=tenant_id, canon_entity_id=item.canon_entity_id) else 1,
            item.enqueued_at,
        ),
    )


_RESOLVER_BUMP_QUEUE_REASONS = frozenset({"resolver_bump", "seed_rematch", "periodic_rescan"})


def enqueue_identity_actor(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    canon_entity_id: uuid.UUID,
    reason: str,
) -> None:
    reason = reason[:32]
    existing = session.scalar(
        select(IdentityDirtyQueue)
        .where(
            IdentityDirtyQueue.tenant_id == tenant_id,
            IdentityDirtyQueue.canon_entity_id == canon_entity_id,
            IdentityDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if existing is not None:
        if reason in _RESOLVER_BUMP_QUEUE_REASONS and existing.reason not in _RESOLVER_BUMP_QUEUE_REASONS:
            existing.reason = reason
        return
    session.add(
        IdentityDirtyQueue(
            tenant_id=tenant_id,
            canon_entity_id=canon_entity_id,
            reason=reason,
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
            and existing_account.link_rule not in REVOCABLE_WEAK_LINK_RULES
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
    weak_merge_ok = _weak_cross_actor_merge_allowed(signal, tenant_domain)
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
        handle_tokens = _cross_actor_match_handles(signal)
        for identity in existing:
            if not identity.primary_email:
                continue
            if not identity.primary_email.endswith(f"@{tenant_domain}"):
                continue
            local_tok = _local_part_token(identity.primary_email)
            if local_tok and _handle_matches_email_local_part(handle_tokens, local_tok):
                handle_to_email_matches.add(identity.id)
        if len(handle_to_email_matches) == 1:
            target_id = next(iter(handle_to_email_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = "handle_to_email_local_part"
                confidence = "medium"
    short_logins = _incoming_short_logins(signal)
    if matched_identity is None and short_logins and tenant_domain:
        email_local_login_matches: dict[uuid.UUID, str] = {}
        anchored = list(
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
        for identity in anchored:
            if identity.primary_email is None or not identity.primary_email.endswith(f"@{tenant_domain}"):
                continue
            local_tok = _local_part_token(identity.primary_email)
            if not local_tok:
                continue
            identity_handles = _handles_for_identity_entity(
                session,
                tenant_id=tenant_id,
                identity_id=identity.id,
            )
            rule = _email_local_login_matches(
                signal=signal,
                local_tok=local_tok,
                identity_handles=identity_handles,
                short_logins=short_logins,
            )
            if rule is not None:
                email_local_login_matches[identity.id] = rule
        if len(email_local_login_matches) == 1:
            target_id = next(iter(email_local_login_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = email_local_login_matches[target_id]
                confidence = "medium"
    incoming_handles = _cross_actor_match_handles(signal)
    # Cross-provider handle match (e.g. Notion email + Slack login) does not require Slack profile email.
    if matched_identity is None and incoming_handles:
        handle_matches: dict[uuid.UUID, str] = {}
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
            if account.canon_entity_id == canon_entity.id:
                continue
            prev_row = _latest_actor_payload(
                session,
                tenant_id=tenant_id,
                canon_entity_id=account.canon_entity_id,
            )
            if prev_row is None:
                continue
            prev_entity, prev_source, prev_raw = prev_row
            prev_payload = dict(prev_raw.payload_body) if isinstance(prev_raw.payload_body, dict) else {}
            prev_signal = extract_actor_signal(
                canon_entity_id=prev_entity.id,
                connector=prev_entity.connector,
                connection_id=prev_entity.connection_id,
                entity_key=prev_entity.entity_key,
                external_id=prev_source.external_id,
                source_revision_key=prev_source.source_revision_key,
                payload_body=prev_payload,
            )
            prev_handles = _cross_actor_match_handles(prev_signal)
            if _significant_handle_overlap(prev_handles, incoming_handles):
                handle_matches[identity.id] = "exact_normalized_handle"
            elif _significant_handles_edit_distance_one(prev_handles, incoming_handles):
                handle_matches[identity.id] = "handle_edit_distance_one"
        if len(handle_matches) == 1:
            target_id = next(iter(handle_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = handle_matches[target_id]
                confidence = "medium"
    suffix_login_handles = _initial_suffix_login_handles(signal)
    if matched_identity is None and suffix_login_handles and tenant_domain:
        initial_suffix_matches: set[uuid.UUID] = set()
        anchored_identities = list(
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
        for identity in anchored_identities:
            if identity.primary_email is None or not identity.primary_email.endswith(f"@{tenant_domain}"):
                continue
            if (
                chosen_email
                and identity.primary_email
                and normalize_email(chosen_email) != normalize_email(identity.primary_email)
            ):
                continue
            local_tok = _local_part_token(identity.primary_email)
            if not local_tok:
                continue
            identity_handles = _handles_for_identity_entity(
                session,
                tenant_id=tenant_id,
                identity_id=identity.id,
            )
            suffixes = _surname_suffixes_from_email_local(local_tok, identity_handles)
            if not suffixes:
                continue
            for handle in suffix_login_handles:
                if _matches_initial_plus_surname_suffix(handle, local_tok, suffixes):
                    initial_suffix_matches.add(identity.id)
                    break
        if len(initial_suffix_matches) == 1:
            target_id = next(iter(initial_suffix_matches))
            matched_identity = session.get(IdentityEntity, target_id)
            if matched_identity is not None:
                link_tier = "T3"
                link_rule = "initial_plus_surname_suffix"
                confidence = "medium"
    # T4: full display-name tokens (e.g. hugobonnome) may link Slack without profile email.
    if matched_identity is None and signal.display_names:
        name_matches: set[uuid.UUID] = set()
        incoming_name_tokens: set[str] = set()
        for name in signal.display_names:
            incoming_name_tokens.update(_cross_actor_full_display_name_tokens(name))
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
                prior_tokens: set[str] = set()
                for name in prior_names:
                    prior_tokens.update(_cross_actor_full_display_name_tokens(name))
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
        should_split = (
            existing_account is not None
            and existing_account.link_rule in REVOCABLE_WEAK_LINK_RULES
        )
        if should_split or existing_identity is None:
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
            if should_split:
                link_tier = "seed"
                link_rule = "resolver_split"
                confidence = "low"
        else:
            identity = existing_identity
            identity.display_name = canon_entity.display_label[:512]
            if chosen_email is not None:
                identity.primary_email = chosen_email
            if identity.resolver_version < resolved_version:
                identity.resolver_version = resolved_version
            identity.resolved_at = utc_now()
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
        "primary_handle": signal.primary_handle,
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
    if signal.avatar_url:
        evidence["avatar_url"] = signal.avatar_url
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
        session.flush()
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
    session.flush()
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


def _fetch_identity_dirty_batch(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    batch_limit: int,
    max_attempts: int,
) -> list[IdentityDirtyQueue]:
    cap = max(1, min(batch_limit, 5000))
    attempt_cap = max(1, min(max_attempts, 100))
    items = list(
        session.scalars(
            select(IdentityDirtyQueue)
            .where(
                IdentityDirtyQueue.tenant_id == tenant_id,
                IdentityDirtyQueue.processed_at.is_(None),
                IdentityDirtyQueue.attempts < attempt_cap,
            )
            .order_by(IdentityDirtyQueue.enqueued_at.asc())
            .limit(cap),
        ).all(),
    )
    return _sort_dirty_queue_email_first(session, tenant_id=tenant_id, items=items)


def execute_identity_pass_for_tenant(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    source_trigger: str,
    batch_limit: int,
    max_attempts: int = 5,
    periodic_rescan_limit: int = 200,
    resolver_version: int | None = None,
    drain: bool | None = None,
) -> dict[str, Any]:
    if drain is None:
        drain = source_trigger == "manual_admin"
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
        "rematched": 0,
        "already_linked": 0,
        "missing_actor": 0,
        "errors": 0,
    }
    rescan_cap = max(1, min(periodic_rescan_limit, 5000))
    max_iterations = 100 if drain else 1
    try:
        for _ in range(max_iterations):
            enqueue_periodic_identity_candidates(
                session,
                tenant_id=tenant_id,
                limit=rescan_cap,
                resolver_version=resolver_version,
            )
            session.flush()
            items = _fetch_identity_dirty_batch(
                session,
                tenant_id=tenant_id,
                batch_limit=batch_limit,
                max_attempts=max_attempts,
            )
            if not items:
                break
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
                    outcome = out.get("outcome")
                    if outcome == "seeded":
                        stats["seeded"] += 1
                    elif outcome == "rematched":
                        stats["rematched"] += 1
                    else:
                        stats["already_linked"] += 1
                    if outcome in ("seeded", "rematched"):
                        try:
                            from vector.domains.cortex.graph.enqueue import (
                                enqueue_graph_actor_for_enrich,
                            )

                            enqueue_graph_actor_for_enrich(
                                session,
                                tenant_id=tenant_id,
                                canon_entity_id=canon_entity.id,
                            )
                        except Exception:
                            pass
                    item.processed_at = utc_now()
                    item.last_error = None
                except Exception as exc:
                    stats["errors"] += 1
                    item.attempts += 1
                    item.last_error = str(exc)[:1000]
            if not drain:
                break
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
    total_stats = {
        "processed": 0,
        "seeded": 0,
        "rematched": 0,
        "already_linked": 0,
        "missing_actor": 0,
        "errors": 0,
    }
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


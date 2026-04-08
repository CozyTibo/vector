"""Resolve Slack mrkdwn IDs to human-readable labels for admin transcripts."""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.manager_onboarding import slack_web_api
from vector.infrastructure.db.repositories import manager_onboarding as mo_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo

log = logging.getLogger(__name__)

# <#C09ABC|optional-label> — label is already human-readable when present.
_CHANNEL_MENTION_RE = re.compile(r"<#([A-Z0-9]+)(?:\|([^>]*))?>")
# <@U09ABC|optional-label>
_USER_MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|([^>]*))?>")
_IDS_PAREN_RE = re.compile(r"\(IDs:\s*([^)]+)\)")
_BARE_CHANNEL_TOKEN_RE = re.compile(r"\b(C[A-Z0-9]{8,})\b")
# Standalone Slack user ids in plain text (e.g. a manager pastes a member id).
_BARE_USER_TOKEN_RE = re.compile(r"\b(U[A-Z0-9]{8,}|W[A-Z0-9]{8,})\b")


def _channel_label_from_conversations_info(data: dict) -> str:
    ch = data.get("channel") or {}
    name = ch.get("name")
    if isinstance(name, str) and name.strip():
        n = name.strip().lstrip("#")
        return f"#{n}"
    return ""


def _user_label_from_slack_user_dict(u: dict[str, Any]) -> str:
    """Label from a ``user`` object (``users.info`` or ``users.list`` member)."""
    prof = u.get("profile")
    if isinstance(prof, dict):
        for key in ("display_name", "real_name"):
            raw = prof.get(key)
            if isinstance(raw, str):
                s = raw.strip()
                if s:
                    return f"@{s}"
    name = u.get("name")
    if isinstance(name, str) and name.strip():
        return f"@{name.strip()}"
    return ""


def _user_label_from_users_info(data: dict) -> str:
    u = data.get("user")
    if isinstance(u, dict):
        return _user_label_from_slack_user_dict(u)
    return ""


def _resolve_slack_user_labels_with_token(token: str, user_ids: set[str]) -> dict[str, str]:
    """
    Resolve Slack user ids to ``@DisplayName`` for admin UI.

    Prefer ``users.list`` (paginate until all ids are found) then ``users.info`` for any gaps.
    """
    labels: dict[str, str] = {}
    need: set[str] = set()
    for u in user_ids:
        if not u or not isinstance(u, str):
            continue
        s = u.strip().upper()
        if s.startswith("U") or s.startswith("W"):
            need.add(s)
    if not need:
        return labels
    missing = set(need)
    try:
        for member in slack_web_api.iter_users_list(token):
            uid = str(member.get("id") or "").strip()
            if uid not in missing:
                continue
            label = _user_label_from_slack_user_dict(member)
            if label:
                labels[uid] = label
                missing.discard(uid)
            if not missing:
                break
    except Exception as e:
        log.info("admin slack users.list for labels failed (will use users.info): %s", e)
    for uid in sorted(missing):
        try:
            data = slack_web_api.users_info(token, user=uid)
            label = _user_label_from_users_info(data)
            if label:
                labels[uid] = label
        except Exception as e:
            log.debug("admin slack user resolve skip %s: %s", uid, e)
    return labels


def _collect_ids_to_resolve(texts: Iterable[str]) -> tuple[set[str], set[str]]:
    need_channels: set[str] = set()
    need_users: set[str] = set()
    for t in texts:
        for m in _CHANNEL_MENTION_RE.finditer(t):
            if not (m.group(2) and m.group(2).strip()):
                need_channels.add(m.group(1))
        for m in _USER_MENTION_RE.finditer(t):
            if not (m.group(2) and m.group(2).strip()):
                need_users.add(m.group(1))
        for m in _IDS_PAREN_RE.finditer(t):
            for raw in m.group(1).split(","):
                tok = raw.strip()
                if re.fullmatch(r"C[A-Z0-9]+", tok):
                    need_channels.add(tok)
        for m in _BARE_CHANNEL_TOKEN_RE.finditer(t):
            need_channels.add(m.group(1))
    return need_channels, need_users


def _replace_ids_paren(
    text: str,
    channel_labels: dict[str, str],
    user_labels: dict[str, str],
) -> str:
    def repl(match: re.Match[str]) -> str:
        inner = match.group(1)
        parts: list[str] = []
        for raw in inner.split(","):
            token = raw.strip()
            if re.fullmatch(r"C[A-Z0-9]+", token):
                parts.append(channel_labels.get(token, token))
            elif re.fullmatch(r"U[A-Z0-9]+|W[A-Z0-9]+", token):
                parts.append(user_labels.get(token, token))
            else:
                parts.append(token)
        return f"(IDs: {', '.join(parts)})"

    return _IDS_PAREN_RE.sub(repl, text)


def _replace_bare_channel_tokens(text: str, channel_labels: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        cid = m.group(1)
        return channel_labels.get(cid, m.group(0))

    return _BARE_CHANNEL_TOKEN_RE.sub(repl, text)


def _replace_bare_user_tokens(text: str, user_labels: dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        uid = m.group(1)
        return user_labels.get(uid, m.group(0))

    return _BARE_USER_TOKEN_RE.sub(repl, text)


def enrich_slack_dm_text_for_admin(
    text: str,
    *,
    channel_labels: dict[str, str],
    user_labels: dict[str, str],
) -> str:
    def ch_sub(m: re.Match[str]) -> str:
        cid = m.group(1)
        embedded = m.group(2)
        if embedded and embedded.strip():
            return embedded.strip()
        return channel_labels.get(cid, f"#{cid}")

    def us_sub(m: re.Match[str]) -> str:
        uid = m.group(1)
        embedded = m.group(2)
        if embedded and embedded.strip():
            return embedded.strip()
        return user_labels.get(uid, uid)

    out = _CHANNEL_MENTION_RE.sub(ch_sub, text)
    out = _USER_MENTION_RE.sub(us_sub, out)
    out = _replace_ids_paren(out, channel_labels, user_labels)
    out = _replace_bare_channel_tokens(out, channel_labels)
    out = _replace_bare_user_tokens(out, user_labels)
    return out


def build_slack_label_maps_for_admin(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    texts: Sequence[str],
    session_slack_user_id: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Build channel id -> '#name' and user id -> '@Display Name' for admin UI.
    Uses channel observations when available, then Slack Web API for gaps.
    """
    channel_labels: dict[str, str] = {}
    user_labels: dict[str, str] = {}

    for o in mo_repo.list_channel_observations_for_tenant(session, tenant_id, limit=500):
        cid = (o.slack_channel_id or "").strip()
        name = (o.channel_name or "").strip()
        if cid and name:
            channel_labels[cid] = f"#{name.lstrip('#')}"

    need_ch, need_u = _collect_ids_to_resolve(texts)
    su = (session_slack_user_id or "").strip()
    if su:
        need_u.add(su)

    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return channel_labels, user_labels

    token = (link.detail.bot_access_token or "").strip()
    if not token:
        return channel_labels, user_labels

    for cid in sorted(need_ch):
        if cid in channel_labels:
            continue
        try:
            data = slack_web_api.conversations_info(token, channel=cid)
            label = _channel_label_from_conversations_info(data)
            if label:
                channel_labels[cid] = label
        except Exception as e:
            log.debug("admin slack channel resolve skip %s: %s", cid, e)

    extra_u = {
        u
        for u in need_u
        if u not in user_labels and (u.startswith("U") or u.startswith("W"))
    }
    if extra_u:
        for uid, lab in _resolve_slack_user_labels_with_token(token, extra_u).items():
            user_labels.setdefault(uid, lab)

    return channel_labels, user_labels


_SLACK_USER_ID_RE = re.compile(r"^[UW][A-Z0-9]+$")
_SLACK_CHANNEL_ID_RE = re.compile(r"^[CG][A-Z0-9]+$")


def collect_slack_user_ids_from_answers(answers: dict[str, Any]) -> set[str]:
    """User ids stored in manager onboarding ``answers_json`` lists."""
    out: set[str] = set()
    for key in ("peer_slack_user_ids", "team_member_slack_ids", "reports_to_slack_ids"):
        v = answers.get(key)
        if not isinstance(v, list):
            continue
        for x in v:
            if isinstance(x, str):
                s = x.strip().upper()
                if _SLACK_USER_ID_RE.fullmatch(s):
                    out.add(s)
    # Legacy or alternate: plain ids / text containing ids in ``team_members``.
    tm = answers.get("team_members")
    if isinstance(tm, list):
        for x in tm:
            if not isinstance(x, str):
                continue
            s = x.strip().upper()
            if _SLACK_USER_ID_RE.fullmatch(s):
                out.add(s)
            else:
                for m in _BARE_USER_TOKEN_RE.finditer(s):
                    out.add(m.group(1).strip().upper())
    return out


def collect_slack_channel_ids_from_answers(answers: dict[str, Any]) -> set[str]:
    """Channel ids stored in ``observed_channel_ids`` (manager onboarding answers)."""
    out: set[str] = set()
    v = answers.get("observed_channel_ids")
    if not isinstance(v, list):
        return out
    for x in v:
        if isinstance(x, str):
            s = x.strip().upper()
            if _SLACK_CHANNEL_ID_RE.fullmatch(s):
                out.add(s)
    return out


def resolve_slack_channel_labels_for_session(
    session: Session,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    channel_ids: set[str],
) -> dict[str, str]:
    """
    Map Slack channel id -> ``#name`` for admin collected-answers UI.

    Prefer rows from ``manager_onboarding_channel_observations`` for this session,
    then ``conversations.info`` for any remaining ids.
    """
    labels: dict[str, str] = {}
    need = {c.strip().upper() for c in channel_ids if c and isinstance(c, str)}
    if not need:
        return labels

    for obs in mo_repo.list_channel_observations_for_session(session, session_id):
        cid = (obs.slack_channel_id or "").strip().upper()
        name = (obs.channel_name or "").strip()
        if cid in need and name:
            labels[cid] = f"#{name.lstrip('#')}"

    remaining = need - set(labels.keys())
    if not remaining:
        return labels

    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return labels
    token = (link.detail.bot_access_token or "").strip()
    if not token:
        return labels

    for cid in sorted(remaining):
        try:
            data = slack_web_api.conversations_info(token, channel=cid)
            label = _channel_label_from_conversations_info(data)
            if label:
                labels[cid] = label
        except Exception as e:
            log.debug("admin slack channel label skip %s: %s", cid, e)
    return labels


def resolve_slack_user_labels_for_ids(
    session: Session,
    tenant_id: uuid.UUID,
    user_ids: set[str],
) -> dict[str, str]:
    """
    Map Slack user id -> display label (e.g. ``@Jane``) for admin UI.
    Best-effort when Slack is not connected or users.info fails.
    """
    labels: dict[str, str] = {}
    need = {u.strip().upper() for u in user_ids if u and isinstance(u, str)}
    if not need:
        return labels
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return labels
    token = (link.detail.bot_access_token or "").strip()
    if not token:
        return labels
    return _resolve_slack_user_labels_with_token(token, need)

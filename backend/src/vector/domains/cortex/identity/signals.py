"""Identity signal extraction from canon actor provenance."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from typing import Any


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm_token(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    v = raw.strip().lower()
    if not v:
        return None
    return v


def normalize_email(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    v = raw.strip().lower()
    if not v or "@" not in v:
        return None
    return v


def normalize_handle(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    v = raw.strip().lower().lstrip("@")
    if not v:
        return None
    folded = unicodedata.normalize("NFKD", v)
    v = "".join(ch for ch in folded if ord(ch) < 128)
    v = _NON_ALNUM.sub("", v)
    return v or None


@dataclass
class ActorSignal:
    canon_entity_id: uuid.UUID
    connector: str
    connection_id: uuid.UUID
    entity_key: str
    external_id: str | None = None
    emails: set[str] = field(default_factory=set)
    handles: set[str] = field(default_factory=set)
    primary_handle: str | None = None
    display_names: set[str] = field(default_factory=set)
    provider_ids: set[str] = field(default_factory=set)
    is_bot: bool | None = None
    bot_reasons: list[str] = field(default_factory=list)
    is_inactive: bool | None = None
    inactive_reasons: list[str] = field(default_factory=list)
    avatar_url: str | None = None
    source_revision_key: str | None = None

    def add_email(self, raw: object) -> None:
        v = normalize_email(raw)
        if v:
            self.emails.add(v)

    def add_handle(self, raw: object) -> None:
        v = normalize_handle(raw)
        if v:
            self.handles.add(v)

    def add_name(self, raw: object) -> None:
        v = _norm_token(raw)
        if v:
            self.display_names.add(v)

    def add_provider_id(self, raw: object) -> None:
        if raw is None:
            return
        s = str(raw).strip()
        if s:
            self.provider_ids.add(s)

    def mark_bot(self, reason: str) -> None:
        self.is_bot = True
        if reason not in self.bot_reasons:
            self.bot_reasons.append(reason)

    def mark_inactive(self, reason: str) -> None:
        self.is_inactive = True
        if reason not in self.inactive_reasons:
            self.inactive_reasons.append(reason)


def _extract_slack(signal: ActorSignal, body: dict[str, Any]) -> None:
    member = body.get("member")
    if not isinstance(member, dict):
        return
    signal.add_provider_id(member.get("id"))
    login = normalize_handle(member.get("name"))
    if login:
        signal.primary_handle = login
    signal.add_handle(member.get("name"))
    signal.add_handle(member.get("real_name"))
    signal.add_name(member.get("real_name"))
    profile = member.get("profile")
    if isinstance(profile, dict):
        signal.add_email(profile.get("email"))
        signal.add_handle(profile.get("display_name"))
        signal.add_handle(profile.get("real_name"))
        signal.add_name(profile.get("display_name"))
        signal.add_name(profile.get("display_name_normalized"))
        signal.add_name(profile.get("real_name"))
        img = profile.get("image_72") or profile.get("image_48")
        if isinstance(img, str) and img.strip():
            signal.avatar_url = img.strip()
    signal.add_email(member.get("email"))
    if bool(member.get("deleted")):
        signal.mark_inactive("slack_deleted_member")
    if bool(member.get("is_bot")):
        signal.mark_bot("slack_is_bot")


def _extract_github(signal: ActorSignal, body: dict[str, Any]) -> None:
    member = body.get("member")
    if not isinstance(member, dict):
        return
    signal.add_provider_id(member.get("id"))
    login = normalize_handle(member.get("login"))
    if login:
        signal.primary_handle = login
    signal.add_handle(member.get("login"))
    signal.add_name(member.get("name"))
    signal.add_email(member.get("email"))
    avatar = member.get("avatar_url")
    if isinstance(avatar, str) and avatar.strip():
        signal.avatar_url = avatar.strip()
    gh_type = member.get("type")
    if isinstance(gh_type, str) and gh_type.strip().lower() == "bot":
        signal.mark_bot("github_type_bot")


def _extract_linear(signal: ActorSignal, body: dict[str, Any]) -> None:
    user = body.get("user")
    if not isinstance(user, dict):
        return
    signal.add_provider_id(user.get("id"))
    signal.add_handle(user.get("displayName"))
    signal.add_handle(user.get("name"))
    signal.add_name(user.get("name"))
    signal.add_name(user.get("displayName"))
    email = user.get("email")
    signal.add_email(email)
    if isinstance(email, str) and "@" in email:
        local = normalize_handle(email.split("@", 1)[0])
        if local:
            signal.primary_handle = local
        signal.add_handle(email.split("@", 1)[0])
    avatar = user.get("avatarUrl")
    if isinstance(avatar, str) and avatar.strip():
        signal.avatar_url = avatar.strip()


def _extract_notion(signal: ActorSignal, body: dict[str, Any]) -> None:
    user = body.get("user")
    if not isinstance(user, dict):
        return
    signal.add_provider_id(user.get("id"))
    signal.add_handle(user.get("name"))
    signal.add_name(user.get("name"))
    person = user.get("person")
    if isinstance(person, dict):
        email = person.get("email")
        signal.add_email(email)
        if isinstance(email, str) and "@" in email:
            local = normalize_handle(email.split("@", 1)[0])
            if local:
                signal.primary_handle = local
            signal.add_handle(email.split("@", 1)[0])
    avatar = user.get("avatar_url")
    if isinstance(avatar, str) and avatar.strip():
        signal.avatar_url = avatar.strip()
    typ = user.get("type")
    if isinstance(typ, str) and typ.strip().lower() == "bot":
        signal.mark_bot("notion_type_bot")
    elif isinstance(typ, str) and typ.strip().lower() == "person" and not signal.emails:
        signal.mark_inactive("notion_person_without_email")


def extract_actor_signal(
    *,
    canon_entity_id: uuid.UUID,
    connector: str,
    connection_id: uuid.UUID,
    entity_key: str,
    external_id: str | None,
    source_revision_key: str | None,
    payload_body: dict[str, Any],
) -> ActorSignal:
    signal = ActorSignal(
        canon_entity_id=canon_entity_id,
        connector=connector,
        connection_id=connection_id,
        entity_key=entity_key,
        external_id=external_id,
        source_revision_key=source_revision_key,
    )
    if connector == "slack":
        _extract_slack(signal, payload_body)
    elif connector == "github":
        _extract_github(signal, payload_body)
    elif connector == "linear":
        _extract_linear(signal, payload_body)
    elif connector == "notion":
        _extract_notion(signal, payload_body)
    return signal


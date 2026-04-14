"""Validate LLM patch fields independently; Slack resolution + subteam expansion (no LLM here)."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from vector.domains.manager_onboarding import slack_web_api
from vector.domains.manager_onboarding.constants import SCOPE_JUST_ME, SCOPE_OTHER_MANAGERS
from vector.domains.manager_onboarding.engine.requirements import (
    REQ_CHANNELS,
    REQ_PEER_HANDLES,
    REQ_REPORTS_WHO,
    REQ_TEAM_MEMBERS,
)

log = logging.getLogger("app")

# primary_requirement id (from ``missing_requirements``) → patch list field
_PRIMARY_TO_LIST_PATCH_KEY: dict[str, str] = {
    REQ_PEER_HANDLES: "peer_slack_user_ids",
    REQ_TEAM_MEMBERS: "team_member_slack_ids",
    REQ_CHANNELS: "observed_channel_ids",
    REQ_REPORTS_WHO: "reports_to_slack_ids",
}


def _may_merge_empty_list(primary_requirement_id: str | None, patch_field: str) -> bool:
    if not primary_requirement_id:
        return False
    return _PRIMARY_TO_LIST_PATCH_KEY.get(primary_requirement_id) == patch_field

MAX_LLM_ENTITIES_PER_PATCH = 50

_WHITELIST = frozenset(
    {
        "scope_intent",
        "peer_slack_user_ids",
        "team_scope",
        "team_member_slack_ids",
        "observed_channel_ids",
        "observed_channels_skipped",
        "reports_to_yes",
        "reports_to_slack_ids",
        "kpi_expectations",
    }
)

_LIST_KEYS = frozenset(
    {"peer_slack_user_ids", "team_member_slack_ids", "reports_to_slack_ids", "observed_channel_ids"}
)

_SUBTEAM_MRKW = re.compile(r"<!subteam\^([S][A-Z0-9]+)(?:\|[^>]+)?>")
_SLACK_UID = re.compile(r"^[UW][A-Z0-9]{8,}$")
_SLACK_SUBTEAM = re.compile(r"^S[A-Z0-9]{8,}$")
_SLACK_CHAN = re.compile(r"^[CG][A-Z0-9]{8,}$")


@dataclass
class PatchValidationResult:
    """Result of validating a raw LLM ``patch`` (partial acceptance per field)."""

    validated_patch: dict[str, Any]
    field_errors: dict[str, str] = field(default_factory=dict)
    channels_inaccessible: bool = False
    any_entity_unresolved: bool = False


def strip_patch_to_whitelist(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _WHITELIST:
            out[k] = v
        else:
            log.debug("manager_onboarding validate: dropped non-whitelist patch key %s", k)
    return out


def _norm_chan_id(cid: str) -> str:
    return (cid or "").strip().upper()


def _norm_uid(uid: str) -> str:
    return (uid or "").strip().upper()


def _parse_subteam_id(entry: str) -> str | None:
    s = (entry or "").strip()
    m = _SUBTEAM_MRKW.search(s)
    if m:
        return m.group(1).strip().upper()
    su = s.upper()
    if _SLACK_SUBTEAM.fullmatch(su):
        return su
    return None


def expand_subteam_to_user_ids(bot_token: str, subteam_id: str) -> list[str]:
    try:
        data = slack_web_api.usergroups_users_list(bot_token, usergroup=subteam_id)
    except Exception as e:
        log.info("usergroups.users.list failed for %s: %s", subteam_id, e)
        return []
    if not data.get("ok"):
        log.info("usergroups.users.list not ok for %s: %s", subteam_id, data.get("error"))
        return []
    users = data.get("users")
    if not isinstance(users, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for u in users:
        if not isinstance(u, str):
            continue
        uid = _norm_uid(u)
        if _SLACK_UID.fullmatch(uid) and uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


@dataclass(frozen=True)
class _UserResolution:
    """Workspace directory for resolving @handles and first names to Slack user ids."""

    exact: dict[str, str]
    first_token: dict[str, tuple[str, ...]]

    @classmethod
    def empty(cls) -> _UserResolution:
        return cls({}, {})

    def resolve_name(self, raw: str) -> str | None:
        s = raw.lstrip("@").strip().lower().rstrip("?!.,:;").strip()
        if not s:
            return None
        if s in self.exact:
            return self.exact[s]
        first = s.split()[0]
        cand = self.first_token.get(first)
        if cand and len(cand) == 1:
            return cand[0]
        return None


def _build_user_resolution(bot_token: str) -> _UserResolution:
    """Lowercased names → uid, plus first-token → uid when unique in the workspace."""
    exact: dict[str, str] = {}
    ft_raw: dict[str, list[str]] = defaultdict(list)
    try:
        for m in slack_web_api.iter_users_list(bot_token):
            uid = _norm_uid(str(m.get("id") or ""))
            if not _SLACK_UID.fullmatch(uid):
                continue
            prof = m.get("profile") if isinstance(m.get("profile"), dict) else {}
            firsts_for_user: set[str] = set()
            for key in ("display_name", "real_name", "first_name"):
                raw = prof.get(key) if isinstance(prof, dict) else None
                if isinstance(raw, str) and raw.strip():
                    low = raw.strip().lower()
                    exact.setdefault(low, uid)
                    tok = low.split()[0]
                    if tok and tok not in firsts_for_user:
                        firsts_for_user.add(tok)
                        ft_raw[tok].append(uid)
            nm = m.get("name")
            if isinstance(nm, str) and nm.strip():
                low = nm.strip().lower()
                exact.setdefault(low, uid)
                tok = low.split()[0]
                if tok and tok not in firsts_for_user:
                    firsts_for_user.add(tok)
                    ft_raw[tok].append(uid)
    except Exception as e:
        log.warning("users.list for name resolution failed: %s", e)
        return _UserResolution.empty()
    first_token = {k: tuple(dict.fromkeys(v)) for k, v in ft_raw.items()}
    return _UserResolution(exact=exact, first_token=first_token)


def _patch_needs_workspace_user_directory(patch: dict[str, Any]) -> bool:
    """True if any list entry might require display-name / handle resolution."""
    for key in ("peer_slack_user_ids", "team_member_slack_ids", "reports_to_slack_ids"):
        v = patch.get(key)
        if not isinstance(v, list) or not v:
            continue
        if len(v) > MAX_LLM_ENTITIES_PER_PATCH:
            continue
        for e in v:
            if not isinstance(e, str):
                continue
            s = e.strip()
            if not s:
                continue
            if _parse_subteam_id(s):
                continue
            if s.lower() in ("self", "me", "i", "myself"):
                continue
            if _SLACK_UID.fullmatch(s.upper()):
                continue
            return True
    return False


def _fix_subteam_expand(
    bot_token: str,
    entries: list[Any],
    *,
    manager_slack_user_id: str,
    resolution: _UserResolution | None,
) -> tuple[list[str], bool]:
    """Expand subteams; resolve users; return merged ids + whether any entry failed."""
    if not isinstance(entries, list):
        return [], False
    mgr = _norm_uid(manager_slack_user_id)
    out: list[str] = []
    seen: set[str] = set()
    any_fail = False
    had_input = False
    for e in entries:
        if not isinstance(e, str):
            continue
        s = e.strip()
        if not s:
            continue
        had_input = True
        st = _parse_subteam_id(s)
        if st:
            expanded = expand_subteam_to_user_ids(bot_token, st)
            if not expanded:
                any_fail = True
            else:
                for uid in expanded:
                    if uid not in seen:
                        seen.add(uid)
                        out.append(uid)
            continue
        if s.lower() in ("self", "me", "i", "myself"):
            if _SLACK_UID.fullmatch(mgr):
                if mgr not in seen:
                    seen.add(mgr)
                    out.append(mgr)
            else:
                any_fail = True
            continue
        if _SLACK_UID.fullmatch(s.upper()):
            uid = _norm_uid(s)
            data = slack_web_api.users_info_raw(bot_token, user=uid)
            if data.get("ok"):
                if uid not in seen:
                    seen.add(uid)
                    out.append(uid)
            else:
                err = (data.get("error") or "").strip()
                if err == "user_not_found":
                    any_fail = True
                else:
                    # Mention IDs and workspace members often validate here even when
                    # users.info returns ratelimited / access noise; user_not_found is the
                    # only hard rejection.
                    if uid not in seen:
                        seen.add(uid)
                        out.append(uid)
            continue
        uid = resolution.resolve_name(s) if resolution is not None else None
        if uid and uid not in seen:
            seen.add(uid)
            out.append(uid)
        elif not uid:
            any_fail = True
    return out, any_fail and had_input


def _channel_accessible(bot_token: str, channel_id: str) -> tuple[bool, bool]:
    """
    Returns (ok_to_store, tried_but_inaccessible).
    Attempts ``conversations.join`` when bot is not a member (public/private per token).
    """
    cid = _norm_chan_id(channel_id)
    if not _SLACK_CHAN.fullmatch(cid):
        return False, False
    try:
        data = slack_web_api.conversations_info(bot_token, channel=cid)
    except Exception as e:
        log.info("conversations.info failed %s: %s", cid, e)
        return False, True
    ch = data.get("channel") if isinstance(data.get("channel"), dict) else {}
    if not ch:
        return False, True
    if ch.get("is_member") is True:
        return True, False
    join = slack_web_api.conversations_join(bot_token, channel=cid)
    if join.get("ok"):
        return True, False
    return False, True


def _resolve_channel_entries(bot_token: str, entries: list[Any]) -> tuple[list[str], bool, bool]:
    """
    Returns (validated_ids, any_inaccessible, any_unresolved).
    Replace semantics: validated subset of patch list, in order.
    """
    if not isinstance(entries, list):
        return [], False, False
    try:
        all_ch = slack_web_api.conversations_list_public_private(bot_token)
    except Exception as e:
        log.warning("conversations.list failed: %s", e)
        all_ch = []
    name_to_id: dict[str, str] = {}
    for ch in all_ch:
        n = str(ch.get("name") or "").strip().lower()
        cid = _norm_chan_id(str(ch.get("id") or ""))
        if n and cid and n not in name_to_id:
            name_to_id[n] = cid
    out: list[str] = []
    seen: set[str] = set()
    any_inacc = False
    any_unres = False
    for e in entries:
        if not isinstance(e, str):
            continue
        s = e.strip().lstrip("#")
        if not s:
            continue
        cid: str | None = None
        su = s.upper()
        if _SLACK_CHAN.fullmatch(su):
            cid = su
        else:
            cid = name_to_id.get(s.lower())
        if not cid:
            any_unres = True
            continue
        ok, inacc = _channel_accessible(bot_token, cid)
        if ok and cid not in seen:
            seen.add(cid)
            out.append(cid)
        else:
            if inacc:
                any_inacc = True
            any_unres = True
    return out, any_inacc, any_unres


def validate_patch(
    raw_patch: dict[str, Any],
    *,
    bot_token: str,
    manager_slack_user_id: str,
    primary_requirement_id: str | None = None,
) -> PatchValidationResult:
    patch = strip_patch_to_whitelist(raw_patch)
    errors: dict[str, str] = {}
    validated: dict[str, Any] = {}
    ch_inacc = False
    any_unres = False

    user_res: _UserResolution | None = None
    if _patch_needs_workspace_user_directory(patch):
        user_res = _build_user_resolution(bot_token)

    for lk in _LIST_KEYS:
        v = patch.get(lk)
        if v is None:
            continue
        if not isinstance(v, list):
            errors[lk] = "not_a_list"
            continue
        if len(v) > MAX_LLM_ENTITIES_PER_PATCH:
            errors[lk] = f"max_llm_entities_exceeded_{MAX_LLM_ENTITIES_PER_PATCH}"
            continue

    if "scope_intent" in patch:
        s = patch["scope_intent"]
        if not isinstance(s, str):
            errors["scope_intent"] = "invalid_type"
        else:
            low = s.strip().lower().replace(" ", "_").replace("-", "_")
            if low in ("just_me", "justme", "me_only", "only_me"):
                validated["scope_intent"] = SCOPE_JUST_ME
            elif low in ("other_managers", "other_managers_too", "others", "multiple_managers"):
                validated["scope_intent"] = SCOPE_OTHER_MANAGERS
            else:
                errors["scope_intent"] = "invalid_enum"

    if "team_scope" in patch and "team_scope" not in errors:
        ts = patch["team_scope"]
        if not isinstance(ts, str) or not ts.strip():
            errors["team_scope"] = "empty_or_invalid"
        else:
            validated["team_scope"] = ts.strip()[:2000]

    if "kpi_expectations" in patch and "kpi_expectations" not in errors:
        kp = patch["kpi_expectations"]
        if kp is None:
            errors["kpi_expectations"] = "null"
        elif not isinstance(kp, str):
            errors["kpi_expectations"] = "invalid_type"
        else:
            validated["kpi_expectations"] = kp.strip()[:4000]

    if "reports_to_yes" in patch and "reports_to_yes" not in errors:
        ry = patch["reports_to_yes"]
        if not isinstance(ry, bool):
            errors["reports_to_yes"] = "invalid_type"
        else:
            validated["reports_to_yes"] = ry

    if "observed_channels_skipped" in patch and "observed_channels_skipped" not in errors:
        sk = patch["observed_channels_skipped"]
        if not isinstance(sk, bool):
            errors["observed_channels_skipped"] = "invalid_type"
        else:
            validated["observed_channels_skipped"] = sk

    if "team_member_slack_ids" in patch and "team_member_slack_ids" not in errors:
        tm = patch["team_member_slack_ids"]
        if isinstance(tm, list) and len(tm) == 0:
            if _may_merge_empty_list(primary_requirement_id, "team_member_slack_ids"):
                validated["team_member_slack_ids"] = []
        elif isinstance(tm, list):
            uids, failed = _fix_subteam_expand(
                bot_token,
                tm,
                manager_slack_user_id=manager_slack_user_id,
                resolution=user_res,
            )
            if failed and not uids:
                errors["team_member_slack_ids"] = "all_unresolvable"
                any_unres = True
            elif uids:
                validated["team_member_slack_ids"] = uids
                if failed:
                    any_unres = True

    if "peer_slack_user_ids" in patch and "peer_slack_user_ids" not in errors:
        pr = patch["peer_slack_user_ids"]
        if isinstance(pr, list) and len(pr) == 0:
            if _may_merge_empty_list(primary_requirement_id, "peer_slack_user_ids"):
                validated["peer_slack_user_ids"] = []
        elif isinstance(pr, list):
            uids, failed = _fix_subteam_expand(
                bot_token,
                pr,
                manager_slack_user_id=manager_slack_user_id,
                resolution=user_res,
            )
            if failed and not uids:
                errors["peer_slack_user_ids"] = "all_unresolvable"
                any_unres = True
            elif uids:
                validated["peer_slack_user_ids"] = uids
                if failed:
                    any_unres = True

    if "reports_to_slack_ids" in patch and "reports_to_slack_ids" not in errors:
        rp = patch["reports_to_slack_ids"]
        if isinstance(rp, list) and len(rp) == 0:
            if _may_merge_empty_list(primary_requirement_id, "reports_to_slack_ids"):
                validated["reports_to_slack_ids"] = []
        elif isinstance(rp, list):
            uids, failed = _fix_subteam_expand(
                bot_token,
                rp,
                manager_slack_user_id=manager_slack_user_id,
                resolution=user_res,
            )
            if failed and not uids:
                errors["reports_to_slack_ids"] = "all_unresolvable"
                any_unres = True
            elif uids:
                validated["reports_to_slack_ids"] = uids
                if failed:
                    any_unres = True

    if "observed_channel_ids" in patch and "observed_channel_ids" not in errors:
        och = patch["observed_channel_ids"]
        if isinstance(och, list) and len(och) == 0:
            if _may_merge_empty_list(primary_requirement_id, "observed_channel_ids"):
                validated["observed_channel_ids"] = []
        elif isinstance(och, list):
            ids, inacc, unres = _resolve_channel_entries(bot_token, och)
            validated["observed_channel_ids"] = ids
            if inacc:
                ch_inacc = True
            if unres and not ids:
                errors["observed_channel_ids"] = "all_unresolvable_or_inaccessible"
            elif unres:
                any_unres = True

    return PatchValidationResult(
        validated_patch=validated,
        field_errors=errors,
        channels_inaccessible=ch_inacc,
        any_entity_unresolved=any_unres,
    )

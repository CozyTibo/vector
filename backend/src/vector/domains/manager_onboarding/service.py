"""Manager Slack onboarding orchestration (DMs + block actions)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vector.domains.manager_onboarding import slack_web_api
from vector.domains.manager_onboarding.constants import (
    ACTION_REPORTS_NO,
    ACTION_REPORTS_YES,
    ACTION_SCOPE_JUST_ME,
    ACTION_SCOPE_OTHER_MGR,
    MAX_MESSAGES_PER_STEP,
    OUTBOUND_INTRO_KEY,
    OUTBOUND_STEP_REPLY_KEY,
    SCOPE_JUST_ME,
    SCOPE_OTHER_MANAGERS,
    STATUS_COMPLETED,
    STATUS_NEEDS_REVIEW,
    STATUS_WAITING_FOR_USER,
    STEP_COMPLETED,
    STEP_ORDER,
    STEP_Q1_SCOPE_INTENT,
    STEP_Q1B_PEER_HANDLES,
    STEP_Q2_TEAM_SCOPE,
    STEP_Q3_TEAM_MEMBERS,
    STEP_Q4_OBSERVED_CHANNELS,
    STEP_Q5_REPORTS_TO,
    STEP_Q5B_REPORTS_WHO,
    STEP_Q6_KPIS,
)
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_onboarding as mo_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo

log = logging.getLogger(__name__)


def slack_outbound_allowed(session: Session, sess: Any) -> bool:
    """False when tenant pauses Slack, disables manager onboarding, or session is muted."""
    t = session.get(Tenant, sess.tenant_id)
    if t is None:
        return False
    if bool(getattr(t, "slack_vector_paused", False)):
        return False
    if bool(getattr(t, "manager_slack_onboarding_disabled", False)):
        return False
    if bool(getattr(sess, "muted", False)):
        return False
    return True

# Q4: user can bail out without channel IDs (reactions are not read — plain text only)
_SKIP_OBSERVED_CHANNELS_RE = re.compile(
    r"^\s*(skip|skipped|done|ok|none|later|pass|n/a|no\s*channels?|nothing|not\s*now)\s*[!.]*\s*$",
    re.IGNORECASE,
)

USER_MENTION_RE = re.compile(r"<@(U[A-Z0-9]+)>")
# Public channels C…, private (incl. converted) G… — capture optional |label for user-facing copy
CHANNEL_MENTION_RE = re.compile(r"<#([CG][A-Z0-9]+)(?:\|([^>]+))?>")


def extract_slack_tokens(text: str) -> tuple[list[str], list[str], str]:
    """Return (user_ids, channel_ids, remainder text with mentions stripped)."""
    uids = USER_MENTION_RE.findall(text or "")
    chan_tuples = CHANNEL_MENTION_RE.findall(text or "")
    cids = list(dict.fromkeys(t[0].strip() for t in chan_tuples if t[0]))
    remainder = USER_MENTION_RE.sub(" ", text or "")
    remainder = CHANNEL_MENTION_RE.sub(" ", remainder)
    remainder = " ".join(remainder.split()).strip()
    return list(dict.fromkeys(uids)), cids, remainder


def channel_mentions_with_labels(text: str) -> tuple[list[str], dict[str, str]]:
    """Channel ids in order, plus id → label from Slack ``<#…|name>`` (for user-facing copy)."""
    ids: list[str] = []
    seen: set[str] = set()
    labels: dict[str, str] = {}
    for m in CHANNEL_MENTION_RE.finditer(text or ""):
        cid = m.group(1).strip()
        lab = (m.group(2) or "").strip()
        if not cid:
            continue
        if cid not in seen:
            seen.add(cid)
            ids.append(cid)
        if lab:
            labels.setdefault(cid, lab)
    return ids, labels


def _human_channel_access_message(failed_ids: list[str], id_to_label: dict[str, str]) -> str:
    """Explain access issues without printing opaque Slack IDs."""
    display: list[str] = []
    for cid in failed_ids:
        lab = id_to_label.get(cid)
        if lab:
            display.append(f"#{lab.lstrip('#')}")
    if display:
        uniq = list(dict.fromkeys(display))
        if len(uniq) == 1:
            target = uniq[0]
        else:
            target = ", ".join(uniq[:-1]) + f", and {uniq[-1]}"
        return (
            f"I couldn’t verify I’m in {target} with the permissions this app has. "
            "If @Vector isn’t in that channel yet, invite the app (e.g. `/invite @Vector` there), "
            "then mention the channel again."
        )
    return (
        "I couldn’t verify access to a channel you mentioned. "
        "Invite @Vector to that channel if needed (`/invite @Vector`), then try again."
    )


def _answers(session_row: Any) -> dict[str, Any]:
    return dict(session_row.answers_json or {})


def _context(session_row: Any) -> dict[str, Any]:
    return dict(session_row.context_json or {})


def _set_answers(session_row: Any, d: dict[str, Any]) -> None:
    session_row.answers_json = d


def _set_context(session_row: Any, d: dict[str, Any]) -> None:
    session_row.context_json = d


_STEP_ANSWER_KEYS: dict[str, tuple[str, ...]] = {
    STEP_Q1_SCOPE_INTENT: ("scope_intent",),
    STEP_Q1B_PEER_HANDLES: ("peer_slack_user_ids",),
    STEP_Q2_TEAM_SCOPE: ("team_scope",),
    STEP_Q3_TEAM_MEMBERS: ("team_member_slack_ids",),
    STEP_Q4_OBSERVED_CHANNELS: (
        "observed_channel_ids",
        "observed_channels_skipped",
        "_pending_channel_ids",
    ),
    STEP_Q5_REPORTS_TO: ("reports_to_yes",),
    STEP_Q5B_REPORTS_WHO: ("reports_to_slack_ids",),
    STEP_Q6_KPIS: ("kpi_expectations",),
}


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


def keys_cleared_when_restarting_from(step: str) -> list[str]:
    steps = [s for s in STEP_ORDER if s != STEP_COMPLETED]
    if step not in steps:
        raise ValueError(f"invalid step: {step!r}")
    i = steps.index(step)
    keys: list[str] = []
    for s in steps[i:]:
        keys.extend(_STEP_ANSWER_KEYS.get(s, ()))
    return keys


def admin_restart_at_step(sess: Any, target_step: str) -> None:
    steps = [s for s in STEP_ORDER if s != STEP_COMPLETED]
    if target_step not in steps:
        raise ValueError("invalid step")
    ans = dict(sess.answers_json or {})
    for k in keys_cleared_when_restarting_from(target_step):
        ans.pop(k, None)
    sess.answers_json = ans
    sess.current_step = target_step
    sess.status = STATUS_WAITING_FOR_USER
    sess.completed_at = None
    sess.error_code = None
    sess.error_detail = None


def admin_merge_answers(sess: Any, patch: dict[str, Any]) -> None:
    sess.answers_json = _deep_merge_dict(dict(sess.answers_json or {}), patch)


def admin_force_complete(sess: Any) -> None:
    sess.status = STATUS_COMPLETED
    sess.current_step = STEP_COMPLETED
    sess.completed_at = datetime.now(UTC)


def admin_mark_needs_review(sess: Any) -> None:
    sess.status = STATUS_NEEDS_REVIEW


def admin_set_session_muted(sess: Any, muted: bool) -> None:
    sess.muted = bool(muted)


def first_unanswered_step(answers: dict[str, Any]) -> str:
    """First step in canonical order that still needs input."""
    scope = answers.get("scope_intent")
    if not scope:
        return STEP_Q1_SCOPE_INTENT
    if scope == SCOPE_OTHER_MANAGERS:
        peers = answers.get("peer_slack_user_ids")
        if not isinstance(peers, list) or len(peers) == 0:
            return STEP_Q1B_PEER_HANDLES
    if not (answers.get("team_scope") or "").strip():
        return STEP_Q2_TEAM_SCOPE
    mem = answers.get("team_member_slack_ids")
    if not isinstance(mem, list) or len(mem) == 0:
        return STEP_Q3_TEAM_MEMBERS
    if answers.get("observed_channels_skipped") is True:
        pass
    else:
        ch = answers.get("observed_channel_ids")
        if not isinstance(ch, list) or len(ch) == 0:
            return STEP_Q4_OBSERVED_CHANNELS
    if answers.get("reports_to_yes") is None:
        return STEP_Q5_REPORTS_TO
    if answers.get("reports_to_yes") is True:
        rpt = answers.get("reports_to_slack_ids")
        if not isinstance(rpt, list) or len(rpt) == 0:
            return STEP_Q5B_REPORTS_WHO
    if answers.get("reports_to_yes") is True:
        if not (answers.get("kpi_expectations") or "").strip():
            return STEP_Q6_KPIS
    return STEP_COMPLETED


def _bump_step_counter(sess: Any, new_step: str) -> None:
    ctx = _context(sess)
    prev = ctx.get("counter_step")
    if prev != new_step:
        ctx["counter_step"] = new_step
        ctx["messages_this_step"] = 0
    _set_context(sess, ctx)


def _inc_messages_this_step(sess: Any) -> int:
    ctx = _context(sess)
    step = sess.current_step
    if ctx.get("counter_step") != step:
        ctx["counter_step"] = step
        ctx["messages_this_step"] = 0
    n = int(ctx.get("messages_this_step") or 0) + 1
    ctx["messages_this_step"] = n
    _set_context(sess, ctx)
    return n


def intro_blocks() -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Hey! Let’s finish a couple quick things so I can start helping your team 🙌\n\n"
                    "Are you setting Vector up just for yourself, or should I help other managers too?"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Just me"},
                    "action_id": ACTION_SCOPE_JUST_ME,
                    "value": SCOPE_JUST_ME,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Other managers"},
                    "action_id": ACTION_SCOPE_OTHER_MGR,
                    "value": SCOPE_OTHER_MANAGERS,
                },
            ],
        },
    ]


def reports_blocks() -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Do you report to anyone?",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Yes"},
                    "action_id": ACTION_REPORTS_YES,
                    "value": "yes",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "No"},
                    "action_id": ACTION_REPORTS_NO,
                    "value": "no",
                },
            ],
        },
    ]


def question_text_for_step(step: str) -> str:
    if step == STEP_Q1B_PEER_HANDLES:
        return (
            "Who else should I set up? Mention them with @ — I’ll DM them a short invite "
            "so we’re aligned."
        )
    if step == STEP_Q2_TEAM_SCOPE:
        return "What’s the scope of your team? (A short phrase is perfect.)"
    if step == STEP_Q3_TEAM_MEMBERS:
        return "Who’s on your team? Mention people with @ or list names."
    if step == STEP_Q4_OBSERVED_CHANNELS:
        return (
            "Which channels should I observe for your team? (e.g. #eng-foo) "
            "Say *skip* if you want to continue without any for now."
        )
    if step == STEP_Q5_REPORTS_TO:
        return "Do you report to anyone?"
    if step == STEP_Q5B_REPORTS_WHO:
        return "Who do you report to? Mention them with @."
    if step == STEP_Q6_KPIS:
        return "What signals or KPIs matter most when you report upward?"
    return "Let’s continue — what else should I know?"


def validate_channels(
    session: Session,
    bot_token: str,
    sess: Any,
    channel_ids: list[str],
) -> tuple[list[str], list[str]]:
    """Return (ok_ids, failed_ids). Persists ManagerOnboardingChannelObservation rows."""
    ok: list[str] = []
    failed: list[str] = []
    for cid in channel_ids:
        cid = (cid or "").strip()
        if not cid:
            continue
        try:
            info = slack_web_api.conversations_info(bot_token, channel=cid)
            ch = info.get("channel") if isinstance(info, dict) else None
            is_member = bool(isinstance(ch, dict) and ch.get("is_member"))
            if is_member:
                mo_repo.upsert_channel_observation(
                    session,
                    session_id=sess.id,
                    tenant_id=sess.tenant_id,
                    slack_channel_id=cid,
                    channel_name=str(ch.get("name") or "") or None,
                    access_status="ok",
                    bot_is_member=True,
                    history_readable=None,
                    validation_error=None,
                )
                ok.append(cid)
                continue
            join_res = slack_web_api.conversations_join(bot_token, channel=cid)
            if join_res.get("ok"):
                mo_repo.upsert_channel_observation(
                    session,
                    session_id=sess.id,
                    tenant_id=sess.tenant_id,
                    slack_channel_id=cid,
                    channel_name=str(ch.get("name") or "") if isinstance(ch, dict) else None,
                    access_status="joined",
                    bot_is_member=True,
                    history_readable=None,
                    validation_error=None,
                )
                ok.append(cid)
            else:
                mo_repo.upsert_channel_observation(
                    session,
                    session_id=sess.id,
                    tenant_id=sess.tenant_id,
                    slack_channel_id=cid,
                    channel_name=None,
                    access_status="pending_invite",
                    bot_is_member=False,
                    history_readable=None,
                    validation_error=str(join_res.get("error")),
                )
                failed.append(cid)
        except Exception as e:
            log.warning("channel validation failed for %s: %s", cid, e)
            mo_repo.upsert_channel_observation(
                session,
                session_id=sess.id,
                tenant_id=sess.tenant_id,
                slack_channel_id=cid,
                channel_name=None,
                access_status="no_access",
                bot_is_member=False,
                history_readable=None,
                validation_error=str(e),
            )
            failed.append(cid)
    return ok, failed


def merge_deterministic_multi_step(sess: Any, text: str) -> None:
    """Fill answers from tokens + remainder (conservative on channels until Q4)."""
    users, channels, remainder = extract_slack_tokens(text)
    answers = _answers(sess)
    step = sess.current_step

    if users and step in (
        STEP_Q1B_PEER_HANDLES,
        STEP_Q3_TEAM_MEMBERS,
        STEP_Q5B_REPORTS_WHO,
    ):
        if step == STEP_Q1B_PEER_HANDLES:
            cur = list(answers.get("peer_slack_user_ids") or [])
            for u in users:
                if u not in cur:
                    cur.append(u)
            answers["peer_slack_user_ids"] = cur
        elif step == STEP_Q3_TEAM_MEMBERS:
            cur = list(answers.get("team_member_slack_ids") or [])
            for u in users:
                if u not in cur:
                    cur.append(u)
            answers["team_member_slack_ids"] = cur
        elif step == STEP_Q5B_REPORTS_WHO:
            cur = list(answers.get("reports_to_slack_ids") or [])
            for u in users:
                if u not in cur:
                    cur.append(u)
            answers["reports_to_slack_ids"] = cur

    if remainder and step == STEP_Q2_TEAM_SCOPE:
        if not (answers.get("team_scope") or "").strip():
            answers["team_scope"] = remainder
    if remainder and step == STEP_Q6_KPIS:
        if not (answers.get("kpi_expectations") or "").strip():
            answers["kpi_expectations"] = remainder

    # Safe early fill: members from NL message while on Q2 if mentions present
    if users and step == STEP_Q2_TEAM_SCOPE:
        cur = list(answers.get("team_member_slack_ids") or [])
        for u in users:
            if u not in cur:
                cur.append(u)
        answers["team_member_slack_ids"] = cur

    # Channels: only persist into answers when we're at or past Q4 intent
    if channels and step in (STEP_Q4_OBSERVED_CHANNELS, STEP_Q2_TEAM_SCOPE, STEP_Q3_TEAM_MEMBERS):
        if step == STEP_Q4_OBSERVED_CHANNELS:
            pass  # handled in apply_text_turn with validation
        else:
            # conservative: stash candidates only
            cur = list(answers.get("_pending_channel_ids") or [])
            for c in channels:
                if c not in cur:
                    cur.append(c)
            answers["_pending_channel_ids"] = cur

    _set_answers(sess, answers)


def apply_text_turn(
    session: Session,
    bot_token: str,
    sess: Any,
    *,
    text: str,
    slack_channel_id: str,
) -> None:
    """Apply free-text / mentions for the current step; advance; send next prompt."""
    if sess.status == STATUS_COMPLETED:
        return
    n = _inc_messages_this_step(sess)
    if n > MAX_MESSAGES_PER_STEP:
        ctx = _context(sess)
        ctx["watchdog_tripped"] = True
        _set_context(sess, ctx)
        sess.status = STATUS_NEEDS_REVIEW
        _send_dm(
            session,
            bot_token,
            sess,
            slack_channel_id,
            "I’ll save this for now — you can tweak it later if needed 👍",
            idempotency_suffix=f"watchdog-{sess.version}",
        )
        sess.current_step = first_unanswered_step(_answers(sess))
        _bump_step_counter(sess, sess.current_step)
        sess.version = int(sess.version) + 1
        return

    merge_deterministic_multi_step(sess, text)
    answers = _answers(sess)

    if sess.current_step == STEP_Q4_OBSERVED_CHANNELS:
        channels, mention_labels = channel_mentions_with_labels(text)
        pending = list(answers.get("_pending_channel_ids") or [])
        for c in channels:
            if c not in pending:
                pending.append(c)
        if pending:
            ok, failed = validate_channels(session, bot_token, sess, pending)
            answers["observed_channel_ids"] = ok
            answers["_pending_channel_ids"] = []
            if ok:
                answers.pop("observed_channels_skipped", None)
            _set_answers(sess, answers)
            if failed:
                msg = _human_channel_access_message(failed, mention_labels)
                _send_dm(
                    session,
                    bot_token,
                    sess,
                    slack_channel_id,
                    msg,
                    idempotency_suffix="ch-warn",
                )
                _send_dm(
                    session,
                    bot_token,
                    sess,
                    slack_channel_id,
                    "When it’s fixed, mention the channel again (e.g. #general), "
                    "or say *skip* to continue without channels for now.",
                    idempotency_suffix="q4-after-warn-hint",
                )
        elif _SKIP_OBSERVED_CHANNELS_RE.match((text or "").strip()):
            answers["observed_channels_skipped"] = True
            answers["observed_channel_ids"] = []
            answers["_pending_channel_ids"] = []
            _set_answers(sess, answers)
            _send_dm(
                session,
                bot_token,
                sess,
                slack_channel_id,
                "No problem — we can add or change channels later. Next question:",
                idempotency_suffix="q4-skip-ack",
            )

    next_step = first_unanswered_step(_answers(sess))
    sess.current_step = next_step
    _bump_step_counter(sess, next_step)
    if next_step == STEP_COMPLETED:
        sess.status = STATUS_COMPLETED
        sess.completed_at = datetime.now(UTC)
        _send_dm(
            session,
            bot_token,
            sess,
            slack_channel_id,
            "That’s everything I need for now — thanks! I’ll start from here and we can refine anytime.",
            idempotency_suffix="done",
        )
    else:
        _send_step_prompt(session, bot_token, sess, slack_channel_id, next_step)
    sess.version = int(sess.version) + 1
    sess.status = STATUS_WAITING_FOR_USER


def apply_scope_button(
    session: Session,
    bot_token: str,
    sess: Any,
    *,
    value: str,
    slack_channel_id: str,
) -> None:
    if sess.current_step != STEP_Q1_SCOPE_INTENT:
        return
    answers = _answers(sess)
    if value == SCOPE_JUST_ME:
        answers["scope_intent"] = SCOPE_JUST_ME
        ack = "Got it — I’ll set this up for just you."
    elif value == SCOPE_OTHER_MANAGERS:
        answers["scope_intent"] = SCOPE_OTHER_MANAGERS
        ack = "Great — we’ll bring in your other managers next."
    else:
        return
    _set_answers(sess, answers)
    next_step = first_unanswered_step(answers)
    sess.current_step = next_step
    _bump_step_counter(sess, next_step)
    sess.version = int(sess.version) + 1
    sess.status = STATUS_WAITING_FOR_USER
    _send_dm(
        session,
        bot_token,
        sess,
        slack_channel_id,
        ack,
        idempotency_suffix="ack-scope",
    )
    _send_step_prompt(session, bot_token, sess, slack_channel_id, next_step)


def apply_reports_button(
    session: Session,
    bot_token: str,
    sess: Any,
    *,
    value: str,
    slack_channel_id: str,
) -> None:
    if sess.current_step != STEP_Q5_REPORTS_TO:
        return
    answers = _answers(sess)
    if value == "yes":
        answers["reports_to_yes"] = True
        ack = "Thanks — noted."
    elif value == "no":
        answers["reports_to_yes"] = False
        answers["reports_to_slack_ids"] = []
        answers.setdefault("kpi_expectations", "")
        ack = "Got it — thanks for letting me know."
    else:
        return
    _set_answers(sess, answers)
    next_step = first_unanswered_step(answers)
    sess.current_step = next_step
    _bump_step_counter(sess, next_step)
    sess.version = int(sess.version) + 1
    sess.status = STATUS_WAITING_FOR_USER
    if next_step == STEP_COMPLETED:
        sess.status = STATUS_COMPLETED
        sess.completed_at = datetime.now(UTC)
        _send_dm(
            session,
            bot_token,
            sess,
            slack_channel_id,
            "All set on my side — talk soon.",
            idempotency_suffix="done",
        )
        return
    _send_dm(
        session,
        bot_token,
        sess,
        slack_channel_id,
        ack,
        idempotency_suffix="ack-reports",
    )
    _send_step_prompt(session, bot_token, sess, slack_channel_id, next_step)


def _send_step_prompt(
    session: Session,
    bot_token: str,
    sess: Any,
    slack_channel_id: str,
    step: str,
) -> None:
    if not slack_outbound_allowed(session, sess):
        log.info("Skip manager onboarding outbound (policy) session=%s", sess.id)
        return
    if step == STEP_Q5_REPORTS_TO:
        slack_web_api.chat_post_message(
            bot_token,
            channel=slack_channel_id,
            text="Do you report to anyone?",
            blocks=reports_blocks(),
        )
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="outbound",
            role="assistant",
            text="[Do you report to anyone? + buttons]",
            slack_channel_id=slack_channel_id,
            outbound_idempotency_key=f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:q5",
        )
        return
    if step == STEP_Q5B_REPORTS_WHO:
        _send_dm(
            session,
            bot_token,
            sess,
            slack_channel_id,
            "Who do you report to? Mention them with @.",
            idempotency_suffix="q5b-who",
        )
        return
    body = question_text_for_step(step)
    _send_dm(
        session,
        bot_token,
        sess,
        slack_channel_id,
        body,
        idempotency_suffix=f"step-{step}",
    )


def _send_dm(
    session: Session,
    bot_token: str,
    sess: Any,
    channel: str,
    text: str,
    *,
    idempotency_suffix: str,
    blocks: list[dict[str, Any]] | None = None,
) -> None:
    if not slack_outbound_allowed(session, sess):
        log.info("Skip manager onboarding DM (policy) session=%s", sess.id)
        return
    key = f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:{idempotency_suffix}"
    if mo_repo.get_outbound_by_idempotency_key(session, key):
        return
    data = slack_web_api.chat_post_message(
        bot_token,
        channel=channel,
        text=text,
        blocks=blocks,
    )
    ts = str(data.get("ts") or "")
    mo_repo.append_message(
        session,
        session_id=sess.id,
        direction="outbound",
        role="assistant",
        text=text,
        slack_channel_id=channel,
        slack_ts=ts,
        outbound_idempotency_key=key,
    )


def send_intro_message(session: Session, bot_token: str, sess: Any) -> None:
    """Post intro + Q1 buttons if not already sent (idempotent)."""
    if not slack_outbound_allowed(session, sess):
        return
    ctx = _context(sess)
    if ctx.get("intro_sent"):
        return
    key = f"{OUTBOUND_INTRO_KEY}:{sess.id}"
    if mo_repo.get_outbound_by_idempotency_key(session, key):
        ctx["intro_sent"] = True
        _set_context(sess, ctx)
        return
    channel = sess.slack_user_id
    data = slack_web_api.chat_post_message(
        bot_token,
        channel=channel,
        text="Let’s finish setup for Vector.",
        blocks=intro_blocks(),
    )
    ts = str(data.get("ts") or "")
    mo_repo.append_message(
        session,
        session_id=sess.id,
        direction="outbound",
        role="assistant",
        text="[Intro + scope question]",
        slack_channel_id=channel,
        slack_ts=ts,
        outbound_idempotency_key=key,
    )
    ctx["intro_sent"] = True
    _set_context(sess, ctx)
    sess.status = STATUS_WAITING_FOR_USER


def get_or_create_session(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    slack_team_id: str,
    slack_user_id: str,
) -> Any:
    existing = mo_repo.get_session_for_tenant_slack_user(
        session,
        tenant_id=tenant_id,
        slack_user_id=slack_user_id,
    )
    if existing is not None:
        return existing
    try:
        return mo_repo.create_session(
            session,
            tenant_id=tenant_id,
            slack_team_id=slack_team_id,
            slack_user_id=slack_user_id,
            initial_step=STEP_Q1_SCOPE_INTENT,
            status=STATUS_WAITING_FOR_USER,
        )
    except IntegrityError:
        session.rollback()
        return mo_repo.get_session_for_tenant_slack_user(
            session,
            tenant_id=tenant_id,
            slack_user_id=slack_user_id,
        )


def process_slack_message_event(
    session: Session,
    *,
    team_id: str,
    slack_user_id: str,
    text: str,
    channel_id: str,
    slack_event_id: str | None,
    bot_token: str,
) -> None:
    """Handle a user message in a DM (or thread — channel_id is conversation)."""
    link = slack_repo.get_slack_connection_by_team_id(session, team_id)
    if link is None:
        log.warning("manager_onboarding: no slack link for team_id=%s", team_id)
        return
    tenant_id = link.tenant_id
    if slack_event_id and not mo_repo.try_claim_slack_event(session, slack_event_id):
        return
    sess = get_or_create_session(
        session,
        tenant_id=tenant_id,
        slack_team_id=team_id,
        slack_user_id=slack_user_id,
    )
    if slack_event_id:
        try:
            with session.begin_nested():
                mo_repo.append_message(
                    session,
                    session_id=sess.id,
                    direction="inbound",
                    role="user",
                    text=text or "",
                    slack_channel_id=channel_id,
                    slack_event_id=slack_event_id,
                )
        except IntegrityError:
            return
    else:
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="inbound",
            role="user",
            text=text or "",
            slack_channel_id=channel_id,
            slack_event_id=None,
        )
    send_intro_message(session, bot_token, sess)
    if not (text or "").strip():
        session.flush()
        return
    apply_text_turn(session, bot_token, sess, text=text.strip(), slack_channel_id=sess.slack_user_id)


def process_slack_block_action(
    session: Session,
    *,
    team_id: str,
    slack_user_id: str,
    channel_id: str,
    action_id: str,
    action_value: str,
    bot_token: str,
) -> None:
    link = slack_repo.get_slack_connection_by_team_id(session, team_id)
    if link is None:
        return
    sess = get_or_create_session(
        session,
        tenant_id=link.tenant_id,
        slack_team_id=team_id,
        slack_user_id=slack_user_id,
    )
    send_intro_message(session, bot_token, sess)
    if action_id in (ACTION_SCOPE_JUST_ME, ACTION_SCOPE_OTHER_MGR):
        apply_scope_button(session, bot_token, sess, value=action_value, slack_channel_id=channel_id)
    elif action_id in (ACTION_REPORTS_YES, ACTION_REPORTS_NO):
        apply_reports_button(session, bot_token, sess, value=action_value, slack_channel_id=channel_id)


def run_send_intro_task(*, tenant_id: uuid.UUID, slack_user_id: str) -> None:
    """Celery entry: open session + intro for primary manager after website handoff."""
    from vector.infrastructure.db.session import session_scope
    from vector.settings import get_settings

    settings = get_settings()
    if not settings.manager_slack_onboarding_enabled:
        return
    for session in session_scope():
        t = session.get(Tenant, tenant_id)
        if t is not None and (
            bool(getattr(t, "slack_vector_paused", False))
            or bool(getattr(t, "manager_slack_onboarding_disabled", False))
        ):
            return
        link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
        if link is None:
            return
        tok = link.detail.bot_access_token
        team_id = link.detail.team_id
        sess = get_or_create_session(
            session,
            tenant_id=tenant_id,
            slack_team_id=team_id,
            slack_user_id=slack_user_id,
        )
        send_intro_message(session, tok, sess)
        session.commit()


def admin_retry_slack_prompt(session: Session, bot_token: str, sess: Any) -> dict[str, Any]:
    """Operator-triggered resend; always uses a fresh idempotency key."""
    import uuid as _uuid

    if not slack_outbound_allowed(session, sess):
        return {"ok": False, "error": "outbound_blocked_by_policy"}
    ch = sess.slack_user_id
    suffix = f"admin-{_uuid.uuid4().hex[:12]}"
    step = sess.current_step
    if step == STEP_Q1_SCOPE_INTENT:
        data = slack_web_api.chat_post_message(
            bot_token,
            channel=ch,
            text="Let’s finish setup for Vector.",
            blocks=intro_blocks(),
        )
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="outbound",
            role="assistant",
            text="[Intro + scope question — admin retry]",
            slack_channel_id=ch,
            slack_ts=str(data.get("ts") or ""),
            outbound_idempotency_key=f"{OUTBOUND_INTRO_KEY}:{sess.id}:{suffix}",
        )
        return {"ok": True, "ts": data.get("ts")}
    if step == STEP_Q5_REPORTS_TO:
        data = slack_web_api.chat_post_message(
            bot_token,
            channel=ch,
            text="Do you report to anyone?",
            blocks=reports_blocks(),
        )
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="outbound",
            role="assistant",
            text="[Reports question — admin retry]",
            slack_channel_id=ch,
            slack_ts=str(data.get("ts") or ""),
            outbound_idempotency_key=f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:{suffix}",
        )
        return {"ok": True, "ts": data.get("ts")}
    body = question_text_for_step(step)
    data = slack_web_api.chat_post_message(bot_token, channel=ch, text=body)
    mo_repo.append_message(
        session,
        session_id=sess.id,
        direction="outbound",
        role="assistant",
        text=body,
        slack_channel_id=ch,
        slack_ts=str(data.get("ts") or ""),
        outbound_idempotency_key=f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:{suffix}",
    )
    return {"ok": True, "ts": data.get("ts")}

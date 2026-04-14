"""Manager Slack onboarding — DB, admin, and DM engine (LLM + validate + merge)."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vector.domains.manager_onboarding.constants import (
    SCOPE_JUST_ME,
    SCOPE_OTHER_MANAGERS,
    STATUS_COMPLETED,
    STATUS_NEEDS_REVIEW,
    STATUS_WAITING_FOR_USER,
    OUTBOUND_INTRO_KEY,
    OUTBOUND_STEP_REPLY_KEY,
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
from vector.domains.manager_onboarding.engine import requirements as eng_req
from vector.domains.manager_onboarding import slack_web_api
from vector.domains.manager_onboarding.engine.messages import intro_dm_text
from vector.domains.manager_onboarding.engine.prompts import build_reply_channel_user_prompt
from vector.domains.manager_onboarding.engine.reply_context import format_recent_messages_transcript
from vector.domains.manager_onboarding.engine.slack_text import normalize_manager_onboarding_outbound
from vector.domains.manager_onboarding.engine.turn import run_engine_turn
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.repositories import manager_onboarding as mo_repo
from vector.infrastructure.db.repositories import onboarding as ob_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.settings import get_settings

log = logging.getLogger("app")


def slack_outbound_allowed(session: Session, sess: Any) -> bool:
    """False when tenant pauses Slack or session is muted (admin / future outbound)."""
    t = session.get(Tenant, sess.tenant_id)
    if t is None:
        return False
    if bool(getattr(t, "slack_vector_paused", False)):
        return False
    if bool(getattr(sess, "muted", False)):
        return False
    return True


def _answers(session_row: Any) -> dict[str, Any]:
    return dict(session_row.answers_json or {})


def _context(session_row: Any) -> dict[str, Any]:
    return dict(session_row.context_json or {})


def _rolling_summary_from_context(ctx: dict[str, Any]) -> str:
    s = (ctx.get("onboarding_conversation_summary") or "").strip()
    if not s:
        s = (ctx.get("conversation_summary") or "").strip()
    return s


def _reply_user_prompt_for_turn(
    session: Session,
    sess: Any,
    *,
    user_line: str,
    ctx_before: dict[str, Any],
) -> str:
    """Recent DM transcript + rolling summary for the reply LLM (interpret still uses latest line only)."""
    rows = mo_repo.list_messages_chronological(session, sess.id, limit=80)
    recent = format_recent_messages_transcript(rows, current_user_text=user_line, max_messages=5)
    return build_reply_channel_user_prompt(
        recent_transcript=recent,
        summary=_rolling_summary_from_context(ctx_before),
    )


def _set_context(session_row: Any, d: dict[str, Any]) -> None:
    session_row.context_json = d


def _deep_merge_dict(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge_dict(out[k], v)
        else:
            out[k] = v
    return out


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


def keys_cleared_when_restarting_from(step: str) -> list[str]:
    steps = [s for s in STEP_ORDER if s != STEP_COMPLETED]
    if step not in steps:
        raise ValueError(f"invalid step: {step!r}")
    i = steps.index(step)
    keys: list[str] = []
    for s in steps[i:]:
        keys.extend(_STEP_ANSWER_KEYS.get(s, ()))
    return keys


def first_unanswered_step(answers: dict[str, Any]) -> str:
    """Derive current step from ``answers_json`` (same ordering as before; for admin UI)."""
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
    if answers.get("observed_channels_skipped") is not True:
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


def reconcile_needs_review_if_manager_flow_complete(sess: Any) -> bool:
    if sess.status != STATUS_NEEDS_REVIEW:
        return False
    if sess.current_step != STEP_COMPLETED:
        return False
    if first_unanswered_step(dict(sess.answers_json or {})) != STEP_COMPLETED:
        return False
    sess.status = STATUS_COMPLETED
    if sess.completed_at is None:
        sess.completed_at = datetime.now(UTC)
    sess.version = int(sess.version) + 1
    return True


def admin_set_session_muted(sess: Any, muted: bool) -> None:
    sess.muted = bool(muted)


def admin_wipe_session_restart(db: Session, sess: Any) -> None:
    sid = sess.id
    mo_repo.delete_messages_for_session(db, sid)
    mo_repo.delete_channel_observations_for_session(db, sid)
    mo_repo.delete_parse_artifacts_for_session(db, sid)
    sess.answers_json = {}
    sess.context_json = {}
    sess.current_step = STEP_Q1_SCOPE_INTENT
    sess.status = STATUS_WAITING_FOR_USER
    sess.error_code = None
    sess.error_detail = None
    sess.completed_at = None
    sess.version = int(sess.version) + 1


def _suffix_with_inbound(base: str, inbound_idempotency_key: str | None) -> str:
    k = (inbound_idempotency_key or "").strip()
    if not k:
        return base
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", k)[:96]
    return f"{base}-{safe}"


def _ensure_intro_context_from_onboarding(session: Session, tenant_id: uuid.UUID, sess: Any) -> None:
    """Load web onboarding answers so the first Slack DM reads as a continuation, not a cold start."""
    ctx = _context(sess)
    row = ob_repo.get_onboarding_for_tenant(session, tenant_id)
    if row is None:
        _set_context(sess, ctx)
        return
    answers = dict(row.answers_json or {})
    prof = answers.get("profile") if isinstance(answers.get("profile"), dict) else {}
    comp = answers.get("company") if isinstance(answers.get("company"), dict) else {}
    if isinstance(prof.get("name"), str) and prof["name"].strip():
        ctx["intro_greeting_name"] = prof["name"].strip()
    if isinstance(comp.get("name"), str) and comp["name"].strip():
        ctx["intro_company_name"] = comp["name"].strip()
    if isinstance(prof.get("role"), str) and prof["role"].strip():
        ctx["intro_role"] = prof["role"].strip()
    ctx["intro_web_handoff"] = True
    ctx["intro_context_enriched"] = True
    _set_context(sess, ctx)


def send_intro_message(session: Session, bot_token: str, sess: Any) -> None:
    """First DM for a session (static intro, idempotent)."""
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
    tid = getattr(sess, "tenant_id", None)
    if tid is not None:
        _ensure_intro_context_from_onboarding(session, tid, sess)
        ctx = _context(sess)
    intro_body = normalize_manager_onboarding_outbound(intro_dm_text(context=ctx))
    channel = sess.slack_user_id
    data = slack_web_api.chat_post_message(
        bot_token,
        channel=channel,
        text=intro_body,
    )
    ts = str(data.get("ts") or "")
    mo_repo.append_message(
        session,
        session_id=sess.id,
        direction="outbound",
        role="assistant",
        text=intro_body,
        slack_channel_id=channel,
        slack_ts=ts,
        outbound_idempotency_key=key,
    )
    ctx["intro_sent"] = True
    ctx["last_assistant_lead_in"] = intro_body[:240]
    _set_context(sess, ctx)
    sess.status = STATUS_WAITING_FOR_USER


def _reset_messages_counter_for_step(sess: Any, step: str) -> None:
    ctx = _context(sess)
    ctx["counter_step"] = step
    ctx["messages_this_step"] = 0
    _set_context(sess, ctx)


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
    message_ts: str | None = None,
) -> None:
    """Persist inbound DM, optional intro, then engine turn + outbound."""
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
    ts = (message_ts or "").strip() or None
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
                    slack_ts=ts,
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
            slack_ts=ts,
            slack_event_id=None,
        )

    send_intro_message(session, bot_token, sess)

    if sess.status == STATUS_COMPLETED:
        return
    if not slack_outbound_allowed(session, sess):
        return

    user_line = (text or "").strip()
    if not user_line:
        return

    answers_before = _answers(sess)
    if not eng_req.missing_requirements(answers_before):
        sess.current_step = STEP_COMPLETED
        if sess.status != STATUS_COMPLETED:
            sess.status = STATUS_COMPLETED
            sess.completed_at = datetime.now(UTC)
        sess.version = int(sess.version) + 1
        return

    cfg = get_settings()
    ctx_before = _context(sess)
    primary_before = eng_req.primary_requirement(answers_before)
    reply_user_prompt = _reply_user_prompt_for_turn(
        session, sess, user_line=user_line, ctx_before=ctx_before
    )

    turn = run_engine_turn(
        user_text=user_line,
        answers_before=answers_before,
        context_before=ctx_before,
        bot_token=bot_token,
        manager_slack_user_id=(slack_user_id or "").strip(),
        settings=cfg,
        reply_user_prompt=reply_user_prompt,
    )

    out = normalize_manager_onboarding_outbound(turn.outbound_text)
    ctx_after = dict(turn.context_after or {})
    ctx_after["last_assistant_lead_in"] = out[:240]
    sess.answers_json = turn.answers_after
    _set_context(sess, ctx_after)
    if turn.session_completed:
        sess.status = STATUS_COMPLETED
        sess.current_step = STEP_COMPLETED
        sess.completed_at = datetime.now(UTC)
    else:
        sess.status = STATUS_WAITING_FOR_USER
        sess.current_step = first_unanswered_step(turn.answers_after)
    sess.version = int(sess.version) + 1

    ib_key = ((slack_event_id or "").strip() or ts or uuid.uuid4().hex)
    artifact_payload: dict[str, Any] = {
        "user_message": user_line,
        "llm_patch": turn.raw_llm_patch,
        "validated_patch": turn.validated_patch,
        "field_validation_errors": turn.field_validation_errors,
        "merged_state_diff": turn.merged_diff,
        "assistant_message": out,
        "primary_requirement": primary_before,
        "session_completed": turn.session_completed,
        "llm_error": turn.llm_error,
        "reply_llm_error": turn.reply_llm_error,
        "interpret_llm_model": turn.interpret_llm_model,
        "reply_llm_model": turn.reply_llm_model,
    }
    mo_repo.append_parse_artifact(
        session,
        session_id=sess.id,
        trigger="engine_turn",
        input_text=user_line[:8000],
        structured_output_json=artifact_payload,
        model=turn.reply_llm_model or turn.interpret_llm_model,
        error=turn.llm_error or turn.reply_llm_error,
    )

    out_key = f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:{_suffix_with_inbound('reply', ib_key)}"
    if mo_repo.get_outbound_by_idempotency_key(session, out_key):
        return
    try:
        data = slack_web_api.chat_post_message(
            bot_token,
            channel=sess.slack_user_id,
            text=out,
        )
        out_ts = str(data.get("ts") or "")
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="outbound",
            role="assistant",
            text=out,
            slack_channel_id=sess.slack_user_id,
            slack_ts=out_ts,
            outbound_idempotency_key=out_key,
        )
    except Exception as e:
        log.exception("manager_onboarding outbound failed session=%s", sess.id)
        mo_repo.append_parse_artifact(
            session,
            session_id=sess.id,
            trigger="engine_outbound_error",
            input_text=user_line[:2000],
            structured_output_json={"error": str(e), "outbound": out[:2000]},
            error=str(e),
        )


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
    """Treat block action as a synthetic user line so the same engine runs."""
    synthetic = f"[Button {action_id}={action_value}]"
    process_slack_message_event(
        session,
        team_id=team_id,
        slack_user_id=slack_user_id,
        text=synthetic,
        channel_id=channel_id,
        slack_event_id=None,
        bot_token=bot_token,
        message_ts=None,
    )


def run_send_intro_task(*, tenant_id: uuid.UUID, slack_user_id: str) -> None:
    """Website handoff: open session and send static intro when feature flag is on."""
    from vector.infrastructure.db.session import session_scope

    settings = get_settings()
    if not settings.manager_slack_onboarding_enabled:
        return
    for session in session_scope():
        t = session.get(Tenant, tenant_id)
        if t is not None and bool(getattr(t, "slack_vector_paused", False)):
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
    """
    Operator resend after wipe or mid-flow.

    - If intro has not been sent yet: post static intro (same as first DM).
    - Otherwise: run one engine turn with a synthetic resume line and post the assistant reply.
    """
    if not slack_outbound_allowed(session, sess):
        return {"ok": False, "error": "outbound_blocked_by_policy"}
    if sess.status == STATUS_COMPLETED:
        return {"ok": False, "error": "session_already_completed"}

    ctx_before = _context(sess)
    had_intro = bool(ctx_before.get("intro_sent"))

    send_intro_message(session, bot_token, sess)

    if not had_intro and _context(sess).get("intro_sent"):
        return {"ok": True, "kind": "intro"}

    if not eng_req.missing_requirements(_answers(sess)):
        return {"ok": True, "kind": "noop", "detail": "nothing_missing"}

    cfg = get_settings()
    resume_line = "[Operator: resend the current onboarding question.]"
    answers_before = _answers(sess)
    ctx0 = _context(sess)
    primary_before = eng_req.primary_requirement(answers_before)
    reply_user_prompt = _reply_user_prompt_for_turn(
        session, sess, user_line=resume_line, ctx_before=ctx0
    )

    turn = run_engine_turn(
        user_text=resume_line,
        answers_before=answers_before,
        context_before=ctx0,
        bot_token=bot_token,
        manager_slack_user_id=(getattr(sess, "slack_user_id", "") or "").strip(),
        settings=cfg,
        reply_user_prompt=reply_user_prompt,
    )

    out = normalize_manager_onboarding_outbound(turn.outbound_text)
    ctx_after = dict(turn.context_after or {})
    ctx_after["last_assistant_lead_in"] = out[:240]
    sess.answers_json = turn.answers_after
    _set_context(sess, ctx_after)
    if turn.session_completed:
        sess.status = STATUS_COMPLETED
        sess.current_step = STEP_COMPLETED
        sess.completed_at = datetime.now(UTC)
    else:
        sess.status = STATUS_WAITING_FOR_USER
        sess.current_step = first_unanswered_step(turn.answers_after)
    sess.version = int(sess.version) + 1

    suffix = f"admin-{uuid.uuid4().hex[:12]}"
    artifact_payload: dict[str, Any] = {
        "user_message": resume_line,
        "llm_patch": turn.raw_llm_patch,
        "validated_patch": turn.validated_patch,
        "field_validation_errors": turn.field_validation_errors,
        "merged_state_diff": turn.merged_diff,
        "assistant_message": out,
        "primary_requirement": primary_before,
        "session_completed": turn.session_completed,
        "llm_error": turn.llm_error,
        "reply_llm_error": turn.reply_llm_error,
        "interpret_llm_model": turn.interpret_llm_model,
        "reply_llm_model": turn.reply_llm_model,
        "trigger": "admin_retry_slack_prompt",
    }
    mo_repo.append_parse_artifact(
        session,
        session_id=sess.id,
        trigger="admin_retry",
        input_text=resume_line[:8000],
        structured_output_json=artifact_payload,
        model=turn.reply_llm_model or turn.interpret_llm_model,
        error=turn.llm_error or turn.reply_llm_error,
    )

    out_key = f"{OUTBOUND_STEP_REPLY_KEY}:{sess.id}:{suffix}"
    if mo_repo.get_outbound_by_idempotency_key(session, out_key):
        return {"ok": True, "kind": "engine", "deduped": True}
    try:
        data = slack_web_api.chat_post_message(
            bot_token,
            channel=sess.slack_user_id,
            text=out,
        )
        out_ts = str(data.get("ts") or "")
        mo_repo.append_message(
            session,
            session_id=sess.id,
            direction="outbound",
            role="assistant",
            text=out,
            slack_channel_id=sess.slack_user_id,
            slack_ts=out_ts,
            outbound_idempotency_key=out_key,
        )
        return {"ok": True, "kind": "engine", "ts": data.get("ts")}
    except Exception as e:
        log.exception("admin_retry_slack_prompt outbound failed session=%s", sess.id)
        return {"ok": False, "error": str(e)}


def admin_apply_recompute_current_step(
    session: Session,
    sess: Any,
    *,
    bot_token: str | None,
) -> dict[str, Any]:
    """Re-sync ``current_step`` from ``answers_json``; optionally resend intro or next question in Slack."""
    step = first_unanswered_step(dict(sess.answers_json or {}))
    sess.current_step = step
    if step == STEP_COMPLETED:
        sess.status = STATUS_COMPLETED
        if sess.completed_at is None:
            sess.completed_at = datetime.now(UTC)
        _reset_messages_counter_for_step(sess, step)
        sess.version = int(sess.version) + 1
        return {"current_step": step, "slack": None}
    sess.status = STATUS_WAITING_FOR_USER
    sess.completed_at = None
    _reset_messages_counter_for_step(sess, step)
    sess.version = int(sess.version) + 1
    if not bot_token:
        return {"current_step": step, "slack": {"ok": False, "error": "no_slack_connection"}}
    try:
        slack_out = admin_retry_slack_prompt(session, bot_token, sess)
    except Exception as e:
        log.exception("admin recompute: Slack resend failed session=%s", sess.id)
        return {"current_step": step, "slack": {"ok": False, "error": str(e)}}
    return {"current_step": step, "slack": slack_out}

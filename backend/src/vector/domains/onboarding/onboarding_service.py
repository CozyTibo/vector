"""Onboarding orchestration: state machine + persistence + LLM phrasing."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.contracts.onboarding import OnboardingChatRequest, OnboardingChatResponse
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import (
    PROFILE_PHASE_CONNECTORS_INTRO,
    PROFILE_PHASE_NAME,
    PROFILE_PHASE_TOOLS,
    STATUS_COMPLETED,
    STEP_CHAT_PROFILE,
)
from vector.domains.onboarding.onboarding_flow import _default_profile_phase, handle_turn
from vector.domains.onboarding.onboarding_llm import generate_onboarding_reply
from vector.infrastructure.db.repositories import onboarding as ob_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings, get_settings


def _denormalize_profile_to_user(
    session: Session, user_id: uuid.UUID, answers: dict[str, Any]
) -> None:
    prof = answers.get("profile")
    if not isinstance(prof, dict):
        return
    raw = prof.get("name")
    if not isinstance(raw, str):
        return
    name = raw.strip()
    if not name:
        return
    user = tenancy_repo.get_user_by_id(session, user_id)
    if user is None:
        return
    user.full_name = name


def _denormalize_company_to_tenant(
    session: Session, tenant_id: uuid.UUID, answers: dict[str, Any]
) -> None:
    comp = answers.get("company")
    if not isinstance(comp, dict):
        return
    raw = comp.get("name")
    if not isinstance(raw, str):
        return
    name = raw.strip()
    if not name:
        return
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        return
    tenant.company_name = name


def _user_turn_content(user_text: str | None, structured: dict[str, Any] | None) -> str | None:
    if user_text is not None and user_text.strip():
        return user_text.strip()
    if structured:
        # Persist readable chat lines for structured-only turns (UI message is null).
        if structured.get("type") == "connectors_intro_ready":
            return "I'm ready to choose tools"
        return json.dumps(structured, default=str)
    return None


def _append_chat_turn(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    user_text: str | None,
    structured: dict[str, Any] | None,
    assistant_segments: list[str],
) -> None:
    if not ob_repo.onboarding_messages_table_exists(session):
        return
    logged = _user_turn_content(user_text, structured)
    if logged:
        ob_repo.append_onboarding_message(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role="user",
            content=logged,
        )
    for seg in assistant_segments:
        t = seg.strip()
        if t:
            ob_repo.append_onboarding_message(
                session,
                tenant_id=tenant_id,
                user_id=user_id,
                role="vector",
                content=t,
            )


def _last_vector_message_content(session: Session, tenant_id: uuid.UUID) -> str | None:
    if not ob_repo.onboarding_messages_table_exists(session):
        return None
    rows = ob_repo.list_onboarding_messages_chronological(session, tenant_id, limit=200)
    for r in reversed(rows):
        if r.role == "vector":
            return r.content
    return None


def _fallback_idle_assistant_text(profile_phase: str) -> str:
    """When DB has no vector rows yet (empty POST past the name phase should not happen often)."""
    if profile_phase == PROFILE_PHASE_TOOLS:
        return (
            "Use the list below to share which tools your organization uses so we can understand "
            "how to help. Then confirm your selection."
        )
    if profile_phase == PROFILE_PHASE_CONNECTORS_INTRO:
        return (
            "Vector uses integrations for execution signals, not to warehouse your code or Slack "
            "chats. Ask anything that helps you feel comfortable, then use the **I'm ready to choose "
            "tools** tag in the chat when you want to continue."
        )
    return "Continue from where you left off."


def process_onboarding_chat(
    session: Session,
    claims: SessionClaims,
    body: OnboardingChatRequest,
    *,
    settings: Settings | None = None,
) -> OnboardingChatResponse:
    row = ob_repo.get_or_create_onboarding(session, claims.tenant_id)
    if row.status == STATUS_COMPLETED:
        merged = dict(row.answers_json or {})
        done_msg = "You're all set. Onboarding is already complete."
        return OnboardingChatResponse(
            assistant_message=done_msg,
            assistant_messages=[done_msg],
            step=row.current_step,
            answers=merged,
        )

    raw_msg = body.message
    user_text: str | None = None
    if isinstance(raw_msg, str):
        s = raw_msg.strip()
        if s:
            user_text = s
    structured = body.structured_action if isinstance(body.structured_action, dict) else None

    answers_snapshot = dict(row.answers_json or {})
    profile_phase = _default_profile_phase(answers_snapshot)

    # Empty POST, no structured payload: only the opening turn (name phase) should run the
    # chat pipeline. Otherwise a page refresh that replays the bootstrap POST would re-run
    # the LLM and append duplicate assistant lines (e.g. tools picker).
    if (
        row.current_step == STEP_CHAT_PROFILE
        and user_text is None
        and not structured
        and profile_phase != PROFILE_PHASE_NAME
    ):
        last_vec = _last_vector_message_content(session, claims.tenant_id)
        msg = last_vec or _fallback_idle_assistant_text(profile_phase)
        return OnboardingChatResponse(
            assistant_message=msg,
            assistant_messages=[msg],
            step=row.current_step,
            answers=answers_snapshot,
        )

    cfg = settings or get_settings()

    sl = slack_repo.get_slack_connection_for_tenant(session, claims.tenant_id)

    turn = handle_turn(
        row.current_step,
        user_text,
        structured,
        dict(row.answers_json or {}),
        slack_connected=sl is not None,
    )

    merged_answers = ob_repo.deep_merge_answers_json(
        dict(row.answers_json or {}), turn.answers_updates
    )
    ob_repo.normalize_slack_stakeholders_in_place(merged_answers)
    row.current_step = turn.next_step
    row.answers_json = merged_answers
    row.version = int(row.version) + 1

    _denormalize_profile_to_user(session, claims.user_id, merged_answers)
    _denormalize_company_to_tenant(session, claims.tenant_id, merged_answers)

    assistant_segments = generate_onboarding_reply(
        step=turn.next_step,
        answers_json=merged_answers,
        last_user_message=user_text,
        assistant_prompt_context=turn.assistant_prompt_context,
        settings=cfg,
    )
    if not assistant_segments:
        assistant_segments = ["Something went wrong. Try again in a moment."]

    _append_chat_turn(
        session,
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        user_text=user_text,
        structured=structured,
        assistant_segments=assistant_segments,
    )

    session.commit()
    session.refresh(row)

    first = assistant_segments[0] if assistant_segments else ""
    return OnboardingChatResponse(
        assistant_message=first,
        assistant_messages=assistant_segments,
        step=row.current_step,
        answers=dict(row.answers_json or {}),
    )

"""Celery tasks for Manager Slack onboarding."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from vector.domains.manager_onboarding.service import (
    process_slack_block_action,
    process_slack_message_event,
    run_send_intro_task,
)
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.session import session_scope

_logger = logging.getLogger("app")

_TASK_INTRO = "vector.manager_onboarding.send_intro"
_TASK_EVENT = "vector.manager_onboarding.process_slack_event"
_TASK_BLOCK = "vector.manager_onboarding.process_block_action"


@celery_app.task(name=_TASK_INTRO)
def send_manager_onboarding_intro_task(tenant_id: str, slack_user_id: str) -> None:
    """After website handoff DM, optionally start manager onboarding in Slack."""
    run_send_intro_task(
        tenant_id=uuid.UUID(tenant_id),
        slack_user_id=slack_user_id,
    )


@celery_app.task(name=_TASK_EVENT)
def process_manager_slack_event_task(
    *,
    team_id: str,
    slack_user_id: str,
    text: str,
    channel_id: str,
    slack_event_id: str | None,
    message_ts: str | None = None,
) -> None:
    """Process a user DM after Slack Events API enqueue.

    ``message_ts`` must stay in sync with ``slack_manager_onboarding`` (Events API).
    If workers log "unexpected keyword argument 'message_ts'", rebuild or restart
    Celery so they load this module version.
    """
    try:
        for session in session_scope():
            link = slack_repo.get_slack_connection_by_team_id(session, team_id)
            if link is None:
                _logger.warning("manager_onboarding: no slack install for team=%s", team_id)
                return
            tok = link.detail.bot_access_token
            process_slack_message_event(
                session,
                team_id=team_id,
                slack_user_id=slack_user_id,
                text=text,
                channel_id=channel_id,
                slack_event_id=slack_event_id,
                bot_token=tok,
                message_ts=message_ts,
            )
    except Exception:
        _logger.exception("manager_onboarding process_slack_event failed team=%s", team_id)
        raise


@celery_app.task(name=_TASK_BLOCK)
def process_manager_slack_block_action_task(
    *,
    team_id: str,
    slack_user_id: str,
    channel_id: str,
    action_id: str,
    action_value: str,
) -> None:
    try:
        for session in session_scope():
            link = slack_repo.get_slack_connection_by_team_id(session, team_id)
            if link is None:
                return
            tok = link.detail.bot_access_token
            process_slack_block_action(
                session,
                team_id=team_id,
                slack_user_id=slack_user_id,
                channel_id=channel_id,
                action_id=action_id,
                action_value=action_value,
                bot_token=tok,
            )
    except Exception:
        _logger.exception("manager_onboarding block_action failed team=%s", team_id)
        raise

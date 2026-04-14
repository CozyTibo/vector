"""Orchestrate one manager-onboarding DM turn: interpret → validate → merge → reply."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from vector.domains.manager_onboarding.engine.blocked import refresh_blocked_after_turn
from vector.domains.manager_onboarding.engine.interpret import (
    run_onboarding_interpret,
    run_onboarding_reply,
)
from vector.domains.manager_onboarding.engine.merge import answers_diff, merge_validated_patch
from vector.domains.manager_onboarding.engine.prompts import (
    build_interpret_system_prompt,
    build_onboarding_user_prompt,
    build_reply_channel_user_prompt,
    build_reply_system_prompt,
)
from vector.domains.manager_onboarding.engine.requirements import missing_requirements, primary_requirement
from vector.domains.manager_onboarding.engine import messages as eng_messages
from vector.domains.manager_onboarding.engine.conversation_signals import (
    extract_name_like_people_for_primary,
    raw_patch_had_substance,
    should_suppress_entity_block,
)
from vector.domains.manager_onboarding.engine.tokens import merge_deterministic_entities_into_patch
from vector.domains.manager_onboarding.engine.validate import validate_patch


@dataclass
class EngineTurnResult:
    answers_after: dict[str, Any]
    context_after: dict[str, Any]
    outbound_text: str
    session_completed: bool
    raw_llm_patch: dict[str, Any] = field(default_factory=dict)
    validated_patch: dict[str, Any] = field(default_factory=dict)
    field_validation_errors: dict[str, str] = field(default_factory=dict)
    merged_diff: dict[str, Any] = field(default_factory=dict)
    interpret_llm_model: str | None = None
    reply_llm_model: str | None = None
    llm_error: str | None = None
    reply_llm_error: str | None = None


def run_engine_turn(
    *,
    user_text: str,
    answers_before: dict[str, Any],
    context_before: dict[str, Any],
    bot_token: str,
    manager_slack_user_id: str,
    settings: Any,
    reply_user_prompt: str | None = None,
) -> EngineTurnResult:
    ctx = dict(context_before or {})
    answers = dict(answers_before or {})
    miss_before = missing_requirements(answers)
    primary_before = primary_requirement(answers)

    summary = (ctx.get("onboarding_conversation_summary") or "").strip()
    if not summary:
        summary = (ctx.get("conversation_summary") or "").strip()

    interpret_system = build_interpret_system_prompt(
        primary_req_id=primary_before,
        missing_req_ids=miss_before,
        answers_json={k: v for k, v in answers.items() if not str(k).startswith("_") or k == "_pending_channel_ids"},
        context_json=ctx,
    )
    user_block = build_onboarding_user_prompt(user_text=user_text, summary=summary)
    reply_block = (
        reply_user_prompt.strip()
        if (reply_user_prompt or "").strip()
        else build_reply_channel_user_prompt(recent_transcript="", summary=summary)
    )

    raw_patch, interpret_model, llm_err = run_onboarding_interpret(
        system_prompt=interpret_system,
        user_prompt=user_block,
        settings=settings,
    )

    if llm_err:
        refresh_blocked_after_turn(
            ctx,
            merged_something=False,
            channels_inaccessible=False,
            entity_unresolved=False,
            primary_requirement=primary_before,
        )
        bump_conversation_summary(ctx, user_text, eng_messages.FALLBACK_LLM_ERROR)
        return EngineTurnResult(
            answers_after=answers,
            context_after=ctx,
            outbound_text=eng_messages.FALLBACK_LLM_ERROR,
            session_completed=False,
            raw_llm_patch=raw_patch,
            validated_patch={},
            field_validation_errors={},
            merged_diff={},
            interpret_llm_model=interpret_model,
            reply_llm_model=None,
            llm_error=llm_err,
            reply_llm_error=None,
        )

    raw_patch = merge_deterministic_entities_into_patch(
        raw_patch,
        user_text,
        primary_req_id=primary_before,
    )

    v = validate_patch(
        raw_patch,
        bot_token=bot_token,
        manager_slack_user_id=manager_slack_user_id,
        primary_requirement_id=primary_before,
    )
    merged_something = bool(v.validated_patch)
    answers_after = merge_validated_patch(answers, v.validated_patch)
    diff = answers_diff(answers, answers_after)

    ctx.pop("soft_pending_people", None)
    soft_names = extract_name_like_people_for_primary(raw_patch, primary_before)
    suppress_entity = should_suppress_entity_block(
        merged_something=merged_something,
        entity_unresolved=v.any_entity_unresolved,
        soft_names=soft_names,
    )
    if suppress_entity and soft_names:
        ctx["soft_pending_people"] = soft_names

    entity_for_block = (
        v.any_entity_unresolved and not merged_something and not suppress_entity
    )
    refresh_blocked_after_turn(
        ctx,
        merged_something=merged_something,
        channels_inaccessible=v.channels_inaccessible,
        entity_unresolved=entity_for_block,
        primary_requirement=primary_before,
    )

    miss_after = missing_requirements(answers_after)
    primary_after = primary_requirement(answers_after)
    completed = len(miss_after) == 0

    fields_merged = sorted(v.validated_patch.keys())
    user_answer_likely_valid = raw_patch_had_substance(raw_patch) and not merged_something
    soft_for_prompt = ctx.get("soft_pending_people") if isinstance(ctx.get("soft_pending_people"), list) else None

    if completed:
        outbound = eng_messages.OUTBOUND_COMPLETION_TEXT
        reply_model: str | None = None
        reply_err: str | None = None
    else:
        reply_system = build_reply_system_prompt(
            primary_req_id=primary_after,
            missing_req_ids=miss_after,
            answers_json={k: v for k, v in answers_after.items() if not str(k).startswith("_") or k == "_pending_channel_ids"},
            context_json=ctx,
            fields_merged_this_turn=fields_merged,
            nothing_merged_this_turn=len(fields_merged) == 0,
            user_answer_likely_valid=user_answer_likely_valid,
            soft_pending_people=soft_for_prompt,
        )
        assistant_msg, reply_model, reply_err = run_onboarding_reply(
            system_prompt=reply_system,
            user_prompt=reply_block,
            settings=settings,
        )
        if (assistant_msg or "").strip():
            outbound = assistant_msg.strip()
        else:
            outbound = eng_messages.FALLBACK_LLM_ERROR

    bump_conversation_summary(ctx, user_text, outbound)

    return EngineTurnResult(
        answers_after=answers_after,
        context_after=ctx,
        outbound_text=outbound,
        session_completed=completed,
        raw_llm_patch=raw_patch,
        validated_patch=v.validated_patch,
        field_validation_errors=dict(v.field_errors),
        merged_diff=diff,
        interpret_llm_model=interpret_model,
        reply_llm_model=reply_model,
        llm_error=None,
        reply_llm_error=reply_err if not completed else None,
    )


def bump_conversation_summary(
    ctx: dict[str, Any],
    user_line: str,
    vector_line: str | None,
) -> None:
    """Append User + Vector lines to rolling summary (same 4000-char cap as before)."""
    parts: list[str] = []
    ul = (user_line or "").strip().replace("\n", " ")[:500]
    if ul:
        parts.append(f"User: {ul}")
    if vector_line and str(vector_line).strip():
        vl = str(vector_line).strip().replace("\n", " ")[:500]
        parts.append(f"Vector: {vl}")
    if not parts:
        ctx["onboarding_conversation_summary_updated_at"] = datetime.now(UTC).isoformat()
        return
    chunk = "\n".join(parts)
    prev = (ctx.get("onboarding_conversation_summary") or "").strip()
    merged = (prev + "\n" + chunk).strip() if prev else chunk
    ctx["onboarding_conversation_summary"] = merged[-4000:]
    ctx["onboarding_conversation_summary_updated_at"] = datetime.now(UTC).isoformat()

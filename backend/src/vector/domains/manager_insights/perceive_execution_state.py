"""§6 Step 9 — LLM execution-state perception (parse only; orchestrator wires Step 10)."""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

from openai import APIError, OpenAI

from vector.contracts.manager_insights_activity import (
    PerceptionExecutionStateLlmDebug,
    WorkItem,
    WorkItemBundle,
)
from vector.openai_chat_params import (
    max_completion_tokens_for_manager_insights_perception,
    temperature_for_chat_model,
)
from vector.settings import Settings

_LLM_DEBUG_MAX_ASSISTANT_CHARS = 48_000


def _chat_message_text(message: Any) -> str:
    c = getattr(message, "content", None)
    if c is None:
        return ""
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts: list[str] = []
        for p in c:
            if isinstance(p, dict) and p.get("type") == "text":
                parts.append(str(p.get("text") or ""))
            elif isinstance(p, str):
                parts.append(p)
        return "".join(parts)
    return str(c)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def _serialize_work_items_for_perception(items: list[WorkItem]) -> str:
    payload = [
        {
            "id": wi.id,
            "source": wi.source,
            "type": wi.type,
            "title": wi.title,
            "summary": wi.summary,
            "status": wi.status,
        }
        for wi in items
    ]
    return json.dumps(payload, ensure_ascii=False)


def perceive_execution_state(
    settings: Settings,
    work_items: WorkItemBundle,
    *,
    completions_create: Callable[..., Any] | None = None,
    max_items_in_prompt: int = 12,
) -> PerceptionExecutionStateLlmDebug:
    """
    Call Chat Completions with a strict JSON schema prompt; return parsed `perception_rows` dicts.

    When ``completions_create`` is set (tests / admin demo stub), ``OPENAI_API_KEY`` may be empty.
    """
    model = settings.openai_model
    slice_items = work_items.items[:max_items_in_prompt]
    if not slice_items:
        return PerceptionExecutionStateLlmDebug(skipped_reason="no_work_items", model=model)

    if completions_create is None and not settings.openai_api_key.strip():
        return PerceptionExecutionStateLlmDebug(skipped_reason="missing_api_key", model=model)

    user_payload = _serialize_work_items_for_perception(slice_items)
    kinds = "action_item | blocker | decision | risk | ambiguity | ownership_hint"
    states = "not_started | in_progress | blocked | waiting | done"
    system = (
        "You extract execution-state PERCEPTION rows from work items (coordination Step 3). "
        "Each row must cite a contiguous quote that appears verbatim in that row's work_item "
        "title or summary. Output STRICT JSON only, no markdown. "
        f'Schema: {{"perception_rows":[{{"id":str,"work_item_id":str,"kind":str({kinds}),'
        f'"statement":str,"quote":str,"execution_state":str|null({states}),'
        '"state_transition":{{"from_state":str|null,"to_state":str,"quote":str}}|null,'
        '"waits_on":[str],"blocked_by":[str],'
        '"commitment_strength":"weak"|"medium"|"strong"|null,'
        '"ambiguity_class":"unclear_scope"|"discussion_loop"|"contradiction"|null,'
        '"ambiguity_quote":str|null,"contradiction_pair_id":str|null,'
        '"ownership_inferred":{{"text_span":str,"role_guess":str|null}}|null}}]}}. '
        "If nothing is grounded, return {\"perception_rows\":[]}."
    )
    user = (
        "work_items JSON (title/summary are the only grounding surfaces):\n"
        f"{user_payload}"
    )

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_completion_tokens_for_manager_insights_perception(model),
    }
    temp = temperature_for_chat_model(model, 0.1)
    if temp is not None:
        kwargs["temperature"] = temp

    started = time.perf_counter()

    try:
        if completions_create is not None:
            resp = completions_create(**kwargs)
        else:
            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.chat.completions.create(**kwargs)
    except (APIError, Exception) as e:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return PerceptionExecutionStateLlmDebug(
            response_level_error=f"{type(e).__name__}: {e}",
            model=model,
            latency_ms=latency_ms,
        )

    latency_ms = int((time.perf_counter() - started) * 1000)
    choice0 = resp.choices[0] if getattr(resp, "choices", None) else None
    msg0 = choice0.message if choice0 is not None else None
    full_text = _chat_message_text(msg0)
    raw_text = full_text
    truncated = False
    if len(raw_text) > _LLM_DEBUG_MAX_ASSISTANT_CHARS:
        raw_text = raw_text[:_LLM_DEBUG_MAX_ASSISTANT_CHARS]
        truncated = True

    usage = getattr(resp, "usage", None)
    pt = getattr(usage, "prompt_tokens", None) if usage is not None else None
    ct = getattr(usage, "completion_tokens", None) if usage is not None else None
    tt = getattr(usage, "total_tokens", None) if usage is not None else None

    if not full_text.strip():
        return PerceptionExecutionStateLlmDebug(
            raw_assistant_text=raw_text or None,
            raw_assistant_truncated=truncated,
            response_level_error="empty_assistant_message",
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
        )

    parsed = _extract_json_object(full_text)
    if parsed is None:
        return PerceptionExecutionStateLlmDebug(
            raw_assistant_text=raw_text,
            raw_assistant_truncated=truncated,
            parse_error="assistant_text_not_json_object",
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
        )

    pr = parsed.get("perception_rows")
    if pr is None:
        return PerceptionExecutionStateLlmDebug(
            raw_assistant_text=raw_text,
            raw_assistant_truncated=truncated,
            response_level_error="missing_perception_rows_key",
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
        )
    if not isinstance(pr, list):
        return PerceptionExecutionStateLlmDebug(
            raw_assistant_text=raw_text,
            raw_assistant_truncated=truncated,
            response_level_error="perception_rows_not_a_list",
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=pt,
            completion_tokens=ct,
            total_tokens=tt,
        )

    rows_out = [x for x in pr if isinstance(x, dict)]
    return PerceptionExecutionStateLlmDebug(
        rows=rows_out,
        raw_assistant_text=raw_text,
        raw_assistant_truncated=truncated,
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=tt,
    )


def build_perception_execution_state_demo_debug(settings: Settings | None = None) -> PerceptionExecutionStateLlmDebug:
    """Deterministic stub completion — documents parse path for fetch-debug / CI without network."""
    s = settings or Settings.model_construct(
        database_url="postgresql://coordination-demo",
        openai_api_key="",
        openai_model="gpt-4o-mini",
        env="development",
        secret_key="dev-only-secret-key-min-32-chars-long!!",
    )
    demo_run = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    demo_tenant = uuid.UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
    wi_a = WorkItem(
        id="coordination:perception-llm:wi-a",
        source="linear",
        type="issue",
        title="Ship patch",
        summary="We are blocked on QA signoff before release.",
    )
    wi_b = WorkItem(
        id="coordination:perception-llm:wi-b",
        source="slack",
        type="message_thread",
        title="#deploy thread",
        summary="I'll merge after review tomorrow.",
    )
    bundle = WorkItemBundle(
        run_id=demo_run,
        tenant_id=demo_tenant,
        window_days=30,
        items=[wi_a, wi_b],
    )
    assistant_obj = {
        "perception_rows": [
            {
                "id": "coordination:perception-llm:row-a",
                "work_item_id": wi_a.id,
                "kind": "blocker",
                "statement": "Release blocked pending QA signoff.",
                "quote": "blocked on QA signoff",
                "execution_state": "blocked",
                "waits_on": [],
                "blocked_by": ["QA signoff"],
            },
            {
                "id": "coordination:perception-llm:row-b",
                "work_item_id": wi_b.id,
                "kind": "action_item",
                "statement": "Merge planned after review.",
                "quote": "I'll merge after review",
                "execution_state": "in_progress",
                "waits_on": [],
                "blocked_by": [],
            },
        ]
    }
    assistant_json = json.dumps(assistant_obj, ensure_ascii=False)

    def stub_create(**_kwargs: Any) -> Any:
        class _Usage:
            prompt_tokens = 42
            completion_tokens = 84
            total_tokens = 126

        class _Msg:
            content = assistant_json

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]
            usage = _Usage()

        return _Resp()

    return perceive_execution_state(s, bundle, completions_create=stub_create)


__all__ = [
    "build_perception_execution_state_demo_debug",
    "perceive_execution_state",
]

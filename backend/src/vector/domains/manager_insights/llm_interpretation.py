"""§6 — optional LLM copy layer on top of deterministic coordination decisions (no selection impact)."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from openai import APIError, OpenAI
from pydantic import ValidationError

from vector.contracts.manager_insights_activity import (
    DecisionBundleItem,
    EvidenceBundle,
    LinkBundle,
    SignalsV0Debug,
    WorkItemBundle,
)
from vector.domains.manager_insights.artifact_decision_context import (
    artifact_action_targets_payload,
    select_primary_work_items,
)
from vector.openai_chat_params import (
    max_completion_tokens_for_manager_insights_decision_interpretation,
    temperature_for_chat_model,
)
from vector.settings import Settings, get_settings

_NONE_OUT: dict[str, str | None] = {
    "llm_headline": None,
    "llm_explanation": None,
    "llm_next_step": None,
}

_BANNED_WORDS_RE = re.compile(
    r"\b(various|some|several|things|issues)\b",
    re.IGNORECASE,
)

_ABSTRACT_NOUNS_RE = re.compile(
    r"\b(coordination|alignment|synerg(?:y|ies)|stakeholders?)\b",
    re.IGNORECASE,
)

_HEADLINE_MAX_WORDS = 14
_EXPLANATION_MAX_SENTENCES = 2
_EXPLANATION_MAX_CHARS = 450
_NEXT_STEP_MAX_CHARS = 300


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


def _summarize_actor_metrics(m: dict[str, Any]) -> dict[str, Any]:
    """Structured, compact actor context — no raw Slack/PR text or long id lists."""
    out: dict[str, Any] = {}
    if m.get("failure_mode_aggregation"):
        out["failure_mode_aggregation"] = True
        by = m.get("by_situation")
        if isinstance(by, list):
            types: list[str] = []
            for row in by:
                if isinstance(row, dict) and row.get("situation_type"):
                    types.append(str(row["situation_type"]))
            if types:
                out["by_situation_types"] = types[:12]
    if isinstance(m.get("rule"), str):
        out["rule"] = m["rule"]
    for k in (
        "actor_fragmentation_observed",
        "open_execution_total",
        "max_owner_share_of_open_execution",
    ):
        if k in m and m[k] is not None:
            out[k] = m[k]
    return out


def _interpretation_payload(
    item: DecisionBundleItem,
    *,
    work_items: WorkItemBundle | None = None,
    evidence: EvidenceBundle | None = None,
    links: LinkBundle | None = None,
    signals: SignalsV0Debug | None = None,
) -> dict[str, Any]:
    """Structured causal context (primary) plus concrete artifact anchors for copy."""
    d = item.decision
    ri = d.required_inputs if isinstance(d.required_inputs, dict) else {}
    dbg = item.decision_debug
    raw_support = ri.get("supporting_failure_modes")
    if isinstance(raw_support, list):
        supporting_failures = raw_support
    else:
        supporting_failures = []
    payload: dict[str, Any] = {
        "dominant_failure": ri.get("failure_mode"),
        "supporting_failures": supporting_failures,
        "signals": list(d.signal_refs),
        "situation": dbg.execution_situation if dbg is not None else None,
        "is_dominant": d.dominant,
        "decision_type": d.decision_type,
        "title": d.title,
    }
    if dbg is not None and isinstance(dbg.actor_situation_metrics, dict):
        summary = _summarize_actor_metrics(dbg.actor_situation_metrics)
        if summary:
            payload["actor_metrics_summary"] = summary

    raw_targets = ri.get("artifact_action_targets")
    if isinstance(raw_targets, list) and raw_targets:
        payload["artifact_action_targets"] = raw_targets
        labels = [
            str(x.get("label")).strip()
            for x in raw_targets
            if isinstance(x, dict) and isinstance(x.get("label"), str) and str(x.get("label")).strip()
        ]
        payload["artifact_labels_for_citation"] = labels[:6]
    elif work_items is not None:
        primary = select_primary_work_items(
            item,
            work_items=work_items,
            evidence=evidence,
            links=links,
            signals=signals,
        )
        targets = artifact_action_targets_payload(primary)
        if targets:
            payload["artifact_action_targets"] = targets
            payload["artifact_labels_for_citation"] = [str(t["label"]) for t in targets][:6]
    return payload


def _parse_three_fields(obj: dict[str, Any]) -> dict[str, str] | None:
    h = obj.get("llm_headline")
    e = obj.get("llm_explanation")
    n = obj.get("llm_next_step")
    if not isinstance(h, str) or not isinstance(e, str) or not isinstance(n, str):
        return None
    h2, e2, n2 = h.strip(), e.strip(), n.strip()
    if not h2 or not e2 or not n2:
        return None
    if len(h2.split()) > 40:
        return None
    return {"llm_headline": h2, "llm_explanation": e2, "llm_next_step": n2}


def _contains_banned_wording(text: str) -> bool:
    return _BANNED_WORDS_RE.search(text) is not None


def _contains_abstract_nouns(text: str) -> bool:
    return _ABSTRACT_NOUNS_RE.search(text) is not None


def _mentions_any_artifact(text: str, labels: list[str]) -> bool:
    t = text.lower()
    for lab in labels:
        s = lab.strip().lower()
        if len(s) >= 2 and s in t:
            return True
    return False


def _trim_headline_words(headline: str, max_words: int) -> str:
    words = headline.split()
    if len(words) <= max_words:
        return headline.strip()
    return " ".join(words[:max_words]).strip()


def _trim_to_two_sentences(text: str, max_chars: int) -> str:
    t = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return ""
    joined = " ".join(parts[:_EXPLANATION_MAX_SENTENCES]).strip()
    if len(joined) > max_chars:
        return joined[:max_chars].rsplit(" ", 1)[0].strip() if " " in joined else joined[:max_chars].strip()
    return joined


def _trim_next_step(text: str, max_chars: int) -> str:
    t = " ".join(text.split()).strip()
    if len(t) <= max_chars:
        return t
    cut = t[: max_chars + 1]
    if " " in cut:
        return cut.rsplit(" ", 1)[0].strip()
    return cut[:max_chars].strip()


def _finalize_llm_interpretation_output(
    raw: dict[str, str],
    *,
    artifact_labels: list[str] | None = None,
) -> dict[str, str] | None:
    """Trim to caps; reject banned / abstract wording or missing artifact citations."""
    h = _trim_headline_words(raw["llm_headline"], _HEADLINE_MAX_WORDS)
    e = _trim_to_two_sentences(raw["llm_explanation"], _EXPLANATION_MAX_CHARS)
    n = _trim_next_step(raw["llm_next_step"], _NEXT_STEP_MAX_CHARS)
    if not h or not e or not n:
        return None
    for field in (h, e, n):
        if _contains_banned_wording(field):
            return None
    if _contains_abstract_nouns(h) or _contains_abstract_nouns(n):
        return None
    if artifact_labels:
        combined = f"{h} {n}"
        if not _mentions_any_artifact(combined, artifact_labels):
            return None
        if not _mentions_any_artifact(e, artifact_labels):
            return None
    return {"llm_headline": h, "llm_explanation": e, "llm_next_step": n}


def _call_openai_interpretation(settings: Settings, user_json: str) -> dict[str, str] | None:
    system = (
        "You are a senior engineering manager writing execution directives tied to real tools.\n\n"
        "Hard rules:\n"
        "* Every headline and next step MUST name at least one concrete artifact from "
        "artifact_action_targets (thread, issue key, PR number, Notion doc title, or calendar event).\n"
        "* Copy artifact labels verbatim when possible (e.g. NEX-112, PR #89, #eng-payments).\n"
        "* Use imperative verbs (Assign, Close, Link, Resolve, Post, Track, Confirm).\n"
        "* Do NOT use abstract nouns: coordination, alignment, synergy, stakeholder(s).\n"
        "* Do NOT invent Slack channels, ticket keys, or PR numbers not present in artifact_action_targets.\n"
        "* Mention a person by first name/handle only if artifact_action_targets.owner is non-null "
        "for that row AND you use Ask … to … framing.\n\n"
        "Tone: control-room brevity, not consultant prose."
    )
    user = (
        "Structured input (JSON):\n"
        f"{user_json}\n\n"
        "Produce JSON only (no markdown), keys exactly:\n"
        '{"llm_headline": str, "llm_explanation": str, "llm_next_step": str}\n\n'
        "1) llm_headline — imperative + specific artifact + em dash + compressed issue "
        f"(max {_HEADLINE_MAX_WORDS} words). Example shape: Close #eng-payments — no decision recorded.\n"
        "2) llm_explanation — exactly two short sentences; both must cite the same artifact label "
        "and describe delivery consequence (slips, rework, blocked merge), not abstract risk.\n"
        "3) llm_next_step — same intent as llm_headline but may add one concrete clause; "
        "must still include the artifact label verbatim.\n"
    )
    model = settings.openai_model
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_completion_tokens": max_completion_tokens_for_manager_insights_decision_interpretation(model),
    }
    temp = temperature_for_chat_model(model, 0.2)
    if temp is not None:
        kwargs["temperature"] = temp

    client = OpenAI(api_key=settings.openai_api_key, timeout=20.0)
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(**kwargs)
            choice0 = resp.choices[0] if getattr(resp, "choices", None) else None
            msg0 = choice0.message if choice0 is not None else None
            full_text = _chat_message_text(msg0)
            parsed = _extract_json_object(full_text)
            if parsed is None:
                return None
            out = _parse_three_fields(parsed)
            if out is None:
                return None
            parsed_payload = _extract_json_object(user_json)
            labels: list[str] = []
            if isinstance(parsed_payload, dict):
                raw_labs = parsed_payload.get("artifact_labels_for_citation")
                if isinstance(raw_labs, list):
                    labels = [str(x).strip() for x in raw_labs if str(x).strip()][:8]
            finalized = _finalize_llm_interpretation_output(out, artifact_labels=labels or None)
            return finalized
        except (APIError, OSError, TimeoutError):
            if attempt < 2:
                time.sleep(0.35 * (attempt + 1))
                continue
            return None
    return None


def interpret_decision_with_llm(
    decision: DecisionBundleItem,
    *,
    settings: Settings | None = None,
    work_items: WorkItemBundle | None = None,
    evidence: EvidenceBundle | None = None,
    links: LinkBundle | None = None,
    signals: SignalsV0Debug | None = None,
) -> dict[str, str | None]:
    """
    Input: one deterministic decision row (bundle item).

    Output: ``{"llm_headline", "llm_explanation", "llm_next_step"}`` each ``str`` on success,
    or ``None`` for all three when the feature is off, the client/key is unavailable, or parsing fails.

    ``settings`` is optional (defaults to ``get_settings()``); tests may pass an in-memory ``Settings`` instance.
    """
    if settings is None:
        try:
            settings = get_settings()
        except ValidationError:
            return dict(_NONE_OUT)
    if not settings.vector_manager_insights_llm_interpretation:
        return dict(_NONE_OUT)
    if not settings.openai_api_key.strip():
        return dict(_NONE_OUT)

    try:
        payload = _interpretation_payload(
            decision,
            work_items=work_items,
            evidence=evidence,
            links=links,
            signals=signals,
        )
        user_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        parsed_ok = _call_openai_interpretation(settings, user_json)
        if parsed_ok is None:
            return dict(_NONE_OUT)
        return parsed_ok
    except Exception:
        return dict(_NONE_OUT)


__all__ = ["interpret_decision_with_llm"]

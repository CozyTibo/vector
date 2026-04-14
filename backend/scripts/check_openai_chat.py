#!/usr/bin/env python3
"""
Verify OpenAI Chat Completions for the same options manager onboarding uses.

Reads OPENAI_API_KEY and OPENAI_MODEL from the repo-root ``.env`` (does not load full
``Settings``, so local GitHub PEM path issues do not block this check).

Usage (from repo root):

  cd backend && PYTHONPATH=src python scripts/check_openai_chat.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
_ROOT_ENV = _BACKEND.parent / ".env"


def _load_openai_from_dotenv(path: Path) -> tuple[str, str]:
    data: dict[str, str] = {}
    if not path.is_file():
        return "", ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1].replace('\\"', '"')
        elif v.startswith("'") and v.endswith("'"):
            v = v[1:-1]
        data[k] = v
    return (data.get("OPENAI_API_KEY") or "").strip(), (data.get("OPENAI_MODEL") or "").strip()


def main() -> int:
    sys.path.insert(0, str(_BACKEND / "src"))
    from openai import OpenAI

    from vector.openai_chat_params import (
        manager_onboarding_completion_cap,
        temperature_for_chat_model,
    )

    key, model = _load_openai_from_dotenv(_ROOT_ENV)
    print("Env file:", _ROOT_ENV)
    print("OPENAI_MODEL:", repr(model or "(empty — will default in script to gpt-4o-mini)"))
    if not key:
        print("FAIL: OPENAI_API_KEY missing or empty in .env")
        return 1
    if not model:
        model = "gpt-4o-mini"

    client = OpenAI(api_key=key)
    cap = manager_onboarding_completion_cap(model, interpret=True)
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": 'Reply with JSON only: {"patch":{}}'},
            {"role": "user", "content": "ping"},
        ],
        "max_completion_tokens": cap,
        "response_format": {"type": "json_object"},
    }
    t = temperature_for_chat_model(model, 0.35)
    if t is not None:
        kwargs["temperature"] = t
    else:
        print("(omitting temperature — gpt-5* uses provider default)")

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:
        print("FAIL:", type(e).__name__, str(e)[:800])
        return 2

    text = (resp.choices[0].message.content or "").strip()
    print("OK — API model:", getattr(resp, "model", None))
    print("Content:", text[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

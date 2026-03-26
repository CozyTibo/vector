"""Stable payload hashing for mapping_event deduplication."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_json_hash(obj: dict[str, Any]) -> str:
    payload = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

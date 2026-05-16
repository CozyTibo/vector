"""Continuity segment retrieval index keys."""

from __future__ import annotations


def continuity_segment_index_key_v1(*, segment_id: str) -> str:
    return f"continuity_segment:{segment_id}"

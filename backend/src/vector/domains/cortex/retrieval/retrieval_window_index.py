"""Chronology window retrieval index keys."""

from __future__ import annotations


def chronology_window_index_key_v1(*, window_start: str, window_end: str, chain_id: str) -> str:
    return f"chronology_window:{window_start}:{window_end}:{chain_id}"

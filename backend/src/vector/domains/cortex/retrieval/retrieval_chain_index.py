"""Causal chain retrieval index keys."""

from __future__ import annotations


def causal_chain_index_key_v1(*, causal_chain_id: str) -> str:
    return f"causal_chain:{causal_chain_id}"

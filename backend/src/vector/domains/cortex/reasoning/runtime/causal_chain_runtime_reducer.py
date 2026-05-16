"""Assemble deterministic causal chain from runtime edges."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from vector.domains.cortex.reasoning.deterministic_causal_chain import hash_causal_chain_id_v1


def reduce_causal_chain_v1(
    edge_rows: Sequence[dict[str, Any]],
    *,
    tenant_id: str,
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
) -> dict[str, Any] | None:
    if not edge_rows:
        return None
    edge_ids = [str(r["tcre_causal_edge_id"]) for r in edge_rows]
    chain_id = hash_causal_chain_id_v1(
        tcre_causal_edge_ids=edge_ids,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        tenant_id=tenant_id,
    )
    return {
        "causal_chain_id": chain_id,
        "tcre_causal_edge_ids": sorted(edge_ids),
        "reasoning_rule_pack_id": reasoning_rule_pack_id,
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest,
        "tenant_id": tenant_id,
    }

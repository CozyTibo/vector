"""OCTS-bound causal chain identity (extends P06-15 with traversal replay envelope)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vector.domains.cortex.reasoning.deterministic_causal_chain import (
    hash_causal_chain_id_v1,
)
from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)


def hash_causal_chain_id_octs_bound_v1(
    *,
    tcre_causal_edge_ids: Sequence[str],
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
    tenant_id: str,
    octs_binding_envelope: Mapping[str, Any],
) -> str:
    """Chain id = hash(base_chain_body + octs replay identity + chronology envelope)."""
    base_id = hash_causal_chain_id_v1(
        tcre_causal_edge_ids=tcre_causal_edge_ids,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
        tenant_id=tenant_id,
    )
    body = {
        "base_causal_chain_id": base_id,
        "ingestion_replay_identity": str(octs_binding_envelope.get("ingestion_replay_identity") or ""),
        "traversal_permutation_profile": str(
            octs_binding_envelope.get("traversal_permutation_profile") or ""
        ),
        "chronology_legality_envelope": str(
            octs_binding_envelope.get("chronology_legality_envelope") or ""
        ),
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest.strip(),
        "walk_hash": str(octs_binding_envelope.get("walk_hash") or ""),
    }
    return hash_reasoning_canonical_json_sha256_v1(body)

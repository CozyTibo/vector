"""Denormalized query pins on ``cortex_synthesis_artifacts`` (lookup id + replay identity)."""

from __future__ import annotations

from collections.abc import Mapping

from vector.domains.cortex.synthesis.normative import PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact


def extract_artifact_query_pins_v1(body: Mapping[str, object]) -> tuple[str | None, str | None]:
    rqid = str(
        body.get(PHASE08_UPSTREAM_REPLAY_IDENTITY_FIELD_V1)
        or body.get("retrieval_query_replay_identity")
        or "",
    ).strip() or None
    lookup = str(body.get("retrieval_lookup_id") or "").strip() or None
    if not lookup:
        scope = body.get("evidence_scope_summary")
        if isinstance(scope, Mapping):
            lookup = str(scope.get("retrieval_lookup_id") or "").strip() or None
    if not lookup:
        cite_env = body.get("synthesis_citation_envelope")
        if isinstance(cite_env, Mapping):
            citations = cite_env.get("citations")
            if isinstance(citations, list):
                for cit in citations:
                    if isinstance(cit, Mapping) and cit.get("retrieval_lookup_id"):
                        lookup = str(cit["retrieval_lookup_id"]).strip()
                        break
    if not lookup:
        binding = body.get("retrieval_binding_envelope")
        if isinstance(binding, Mapping):
            lookup = str(binding.get("retrieval_lookup_id") or "").strip() or None
    return lookup, rqid


def apply_artifact_query_pins_to_row_v1(
    row: CortexSynthesisArtifact,
    *,
    body: Mapping[str, object] | None = None,
) -> None:
    payload = dict(body or row.body_json or {})
    lookup, rqid = extract_artifact_query_pins_v1(payload)
    row.retrieval_lookup_id = lookup
    row.retrieval_query_replay_identity = rqid

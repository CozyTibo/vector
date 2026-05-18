"""Phase 08 P08-09 — cite-or-omit + ``SynthesisCitationV1`` (**SYN-LAW-09**, **G-P08-CITE-01**).

Normative: ``DOCS/cortex/synthesis/phase-08-data-contracts.md`` §Citations,
``phase-08-endgoal-doctrine.md`` §8.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.synthesis.synthesis_legality_matrix import SD_CITE_GAP_V1

PHASE08_SYNTHESIS_EVIDENCE_BINDING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

SYNTHESIS_CITATION_SCHEMA_VERSION_V1: Final[int] = 1

SYNTHESIS_CITATION_ENVELOPE_SCHEMA_VERSION_V1: Final[int] = 1

GP08_CITE01_GATE_ID_V1: Final[str] = "G-P08-CITE-01"

SYN_LAW_09_RULE_ID_V1: Final[str] = "SYN-LAW-09"

SD_SCOPE_EMPTY_V1: Final[str] = "SD-SCOPE-EMPTY"

PHASE08_CITATION_LAW_SPEC_REF_V1: Final[str] = (
    "DOCS/cortex/synthesis/phase-08-data-contracts.md"
)

SYNTHESIS_CLAIM_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "temporal_fact",
        "causal_link",
        "ownership_fact",
        "degradation_fact",
        "discourse_only",
    },
)

_SYNTHESIS_CITATION_REQUIRED_FIELDS_V1: Final[tuple[str, ...]] = (
    "citation_id",
    "retrieval_lookup_id",
    "hit_index",
    "hit_digest",
    "evidence_legality_class",
    "retrieval_omission_classes",
    "source_artifact_kind",
    "source_artifact_ref",
    "quoted_fields",
)

_CITATION_ID_RE_V1: Final[re.Pattern[str]] = re.compile(r"^cite-[0-9]{4,}$")

_CLAIM_ID_RE_V1: Final[re.Pattern[str]] = re.compile(r"^clm-[0-9]{4,}$")


class SynthesisEvidenceBindingError(ValueError):
    """Fail-closed synthesis citation / cite-or-omit law."""

    def __init__(
        self,
        code: str,
        *,
        http_status: int = 403,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.http_status = http_status
        self.detail = dict(detail or {})
        super().__init__(code)


def normalize_retrieval_hits_v1(
    retrieval_response_or_hits: Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Extract ``retrieval_evidence_hits`` array from a response or pass-through a hit list."""
    if isinstance(retrieval_response_or_hits, Mapping):
        hits = retrieval_response_or_hits.get("retrieval_evidence_hits")
        if hits is None:
            hits = retrieval_response_or_hits.get("hits")
    else:
        hits = retrieval_response_or_hits
    if not isinstance(hits, list):
        return []
    return [dict(row) for row in hits if isinstance(row, Mapping)]


def compute_retrieval_hit_digest_v1(hit: Mapping[str, Any]) -> str:
    """Content-addressed digest for a single retrieval evidence hit (replay-stable)."""
    body = {
        "retrieval_lookup_id": hit.get("retrieval_lookup_id"),
        "upstream_digest": hit.get("upstream_digest"),
        "evidence_legality_class": hit.get("evidence_legality_class"),
    }
    prov = hit.get("provenance")
    if isinstance(prov, Mapping):
        body["provenance_upstream_digest"] = prov.get("upstream_digest")
    digest = hash_reasoning_canonical_json_sha256_v1(body)
    if digest.startswith("sha256:"):
        return digest
    return f"sha256:{digest}"


def _source_artifact_from_hit_v1(hit: Mapping[str, Any]) -> tuple[str, str]:
    prov = hit.get("provenance")
    if isinstance(prov, Mapping):
        kind = str(prov.get("artifact_kind") or prov.get("source_artifact_kind") or "retrieval_index")
        ref = str(
            prov.get("artifact_ref")
            or prov.get("source_artifact_ref")
            or hit.get("retrieval_lookup_id")
            or "",
        )
        return kind, ref
    artifact_ref = hit.get("artifact_ref_json")
    if isinstance(artifact_ref, Mapping):
        for key in ("causal_chain_id", "walk_id", "lineage_id"):
            if artifact_ref.get(key):
                return "tcre_chain" if key == "causal_chain_id" else key.replace("_id", ""), str(
                    artifact_ref[key],
                )
    return "retrieval_index", str(hit.get("retrieval_lookup_id") or "")


def build_synthesis_citation_v1(
    *,
    hit: Mapping[str, Any],
    hit_index: int,
    citation_id: str | None = None,
) -> dict[str, Any]:
    """Build ``SynthesisCitationV1`` from a Phase **07** evidence hit."""
    cid = citation_id or f"cite-{hit_index:04d}"
    omission_classes: list[str] = []
    prov = hit.get("provenance")
    if isinstance(prov, Mapping):
        deg = prov.get("degradation_classes")
        if isinstance(deg, list):
            omission_classes = sorted({str(x) for x in deg if str(x).strip()})
    source_kind, source_ref = _source_artifact_from_hit_v1(hit)
    return {
        "schema_version": SYNTHESIS_CITATION_SCHEMA_VERSION_V1,
        "citation_id": cid,
        "retrieval_lookup_id": str(hit.get("retrieval_lookup_id") or ""),
        "hit_index": int(hit_index),
        "hit_digest": compute_retrieval_hit_digest_v1(hit),
        "evidence_legality_class": str(hit.get("evidence_legality_class") or "unverifiable"),
        "retrieval_omission_classes": omission_classes,
        "source_artifact_kind": source_kind,
        "source_artifact_ref": source_ref,
        "quoted_fields": [
            "retrieval_lookup_id",
            "upstream_digest",
            "evidence_legality_class",
        ],
    }


def list_synthesis_citation_violations_v1(citation: Mapping[str, Any]) -> list[str]:
    """Validate a single ``SynthesisCitationV1`` row."""
    violations: list[str] = []
    if int(citation.get("schema_version") or 0) != SYNTHESIS_CITATION_SCHEMA_VERSION_V1:
        violations.append("schema_version_mismatch")
    for field in _SYNTHESIS_CITATION_REQUIRED_FIELDS_V1:
        if field not in citation:
            violations.append(f"missing:{field}")
    cid = str(citation.get("citation_id") or "")
    if cid and not _CITATION_ID_RE_V1.match(cid):
        violations.append("invalid:citation_id_format")
    lookup = str(citation.get("retrieval_lookup_id") or "")
    if not lookup.strip():
        violations.append("missing:retrieval_lookup_id")
    digest = str(citation.get("hit_digest") or "")
    if digest and not digest.startswith("sha256:"):
        violations.append("invalid:hit_digest_prefix")
    return violations


def validate_synthesis_citation_v1(citation: Mapping[str, Any]) -> None:
    violations = list_synthesis_citation_violations_v1(citation)
    if violations:
        raise SynthesisEvidenceBindingError(
            "invalid_synthesis_citation",
            detail={"violations": violations, "citation_id": citation.get("citation_id")},
        )


def build_synthesis_citations_from_hits_v1(
    hits: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Map ``citation_id`` → ``SynthesisCitationV1`` for all retrieval hits."""
    out: dict[str, dict[str, Any]] = {}
    for idx, hit in enumerate(hits):
        if not isinstance(hit, Mapping):
            continue
        citation = build_synthesis_citation_v1(hit=hit, hit_index=idx)
        validate_synthesis_citation_v1(citation)
        out[str(citation["citation_id"])] = citation
    return out


def list_synthesis_claim_citation_violations_v1(
    claim: Mapping[str, Any],
    *,
    citations_by_id: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """**SYN-LAW-09** — each non-omitted claim must cite ≥1 resolved hit field."""
    violations: list[str] = []
    claim_id = str(claim.get("claim_id") or "")
    if claim_id and not _CLAIM_ID_RE_V1.match(claim_id):
        violations.append("invalid:claim_id_format")
    kind = str(claim.get("claim_kind") or "")
    if kind and kind not in SYNTHESIS_CLAIM_KINDS_V1:
        violations.append(f"invalid:claim_kind:{kind}")
    if claim.get("omitted_reason"):
        return violations
    if claim.get("discourse_only") is True:
        return violations
    citation_ids = claim.get("citations")
    if not isinstance(citation_ids, list) or len(citation_ids) == 0:
        violations.append("SYN-LAW-09:missing_citations")
        return violations
    for cid in citation_ids:
        if str(cid) not in citations_by_id:
            violations.append(f"unknown_citation_id:{cid}")
    return violations


def build_synthesis_claim_v1(
    *,
    claim_id: str,
    claim_kind: str,
    text: str,
    citation_ids: Sequence[str],
    discourse_only: bool = False,
    confidence_band: str | None = None,
) -> dict[str, Any]:
    """Normalized claim object for artifacts / claim slots."""
    return {
        "claim_id": claim_id,
        "claim_kind": claim_kind,
        "text": text,
        "citations": list(citation_ids),
        "confidence_band": confidence_band,
        "omitted_reason": None,
        "discourse_only": discourse_only,
    }


def build_sd_cite_gap_row_v1(
    *,
    claim_id: str,
    claim_kind: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "synthesis_omission_class": SD_CITE_GAP_V1,
        "sd_code": SD_CITE_GAP_V1,
        "claim_id": claim_id,
        "claim_kind": claim_kind,
        "reason": reason,
        "upstream_trigger": "SYN-LAW-09",
    }


def apply_syn_law_09_cite_or_omit_v1(
    proposed_claims: Sequence[Mapping[str, Any]],
    *,
    citations_by_id: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(accepted_claims, omitted_claims, sd_cite_gap_rows)``."""
    accepted: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    sd_rows: list[dict[str, Any]] = []
    for row in proposed_claims:
        if not isinstance(row, Mapping):
            continue
        violations = list_synthesis_claim_citation_violations_v1(row, citations_by_id=citations_by_id)
        if violations:
            omitted_row = {
                "claim_id": row.get("claim_id"),
                "claim_kind": row.get("claim_kind"),
                "text": row.get("text"),
                "omitted_reason": SD_CITE_GAP_V1,
                "violations": violations,
            }
            omitted.append(omitted_row)
            sd_rows.append(
                build_sd_cite_gap_row_v1(
                    claim_id=str(row.get("claim_id") or ""),
                    claim_kind=str(row.get("claim_kind") or ""),
                    reason=";".join(violations),
                ),
            )
            continue
        accepted.append(
            build_synthesis_claim_v1(
                claim_id=str(row.get("claim_id") or ""),
                claim_kind=str(row.get("claim_kind") or "temporal_fact"),
                text=str(row.get("text") or ""),
                citation_ids=[str(c) for c in (row.get("citations") or [])],
                discourse_only=bool(row.get("discourse_only")),
                confidence_band=(
                    str(row["confidence_band"]) if row.get("confidence_band") is not None else None
                ),
            ),
        )
    return accepted, omitted, sd_rows


def build_synthesis_citation_envelope_v1(
    citations_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Per-job citation envelope with canonical digest (structural replay pin)."""
    citations_sorted = {
        cid: citations_by_id[cid]
        for cid in sorted(citations_by_id.keys())
    }
    body = {
        "schema_version": SYNTHESIS_CITATION_ENVELOPE_SCHEMA_VERSION_V1,
        "citations": citations_sorted,
    }
    return {
        **body,
        "citation_envelope_digest": hash_reasoning_canonical_json_sha256_v1(body),
        "citation_count": len(citations_sorted),
    }


def build_claim_slots_from_claims_v1(
    claims: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Claim slot plan rows for replay identity digest (structural only)."""
    slots: list[dict[str, Any]] = []
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        slots.append(
            {
                "claim_id": claim.get("claim_id"),
                "claim_kind": claim.get("claim_kind"),
                "citation_placeholders": list(claim.get("citations") or []),
            },
        )
    return slots


def propose_claims_from_envelope_v1(
    envelope: Mapping[str, Any],
    *,
    citations_by_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Read operator/LLM ``claim_plan`` or synthesize skeleton claims from hits."""
    plan = envelope.get("claim_plan")
    if isinstance(plan, list) and plan:
        proposed: list[dict[str, Any]] = []
        for row in plan:
            if not isinstance(row, Mapping):
                continue
            proposed.append(dict(row))
        return proposed
    if not citations_by_id:
        return []
    proposed = []
    for cid in sorted(citations_by_id.keys()):
        citation = citations_by_id[cid]
        proposed.append(
            {
                "claim_id": f"clm-{citation['hit_index']:04d}",
                "claim_kind": "temporal_fact",
                "text": f"Evidence hit {citation['hit_index']} ({citation['retrieval_lookup_id']})",
                "citations": [cid],
            },
        )
    return proposed


def bind_synthesis_evidence_v1(
    *,
    envelope: Mapping[str, Any],
    retrieval_hits: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """BIND+ASSEMBLE law — citations, cite-or-omit claims, SD rows, claim slots."""
    hits = [dict(h) for h in retrieval_hits if isinstance(h, Mapping)]
    citations_by_id = build_synthesis_citations_from_hits_v1(hits)
    proposed = propose_claims_from_envelope_v1(envelope, citations_by_id=citations_by_id)
    accepted, omitted, sd_rows = apply_syn_law_09_cite_or_omit_v1(
        proposed,
        citations_by_id=citations_by_id,
    )
    if not hits and not proposed:
        sd_rows.append(
            {
                "synthesis_omission_class": SD_SCOPE_EMPTY_V1,
                "sd_code": SD_SCOPE_EMPTY_V1,
                "reason": "no_retrieval_hits_and_no_claim_plan",
            },
        )
    citation_envelope = build_synthesis_citation_envelope_v1(citations_by_id)
    claim_slots = build_claim_slots_from_claims_v1(accepted)
    return {
        "schema_version": PHASE08_SYNTHESIS_EVIDENCE_BINDING_RUNTIME_SCHEMA_VERSION,
        "gate_id": GP08_CITE01_GATE_ID_V1,
        "syn_law_rule": SYN_LAW_09_RULE_ID_V1,
        "citations_by_id": citations_by_id,
        "synthesis_citation_envelope": citation_envelope,
        "claims": accepted,
        "omitted_claims": omitted,
        "omitted_claim_count": len(omitted),
        "claim_slots": claim_slots,
        "synthesis_omission_rows": sd_rows,
        "evidence_scope_summary": {
            "hit_count": len(hits),
            "citation_count": len(citations_by_id),
            "accepted_claim_count": len(accepted),
            "omitted_claim_count": len(omitted),
            "sd_cite_gap_count": sum(1 for r in sd_rows if r.get("sd_code") == SD_CITE_GAP_V1),
        },
    }


def build_synthesis_citation_law_catalog_v1() -> dict[str, Any]:
    """Admin doctrine catalog — cite-or-omit + ``SynthesisCitationV1`` fields."""
    return {
        "surface_kind": "doctrine_catalog",
        "catalog_id": "synthesis_citation_law_v1",
        "phase08_synthesis_evidence_binding_runtime_schema_version": (
            PHASE08_SYNTHESIS_EVIDENCE_BINDING_RUNTIME_SCHEMA_VERSION
        ),
        "gate_id": GP08_CITE01_GATE_ID_V1,
        "syn_law_rule": SYN_LAW_09_RULE_ID_V1,
        "synthesis_citation_schema_version": SYNTHESIS_CITATION_SCHEMA_VERSION_V1,
        "claim_kinds": sorted(SYNTHESIS_CLAIM_KINDS_V1),
        "citation_required_fields": list(_SYNTHESIS_CITATION_REQUIRED_FIELDS_V1),
        "sd_codes": [SD_CITE_GAP_V1, SD_SCOPE_EMPTY_V1],
        "cite_or_omit_law": (
            "If a claim cannot cite >=1 hit field, omit claim and emit SD-CITE-GAP — "
            "never best-effort citation."
        ),
        "spec_ref": PHASE08_CITATION_LAW_SPEC_REF_V1,
    }


def build_synthesis_citation_binding_inspector_v1(
    *,
    retrieval_hits: Sequence[Mapping[str, Any]],
    claim_plan: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Admin preview — bind hits to claims under **SYN-LAW-09**."""
    envelope: dict[str, Any] = {}
    if claim_plan is not None:
        envelope["claim_plan"] = list(claim_plan)
    binding = bind_synthesis_evidence_v1(envelope=envelope, retrieval_hits=retrieval_hits)
    return {
        "surface_kind": "synthesis_citation_binding_inspector",
        "gate_id": GP08_CITE01_GATE_ID_V1,
        "passed": all(
            r.get("sd_code") != SD_CITE_GAP_V1 for r in binding.get("synthesis_omission_rows", [])
        )
        or binding.get("omitted_claim_count", 0) == 0,
        "binding": binding,
    }


def _cite_meta(name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "id": GP08_CITE01_GATE_ID_V1,
        "name": name,
        "passed": len(errors) == 0,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp08_cite01_citation_schema_static() -> dict[str, Any]:
    errors: list[str] = []
    hit = {
        "retrieval_lookup_id": "sha256:" + "a" * 64,
        "upstream_digest": "b" * 64,
        "evidence_legality_class": "verified",
        "provenance": {"artifact_kind": "tcre_chain", "artifact_ref": "chain-1"},
    }
    citation = build_synthesis_citation_v1(hit=hit, hit_index=0)
    try:
        validate_synthesis_citation_v1(citation)
    except SynthesisEvidenceBindingError as exc:
        errors.append(f"valid_citation_rejected:{exc}")
    bad = dict(citation)
    bad.pop("hit_digest")
    if not list_synthesis_citation_violations_v1(bad):
        errors.append("expected_missing_hit_digest_violation")
    return _cite_meta("gp08_cite01_citation_schema", errors)


def verify_gp08_cite01_cite_or_omit_static() -> dict[str, Any]:
    errors: list[str] = []
    hit = {
        "retrieval_lookup_id": "sha256:" + "c" * 64,
        "upstream_digest": "d" * 64,
        "evidence_legality_class": "verified",
    }
    citations = build_synthesis_citations_from_hits_v1([hit])
    accepted, omitted, sd = apply_syn_law_09_cite_or_omit_v1(
        [
            {
                "claim_id": "clm-0001",
                "claim_kind": "temporal_fact",
                "text": "ok",
                "citations": ["cite-0000"],
            },
            {
                "claim_id": "clm-0002",
                "claim_kind": "causal_link",
                "text": "no cites",
                "citations": [],
            },
        ],
        citations_by_id=citations,
    )
    if len(accepted) != 1:
        errors.append("expected_one_accepted_claim")
    if len(omitted) != 1:
        errors.append("expected_one_omitted_claim")
    if not any(r.get("sd_code") == SD_CITE_GAP_V1 for r in sd):
        errors.append("expected_sd_cite_gap")
    try:
        apply_syn_law_09_cite_or_omit_v1(
            [{"claim_id": "clm-0099", "claim_kind": "bad_kind", "text": "x", "citations": ["cite-0000"]}],
            citations_by_id=citations,
        )
    except SynthesisEvidenceBindingError:
        errors.append("unexpected_raise_on_bad_kind")
    binding = bind_synthesis_evidence_v1(envelope={}, retrieval_hits=[])
    if not any(r.get("sd_code") == SD_SCOPE_EMPTY_V1 for r in binding["synthesis_omission_rows"]):
        errors.append("expected_sd_scope_empty_on_empty_scope")
    return _cite_meta("gp08_cite01_cite_or_omit", errors)


def verify_gp08_cite01_envelope_digest_stable_static() -> dict[str, Any]:
    errors: list[str] = []
    hit = {
        "retrieval_lookup_id": "sha256:" + "e" * 64,
        "upstream_digest": "f" * 64,
        "evidence_legality_class": "verified",
    }
    citations = build_synthesis_citations_from_hits_v1([hit])
    env_a = build_synthesis_citation_envelope_v1(citations)
    env_b = build_synthesis_citation_envelope_v1(citations)
    if env_a["citation_envelope_digest"] != env_b["citation_envelope_digest"]:
        errors.append("citation_envelope_digest_not_stable")
    return _cite_meta("gp08_cite01_envelope_digest_stable", errors)

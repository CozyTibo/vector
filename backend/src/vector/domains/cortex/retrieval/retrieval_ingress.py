"""Phase 07 P07-04 — upstream ingress law (observed vs derived).

Normative: ``DOCS/cortex/retrieval/phase-07-query-contract-doctrine.md`` §Ingress.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from vector.domains.cortex.retrieval.phase_boundaries import RETRIEVAL_RD_TCRE_GAP_V1

PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION: Final[int] = 1

RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1: Final[str] = "observed"
RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1: Final[str] = "derived"
RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1: Final[str] = "forbidden"

RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1: Final[str] = "evidence_candidate_only"
RETRIEVAL_RD_INDEX_STALE_V1: Final[str] = "RD-INDEX-STALE"

# §Ingress — observed artifact kinds retrieval MAY read.
RETRIEVAL_OBSERVED_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "raw_record",
        "raw_row",
        "canonical_materialization",
        "authoritative_link",
        "org_link",
        "octs_walk_record",
        "walk_record",
        "tcre_reconstruction_job",
        "tcre_artifact",
        "chronology_receipt",
        "causal_chain",
        "causal_edge",
        "tcre_causal_edge",
        "lineage_chain",
        "continuity_topology",
    }
)

# §Ingress — derived kinds (index_epoch / published epoch required).
RETRIEVAL_DERIVED_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "retrieval_index",
        "retrieval_index_entry",
    }
)

# §Ingress — MUST NOT read.
RETRIEVAL_FORBIDDEN_ARTIFACT_KINDS_V1: Final[frozenset[str]] = frozenset(
    {
        "llm_cache",
        "embedding_table",
        "embeddings_index",
        "synthesis_output",
        "synthesis_artifact",
        "operator_notes",
        "operator_note",
        "semantic_index",
        "vector_index",
        "rag_cache",
    }
)

RETRIEVAL_INGRESS_REJECT_METRIC_NAMES_V1: Final[tuple[str, ...]] = (
    "retrieval_ingress_forbidden_artifact_total",
    "retrieval_ingress_derived_without_epoch_total",
    "retrieval_ingress_index_stale_total",
    "retrieval_ingress_candidate_only_total",
)

_AUTHORITATIVE_LINK_AUTHORITY_VALUES_V1: Final[frozenset[str]] = frozenset(
    {"authoritative", "AUTHORITATIVE"}
)

_CANDIDATE_LINK_AUTHORITY_VALUES_V1: Final[frozenset[str]] = frozenset(
    {"candidate", "CANDIDATE", "pending", "PENDING"}
)


class RetrievalIngressError(ValueError):
    """Raised when a retrieval read scope violates ingress law."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def classify_retrieval_artifact_kind_provenance_v1(artifact_kind: str) -> str:
    """Map artifact kind → ``observed`` | ``derived`` | ``forbidden``."""
    norm = artifact_kind.strip().lower().replace("-", "_")
    if norm in RETRIEVAL_FORBIDDEN_ARTIFACT_KINDS_V1:
        return RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1
    if norm in RETRIEVAL_DERIVED_ARTIFACT_KINDS_V1:
        return RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1
    if norm in RETRIEVAL_OBSERVED_ARTIFACT_KINDS_V1:
        return RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1
    return RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1


def validate_retrieval_ingress_artifact_kind_v1(artifact_kind: str) -> None:
    """Reject forbidden or unknown artifact kinds at ingress."""
    prov = classify_retrieval_artifact_kind_provenance_v1(artifact_kind)
    if prov == RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1:
        raise RetrievalIngressError(
            "retrieval_ingress_forbidden_artifact",
            detail={
                "artifact_kind": artifact_kind,
                "metric": "retrieval_ingress_forbidden_artifact_total",
            },
        )


def validate_retrieval_derived_index_read_v1(
    *,
    artifact_kind: str,
    index_epoch: str | None,
    published_epoch: str | None = None,
) -> None:
    """Derived retrieval index reads require a published ``index_epoch`` (RET-IDX-01 sketch)."""
    prov = classify_retrieval_artifact_kind_provenance_v1(artifact_kind)
    if prov != RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1:
        return
    epoch = (index_epoch or "").strip() or (published_epoch or "").strip()
    if not epoch:
        raise RetrievalIngressError(
            RETRIEVAL_RD_INDEX_STALE_V1,
            detail={
                "artifact_kind": artifact_kind,
                "reason": "derived_read_requires_index_epoch",
                "metric": "retrieval_ingress_derived_without_epoch_total",
            },
        )


def classify_org_link_authority_for_retrieval_v1(
    link_authority: str | None,
    *,
    execution_partition: str = "authoritative",
) -> str:
    """Classify graph link authority for retrieval hits (**RET-IDX** / graph binding)."""
    if link_authority in _AUTHORITATIVE_LINK_AUTHORITY_VALUES_V1:
        return "authoritative"
    if link_authority in _CANDIDATE_LINK_AUTHORITY_VALUES_V1:
        return RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
    if execution_partition.strip().lower() == "exploration":
        return RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
    return RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1


def validate_retrieval_graph_edge_ingress_v1(
    edge: Mapping[str, Any],
    *,
    execution_partition: str = "authoritative",
) -> None:
    """Authoritative partition MUST NOT treat candidate links as authoritative evidence."""
    authority = edge.get("link_authority") or edge.get("authority")
    classification = classify_org_link_authority_for_retrieval_v1(
        str(authority) if authority is not None else None,
        execution_partition=execution_partition,
    )
    if (
        execution_partition.strip().lower() == "authoritative"
        and classification == RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1
    ):
        raise RetrievalIngressError(
            RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
            detail={
                "edge_id": edge.get("id"),
                "link_authority": authority,
                "metric": "retrieval_ingress_candidate_only_total",
            },
        )


def list_retrieval_ingress_scope_violations_v1(scope: Mapping[str, Any]) -> list[str]:
    """Validate ``ingress_scope`` / envelope ingress block (artifact reads list)."""
    violations: list[str] = []
    reads = scope.get("artifact_reads")
    if reads is None:
        kinds = scope.get("artifact_kinds")
        if isinstance(kinds, list):
            reads = [{"artifact_kind": k} for k in kinds]
    if not isinstance(reads, list):
        return violations
    index_epoch = scope.get("index_epoch") or scope.get("published_epoch")
    for i, raw in enumerate(reads):
        if not isinstance(raw, Mapping):
            violations.append(f"artifact_reads[{i}]:not_an_object")
            continue
        kind = str(raw.get("artifact_kind") or "").strip()
        if not kind:
            violations.append(f"artifact_reads[{i}]:missing_artifact_kind")
            continue
        prov = classify_retrieval_artifact_kind_provenance_v1(kind)
        if prov == RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1:
            violations.append(f"artifact_reads[{i}].{kind}:forbidden_artifact_kind")
            continue
        if prov == RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1:
            row_epoch = raw.get("index_epoch") or index_epoch
            if not str(row_epoch or "").strip():
                violations.append(f"artifact_reads[{i}].{kind}:derived_without_index_epoch")
        link_auth = raw.get("link_authority")
        if link_auth is not None:
            try:
                validate_retrieval_graph_edge_ingress_v1(
                    raw,
                    execution_partition=str(
                        scope.get("execution_partition") or "authoritative"
                    ),
                )
            except RetrievalIngressError as exc:
                violations.append(f"artifact_reads[{i}]:{exc.code}")
    return violations


def enforce_retrieval_ingress_scope_v1(scope: Mapping[str, Any]) -> None:
    """Ingress law gate for query envelopes / operator scopes (P07-04)."""
    hits = list_retrieval_ingress_scope_violations_v1(scope)
    if hits:
        code = RETRIEVAL_RD_INDEX_STALE_V1 if any(
            "derived_without_index_epoch" in h for h in hits
        ) else "retrieval_ingress_forbidden"
        raise RetrievalIngressError(code, detail={"violations": hits[:32]})


def validate_retrieval_index_entry_derived_read_v1(
    *,
    index_epoch_on_row: str | None,
    pinned_index_epoch: str | None = None,
) -> None:
    """Validate derived ``retrieval_index`` row read (**RET-IDX-01** — published epoch required)."""
    epoch = (index_epoch_on_row or "").strip()
    if not epoch:
        raise RetrievalIngressError(
            RETRIEVAL_RD_INDEX_STALE_V1,
            detail={
                "reason": "index_row_missing_published_epoch",
                "metric": "retrieval_ingress_index_stale_total",
            },
        )
    pinned = (pinned_index_epoch or "").strip()
    if pinned and pinned != epoch:
        raise RetrievalIngressError(
            RETRIEVAL_RD_INDEX_STALE_V1,
            detail={
                "reason": "index_epoch_mismatch",
                "pinned_index_epoch": pinned,
                "row_index_epoch": epoch,
                "metric": "retrieval_ingress_index_stale_total",
            },
        )


def build_rd_index_stale_omission_row_v1(*, detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "retrieval_omission_class": RETRIEVAL_RD_INDEX_STALE_V1,
        "upstream_trigger": "index_epoch_unpublished",
        "detail": dict(detail or {}),
    }


def build_retrieval_ingress_law_catalog_v1() -> dict[str, Any]:
    """Operator/admin ingress table (P07-04)."""
    return {
        "phase07_ingress_runtime_schema_version": PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION,
        "provenance_classes": [
            RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1,
            RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1,
        ],
        "observed_artifact_kinds": sorted(RETRIEVAL_OBSERVED_ARTIFACT_KINDS_V1),
        "derived_artifact_kinds": sorted(RETRIEVAL_DERIVED_ARTIFACT_KINDS_V1),
        "forbidden_artifact_kinds": sorted(RETRIEVAL_FORBIDDEN_ARTIFACT_KINDS_V1),
        "evidence_legality_candidate_only": RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
        "rd_index_stale_code": RETRIEVAL_RD_INDEX_STALE_V1,
        "ingress_reject_metrics": list(RETRIEVAL_INGRESS_REJECT_METRIC_NAMES_V1),
        "rules": [
            {
                "id": "RET-ING-01",
                "text": "Observed artifacts (raw, canonical, authoritative links, OCTS walks, TCRE) may be read as stored.",
            },
            {
                "id": "RET-ING-02",
                "text": "Derived retrieval index rows require published index_epoch.",
            },
            {
                "id": "RET-ING-03",
                "text": "Forbidden: LLM caches, embedding tables, synthesis outputs, operator notes.",
            },
            {
                "id": "RET-ING-04",
                "text": "Candidate graph links → evidence_candidate_only in authoritative partition.",
            },
        ],
    }


def build_retrieval_provenance_inspector_fields_v1() -> dict[str, Any]:
    """Provenance inspector field catalog for admin surfaces (Step 4 / Step 23 precursor)."""
    return {
        "artifact_kind": {"type": "string", "required": True},
        "provenance_class": {
            "type": "enum",
            "values": [
                RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1,
                RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1,
            ],
        },
        "index_epoch": {"type": "string", "required_when": "provenance_class=derived"},
        "link_authority": {
            "type": "enum",
            "values": sorted(
                _AUTHORITATIVE_LINK_AUTHORITY_VALUES_V1 | _CANDIDATE_LINK_AUTHORITY_VALUES_V1
            ),
        },
        "evidence_legality": {
            "type": "enum",
            "values": ["authoritative", RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1],
        },
        "upstream_chronology_legality_class": {"type": "string"},
        "upstream_causal_legality_class": {"type": "string"},
        "retrieval_lookup_id": {"type": "string"},
        "retrieval_chain_ref": {"type": "string"},
        "chronology_window_ref": {"type": "string"},
        "omission_class": {"type": "string", "examples": [RETRIEVAL_RD_INDEX_STALE_V1, RETRIEVAL_RD_TCRE_GAP_V1]},
    }


def verify_gp07_ingress01_observed_derived_partition_static() -> dict[str, Any]:
    errors: list[str] = []
    if classify_retrieval_artifact_kind_provenance_v1("raw_record") != RETRIEVAL_PROVENANCE_CLASS_OBSERVED_V1:
        errors.append("raw_record_not_observed")
    if classify_retrieval_artifact_kind_provenance_v1("retrieval_index") != RETRIEVAL_PROVENANCE_CLASS_DERIVED_V1:
        errors.append("retrieval_index_not_derived")
    if classify_retrieval_artifact_kind_provenance_v1("llm_cache") != RETRIEVAL_PROVENANCE_CLASS_FORBIDDEN_V1:
        errors.append("llm_cache_not_forbidden")
    passed = len(errors) == 0
    return {
        "id": "G-P07-INGRESS-01",
        "name": "retrieval_observed_derived_partition",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_ingress02_forbidden_artifact_kinds_static() -> dict[str, Any]:
    errors: list[str] = []
    for kind in ("embedding_table", "synthesis_output", "operator_notes"):
        try:
            validate_retrieval_ingress_artifact_kind_v1(kind)
        except RetrievalIngressError:
            continue
        errors.append(f"expected_rejection_for_{kind}")
    try:
        validate_retrieval_ingress_artifact_kind_v1("causal_chain")
    except RetrievalIngressError as exc:
        errors.append(f"unexpected_rejection_causal_chain:{exc}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-INGRESS-02",
        "name": "retrieval_forbidden_artifact_kinds",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_ingress03_derived_index_epoch_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_retrieval_derived_index_read_v1(
            artifact_kind="retrieval_index", index_epoch=None
        )
    except RetrievalIngressError as exc:
        if exc.code != RETRIEVAL_RD_INDEX_STALE_V1:
            errors.append(f"wrong_code:{exc.code}")
    else:
        errors.append("expected_stale_without_epoch")
    try:
        validate_retrieval_derived_index_read_v1(
            artifact_kind="retrieval_index", index_epoch="epoch-1"
        )
    except RetrievalIngressError as exc:
        errors.append(f"unexpected_rejection_with_epoch:{exc}")
    try:
        validate_retrieval_index_entry_derived_read_v1(index_epoch_on_row=None)
    except RetrievalIngressError:
        pass
    else:
        errors.append("expected_row_stale_without_epoch")
    passed = len(errors) == 0
    return {
        "id": "G-P07-INGRESS-03",
        "name": "retrieval_derived_index_epoch_law",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_ingress04_candidate_link_authority_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_retrieval_graph_edge_ingress_v1(
            {"id": "e1", "link_authority": "candidate"},
            execution_partition="authoritative",
        )
    except RetrievalIngressError as exc:
        if exc.code != RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1:
            errors.append(f"wrong_code:{exc.code}")
    else:
        errors.append("expected_candidate_rejection_authoritative")
    try:
        validate_retrieval_graph_edge_ingress_v1(
            {"id": "e2", "link_authority": "authoritative"},
            execution_partition="authoritative",
        )
    except RetrievalIngressError as exc:
        errors.append(f"unexpected_rejection_authoritative:{exc}")
    passed = len(errors) == 0
    return {
        "id": "G-P07-INGRESS-04",
        "name": "retrieval_candidate_link_ingress",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }


def verify_gp07_ingress_catalog_static() -> dict[str, Any]:
    cat = build_retrieval_ingress_law_catalog_v1()
    errors: list[str] = []
    if "raw_record" not in cat["observed_artifact_kinds"]:
        errors.append("missing_raw_record")
    if "retrieval_index" not in cat["derived_artifact_kinds"]:
        errors.append("missing_retrieval_index")
    if cat["rd_index_stale_code"] != RETRIEVAL_RD_INDEX_STALE_V1:
        errors.append("rd_index_stale")
    passed = len(errors) == 0
    return {
        "id": "G-P07-INGRESS-CATALOG",
        "name": "retrieval_ingress_law_catalog",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }

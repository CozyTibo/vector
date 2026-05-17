"""P07-01 — Normative index + program freeze: doc contract + runtime metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.retrieval.normative import (
    PHASE07_FREEZE_BUNDLE_IDS,
    PHASE07_PROGRAM_FREEZE_VERSION,
    PHASE07_REPLAY_IDENTITY_FIELD_V1,
    PHASE07_STEP_PROGRAM_COUNT,
    PHASE07_SUBSTRATE_PIPELINE_STAGES_V1,
    build_phase07_normative_program_document_v1,
)


def _repo_root_containing_phase07_docs() -> Path:
    """Resolve repo root whether tests run from a full checkout or from ``/app`` in Docker."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "retrieval" / "phase-07-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/retrieval/phase-07-normative-index.md by walking parents "
        "from this test file. From Docker Compose, mount the repo DOCS tree read-only, e.g. "
        "``./DOCS:/app/DOCS:ro`` on the backend service used for ``make test``.",
    )


_REPO_ROOT = _repo_root_containing_phase07_docs()
_PHASE07_DIR = _REPO_ROOT / "DOCS" / "cortex" / "retrieval"

_REQUIRED_FILES = (
    "PHASE07_CONSTITUTIONAL_CHANGELOG.md",
    "phase-07-anti-goals-doctrine.md",
    "phase-07-closure-gates-doctrine.md",
    "phase-07-implementation-sequencing-plan.md",
    "phase-07-normative-index.md",
    "phase-07-phase-boundaries-doctrine.md",
    "phase-07-query-contract-doctrine.md",
    "phase-07-replay-equivalence-retrieval-spec.md",
    "phase-07-retrieval-addressing-model.md",
    "phase-07-retrieval-admin-control-plane-spec.md",
    "phase-07-retrieval-completeness-doctrine.md",
    "phase-07-retrieval-degradation-taxonomy.md",
    "phase-07-retrieval-observability-doctrine.md",
    "phase-07-retrieval-provenance-evidence-doctrine.md",
    "phase-07-retrieval-ranking-selection-doctrine.md",
    "phase-07-retrieval-runtime-architecture.md",
    "phase-07-retrieval-runtime-legality-matrix.md",
    "phase-07-substrate-overview-integration.md",
    "phase-07-temporal-retrieval-doctrine.md",
    "phase-07-verification-harness-spec.md",
    "retrieval-legality-matrix.md",
    "retrieval-spec-gap-matrix.md",
)

_VOCABULARY_TERMS = (
    "**LRE**",
    "**Query**",
    "**Hit**",
    "**Omission**",
    "**Authoritative retrieval**",
    "**Exploration retrieval**",
)


def test_phase07_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE07_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE07_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE07_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase07_required_normative_files_exist(name: str) -> None:
    path = _PHASE07_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase07_normative_index_has_vocabulary_freeze_bundles_and_steps() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text
    for bundle in (
        "**FF‑P07‑0**",
        "**FF‑P07‑1**",
        "**FF‑P07‑2**",
        "**FF‑P07‑3**",
        "**FF‑P07‑4**",
        "**FF‑P07‑5**",
    ):
        assert bundle in text, f"normative index must mention {bundle}"
    assert "| 1 | Normative index + program freeze" in text
    assert "| 30 | Closure + admin program freeze" in text
    for path in (
        "phase-07-anti-goals-doctrine.md",
        "phase-07-verification-harness-spec.md",
        "retrieval-legality-matrix.md",
        "retrieval-spec-gap-matrix.md",
    ):
        assert path in text, f"document hierarchy must reference {path}"


def test_phase07_normative_index_names_runtime_constant_path() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    assert "vector.domains.cortex.retrieval.normative.PHASE07_PROGRAM_FREEZE_VERSION" in text


def test_phase07_normative_index_cites_replay_identity_law() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    assert PHASE07_REPLAY_IDENTITY_FIELD_V1 in text
    assert "phase-07-replay-equivalence-retrieval-spec.md" in text


def test_phase07_normative_index_defines_substrate_pipeline() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    assert "Raw → Canonical → Identity → Graph → Traversal → TCRE → Retrieval" in text


def test_phase07_vocabulary_defines_core_terms() -> None:
    text = (_PHASE07_DIR / "phase-07-normative-index.md").read_text(encoding="utf-8")
    start = text.find("## Vocabulary")
    assert start != -1
    vocab_block = text[start : start + 8000]
    for term in _VOCABULARY_TERMS:
        assert term in vocab_block, f"vocabulary should define or mention {term!r}"


def test_phase07_normative_program_document_matches_freeze_metadata() -> None:
    doc = build_phase07_normative_program_document_v1()
    assert doc["phase07_program_freeze_version"] == PHASE07_PROGRAM_FREEZE_VERSION
    assert doc["step_program_count"] == PHASE07_STEP_PROGRAM_COUNT
    assert doc["freeze_bundle_ids"] == list(PHASE07_FREEZE_BUNDLE_IDS)
    assert doc["substrate_pipeline_stages"] == list(PHASE07_SUBSTRATE_PIPELINE_STAGES_V1)
    assert doc["replay_identity_field"] == PHASE07_REPLAY_IDENTITY_FIELD_V1
    assert doc["runtime_package"] == "vector.domains.cortex.retrieval"
    assert doc["normative_tree"] == "DOCS/cortex/retrieval/"

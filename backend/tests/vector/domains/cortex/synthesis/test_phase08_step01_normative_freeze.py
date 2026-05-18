"""P08-01 — Normative index + program freeze: doc contract + runtime metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.synthesis.doctrine_catalog import (
    build_synthesis_program_doctrine_catalog_v1,
)
from vector.domains.cortex.synthesis.normative import (
    PHASE08_FREEZE_BUNDLE_IDS,
    PHASE08_PROGRAM_FREEZE_VERSION,
    PHASE08_REPLAY_IDENTITY_FIELD_V1,
    PHASE08_STEP_PROGRAM_COUNT,
    PHASE08_SUBSTRATE_PIPELINE_STAGES_V1,
    build_phase08_normative_program_document_v1,
)


def _repo_root_containing_phase08_docs() -> Path:
    """Resolve repo root whether tests run from a full checkout or from ``/app`` in Docker."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "synthesis" / "phase-08-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/synthesis/phase-08-normative-index.md by walking parents "
        "from this test file. From Docker Compose, mount the repo DOCS tree read-only, e.g. "
        "``./DOCS:/app/DOCS:ro`` on the backend service used for ``make test``.",
    )


_REPO_ROOT = _repo_root_containing_phase08_docs()
_PHASE08_DIR = _REPO_ROOT / "DOCS" / "cortex" / "synthesis"

_REQUIRED_FILES = (
    "PHASE08_CONSTITUTIONAL_CHANGELOG.md",
    "phase-08-admin-control-plane-spec.md",
    "phase-08-anti-goals-doctrine.md",
    "phase-08-closure-gates-doctrine.md",
    "phase-08-data-contracts.md",
    "phase-08-e2e-operational-flow.md",
    "phase-08-endgoal-doctrine.md",
    "phase-08-evaluation-quality-governance.md",
    "phase-08-failure-degradation-taxonomy.md",
    "phase-08-implementation-sequencing-plan.md",
    "phase-08-normative-index.md",
    "phase-08-phase-boundaries-doctrine.md",
    "phase-08-pipeline-orchestration.md",
    "phase-08-replay-equivalence-spec.md",
    "phase-08-runtime-flow-e2e.md",
    "phase-08-synthesis-law-system.md",
    "phase-08-synthesis-runtime-architecture.md",
    "phase-08-testing-strategy.md",
    "synthesis-spec-gap-matrix.md",
    "fixtures/SynthesisPolicyPackV1_Default.json",
    "schemas/synthesis-intelligence-artifact-v1.schema.json",
    "schemas/synthesis-job-envelope-v1.schema.json",
)

_VOCABULARY_TERMS = (
    "**SIL**",
    "**Synthesis job**",
    "**Intelligence artifact**",
    "**Claim**",
    "**Citation**",
    "**Authoritative synthesis**",
    "**Exploration synthesis**",
    "**Deterministic shell**",
    "**Probabilistic core**",
)


def test_phase08_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE08_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE08_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE08_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase08_required_normative_files_exist(name: str) -> None:
    path = _PHASE08_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase08_normative_index_has_vocabulary_freeze_bundles_and_steps() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text
    for bundle in (
        "**FF‑P08‑0**",
        "**FF‑P08‑1**",
        "**FF‑P08‑2**",
        "**FF‑P08‑3**",
        "**FF‑P08‑4**",
        "**FF‑P08‑5**",
    ):
        assert bundle in text, f"normative index must mention {bundle}"
    assert "| 1 | Normative index + program freeze" in text
    assert "| 35 | Constitutional changelog + doctrine freeze sign-off" in text
    for path in (
        "phase-08-anti-goals-doctrine.md",
        "phase-08-testing-strategy.md",
        "phase-08-replay-equivalence-spec.md",
        "synthesis-spec-gap-matrix.md",
    ):
        assert path in text, f"document hierarchy must reference {path}"


def test_phase08_normative_index_names_runtime_constant_path() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    assert "vector.domains.cortex.synthesis.normative.PHASE08_PROGRAM_FREEZE_VERSION" in text


def test_phase08_normative_index_cites_replay_identity_law() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    assert PHASE08_REPLAY_IDENTITY_FIELD_V1 in text
    assert "phase-08-replay-equivalence-spec.md" in text


def test_phase08_normative_index_defines_substrate_pipeline() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    assert (
        "01 Ingest → 02 Raw → 03 Canonical → 04 Identity → 05 OCTS → 06 TCRE → "
        "07 Retrieval → 08 Synthesis → 09 Products"
    ) in text


def test_phase08_vocabulary_defines_core_terms() -> None:
    text = (_PHASE08_DIR / "phase-08-normative-index.md").read_text(encoding="utf-8")
    start = text.find("## Vocabulary")
    assert start != -1
    vocab_block = text[start : start + 8000]
    for term in _VOCABULARY_TERMS:
        assert term in vocab_block, f"vocabulary should define or mention {term!r}"


def test_phase08_normative_program_document_matches_freeze_metadata() -> None:
    doc = build_phase08_normative_program_document_v1()
    assert doc["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    assert doc["step_program_count"] == PHASE08_STEP_PROGRAM_COUNT
    assert doc["freeze_bundle_ids"] == list(PHASE08_FREEZE_BUNDLE_IDS)
    assert doc["substrate_pipeline_stages"] == list(PHASE08_SUBSTRATE_PIPELINE_STAGES_V1)
    assert doc["replay_identity_field"] == PHASE08_REPLAY_IDENTITY_FIELD_V1
    assert doc["runtime_package"] == "vector.domains.cortex.synthesis"
    assert doc["normative_tree"] == "DOCS/cortex/synthesis/"
    assert doc["replay_law_spec_ref"] == "phase-08-replay-equivalence-spec.md"
    assert doc["degradation_taxonomy_spec_ref"] == "phase-08-failure-degradation-taxonomy.md"


def test_phase08_program_doctrine_catalog_is_doctrine_surface() -> None:
    catalog = build_synthesis_program_doctrine_catalog_v1()
    assert catalog["surface_kind"] == "doctrine_catalog"
    assert catalog["phase08_program_freeze_version"] == PHASE08_PROGRAM_FREEZE_VERSION
    assert catalog["normative_program"]["step_program_count"] == PHASE08_STEP_PROGRAM_COUNT
    assert catalog["replay_law"]["replay_identity_field"] == PHASE08_REPLAY_IDENTITY_FIELD_V1
    assert catalog["degradation_registry"]["code_prefix"] == "SD-"

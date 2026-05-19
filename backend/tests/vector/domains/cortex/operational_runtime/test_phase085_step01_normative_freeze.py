"""P085-01 — Normative index + program freeze: doc contract + runtime metadata alignment."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vector.domains.cortex.operational_runtime.cesp_program_freeze import (
    GP085_CESP01_GATE_ID_V1,
    verify_gp085_cesp01_program_freeze_static,
)
from vector.domains.cortex.operational_runtime.doctrine_catalog import (
    build_operational_runtime_program_doctrine_catalog_v1,
)
from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_CONTINUATION_NONCE_FIELD_V1,
    PHASE085_FREEZE_BUNDLE_IDS,
    PHASE085_PROGRAM_FREEZE_VERSION,
    PHASE085_PROGRAM_ID_V1,
    PHASE085_RESUME_RECEIPT_HASH_FIELD_V1,
    PHASE085_STEP_PROGRAM_COUNT,
    PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1,
    build_phase085_normative_program_document_v1,
)


def _repo_root_containing_phase085_docs() -> Path:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        marker = root / "DOCS" / "cortex" / "operational-runtime" / "phase-085-normative-index.md"
        if marker.is_file():
            return root
    pytest.fail(
        "Could not find DOCS/cortex/operational-runtime/phase-085-normative-index.md by walking parents "
        "from this test file.",
    )


_REPO_ROOT = _repo_root_containing_phase085_docs()
_PHASE085_DIR = _REPO_ROOT / "DOCS" / "cortex" / "operational-runtime"

_REQUIRED_FILES = (
    "PHASE085_CONSTITUTIONAL_CHANGELOG.md",
    "PHASE085_EXECUTIVE_BRIEF.md",
    "phase-085-admin-cockpit-spec.md",
    "phase-085-closure-gates-doctrine.md",
    "phase-085-endgoal-doctrine.md",
    "phase-085-graph-density-doctrine.md",
    "phase-085-implementation-sequencing-plan.md",
    "phase-085-normative-index.md",
    "phase-085-operational-health-maturity-doctrine.md",
    "phase-085-phase-09-readiness-doctrine.md",
    "phase-085-phase-boundaries-doctrine.md",
    "phase-085-recovery-continuity-doctrine.md",
    "phase-085-retrieval-density-doctrine.md",
    "phase-085-runtime-architecture.md",
    "phase-085-runtime-economics-doctrine.md",
    "phase-085-substrate-continuity-doctrine.md",
    "phase-085-synthesis-activation-doctrine.md",
    "phase-085-testing-strategy.md",
    "phase-085-tcre-maturity-doctrine.md",
    "phase-085-traversal-completion-doctrine.md",
    "cesp-spec-gap-matrix.md",
)

_VOCABULARY_TERMS = (
    "**CESP**",
    "**Operational aliveness**",
    "**Fake-green idle**",
    "**Starvation**",
    "**Healthy idle**",
    "**Continuation**",
    "**Density**",
    "**Recovery receipt**",
    "**RET-SKIP-***",
    "**OPERATIONAL_ALIVE**",
)


def test_phase085_program_freeze_version_matches_normative_index() -> None:
    text = (_PHASE085_DIR / "phase-085-normative-index.md").read_text(encoding="utf-8")
    m = re.search(
        r"\|\s*\*\*PHASE085_PROGRAM_FREEZE_VERSION\*\*\s*\|\s*`(\d+)`",
        text,
    )
    assert m is not None, (
        "normative index must declare PHASE085_PROGRAM_FREEZE_VERSION in Program freeze table"
    )
    assert int(m.group(1)) == PHASE085_PROGRAM_FREEZE_VERSION


@pytest.mark.parametrize("name", _REQUIRED_FILES)
def test_phase085_required_normative_files_exist(name: str) -> None:
    path = _PHASE085_DIR / name
    assert path.is_file(), f"missing {path.relative_to(_REPO_ROOT)}"


def test_phase085_normative_index_has_vocabulary_freeze_bundles_and_steps() -> None:
    text = (_PHASE085_DIR / "phase-085-normative-index.md").read_text(encoding="utf-8")
    assert "## Vocabulary" in text
    for bundle in (
        "**FF-P085-0**",
        "**FF-P085-1**",
        "**FF-P085-2**",
        "**FF-P085-3**",
        "**FF-P085-4**",
        "**FF-P085-5**",
        "**FF-P085-6**",
    ):
        assert bundle in text, f"normative index must mention {bundle}"
    assert "| 1 | Normative index + program freeze" in text
    assert "| 36 | Certification pack + closure" in text
    for path in (
        "phase-085-endgoal-doctrine.md",
        "phase-085-substrate-continuity-doctrine.md",
        "cesp-spec-gap-matrix.md",
        "phase-085-runtime-architecture.md",
    ):
        assert path in text, f"document hierarchy must reference {path}"


def test_phase085_normative_index_names_runtime_constant_path() -> None:
    text = (_PHASE085_DIR / "phase-085-normative-index.md").read_text(encoding="utf-8")
    assert (
        "vector.domains.cortex.operational_runtime.normative.PHASE085_PROGRAM_FREEZE_VERSION"
        in text
    )


def test_phase085_normative_index_cites_continuation_doctrine() -> None:
    text = (_PHASE085_DIR / "phase-085-normative-index.md").read_text(encoding="utf-8")
    assert "phase-085-substrate-continuity-doctrine.md" in text
    assert "phase-085-recovery-continuity-doctrine.md" in text


def test_phase085_vocabulary_defines_core_terms() -> None:
    text = (_PHASE085_DIR / "phase-085-normative-index.md").read_text(encoding="utf-8")
    start = text.find("## Vocabulary")
    assert start != -1
    vocab_block = text[start : start + 8000]
    for term in _VOCABULARY_TERMS:
        assert term in vocab_block, f"vocabulary should define or mention {term!r}"


def test_phase085_normative_program_document_matches_freeze_metadata() -> None:
    doc = build_phase085_normative_program_document_v1()
    assert doc["phase085_program_freeze_version"] == PHASE085_PROGRAM_FREEZE_VERSION
    assert doc["program_id"] == PHASE085_PROGRAM_ID_V1
    assert doc["step_program_count"] == PHASE085_STEP_PROGRAM_COUNT
    assert doc["freeze_bundle_ids"] == list(PHASE085_FREEZE_BUNDLE_IDS)
    assert doc["substrate_execution_chain"] == list(PHASE085_SUBSTRATE_EXECUTION_CHAIN_V1)
    assert doc["continuation_nonce_field"] == PHASE085_CONTINUATION_NONCE_FIELD_V1
    assert doc["resume_receipt_hash_field"] == PHASE085_RESUME_RECEIPT_HASH_FIELD_V1
    assert doc["runtime_package"] == "vector.domains.cortex.operational_runtime"
    assert doc["normative_tree"] == "DOCS/cortex/operational-runtime/"
    assert doc["primary_gate_id"] == GP085_CESP01_GATE_ID_V1
    assert len(str(doc["executive_brief_fixture_digest_sha256"])) == 64


def test_phase085_program_doctrine_catalog_is_doctrine_surface() -> None:
    catalog = build_operational_runtime_program_doctrine_catalog_v1()
    assert catalog["surface_kind"] == "doctrine_catalog"
    assert catalog["program_id"] == PHASE085_PROGRAM_ID_V1
    assert catalog["phase085_program_freeze_version"] == PHASE085_PROGRAM_FREEZE_VERSION
    assert catalog["normative_program"]["step_program_count"] == PHASE085_STEP_PROGRAM_COUNT
    assert catalog["continuity_law"]["continuation_nonce_field"] == PHASE085_CONTINUATION_NONCE_FIELD_V1
    assert catalog["density_law"]["skip_code_prefix"] == "RET-SKIP-"
    assert GP085_CESP01_GATE_ID_V1 in catalog["gate_ids"]
    assert "G-P085-ANTI-IDLE-01" in catalog["gate_ids"]
    assert "G-P085-BND" in catalog["gate_ids"]
    assert "G-P085-GAP-MATRIX" in catalog["gate_ids"]
    assert "G-P085-CONT-01" in catalog["gate_ids"]
    assert catalog["gap_matrix_law"]["discipline"] == "P0_blocks_step_36_freeze"
    assert catalog["vocabulary_law"]["term_count"] == 10
    assert catalog["phase_boundary_law"]["rule_ids"] == [
        "CESP-BND-08-01",
        "CESP-BND-08-02",
        "CESP-BND-09-01",
        "CESP-BND-10-01",
    ]


def test_verify_gp085_cesp01_program_freeze_static_passes() -> None:
    out = verify_gp085_cesp01_program_freeze_static()
    assert out["passed"] is True
    assert out["gate_id"] == GP085_CESP01_GATE_ID_V1

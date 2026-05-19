"""Phase 08.5 P085-04 — CESP spec gap matrix parser + runtime catalog.

Normative: ``DOCS/cortex/operational-runtime/cesp-spec-gap-matrix.md``.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_GAP_MATRIX_REF_V1,
    PHASE085_NORMATIVE_TREE_V1,
    _repo_root_v1,
)

PHASE085_GAP_MATRIX_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_GAP_MATRIX_SPEC_REF_V1: Final[str] = f"{PHASE085_NORMATIVE_TREE_V1}{PHASE085_GAP_MATRIX_REF_V1}"

GP085_GAP_MATRIX_GATE_ID_V1: Final[str] = "G-P085-GAP-MATRIX"

_GAP_ID_RE_V1: Final[re.Pattern[str]] = re.compile(r"^(P[01]-085-\d{2})$")

_PROMOTION_RULES_V1: Final[tuple[str, ...]] = (
    "implement_and_test_moves_to_closed",
    "doctrine_only_gap_updates_doctrine_same_pr",
    "red_team_adds_row_before_merge",
)

# Baselined registry — must stay aligned with ``cesp-spec-gap-matrix.md`` (Step 4 lock).
_CESP_GAP_MATRIX_BASELINE_IDS_V1: Final[frozenset[str]] = frozenset(
    {
        "P0-085-01",
        "P0-085-02",
        "P0-085-03",
        "P0-085-04",
        "P0-085-05",
        "P0-085-06",
        "P0-085-07",
        "P0-085-08",
        "P0-085-09",
        "P0-085-10",
        "P1-085-01",
        "P1-085-02",
        "P1-085-03",
        "P1-085-04",
        "P1-085-05",
        "P1-085-06",
        "P1-085-07",
        "P1-085-08",
    }
)


class CespGapMatrixError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def cesp_gap_matrix_document_path_v1() -> Path:
    return _repo_root_v1() / "DOCS" / "cortex" / "operational-runtime" / PHASE085_GAP_MATRIX_REF_V1


def load_cesp_gap_matrix_document_v1() -> str:
    path = cesp_gap_matrix_document_path_v1()
    if not path.is_file():
        msg = "cesp_gap_matrix_document_missing"
        raise CespGapMatrixError(msg, detail={"path": str(path)})
    return path.read_text(encoding="utf-8")


def hash_cesp_gap_matrix_fixture_v1() -> str:
    """Pinned digest of living gap matrix for program attestation."""
    return hashlib.sha256(load_cesp_gap_matrix_document_v1().encode("utf-8")).hexdigest()


def _extract_section_v1(text: str, heading: str, *, next_heading_prefix: str = "## ") -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start_body = text.find("\n", start)
    if start_body < 0:
        return ""
    rest = text[start_body + 1 :]
    end = len(rest)
    for marker in ("## Active P1", "## Partially shipped", "## Closed", "## Promotion"):
        idx = rest.find(marker)
        if idx >= 0:
            end = min(end, idx)
    return rest[:end]


def _classify_gap_status_v1(gap_text: str) -> str:
    lowered = gap_text.lower()
    if "closed" in lowered or "~~" in gap_text:
        return "closed"
    if "partial" in lowered:
        return "partial"
    return "open"


def _parse_gap_table_rows_v1(section: str, *, severity: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "---" in stripped or stripped.startswith("| Id |") or stripped.startswith("| --"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        gap_id = cells[0]
        if not _GAP_ID_RE_V1.match(gap_id):
            continue
        step = int(cells[1]) if len(cells) > 1 and cells[1].isdigit() else None
        if severity == "P0":
            gap_text = cells[2] if len(cells) > 2 else ""
            owner = cells[3] if len(cells) > 3 else ""
        else:
            gap_text = cells[2] if len(cells) > 2 else ""
            owner = ""
        status = _classify_gap_status_v1(gap_text)
        rows.append(
            {
                "gap_id": gap_id,
                "severity": severity,
                "step": step,
                "gap": gap_text,
                "owner_slice": owner,
                "status": status,
            },
        )
    return rows


def _parse_partially_shipped_v1(text: str) -> list[dict[str, Any]]:
    section = _extract_section_v1(text, "## Partially shipped")
    out: list[dict[str, Any]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if "---" in stripped or "Step |" in stripped:
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        try:
            step = int(cells[0])
        except ValueError:
            continue
        out.append({"step": step, "artifact": cells[1]})
    return out


def parse_cesp_gap_matrix_markdown_v1(text: str | None = None) -> dict[str, Any]:
    """Parse living gap matrix markdown into structured rows."""
    body = text if text is not None else load_cesp_gap_matrix_document_v1()
    p0 = _parse_gap_table_rows_v1(_extract_section_v1(body, "## Active P0"), severity="P0")
    p1 = _parse_gap_table_rows_v1(_extract_section_v1(body, "## Active P1"), severity="P1")
    partially = _parse_partially_shipped_v1(body)
    return {
        "active_p0": p0,
        "active_p1": p1,
        "partially_shipped": partially,
        "promotion_rules": list(_PROMOTION_RULES_V1),
    }


def summarize_cesp_gap_matrix_v1(parsed: Mapping[str, Any]) -> dict[str, int]:
    p0_rows = list(parsed.get("active_p0") or [])
    p1_rows = list(parsed.get("active_p1") or [])
    return {
        "active_p0_total": len(p0_rows),
        "active_p0_open": sum(1 for r in p0_rows if r.get("status") == "open"),
        "active_p0_partial": sum(1 for r in p0_rows if r.get("status") == "partial"),
        "active_p0_closed": sum(1 for r in p0_rows if r.get("status") == "closed"),
        "active_p1_total": len(p1_rows),
        "active_p1_open": sum(1 for r in p1_rows if r.get("status") == "open"),
        "partially_shipped_steps": len(parsed.get("partially_shipped") or []),
    }


def build_cesp_gap_matrix_catalog_v1() -> dict[str, Any]:
    """Admin/operator gap matrix catalog (P085-04)."""
    parsed = parse_cesp_gap_matrix_markdown_v1()
    summary = summarize_cesp_gap_matrix_v1(parsed)
    gap_ids = {str(r["gap_id"]) for r in parsed["active_p0"]} | {
        str(r["gap_id"]) for r in parsed["active_p1"]
    }
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_gap_matrix_runtime_schema_version": int(PHASE085_GAP_MATRIX_RUNTIME_SCHEMA_VERSION),
        "spec_ref": PHASE085_GAP_MATRIX_SPEC_REF_V1,
        "gap_matrix_fixture_digest_sha256": hash_cesp_gap_matrix_fixture_v1(),
        "baseline_gap_ids": sorted(_CESP_GAP_MATRIX_BASELINE_IDS_V1),
        "parsed_gap_ids": sorted(gap_ids),
        "promotion_rules": list(parsed.get("promotion_rules") or []),
        "summary": summary,
        "active_p0": parsed["active_p0"],
        "active_p1": parsed["active_p1"],
        "partially_shipped": parsed["partially_shipped"],
        "blocks_step_36_freeze": summary["active_p0_open"] > 0,
        "blocks_slice_frozen_runtime": summary["active_p0_open"] > 0,
    }


def assert_gap_id_registered_in_baseline_v1(gap_id: str) -> None:
    if gap_id not in _CESP_GAP_MATRIX_BASELINE_IDS_V1:
        raise CespGapMatrixError(
            "gap_id_not_in_baseline_registry",
            detail={"gap_id": gap_id},
        )


def verify_gap_matrix_matches_baseline_registry_v1(parsed: Mapping[str, Any]) -> list[str]:
    """Runtime baseline IDs must match parsed document IDs."""
    errors: list[str] = []
    parsed_ids = {str(r["gap_id"]) for r in parsed.get("active_p0") or []} | {
        str(r["gap_id"]) for r in parsed.get("active_p1") or []
    }
    if parsed_ids != _CESP_GAP_MATRIX_BASELINE_IDS_V1:
        missing = sorted(_CESP_GAP_MATRIX_BASELINE_IDS_V1 - parsed_ids)
        extra = sorted(parsed_ids - _CESP_GAP_MATRIX_BASELINE_IDS_V1)
        if missing:
            errors.append(f"baseline_missing_in_doc:{missing}")
        if extra:
            errors.append(f"doc_extra_not_in_baseline:{extra}")
    return errors

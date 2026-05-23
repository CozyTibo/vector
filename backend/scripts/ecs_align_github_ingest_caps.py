#!/usr/bin/env python3
"""Merge GitHub ingest cap env vars (10/16/120) into ECS task definition JSON (D2)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

from vector.domains.cortex.ingestion.github_ingest_caps_code_defaults import (
    merge_github_caps_into_ecs_task_definition_v1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Align ECS task def GitHub ingest caps to code defaults")
    parser.add_argument("input", type=Path, help="Input ECS task definition JSON")
    parser.add_argument("output", type=Path, help="Output ECS task definition JSON")
    args = parser.parse_args()

    task_def = json.loads(args.input.read_text(encoding="utf-8"))
    merged = merge_github_caps_into_ecs_task_definition_v1(task_def)
    args.output.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

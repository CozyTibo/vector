"""Ownership transfer chain projection (structural)."""

from __future__ import annotations

from typing import Any


def project_ownership_transfer_chain_v1(*, transfer_refs: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(transfer_refs, key=lambda r: str(r.get("ref") or ""))
    return {"transfer_count": len(ordered), "transfers": ordered}

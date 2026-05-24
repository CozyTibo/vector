"""Legacy cortex pipeline HTTP surface — retired in R6 (use ``/cortex/operator/*``)."""

from __future__ import annotations

from fastapi import APIRouter


def register_legacy_pipeline_overview_alias(_router: APIRouter) -> None:
    """R6: legacy overview aliases removed."""


def register_cortex_pipeline_routes(_router: APIRouter) -> None:
    """R6: bootstrap, monolith, slices, semantic-readiness, graph-truth, phase routes removed."""

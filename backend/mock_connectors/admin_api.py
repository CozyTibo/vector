"""Admin endpoints for mock dataset (local dev only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from mock_connectors.runtime_state import state


def _scenario_slugs(data: dict[str, Any]) -> list[str]:
    """Human-readable scenario ids; aligns with strategy §11 and debug UX."""
    raw = list(data.get("pattern_coverage", []))
    aliases = {"duplicate_work": "duplicate_issue"}
    out: list[str] = []
    seen: set[str] = set()
    for x in raw:
        slug = aliases.get(x, x)
        if slug not in seen:
            seen.add(slug)
            out.append(slug)
    return sorted(out)


def build_admin_router() -> APIRouter:
    r = APIRouter(prefix="/admin", tags=["admin"])

    @r.post("/reseed")
    def reseed(
        seed: int = Query(..., description="New dataset seed (deterministic)."),
    ) -> dict[str, Any]:
        state.reseed(seed)
        return {"ok": True, "seed": state.seed}

    @r.get("/dataset")
    def dataset_summary() -> dict[str, Any]:
        d = state.data
        gh = d["github"]
        lin = d["linear"]
        return {
            "seed": state.seed,
            "github": {
                "repos": len(gh["repos"]),
                "pull_requests": len(gh["pull_requests"]),
                "commits": len(gh["commits"]),
                "issues": len(gh["issues"]),
            },
            "linear": {
                "organization": lin["organization"]["name"],
                "teams": len(lin["teams"]),
                "projects": len(lin["projects"]),
                "epics": len(lin["epics"]),
                "issues": len(lin["issues"]),
                "users": len(lin["users"]),
                "comments": len(lin["comments"]),
                "issue_relations": len(lin["issueRelations"]),
                "workflow_states": len(lin["workflowStates"]),
            },
        }

    @r.get("/scenarios")
    def scenarios() -> list[str]:
        return _scenario_slugs(state.data)

    return r

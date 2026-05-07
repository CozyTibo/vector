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
        notion = d.get("notion") if isinstance(d.get("notion"), dict) else {}
        calls = d.get("calls") if isinstance(d.get("calls"), dict) else {}
        slack_events = d.get("slack_events") if isinstance(d.get("slack_events"), list) else []
        return {
            "seed": state.seed,
            "github": {
                "repos": len(gh["repos"]),
                "pull_requests": len(gh["pull_requests"]),
                "pull_request_reviews": len(gh.get("pull_request_reviews", [])),
                "commits": len(gh["commits"]),
                "issues": len(gh["issues"]),
                "issue_comments": len(gh.get("issue_comments", [])),
            },
            "linear": {
                "organization": lin["organization"]["name"],
                "teams": len(lin["teams"]),
                "projects": len(lin["projects"]),
                "epics": len(lin["epics"]),
                "initiatives": len(lin.get("initiatives", [])),
                "cycles": len(lin.get("cycles", [])),
                "issue_labels": len(lin.get("labels", [])),
                "issues": len(lin["issues"]),
                "users": len(lin["users"]),
                "comments": len(lin["comments"]),
                "issue_relations": len(lin["issueRelations"]),
                "workflow_states": len(lin["workflowStates"]),
            },
            "slack": {
                "events": len(slack_events),
                "threads": sum(1 for ev in slack_events if ev.get("event_type") == "thread_reply"),
                "edits": sum(1 for ev in slack_events if ev.get("event_type") == "message_changed"),
                "deletes": sum(1 for ev in slack_events if ev.get("event_type") == "message_deleted"),
            },
            "notion": {
                "pages": len(notion.get("sampled_pages", [])),
                "databases": len((notion.get("databases") or {}).keys())
                if isinstance(notion.get("databases"), dict)
                else 0,
                "database_rows": len(notion.get("database_rows", [])),
                "comments": len(notion.get("comments", [])),
                "relations": len(notion.get("relations", [])),
            },
            "calls": {
                "events": len(calls.get("events", [])),
                "transcripts": sum(
                    1 for ev in calls.get("events", []) if isinstance(ev.get("transcript"), dict)
                ),
                "recordings": sum(
                    1 for ev in calls.get("events", []) if isinstance(ev.get("recording"), dict)
                ),
            },
        }

    @r.get("/dataset/full")
    def dataset_full() -> dict[str, Any]:
        # Local dev only; payload intentionally verbose for ingestion-depth validation.
        d = {"seed": state.seed, **state.data}
        meta = d.get("meta") if isinstance(d.get("meta"), dict) else {}
        cc = meta.get("cortex_capability_evidence")
        if isinstance(cc, dict):
            d["cortex_capability"] = {
                "scenarios": meta.get("cortex_capability_scenarios"),
                "evidence": cc,
            }
        return d

    @r.get("/scenarios")
    def scenarios() -> list[str]:
        return _scenario_slugs(state.data)

    return r

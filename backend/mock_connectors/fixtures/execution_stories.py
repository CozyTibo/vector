"""Deterministic execution story templates for Nexora mock data (local dev).

Each issue is assigned a story that controls timestamps, Linear state, optional PR
shape, relations, and comment spacing. All choices derive from ``VECTOR_MOCK_SEED``.

**Linear ``blocks`` semantics:** edge ``(source, target)`` means *source blocks target* —
the target issue cannot complete until the source is done. If issue A is *blocked by* B,
we emit ``blocks(B_id, A_id)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

from mock_connectors.fixtures import seed_config as sc

LinkStyle = Literal["title_ref", "body_closes", "issue_field_only", "none"]


def _h(days: float = 0, hours: float = 0) -> float:
    """Offset in hours from an anchor (issue or PR created)."""
    return days * 24.0 + hours


@dataclass
class PRSpec:
    """GitHub PR timeline relative to *its* open time unless noted in builder."""

    repo_index: int
    link_style: LinkStyle
    created_offset_h: float  # hours from issue created (or absolute for orphan)
    updated_offset_h: float
    merged_offset_h: float | None
    draft: bool = False
    abandoned: bool = False
    last_commit_offset_h: float | None = None
    # Filled after PR numbering:
    pr_number: int = 0


@dataclass
class IssueExecutionPlan:
    issue_index: int
    story_slug: str
    team_key: str
    created_at: datetime
    updated_at: datetime
    state_name: str
    metadata: dict[str, Any]
    pr: PRSpec | None
    comment_offsets_h: list[float]
    comment_em_mask: list[bool]  # parallel to offsets, True -> EM author
    duplicate_partner_index: int | None = None
    blocked_by_index: int | None = None  # that issue blocks this one
    blocks_next_index: int | None = None  # this issue blocks that one (chain)
    initiative: str | None = None  # "soc2" | "mobile_offline" | None
    github_pr_number: int | None = None
    shadow_pr_global_index: int | None = None  # ties to orphan PR slot
    final_assignee_override_login: str | None = None  # EM "reassign" narrative


@dataclass
class OrphanPRPlan:
    """PR with no ticket yet (shadow work front)."""

    story_slug: str
    repo_index: int
    created_at: datetime
    updated_at: datetime
    merged_at: datetime | None
    last_commit_at: datetime
    draft: bool
    abandoned: bool
    linked_issue_index: int  # issue that will reference this PR later
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionBundle:
    issue_plans: list[IssueExecutionPlan]
    orphan_prs: list[OrphanPRPlan]
    extra_slack: list[dict[str, Any]]
    epic_drift_epic_index: int | None


def _team_key_for_issue_index(issue_index: int) -> str:
    keys = [k for k, _ in sc.TEAM_NAMES[: sc.TARGET_TEAMS]]
    return keys[issue_index % len(keys)]


def story_cycle_slug(seed: int, issue_index: int) -> str:
    """Rotating story for bulk issues not in golden slots."""
    cycle = (
        "normal_delivery",
        "review_bottleneck",
        "normal_delivery",
        "misaligned_completion",
        "normal_delivery",
        "abandoned_pr",
        "cross_team_dependency_a",  # will pair poorly if alone — handled in builder
        "normal_delivery",
    )
    r = (seed * 1009 + issue_index * 9176) % len(cycle)
    return cycle[r]


def _golden_story(issue_index: int) -> str | None:
    """Fixed slots for canonical scenarios (deterministic)."""
    m = {
        0: "normal_delivery",
        1: "review_bottleneck",
        2: "cross_team_dependency_a",
        3: "cross_team_dependency_b",
        4: "shadow_work_ticket",
        5: "duplicate_work_a",
        6: "duplicate_work_b",
        7: "misaligned_completion",
        8: "abandoned_pr",
        10: "em_reassign_escalation",
        # five-level chain 160–164
        160: "dependency_chain_0",
        161: "dependency_chain_1",
        162: "dependency_chain_2",
        163: "dependency_chain_3",
        164: "dependency_chain_4",
    }
    if issue_index in m:
        return m[issue_index]
    if 200 <= issue_index <= 209:
        return "initiative_soc2"
    if 210 <= issue_index <= 217:
        return "initiative_mobile_offline"
    # Epic drift children: issues under epic 12 (NEX-212) — use band 218-227
    if 218 <= issue_index <= 227:
        return "epic_drift_child"
    return None


def _offsets_normal(
    issue_created: datetime,
) -> tuple[datetime, datetime, datetime, datetime | None]:
    """issue_created, pr_open, pr_merge, issue_done."""
    t0 = issue_created
    return (
        t0,
        t0 + timedelta(hours=_h(3)),
        t0 + timedelta(hours=_h(5)),
        t0 + timedelta(hours=_h(6)),
    )


def _comment_grid(
    seed: int,
    issue_index: int,
    story: str,
    issue_created: datetime,
    issue_updated: datetime,
    *,
    em_slots: list[int],
) -> tuple[list[float], list[bool]]:
    """Hours from issue_created; multi-day gaps, deterministic."""
    base_sets: dict[str, list[float]] = {
        "normal_delivery": [_h(0, 2), _h(1), _h(3), _h(5)],
        "review_bottleneck": [_h(0, 4), _h(2), _h(5), _h(8), _h(11)],
        "misaligned_completion": [_h(0, 3), _h(4), _h(12), _h(18)],
        "abandoned_pr": [_h(0, 2), _h(1), _h(9), _h(16)],
        "cross_team_dependency_a": [_h(0, 5), _h(8), _h(15), _h(22)],
        "cross_team_dependency_b": [_h(0, 3), _h(2), _h(6), _h(9)],
        "duplicate_work_a": [_h(0, 2), _h(4)],
        "duplicate_work_b": [_h(0, 3), _h(2), _h(6)],
        "shadow_work_ticket": [_h(0, 6), _h(1), _h(2)],
        "initiative_soc2": [_h(0, 3), _h(2), _h(5), _h(9), _h(14)],
        "initiative_mobile_offline": [_h(0, 2), _h(1), _h(4), _h(7), _h(10)],
        "epic_drift_child": [_h(0, 4), _h(3), _h(10)],
        "dependency_chain_0": [_h(0, 2), _h(4)],
        "dependency_chain_1": [_h(0, 2), _h(4)],
        "dependency_chain_2": [_h(0, 2), _h(4)],
        "dependency_chain_3": [_h(0, 2), _h(4)],
        "dependency_chain_4": [_h(0, 2), _h(4)],
        "em_reassign_escalation": [_h(0, 3), _h(1), _h(2), _h(5), _h(8)],
        "bulk_default": [_h(0, 2), _h(1), _h(3, 6), _h(7), _h(14)],
    }
    hours = list(base_sets.get(story, base_sets["bulk_default"]))
    # Perturb deterministically (still same seed)
    bump = (seed + issue_index * 31) % 7
    hours = [h + bump * 0.25 for h in hours]
    # Trim to updated window
    last = (issue_updated - issue_created).total_seconds() / 3600.0
    hours = [h for h in hours if h <= last + 1] or [2.0, 26.0]
    em_mask = [i in em_slots for i in range(len(hours))]
    return hours, em_mask


def build_execution_bundle(
    seed: int,
    t0: datetime,
    end: datetime,
    num_issues: int,
) -> ExecutionBundle:
    """Build per-issue plans and orphan PRs. ``t0`` is simulation start."""
    del end
    issue_plans: list[IssueExecutionPlan] = []
    orphan_prs: list[OrphanPRPlan] = []
    extra_slack: list[dict[str, Any]] = []

    # --- Shadow work: orphan PR opens before issue 4 exists ---
    shadow_pr_created = t0 + timedelta(days=2, hours=4)
    shadow_pr_merged = shadow_pr_created + timedelta(days=5, hours=2)
    shadow_commit_end = shadow_pr_created + timedelta(days=1, hours=3)
    orphan_prs.append(
        OrphanPRPlan(
            story_slug="shadow_work",
            repo_index=2,  # web
            created_at=shadow_pr_created,
            updated_at=shadow_pr_merged - timedelta(hours=6),
            merged_at=shadow_pr_merged,
            last_commit_at=shadow_commit_end,
            draft=False,
            abandoned=False,
            linked_issue_index=4,
            metadata={"scenario": "shadow_work"},
        ),
    )
    extra_slack.append(
        {
            "channel": "#eng-core",
            "text": (
                "Shipping cache fix directly — will backfill a Linear ticket once QA signs off."
            ),
            "ts_offset_days": 1.0,
            "anchor": shadow_pr_created,
            "user_email": "alex.kim@nexora.dev",
            "linear_issue_id": None,
            "pattern": "shadow_work_slack",
            "metadata": {"scenario": "shadow_work"},
        },
    )

    epic_drift_epic_index = 12  # NEX-212

    for i in range(num_issues):
        g = _golden_story(i)
        slug = g or story_cycle_slug(seed, i)
        # Avoid orphan cross_team_dependency_a without partner in bulk band
        if g is None and slug == "cross_team_dependency_a":
            slug = "normal_delivery"

        team_key = _team_key_for_issue_index(i)
        if i == 2:
            team_key = "WEB"
        elif i == 3:
            team_key = "CORE"
        # Anchor issue start spread across simulation (deterministic)
        day_offset = (seed * 17 + i * 13) % max(1, sc.SIMULATION_DAYS - 30)
        hour_jitter = (seed + i * 5) % 20
        issue_created = t0 + timedelta(days=day_offset, hours=hour_jitter)

        pr_spec: PRSpec | None = None
        state_name = "Done"
        updated_at = issue_created + timedelta(days=6)
        meta: dict[str, Any] = {"scenario": slug}
        dup_partner: int | None = None
        blocked_by: int | None = None
        blocks_next: int | None = None
        initiative: str | None = None
        shadow_slot: int | None = None
        assignee_override: str | None = None
        em_slots: list[int] = []

        if slug == "normal_delivery" and i == 0:
            _, pr_open, pr_merge, done_t = _offsets_normal(issue_created)
            updated_at = done_t
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(pr_merge - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(pr_merge - issue_created).total_seconds() / 3600,
                last_commit_offset_h=(pr_merge - issue_created).total_seconds() / 3600 - 4,
            )
            state_name = "Done"
            em_slots = [1]
        elif slug == "review_bottleneck" and i == 1:
            pr_open = issue_created + timedelta(days=4)
            review_done = issue_created + timedelta(days=9)
            merged = issue_created + timedelta(days=10)
            updated_at = issue_created + timedelta(days=12)
            pr_spec = PRSpec(
                repo_index=1,
                link_style="body_closes",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(review_done - issue_created).total_seconds() / 3600,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
                last_commit_offset_h=(merged - issue_created).total_seconds() / 3600 - 1,
            )
            state_name = "Done"
            em_slots = [2]
        elif slug == "cross_team_dependency_a" and i == 2:
            # A (WEB) blocked until B (CORE) ships
            blocked_by = 3
            pr_open = issue_created + timedelta(days=14)
            merged = issue_created + timedelta(days=18)
            updated_at = issue_created + timedelta(days=20)
            pr_spec = PRSpec(
                repo_index=2,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 3,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
                last_commit_offset_h=(merged - issue_created).total_seconds() / 3600 - 2,
            )
            state_name = "Done"
            em_slots = [1, 3]
        elif slug == "cross_team_dependency_b" and i == 3:
            pr_open = issue_created + timedelta(days=6)
            merged = issue_created + timedelta(days=9)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=0,
                link_style="issue_field_only",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 1,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
                last_commit_offset_h=(merged - issue_created).total_seconds() / 3600 - 3,
            )
            state_name = "Done"
        elif slug == "shadow_work_ticket" and i == 4:
            # Issue created after orphan PR; link via github_pr_number + body
            issue_created = shadow_pr_created + timedelta(days=3, hours=2)
            updated_at = shadow_pr_merged + timedelta(days=1)
            pr_spec = None  # uses orphan
            shadow_slot = 0
            state_name = "Done"
            meta["scenario"] = "shadow_work"
            em_slots = [0]
        elif slug == "duplicate_work_a" and i == 5:
            dup_partner = 6
            pr_open = issue_created + timedelta(days=5)
            merged = issue_created + timedelta(days=8)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=4,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "duplicate_work_b" and i == 6:
            dup_partner = 5
            pr_open = issue_created + timedelta(days=4)
            merged = issue_created + timedelta(days=7)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=4,
                link_style="body_closes",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "misaligned_completion" and i == 7:
            pr_open = issue_created + timedelta(days=2)
            merged = issue_created + timedelta(days=5)
            updated_at = issue_created + timedelta(days=20)  # issue closes late
            pr_spec = PRSpec(
                repo_index=3,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "abandoned_pr" and i == 8:
            pr_open = issue_created + timedelta(days=4)
            last_c = issue_created + timedelta(days=5, hours=4)
            updated_at = issue_created + timedelta(days=30)  # ticket went stale
            pr_spec = PRSpec(
                repo_index=0,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(last_c - issue_created).total_seconds() / 3600,
                merged_offset_h=None,
                abandoned=True,
                last_commit_offset_h=(last_c - issue_created).total_seconds() / 3600,
            )
            state_name = "In Review"
            em_slots = [2, 4]
        elif slug.startswith("dependency_chain_"):
            idx = int(slug.rsplit("_", 1)[-1])
            pr_open = issue_created + timedelta(days=2 + idx)
            merged = pr_open + timedelta(days=3)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=idx % len(sc.REPO_NAMES),
                link_style="title_ref" if idx % 2 == 0 else "body_closes",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
            if idx < 4:
                blocks_next = 160 + idx + 1
        elif slug == "initiative_soc2":
            initiative = "soc2"
            pr_open = issue_created + timedelta(days=5)
            merged = issue_created + timedelta(days=11)
            updated_at = merged + timedelta(days=2)
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="issue_field_only" if i % 3 == 0 else "title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 4,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
            em_slots = [1] if i % 4 == 0 else []
        elif slug == "initiative_mobile_offline":
            initiative = "mobile_offline"
            pr_open = issue_created + timedelta(days=4)
            merged = issue_created + timedelta(days=9)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="body_closes" if i % 2 == 0 else "title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 3,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "epic_drift_child":
            initiative = "epic_drift"
            pr_open = issue_created + timedelta(days=6)
            merged = issue_created + timedelta(days=14)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=5,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "em_reassign_escalation" and i == 10:
            pr_open = issue_created + timedelta(days=3)
            merged = issue_created + timedelta(days=9)
            updated_at = merged + timedelta(days=1)
            pr_spec = PRSpec(
                repo_index=1,
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600 + 2,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
            assignee_override = "akim"  # narrative: reassigned from srivera
            em_slots = [0, 2]
        elif slug == "review_bottleneck":
            pr_open = issue_created + timedelta(days=5)
            review = issue_created + timedelta(days=11)
            merged = issue_created + timedelta(days=13)
            updated_at = issue_created + timedelta(days=15)
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="body_closes",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(review - issue_created).total_seconds() / 3600,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
            em_slots = [2]
        elif slug == "misaligned_completion":
            pr_open = issue_created + timedelta(days=2)
            merged = issue_created + timedelta(days=6)
            updated_at = issue_created + timedelta(days=22)
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="title_ref",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(merged - issue_created).total_seconds() / 3600,
                merged_offset_h=(merged - issue_created).total_seconds() / 3600,
            )
            state_name = "Done"
        elif slug == "abandoned_pr":
            pr_open = issue_created + timedelta(days=3)
            last_c = issue_created + timedelta(days=4, hours=6)
            updated_at = issue_created + timedelta(days=25)
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="none",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(last_c - issue_created).total_seconds() / 3600,
                merged_offset_h=None,
                abandoned=True,
                last_commit_offset_h=(last_c - issue_created).total_seconds() / 3600,
            )
            state_name = "In Progress"
        else:
            # normal_delivery bulk
            _, pr_open, pr_merge, done_t = _offsets_normal(issue_created)
            updated_at = done_t
            pr_spec = PRSpec(
                repo_index=i % len(sc.REPO_NAMES),
                link_style="title_ref" if i % 4 != 0 else "body_closes",
                created_offset_h=(pr_open - issue_created).total_seconds() / 3600,
                updated_offset_h=(pr_merge - issue_created).total_seconds() / 3600 + 1,
                merged_offset_h=(pr_merge - issue_created).total_seconds() / 3600,
                last_commit_offset_h=(pr_merge - issue_created).total_seconds() / 3600 - 2,
            )
            state_name = "Done"
            if (seed + i) % 11 == 0:
                em_slots = [1]

        # Style D: some bulk issues explicitly untracked PRs
        if g is None and pr_spec and (seed + i * 7) % 23 == 0:
            pr_spec = PRSpec(
                repo_index=(i + 3) % len(sc.REPO_NAMES),
                link_style="none",
                created_offset_h=pr_spec.created_offset_h,
                updated_offset_h=pr_spec.updated_offset_h,
                merged_offset_h=pr_spec.merged_offset_h,
                draft=pr_spec.draft,
                abandoned=pr_spec.abandoned,
                last_commit_offset_h=pr_spec.last_commit_offset_h,
            )
            meta["scenario"] = "untracked_pr"

        co, em_m = _comment_grid(
            seed,
            i,
            meta["scenario"],
            issue_created,
            updated_at,
            em_slots=em_slots,
        )

        issue_plans.append(
            IssueExecutionPlan(
                issue_index=i,
                story_slug=slug,
                team_key=team_key,
                created_at=issue_created,
                updated_at=updated_at,
                state_name=state_name,
                metadata=meta,
                pr=pr_spec,
                comment_offsets_h=co,
                comment_em_mask=em_m,
                duplicate_partner_index=dup_partner,
                blocked_by_index=blocked_by,
                blocks_next_index=blocks_next,
                initiative=initiative,
                shadow_pr_global_index=shadow_slot,
                final_assignee_override_login=assignee_override,
            ),
        )

    _trim_issue_prs_to_budget(
        issue_plans,
        orphan_count=len(orphan_prs),
        target_prs=sc.TARGET_PRS,
        multi_repo_extra=2,
    )

    from mock_connectors.fixtures import cortex_capability_scenarios as ccs

    bundle_out = ExecutionBundle(
        issue_plans=issue_plans,
        orphan_prs=orphan_prs,
        extra_slack=extra_slack,
        epic_drift_epic_index=epic_drift_epic_index,
    )
    ccs.patch_execution_bundle_for_cortex_capabilities(bundle_out)
    return bundle_out


def _trim_issue_prs_to_budget(
    plans: list[IssueExecutionPlan],
    *,
    orphan_count: int,
    target_prs: int,
    multi_repo_extra: int,
) -> None:
    """Keep deterministic golden PRs; drop bulk ``pr`` until within GitHub PR budget."""
    golden_keep_pr = {
        0,
        1,
        2,
        3,
        5,
        6,
        7,
        8,
        10,
        *range(160, 165),
        *range(200, 218),
        *range(218, 228),
    }
    budget = max(0, target_prs - orphan_count - multi_repo_extra)
    current = sum(1 for p in plans if p.pr is not None)
    i = len(plans) - 1
    while current > budget and i >= 0:
        pl = plans[i]
        if i in golden_keep_pr or pl.shadow_pr_global_index is not None:
            i -= 1
            continue
        if pl.pr is not None:
            pl.pr = None
            current -= 1
        i -= 1


def workflow_state_for_team(
    workflow_states: list[dict[str, Any]], team_id: str, state_name: str
) -> dict[str, Any]:
    for s in workflow_states:
        if s["team"]["id"] == team_id and s["name"] == state_name:
            return s
    # Fallback: first state for team
    for s in workflow_states:
        if s["team"]["id"] == team_id:
            return s
    msg = f"no workflow state for team {team_id}"
    raise RuntimeError(msg)

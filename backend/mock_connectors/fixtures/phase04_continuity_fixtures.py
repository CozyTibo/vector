"""Phase 04 mock continuity sidecar + scenario registry (P04-20 / mock strategy §3–§6)."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any, Final


def _iso_ts(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _ev_id(seed: int, *parts: str) -> str:
    h = hashlib.sha256((f"{seed}:" + ":".join(parts)).encode()).hexdigest()
    b = h[:32]
    return f"{b[:8]}-{b[8:12]}-{b[12:16]}-{b[16:20]}-{b[20:32]}"

PHASE04_MOCK_FIXTURE_SCHEMA_VERSION: Final[str] = "phase04_mock_fixture_v1"

PHASE04_SCENARIO_KEYS: Final[frozenset[str]] = frozenset(
    {
        "nexora_p04_hostile_baseline",
        "nexora_p04_ci_slice_identity",
        "nexora_p04_ci_slice_temporal",
        "nexora_p04_ci_slice_cross_tool",
        "nexora_p04_ci_slice_primitives",
        "nexora_p04_ci_slice_bundle",
    }
)


def resolve_phase04_continuity_scenario_key() -> str:
    raw = (os.environ.get("P04_CONTINUITY_SCENARIO") or "nexora_p04_ci_slice_identity").strip()
    return raw if raw in PHASE04_SCENARIO_KEYS else "nexora_p04_ci_slice_identity"


def build_continuity_fixture_sidecar(*, seed: int) -> dict[str, Any]:
    """Optional ``continuity_fixture`` block attached to generated mock datasets."""
    scenario_key = resolve_phase04_continuity_scenario_key()
    return {
        "schema_version": PHASE04_MOCK_FIXTURE_SCHEMA_VERSION,
        "seed": seed,
        "scenario_key": scenario_key,
        "scenario_keys_catalog": sorted(PHASE04_SCENARIO_KEYS),
        "expectations": [
            {
                "scenario_family_id": "P04MD-H06",
                "note": "Two Linear users share displayName prefix Alex (company_generator hygiene)",
                "must_not_auto_merge": True,
            },
            {
                "scenario_family_id": "P04MD-H01",
                "note": "Cross-tool identity fracture hints via Slack/GitHub/Linear user matrix",
                "must_not_auto_merge": True,
            },
        ],
    }


def extend_slack_events_for_hostile_identity_continuity(
    slack_events: list[dict[str, Any]],
    *,
    seed: int,
    users: list[dict[str, Any]],
    t0: datetime,
) -> None:
    """Append deterministic hostile Slack rows (fixture metadata only; no semantic matching).

    Surfaces: dense same-Slack-user handles, shared-inbox multiplicity, two-Alex cohort pressure.
    """
    workspace_id: str | None = None
    for ev in slack_events:
        if isinstance(ev, dict) and isinstance(ev.get("workspace_id"), str) and ev["workspace_id"].strip():
            workspace_id = ev["workspace_id"].strip()
            break
    if workspace_id is None:
        workspace_id = f"T{seed % 10_000:04d}NEXORA"

    def _by_login(login: str) -> dict[str, Any] | None:
        for u in users:
            if str(u.get("login") or "") == login:
                return u
        return None

    th = _by_login("thagler")
    ak = _by_login("akim")
    sr = _by_login("srivera")
    channel_id = "CENGP04HOST"
    base_ts = t0 + timedelta(days=7, hours=2)
    shared_subject = "p04:cross_tool_morgan_split_identity_bundle"
    stable_acc = f"p04_hostile_stable_account_{seed % 10009:05d}"

    def _append_row(suffix: str, **fields: Any) -> None:
        row: dict[str, Any] = {
            "id": _ev_id(seed, "slack", "p04hostile", suffix),
            "workspace_id": workspace_id,
            "event_type": "message",
            "channel_id": channel_id,
            "channel": "#eng-hostile-p04",
            "thread_ts": None,
            "parent_ts": None,
            "deleted_at": None,
            "linear_issue_id": None,
            "pattern": "p04_hostile_identity",
            "reactions": [{"name": "warning", "count": 1}],
        }
        row.update(fields)
        slack_events.append(row)

    if th:
        sid = "UTHAGLERP04"
        dn = (th.get("name") or th["login"]).strip().lower()
        for i in range(3):
            ts = base_ts + timedelta(minutes=i * 19)
            _append_row(
                f"th-multi-{i}",
                text=f"P04 hostile continuity shard {i} (same Slack user id).",
                ts=_iso_ts(ts),
                created_at=_iso_ts(ts),
                updated_at=_iso_ts(ts),
                user_email=th["email"],
                user_id=sid,
                display_name=dn,
                metadata={
                    "continuity_fixture": {
                        "cluster_key": "p04md_hostile_dense_slack_user",
                        "link_subject": shared_subject,
                        "stable_account_key": stable_acc,
                        "family": "P04MD-H01",
                    },
                },
            )

    shared_email = "supportops.shared@nexora.dev"
    shared_dn = "nexora support"
    for i, sid in enumerate(("USUPINBOX1", "USUPINBOX2")):
        ts = base_ts + timedelta(hours=3, minutes=i * 7)
        _append_row(
            f"shared-inbox-{i}",
            text="Shared inbox triage — duplicate connector identities (mock).",
            ts=_iso_ts(ts),
            created_at=_iso_ts(ts),
            updated_at=_iso_ts(ts),
            user_email=shared_email,
            user_id=sid,
            display_name=shared_dn,
            metadata={
                "continuity_fixture": {
                    "cluster_key": "p04md_shared_support_inbox",
                    "ambiguity_cohort_key": "p04_hostile_shared_support_inbox",
                    "org_ambiguity_class": "multiple_persona_unresolved",
                    "family": "P04MD-H04",
                },
            },
        )

    if ak and sr:
        for i, (u, sid) in enumerate(((ak, "UALEXKIM01"), (sr, "UALEXRIV02"))):
            ts = base_ts + timedelta(hours=5, minutes=i * 11)
            _append_row(
                f"two-alex-{i}",
                text=f"Alex nickname collision shard {i} (mock).",
                ts=_iso_ts(ts),
                created_at=_iso_ts(ts),
                updated_at=_iso_ts(ts),
                user_email=u["email"],
                user_id=sid,
                display_name="alex",
                metadata={
                    "continuity_fixture": {
                        "cluster_key": "p04md_two_alexes",
                        "ambiguity_cohort_key": "p04_hostile_two_alex_handles",
                        "org_ambiguity_class": "handle_collision_unresolved",
                        "family": "P04MD-H06",
                    },
                },
            )

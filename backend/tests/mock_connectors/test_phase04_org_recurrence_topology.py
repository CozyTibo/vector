"""P04 — deterministic org recurrence topology on mock company datasets."""

from __future__ import annotations

from mock_connectors.fixtures.company_generator import dataset_to_json_dict, generate_dataset


def test_org_recurrence_topology_applied_with_expected_density() -> None:
    ds = generate_dataset(101)
    topo = ds.meta.get("p04_org_recurrence_topology") or {}
    assert topo.get("applied") is True
    assert topo.get("anchor_login") == "akim"
    assert topo.get("shared_email_norm") == "alex.kim@nexora.dev"
    assert int(topo.get("slack_rows_added") or 0) >= 6
    assert int(topo.get("github_commits_added") or 0) >= 5
    assert int(topo.get("linear_comments_added") or 0) >= 4

    data = dataset_to_json_dict(ds)
    shared = topo["shared_email_norm"]
    slack_hits = sum(
        1
        for e in data["slack_events"]
        if isinstance(e, dict)
        and str(e.get("user_email") or "").strip().lower() == shared
        and e.get("pattern") == "p04_org_recurrence"
    )
    assert slack_hits >= 6

    gh_emails = []
    for c in data["github"].get("commits") or []:
        if not isinstance(c, dict):
            continue
        commit = c.get("commit") or {}
        auth = (commit.get("author") or {}) if isinstance(commit, dict) else {}
        em = auth.get("email")
        if isinstance(em, str) and em.strip().lower() == shared:
            gh_emails.append(c.get("sha"))
    assert len(gh_emails) >= 5


def test_org_recurrence_topology_stable_across_seeds_shape() -> None:
    a = (generate_dataset(1).meta.get("p04_org_recurrence_topology") or {}).get("slack_rows_added")
    b = (generate_dataset(2).meta.get("p04_org_recurrence_topology") or {}).get("slack_rows_added")
    assert a == b == 6

"""Tests for answers_json.slack_collaborators normalization."""

from vector.infrastructure.db.repositories.onboarding import normalize_slack_collaborators_in_place


def test_normalize_slack_collaborators_dedupes_and_trims() -> None:
    answers = {
        "slack_collaborators": {
            "members": [
                {
                    "slack_user_id": "U1",
                    "username": "@ada",
                    "label": "Ada",
                },
                {
                    "slack_user_id": "U1",
                    "username": "ada",
                    "label": "Ada",
                },
                {"slack_user_id": "U2", "username": "bob", "label": ""},
            ]
        }
    }
    normalize_slack_collaborators_in_place(answers)
    members = answers["slack_collaborators"]["members"]
    assert len(members) == 2
    assert members[0] == {"slack_user_id": "U1", "username": "ada", "label": "Ada"}
    assert members[1] == {"slack_user_id": "U2", "username": "bob", "label": "bob"}

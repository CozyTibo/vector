from vector.domains.manager_onboarding.engine.messages import intro_dm_text


def test_intro_no_em_dash() -> None:
    t = intro_dm_text(context=None)
    assert "\u2014" not in t
    assert "I'm Vector" in t
    assert "Just answer however you normally would." in t


def test_intro_web_handoff_and_name_company() -> None:
    t = intro_dm_text(
        context={
            "intro_web_handoff": True,
            "intro_greeting_name": "Tibo Hagler",
            "intro_company_name": "Acme Corp",
            "intro_role": "Engineering Manager",
        },
    )
    assert "\u2014" not in t
    assert "Hey Tibo." in t
    assert "Continuing in Slack from what we already covered on the site." in t
    assert "Acme Corp" in t
    assert "Engineering Manager" in t


def test_intro_truncates_long_company() -> None:
    long_co = "X" * 200
    t = intro_dm_text(
        context={
            "intro_web_handoff": True,
            "intro_greeting_name": "Pat",
            "intro_company_name": long_co,
        },
    )
    assert "..." in t or len(t) < len(long_co) + 500

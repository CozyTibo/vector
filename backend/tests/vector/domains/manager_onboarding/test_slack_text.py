from vector.domains.manager_onboarding.engine.slack_text import normalize_manager_onboarding_outbound


def test_replaces_em_dash() -> None:
    t = normalize_manager_onboarding_outbound("Hello\u2014there")
    assert "\u2014" not in t
    assert "Hello, there" == t


def test_strips_got_it_opener() -> None:
    raw = "Got it \u2014 which Slack channels should I watch for your team?"
    out = normalize_manager_onboarding_outbound(raw)
    assert not out.lower().startswith("got it")
    assert "which slack channels" in out.lower()


def test_preserves_short_got_it_only() -> None:
    assert normalize_manager_onboarding_outbound("Got it.") == "Got it."


def test_strips_doc_parentheticals() -> None:
    raw = "Which channels? (or say skip) Pick a few."
    out = normalize_manager_onboarding_outbound(raw)
    assert "or say skip" not in out.lower()
    assert "which channels" in out.lower()


def test_collapses_stacked_got_it() -> None:
    raw = "Got it. Got it, which channels should I watch?"
    out = normalize_manager_onboarding_outbound(raw)
    assert out.lower().count("got it") <= 1
    assert "which channels" in out.lower()


def test_strips_thanks_opener_when_substance_follows() -> None:
    raw = "Thanks. Which channels should I keep an eye on for your team?"
    out = normalize_manager_onboarding_outbound(raw)
    assert not out.lower().startswith("thanks")
    assert "which channels" in out.lower()


def test_preserves_line_breaks_for_structured_examples() -> None:
    raw = "Which channels should I keep an eye on?\n\nExamples:\n#general\n#experiments"
    out = normalize_manager_onboarding_outbound(raw)
    assert "\n" in out
    assert "#general" in out
    assert "#experiments" in out

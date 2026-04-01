"""Unit tests for answer_normalize helpers."""

from __future__ import annotations

from vector.domains.onboarding.answer_normalize import (
    normalize_company_name,
    normalize_company_size,
    normalize_person_name,
    normalize_role,
    normalize_website,
)


def test_normalize_role_foundr() -> None:
    assert normalize_role("Foundr") == "Founder"
    assert normalize_role("foundr") == "Founder"


def test_normalize_role_unknown_maps_to_other() -> None:
    assert normalize_role("Head of Platform") == "Other"


def test_normalize_role_noisy_product_manager_typos() -> None:
    assert normalize_role("i'm a Prodct Managr") == "Product Manager"
    assert normalize_role("I am a product managr") == "Product Manager"


def test_normalize_role_manager_phrase() -> None:
    assert normalize_role("I'm a manager") == "Manager"
    assert normalize_role("manager") == "Manager"


def test_normalize_role_head_of_platform_stays_other() -> None:
    assert normalize_role("Head of Platform") == "Other"


def test_normalize_person_name_case() -> None:
    assert normalize_person_name("tibo") == "Tibo"


def test_normalize_company_name_case() -> None:
    assert normalize_company_name("ma super boite") == "Ma Super Boite"


def test_normalize_website() -> None:
    assert normalize_website("vector.so") == "https://vector.so"
    assert normalize_website("HTTPS://Vector.So/path") == "https://vector.so/path"


def test_normalize_company_size_synonyms() -> None:
    assert normalize_company_size("5 to 15") == "5-15"
    assert normalize_company_size("50+") == "50+"


def test_normalize_company_size_numeric_headcount() -> None:
    assert normalize_company_size("86") == "50+"
    assert normalize_company_size("12") == "5-15"
    assert normalize_company_size("3") == "1-5"
    assert normalize_company_size("about 200 people") == "50+"
    assert normalize_company_size("1,500") == "50+"

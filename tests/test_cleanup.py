"""Checks from specs/cleanup-dead-code.md."""

from pathlib import Path

import pytest

import app
import logic

ROOT = Path(app.__file__).parent
STATIC = ROOT / "static"


@pytest.mark.parametrize("text", ["1e2", "1E1", "1_0", "٣", "２", "0x10", "2.5.0", "", " ", ".", "1 0", "€4", "--3", "3-"])
def test_a_price_that_is_not_plain_digits_is_refused(text):
    with pytest.raises(logic.RejectedAction):
        logic.euros_to_cents(text)


@pytest.mark.parametrize("text, cents", [("4", 400), ("4.5", 450), ("4,01", 401), (" 2,50 ", 250), (".5", 50), ("0", 0), ("12.", 1200), ("+3", 300), ("-3", -300)])
def test_plain_prices_still_convert(text, cents):
    assert logic.euros_to_cents(text) == cents


@pytest.mark.parametrize("text", ["Infinity", "-inf", "NaN", "sNaN", "1e999"])
def test_non_finite_text_is_still_refused(text):
    with pytest.raises(logic.RejectedAction):
        logic.euros_to_cents(text)


def test_the_dead_code_is_gone():
    gone = ["playDay", "dayRunning", "btn-fast", "novaIsOpen", "rectCollider", "circleCollider",
            "drawColumnLine", "shift_day_ticks"]
    files = [*STATIC.rglob("*.js"), *STATIC.rglob("*.html"), ROOT / "app.py"]
    found = [(name, f.name) for f in files for name in gone if name in f.read_text(encoding="utf-8")]
    assert found == []
    assert "animating" not in (STATIC / "world" / "ui.js").read_text(encoding="utf-8")


def test_a_negative_price_is_refused_by_the_price_rule_with_its_own_words():
    import app
    client = app.app.test_client()
    response = client.post("/api/price_preview", json={"product": "coffee", "price": "-3"})
    assert response.status_code == 400  # the price rule: "must be more than 0", not a typing error


def test_the_old_specs_say_they_are_dropped():
    for name in ("employees", "investments", "multi-business", "net-worth"):
        assert (ROOT / "specs" / f"{name}.md").read_text(encoding="utf-8").startswith("> **Dropped.**")

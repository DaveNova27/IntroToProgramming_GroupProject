"""Price boundary regression checks without modifying the existing tests."""

import pytest

import app
import db
import logic


@pytest.mark.parametrize("price", ["Infinity", "-Infinity", "NaN", "sNaN", "1e999"])
def test_invalid_decimal_price_does_not_change_saved_run(tmp_path, monkeypatch, price):
    path = tmp_path / "run.db"
    state = logic.buy(logic.new_state(), "coffee", 15)
    state, _ = logic.trade_day(state)
    db.save(state, path)
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    monkeypatch.setattr(app.db, "save", lambda *_: pytest.fail("Rejected price was saved"))

    with pytest.raises(logic.RejectedAction):
        logic.euros_to_cents(price)
    response = app.app.test_client().post(
        "/api/price", json={"product": "coffee", "price": price}
    )
    assert response.status_code == 400
    assert response.get_json()["error"]
    assert response.get_json()["state"] == app.view(state)
    assert db.load(path) == state


@pytest.mark.parametrize("price, cents", [("4", 400), ("4.5", 450), ("4,01", 401)])
def test_valid_euro_amounts_still_convert(price, cents):
    assert logic.euros_to_cents(price) == cents

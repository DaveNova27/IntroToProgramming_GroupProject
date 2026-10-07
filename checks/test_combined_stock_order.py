"""Regression checks for specs/combined-stock-order.md."""

import copy

import pytest

import logic


def test_combined_order_updates_cash_and_every_selected_product():
    state = logic.new_state()

    ordered = logic.buy_many(state, {"sandwich": 10, "coffee": 10, "cookie": 10})

    assert ordered["cash"] == 6_700
    assert ordered["stock"] == {"sandwich": 10, "coffee": 10, "cookie": 10}
    assert state == logic.new_state()


def test_combined_order_can_skip_a_product_with_zero():
    ordered = logic.buy_many(
        logic.new_state(),
        {"sandwich": 5, "coffee": 0, "cookie": 10},
    )

    assert ordered["cash"] == 8_500
    assert ordered["stock"] == {"sandwich": 5, "coffee": 0, "cookie": 10}


def test_unaffordable_combined_order_is_all_or_nothing():
    state = logic.new_state()
    before = copy.deepcopy(state)

    with pytest.raises(logic.RejectedAction):
        logic.buy_many(state, {"sandwich": 50, "coffee": 1, "cookie": 1})

    assert state == before

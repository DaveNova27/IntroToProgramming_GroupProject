"""Leftovers of the outlook review: the editor panel knows the fixed weather."""

import app
import logic


def test_editor_info_names_the_fixed_weather_or_none():
    state = logic.new_state(987654321)
    assert app.editor_info(state)["weather_override"] is None
    fixed = logic.set_day_override(state, "storm")
    assert app.editor_info(fixed)["weather_override"] == "storm"

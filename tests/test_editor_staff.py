"""Checks from specs/editor-staff.md: the editor patch sets the employees."""

import pytest

import app
import logic


def rich_state():
    state = logic.new_state(1)
    state["cash"] = 1_000_000
    state = logic.editor_set_state(state, {"shops": {"cafe": {"level": 5}, "beach_cafe": {"level": 5}}})
    return state


def test_the_patch_sets_employees_with_level_and_working():
    state = rich_state()
    assert state["employees"] == []  # buying places through the editor hires nobody
    new = logic.editor_set_state(state, {"employees": [
        {"shop": "cafe", "place": 1, "level": 3},
        {"shop": "cafe", "place": 2, "working": False},
        {"shop": "beach_cafe", "place": 1},
    ]})
    assert [(e["shop"], e["place"], e["level"], e["working"], e["job"]) for e in new["employees"]] == [
        ("cafe", 1, 3, True, "refiller"), ("cafe", 2, 1, False, "seller"), ("beach_cafe", 1, 1, True, "refiller")]
    assert [e["id"] for e in new["employees"]] == [1, 2, 3] and new["employee_seq"] == 3
    # the new people work like hired ones: a day with them sells
    played, _ = logic.skip_shift(logic.open_day(logic.buy(new, "coffee", 20)))
    assert any(line["sold"] for line in played["history"][-1]["lines"])


def test_the_same_place_keeps_the_same_person_and_a_dismissed_id_is_not_reused():
    state = rich_state()
    first = logic.editor_set_state(state, {"employees": [{"shop": "cafe", "place": 1}]})
    again = logic.editor_set_state(first, {"employees": [{"shop": "cafe", "place": 1, "level": 3, "working": False}]})
    assert [(e["id"], e["name"], e["level"], e["working"]) for e in again["employees"]] == [
        (1, first["employees"][0]["name"], 3, False)]  # the same person, changed
    both = logic.editor_set_state(again, {"employees": [{"shop": "cafe", "place": 1}, {"shop": "cafe", "place": 2}]})
    assert [e["id"] for e in both["employees"]] == [1, 2]
    gone = logic.editor_set_state(both, {"employees": []})  # everybody dismissed
    assert gone["employees"] == []
    back = logic.editor_set_state(gone, {"employees": [{"shop": "cafe", "place": 1}]})
    assert [e["id"] for e in back["employees"]] == [3]  # a dismissed id is never used again


def test_a_partial_list_dismisses_the_rest():
    state = rich_state()
    full = logic.editor_set_state(state, {"employees": [
        {"shop": "cafe", "place": 1}, {"shop": "beach_cafe", "place": 1}]})
    partial = logic.editor_set_state(full, {"employees": [{"shop": "cafe", "place": 1}]})
    assert [e["shop"] for e in partial["employees"]] == ["cafe"]


def test_patched_employees_survive_save_and_load(tmp_path):
    import db
    state = logic.editor_set_state(rich_state(), {"employees": [
        {"shop": "cafe", "place": 1, "level": 2}, {"shop": "cafe", "place": 2, "working": False}]})
    db.save(state, tmp_path / "run.db")
    loaded = db.load(tmp_path / "run.db")
    assert loaded["employees"] == state["employees"] and loaded["employee_seq"] == state["employee_seq"] == 2


@pytest.mark.parametrize("employees", [
    "x", [1], [{"shop": "cafe"}], [{"shop": "cafe", "place": 1, "extra": 1}],
    [{"shop": "dragon", "place": 1}], [{"shop": "cafe", "place": 0}], [{"shop": "cafe", "place": 3}],
    [{"shop": "cafe", "place": True}], [{"shop": "surf_shop", "place": 1}],  # locked shop
    [{"shop": "cafe", "place": 1}, {"shop": "cafe", "place": 1}],
    [{"shop": "cafe", "place": 1, "level": 0}], [{"shop": "cafe", "place": 1, "level": 4}],
    [{"shop": "cafe", "place": 1, "level": 1.5}], [{"shop": "cafe", "place": 1, "working": "yes"}],
])
def test_a_bad_employee_list_is_refused_and_changes_nothing(employees):
    state = rich_state()
    before = repr(state)
    with pytest.raises(logic.RejectedAction):
        logic.editor_set_state(state, {"employees": employees})
    assert repr(state) == before


def test_a_place_that_is_not_bought_is_refused_and_lowering_shops_still_dismisses():
    state = logic.new_state(1)  # the Cafe has no places yet
    with pytest.raises(logic.RejectedAction):
        logic.editor_set_state(state, {"employees": [{"shop": "cafe", "place": 1}]})
    # shops and employees in one patch: the places come first
    both = logic.editor_set_state(state, {"shops": {"cafe": {"level": 5}}, "employees": [{"shop": "cafe", "place": 2}]})
    assert [e["place"] for e in both["employees"]] == [2]
    lowered = logic.editor_set_state(both, {"shops": {"cafe": {"level": 1}}})
    assert lowered["employees"] == []


def test_the_endpoint_needs_the_editor_switch_and_validates(monkeypatch, tmp_path):
    import db
    path = tmp_path / "run.db"
    db.save(rich_state(), path)
    monkeypatch.setattr(app, "load_run", lambda: db.load(path))
    real = db.save_new_run
    monkeypatch.setattr(app.db, "save_new_run", lambda state: real(state, path))
    client = app.app.test_client()
    body = {"patch": {"employees": [{"shop": "cafe", "place": 1, "level": 2}]}}
    monkeypatch.delenv("CT_EDITOR", raising=False)
    assert client.post("/api/editor/state", json=body).status_code == 400  # off
    assert db.load(path)["employees"] == []
    monkeypatch.setenv("CT_EDITOR", "1")
    ok = client.post("/api/editor/state", json=body)
    assert ok.status_code == 200
    assert ok.get_json()["state"]["staff"]["employees"][0]["level"] == 2
    bad = client.post("/api/editor/state", json={"patch": {"employees": [{"shop": "cafe", "place": 9}]}})
    assert bad.status_code == 400 and len(db.load(path)["employees"]) == 1

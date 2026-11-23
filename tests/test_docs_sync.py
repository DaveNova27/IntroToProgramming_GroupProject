"""Checks from specs/docs-sync.md ("Done when"): AGENTS.md names every module of the world and the files the
agents need to know, and three outdated sentences are gone."""

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WORLD = sorted(p.name for p in (ROOT / "static" / "world").glob("*.js"))


@pytest.mark.parametrize("module", WORLD)
def test_every_world_module_is_named_in_agents_md(module):
    assert f"`{module}`" in AGENTS, f"{module} is missing in AGENTS.md (Structure, static/world/)"


def test_the_shared_files_and_the_checks_folder_are_named():
    assert "`static/badges.css`" in AGENTS
    assert "`checks/`" in AGENTS and "new checks go in new files in `tests/`" in AGENTS


@pytest.mark.parametrize("old, where", [
    ("erased on restart for now", README),
    ("state of 2026-11-10", README),
    ("erases every run", APP),
])
def test_the_outdated_sentences_are_gone(old, where):
    assert old not in where

"""Checks from specs/docs-cleanup.md ("Done when"): the README keeps its sections in order, names every
route of the server and lists every spec in a grouped table with its pull request; the roadmap is v7 and
lists no built spec as open; AGENTS.md points to the game design and the Issues. Files only."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
ROADMAP = (ROOT / "docs" / "feature-roadmap.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

SECTIONS = ["Group", "Run", "Putting it online", "How it fits together", "Working in the group", "Specs",
            "Known issues and ideas"]


def spec_rows():
    """(spec file, PR cell, description) of every row of the README's spec tables."""
    start = README.index("## Specs\n")
    end = README.index("## Known issues and ideas")
    rows = []
    for line in README[start:end].splitlines():
        m = re.match(r"\| \[`([\w-]+\.md)`\]\(specs/\1\) \| (.*?) \| (.*) \|$", line)
        if m:
            rows.append(m.groups())
    return rows


def test_the_readme_keeps_its_sections_in_order():
    found = re.findall(r"^## (.+)$", README, re.M)
    assert found == SECTIONS


def test_every_route_of_the_server_is_named_in_the_readme():
    routes = set(re.findall(r'@app\.(?:route|get|post)\("([^"]+)"', APP)) - {"/"}
    assert len(routes) >= 30  # the parse found the routes
    missing = sorted(r for r in routes if f"`{r}`" not in README and f"`GET {r}`" not in README
                     and f"`POST {r}`" not in README)
    assert not missing, missing


def test_every_spec_is_in_a_grouped_table_with_its_pull_request():
    rows = spec_rows()
    files = {p.name for p in (ROOT / "specs").glob("*.md")}
    dropped = {"employees.md", "investments.md", "multi-business.md", "net-worth.md"}
    assert {name for name, _, _ in rows} == files - dropped
    assert len(re.findall(r"^### ", README[README.index("## Specs"):README.index("## Known issues")], re.M)) >= 4
    for name, pr, _ in rows:
        assert pr == "–" or re.fullmatch(r"#\d+(, #\d+)*", pr), (name, pr)


@pytest.mark.parametrize("name, pr, description", spec_rows())
def test_each_spec_says_what_it_does_in_at_most_400_characters(name, pr, description):
    assert 0 < len(description) <= 400, (name, len(description))


@pytest.mark.parametrize("doc", [README, ROADMAP], ids=["README", "roadmap"])
def test_no_doc_says_one_shift_per_day(doc):
    text = doc.lower()
    assert "one shift per day" not in text and "the one shift of the day" not in text


def test_the_roadmap_is_v7_and_lists_no_built_spec_as_open():
    assert ROADMAP.startswith("# Campus Tycoon: Feature Roadmap (v7)")
    assert "state of 2026-11-23" in ROADMAP.split("\n\n")[1]
    built_start = ROADMAP.index("### What is built (merged)")
    built_table = ROADMAP[built_start:ROADMAP.index("### What we took from Felix")]
    built = {name for cell in re.findall(r"^\| ([^|]+) \|", built_table, re.M)
             for name in re.findall(r"`([\w-]+)`", cell)}  # the first column only
    open_start = ROADMAP.index("### 4.1 Open specs")
    open_table = ROADMAP[open_start:ROADMAP.index("### 4.2", open_start)]
    open_specs = set(re.findall(r"^\| `([\w-]+)` \|", open_table, re.M))  # "`staff` follow-up" is a follow-up, not the spec
    assert open_specs and not (open_specs & built), open_specs & built
    status = ROADMAP[ROADMAP.index("## 5. Issue status"):ROADMAP.index("## 6.")]
    closed = set(re.findall(r"#(\d+)", next(l for l in status.splitlines() if l.startswith("| Closed, built"))))
    still_open = set(re.findall(r"#(\d+)", next(l for l in status.splitlines() if l.startswith("| Open"))))
    assert still_open == {"11", "20", "24", "40"} and not (still_open & closed)


def test_agents_md_points_to_the_game_design_and_the_issues():
    line = next(l for l in AGENTS.splitlines() if l.startswith("- `docs/feature-roadmap.md`"))
    assert "Read Part B before starting a spec" in line and "GitHub Issues" in line

"""Checks from specs/docs-cleanup.md ("Done when"): the README keeps its sections in order, names every
route of the server and lists the specs in grouped tables with their pull requests; the roadmap's
header agrees with itself and lists nothing as both built and open; AGENTS.md points to the game design,
the security rules and the Issues. Files only (plus the server's route table).

After the AI review these check rules that stay true, not today's values: closing an issue or writing
roadmap v8 must not need a change to this file."""

import re
from pathlib import Path

import app

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
ROADMAP = (ROOT / "docs" / "feature-roadmap.md").read_text(encoding="utf-8")
AGENTS = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

SECTIONS = ["Group", "Run", "Putting it online", "How it fits together", "Working in the group", "Specs",
            "Known issues and ideas"]


def between(text, start, end):
    """The part of `text` from the heading `start` to the next `end`; fails clearly if one is missing."""
    assert start in text, f"{start!r} is missing"
    i = text.index(start)
    assert end in text[i:], f"{end!r} is missing after {start!r}"
    return text[i:text.index(end, i)]


def spec_rows():
    """(spec file, PR cell, description) of every row of the README's spec tables."""
    part = between(README, "## Specs", "## Known issues and ideas")
    return [m.groups() for m in re.finditer(r"^\| \[`([\w-]+\.md)`\]\(specs/\1\) \| (.*?) \| (.*) \|$", part, re.M)]


def test_the_readme_keeps_its_sections_in_order():
    found = re.findall(r"^## (.+)$", README, re.M)
    assert all(s in found for s in SECTIONS), [s for s in SECTIONS if s not in found]
    assert [s for s in found if s in SECTIONS] == SECTIONS  # in this order; more sections are fine


def test_every_route_of_the_server_is_named_in_the_readme():
    routes = {rule.rule for rule in app.app.url_map.iter_rules() if rule.endpoint != "static"} - {"/"}
    assert len(routes) >= 30
    missing = sorted(r for r in routes if not re.search(rf"`(?:GET |POST )?{re.escape(r)}`", README))
    assert not missing, missing


def test_the_specs_stand_in_grouped_tables_with_their_pull_requests():
    rows = spec_rows()
    assert rows, "no spec rows found under ## Specs"
    groups = re.findall(r"^### ", between(README, "## Specs", "## Known issues and ideas"), re.M)
    assert len(groups) >= 4
    files = {p.name for p in (ROOT / "specs").glob("*.md")}
    assert not {name for name, _, _ in rows} - files  # no row links to a spec that is not there
    bad = [(name, pr) for name, pr, _ in rows if not (pr == "–" or re.fullmatch(r"#\d+(, #\d+)*", pr))]
    assert not bad, bad


def test_each_spec_says_what_it_does_in_at_most_400_characters():
    too_long = [(name, len(d)) for name, _, d in spec_rows() if not 0 < len(d) <= 400]
    assert not too_long, too_long


def test_no_doc_says_one_shift_per_day():
    for name, doc in (("README", README), ("roadmap", ROADMAP)):
        text = doc.lower()
        assert "one shift per day" not in text and "the one shift of the day" not in text, name


def test_the_roadmaps_header_agrees_with_itself():
    title = re.match(r"# Campus Tycoon: Feature Roadmap \(v(\d+)\)\n", ROADMAP)
    assert title, "the first line names the version"
    status = re.search(r"^Status: roadmap v(\d+), state of (\d{4}-\d{2}-\d{2})", ROADMAP, re.M)
    assert status and status.group(1) == title.group(1)


def test_the_roadmap_lists_nothing_as_both_built_and_open():
    built_table = between(ROADMAP, "### What is built (merged)", "### What we took from Felix")
    built = {name for cell in re.findall(r"^\| ([^|]+) \|", built_table, re.M)
             for name in re.findall(r"`([\w-]+)`", cell)}  # the first column only
    open_table = between(ROADMAP, "### 4.1 Open specs", "### 4.2")
    open_specs = set(re.findall(r"^\| `([\w-]+)` \|", open_table, re.M))  # "`staff` follow-up" is a follow-up
    assert not open_specs & built, open_specs & built
    status = between(ROADMAP, "## 5. Issue status", "## 6.")
    rows = {line.split("|")[1].strip(): set(re.findall(r"#(\d+)", line.split("|")[2]))
            for line in status.splitlines() if line.startswith("| ") and line.count("|") >= 3}
    closed = rows.get("Closed, built", set()) | rows.get("Closed, dropped", set())
    assert closed and not rows.get("Open", set()) & closed, rows.get("Open", set()) & closed


def test_agents_md_points_to_the_game_design_the_security_rules_and_the_issues():
    line = next(l for l in AGENTS.splitlines() if l.startswith("- `docs/feature-roadmap.md`"))
    assert "Part B" in line and "security rules in section 3" in line and "GitHub Issues" in line

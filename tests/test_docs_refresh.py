"""Checks from specs/docs-refresh.md ("Done when"): the README matches the game, the CI actions are
pinned to commit SHAs, Dependabot is set up. Files only: nothing here runs the game.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text()
WORKFLOWS = ROOT / ".github" / "workflows"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"


def test_the_name_is_spelled_right():
    assert "Felix Antes" not in README
    assert README.count("Felix Anthes") >= 2  # the members table and the campus description


def test_every_spec_file_is_named_in_the_readme():
    missing = [p.name for p in sorted((ROOT / "specs").glob("*.md")) if f"`{p.name}`" not in README]
    assert not missing, missing


def test_the_dropped_specs_are_marked_dropped():
    row = next(line for line in README.splitlines() if "`investments.md`" in line)
    assert "Dropped" in row
    for name in ("employees.md", "multi-business.md", "net-worth.md"):
        assert f"`{name}`" in row


def known_issues():
    start = README.index("## Known issues and ideas")
    return README[start:]


def test_the_outdated_known_issues_are_fixed():
    issues = known_issues()
    ideas = next(line for line in issues.splitlines() if line.startswith("- Ideas not yet a spec"))
    assert "wear the clothes" not in ideas and "merch-wear" in ideas  # built, no longer an idea
    assert "Supply Hall (`order-at-warehouse`)" in issues  # ordering happens there now
    assert "Cafe, Merchandise and the three printers in the Nova are places only" not in issues
    assert "`WORK_SPOTS`" in issues and "`PLACES` in `world.py`" in issues
    assert "Only the Cafe has figures in the world so far" in issues  # still true, so it stays


def uses_lines():
    return [line.strip() for path in sorted(WORKFLOWS.glob("*.yml")) for line in path.read_text().splitlines()
            if re.match(r"\s*(-\s*)?uses:", line)]


def test_every_action_is_pinned_to_a_full_commit_sha():
    lines = uses_lines()
    assert lines  # the workflow uses actions
    for line in lines:
        assert re.search(r"uses:\s*[\w.-]+/[\w.-]+@[0-9a-f]{40}\s+#\s*v\d+\.\d+\.\d+$", line), line


def test_the_same_actions_stay_and_the_required_job_id_too():
    # only which actions, not their SHAs: a Dependabot update of a pin must not fail this check
    text = (WORKFLOWS / "tests.yml").read_text()
    actions = sorted(re.findall(r"uses:\s*([\w.-]+/[\w.-]+)@", text))
    assert actions == ["actions/checkout", "astral-sh/setup-uv"]
    assert re.search(r"^jobs:\n(?:\s*#.*\n)*  pytest:\n", text, re.M)  # the required check of main


def test_dependabot_checks_the_packages_and_the_actions_weekly():
    text = DEPENDABOT.read_text()
    assert re.search(r"^version: 2$", text, re.M)
    entries = re.split(r"\n  - ", text.split("updates:", 1)[1])[1:]
    ecosystems = {re.search(r'package-ecosystem: "([\w-]+)"', e).group(1): e for e in entries}
    assert set(ecosystems) == {"uv", "github-actions"}
    for entry in ecosystems.values():
        assert 'directory: "/"' in entry
        assert 'interval: "weekly"' in entry
        assert "open-pull-requests-limit: 3" in entry
        # review finding: no major versions (they can break the CI or, merged, the live site)
        assert re.search(r'dependency-name: "\*"\s+update-types: \["version-update:semver-major"\]', entry)

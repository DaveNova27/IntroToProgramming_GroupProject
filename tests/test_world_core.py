"""Checks from specs/world-core.md ("Done when"). One test per check."""

import re
from pathlib import Path

import pytest

import app

STATIC = Path(app.__file__).parent / "static"
WORLD = STATIC / "world"
MODULES = sorted(WORLD.glob("*.js"))
PAGES = sorted(STATIC.glob("*.html"))
CODE = MODULES + sorted(STATIC.glob("*.js")) + sorted(STATIC.glob("*.css")) + PAGES


@pytest.fixture
def client():
    return app.app.test_client()


# ---- Check 1: everything loads from this server --------------------------------

def test_the_main_page_opens_with_the_campus_frame(client):
    page = client.get("/").get_data(as_text=True)
    assert 'src="/map?embed=1"' in page


def test_the_campus_page_is_served_and_starts_the_world(client):
    page = client.get("/map?embed=1").get_data(as_text=True)
    assert 'id="world"' in page
    assert 'src="/static/world/main.js"' in page


def test_the_map_address_leads_to_the_main_page(client):
    response = client.get("/map")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.name)
def test_every_module_is_served_as_javascript(client, module):
    response = client.get(f"/static/world/{module.name}")
    assert response.status_code == 200
    assert "javascript" in response.content_type


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.name)
def test_every_import_resolves_to_an_exported_name(module):
    for names, target in re.findall(r'import \{([^}]*)\} from "\./([\w-]+\.js)"', module.read_text()):
        exporter = (WORLD / target).read_text()
        for name in re.split(r"\s*,\s*", names.strip().rstrip(",")):
            assert re.search(rf"export (?:async )?(?:function|const|let) {name}\b", exporter), f"{name} in {target}"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_local_file_of_a_page_exists(page):
    for path in re.findall(r'(?:src|href)="/static/([^"]+)"', page.read_text()):
        assert (STATIC / path).is_file(), path


@pytest.mark.parametrize("path", CODE, ids=lambda p: p.name)
def test_nothing_loads_from_outside_this_app(path):
    text = path.read_text()
    assert not re.search(r"""(?:src|href)=["']https?:""", text)
    assert not re.search(r"""(?:fetch\(|import\(|from )["']https?:""", text)
    assert not re.search(r"@import|url\(\s*[\"']?https?:", text)
    assert "importmap" not in text


@pytest.mark.parametrize("module", MODULES, ids=lambda m: m.name)
def test_the_world_has_no_unseeded_randomness(module):
    assert "Math.random" not in module.read_text()


def test_the_old_three_js_map_is_gone():
    assert not (STATIC / "map.js").exists()
    assert "three" not in (STATIC / "map.html").read_text().lower()

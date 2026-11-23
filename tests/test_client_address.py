"""Checks from specs/client-address.md ("Done when"): behind the trusted proxy the visitor is the entry
Cloudflare wrote, PROXY_HOPS + 1 from the right of X-Forwarded-For (measured in Render's log: three
entries, the visitor first), but only when Render received the request from a Cloudflare address; nothing a
visitor sends moves it, and first visits from many addresses cannot fill the counters."""

import inspect
import logging

import pytest

import app
import pgstore

VISITOR = "203.0.113.7"
EDGE = "172.70.1.2"      # inside Cloudflare's 172.64.0.0/13: the address Render received the request from
RENDER = "10.0.0.1"      # Render's own proxy
CHAIN = f"{VISITOR}, {EDGE}, {RENDER}"  # as measured: the visitor first, then Render's two entries


@pytest.fixture
def proxy(monkeypatch):
    monkeypatch.setenv("CT_PROXY", "1")


def address_of(headers, remote="192.0.2.50"):
    with app.app.test_request_context("/", headers=headers, environ_base={"REMOTE_ADDR": remote}):
        return app.client_address()


# ---- the measured chain ----------------------------------------------------------------------------------

def test_the_measured_chain_gives_the_visitor(proxy):
    assert app.PROXY_HOPS == 2
    assert address_of({"X-Forwarded-For": CHAIN}) == VISITOR


def test_two_visitors_behind_the_same_proxies_count_apart_and_one_visitor_counts_once(proxy):
    other = address_of({"X-Forwarded-For": f"198.51.100.77, {EDGE}, {RENDER}"})
    assert other == "198.51.100.77" and other != address_of({"X-Forwarded-For": CHAIN})
    via_another_edge = address_of({"X-Forwarded-For": f"{VISITOR}, 104.16.5.9, 10.0.0.9"})
    assert via_another_edge == VISITOR


@pytest.mark.parametrize("sent", [
    "1.1.1.1",                      # one address written by the visitor
    "1.1.1.1, 9.9.9.9, 8.8.8.8",    # a whole made-up chain
    "not-an-address",
])
def test_what_a_visitor_writes_on_the_left_does_not_move_the_address(proxy, sent):
    # Cloudflare appends to whatever the visitor sent: their entries end up left of the measured three
    assert address_of({"X-Forwarded-For": f"{sent}, {CHAIN}"}) == VISITOR


def test_a_forged_cf_connecting_ip_is_ignored(proxy):
    assert address_of({"X-Forwarded-For": CHAIN, "CF-Connecting-IP": "1.2.3.4",
                       "True-Client-IP": "5.6.7.8"}) == VISITOR


@pytest.mark.parametrize("forwarded, expected", [
    ("198.51.100.9", "198.51.100.9"),                 # one entry: the last one, as before
    ("198.51.100.9, 10.0.0.1", "10.0.0.1"),           # two entries: the last one, as before
])
def test_a_shorter_chain_keeps_the_old_rule(proxy, forwarded, expected):
    assert address_of({"X-Forwarded-For": forwarded}) == expected


def test_no_entry_means_the_connections_address(proxy):
    assert address_of({}, remote="192.0.2.50") == "192.0.2.50"
    assert address_of({"X-Forwarded-For": " , "}, remote="192.0.2.50") == "192.0.2.50"


def test_without_the_trusted_proxy_the_headers_are_ignored(monkeypatch):
    monkeypatch.delenv("CT_PROXY", raising=False)
    assert address_of({"X-Forwarded-For": CHAIN, "CF-Connecting-IP": VISITOR}, remote="192.0.2.50") == "192.0.2.50"


def test_ipv6_counts_by_its_64_network_and_spellings_count_once(proxy):
    one = address_of({"X-Forwarded-For": f"2001:db8:1:2::10, {EDGE}, {RENDER}"})
    two = address_of({"X-Forwarded-For": f"2001:0db8:0001:0002:ffff:0:0:1, {EDGE}, {RENDER}"})
    elsewhere = address_of({"X-Forwarded-For": f"2001:db8:1:3::10, {EDGE}, {RENDER}"})
    assert one == two == "2001:db8:1:2::/64" and elsewhere == "2001:db8:1:3::/64"
    mapped = address_of({"X-Forwarded-For": f"::ffff:{VISITOR}, {EDGE}, {RENDER}"})
    assert mapped == VISITOR  # an IPv4 address written as IPv6 is that IPv4 address
    via_v6_edge = address_of({"X-Forwarded-For": f"{VISITOR}, 2606:4700::6810:1, {RENDER}"})
    assert via_v6_edge == VISITOR  # Cloudflare's IPv6 ranges count too


def test_an_entry_that_is_no_address_falls_back_to_the_last_entry(proxy):
    assert address_of({"X-Forwarded-For": f"unknown, {EDGE}, {RENDER}"}) == RENDER


# ---- review finding 3: a port written with an entry ------------------------------------------------------

def test_a_port_with_an_entry_is_dropped(proxy):
    assert address_of({"X-Forwarded-For": f"{VISITOR}:51234, {EDGE}:443, {RENDER}"}) == VISITOR
    assert address_of({"X-Forwarded-For": f"[2001:db8:1:2::10]:443, {EDGE}, {RENDER}"}) == "2001:db8:1:2::/64"


# ---- review finding 4: only a chain that Render received from Cloudflare is trusted ---------------------

def test_a_request_that_did_not_come_through_cloudflare_keeps_the_coarse_rule(proxy):
    # Render received it from an address outside Cloudflare: whoever sent it wrote the entries before it
    assert address_of({"X-Forwarded-For": f"{VISITOR}, 198.51.100.1, {RENDER}"}) == RENDER


def test_writing_a_cloudflare_address_yourself_does_not_help(proxy):
    # straight to Render with a made-up chain: Render adds the sender's real address after the fake edge
    forged = address_of({"X-Forwarded-For": f"1.2.3.4, 104.16.0.1, 198.51.100.66, {RENDER}"})
    assert forged == RENDER


def test_cloudflares_published_ranges_are_all_there():
    assert len(app.CLOUDFLARE_NETWORKS) == 22
    assert app._from_cloudflare("173.245.48.1") and app._from_cloudflare("2c0f:f248::1")
    assert not app._from_cloudflare("198.51.100.1") and not app._from_cloudflare("nonsense")


# ---- review finding 2: many first visits cannot fill the counters ----------------------------------------

def test_first_visits_from_many_addresses_share_one_budget_once_half_the_counters_are_used(monkeypatch):
    monkeypatch.setattr(app, "MAX_KEYS", 6)
    monkeypatch.setattr(app, "_last_sweep", [0.0])
    app._hits.clear()
    overflow = ("new", "many addresses")
    for i in range(3):  # up to half of MAX_KEYS: each address its own budget
        assert app._too_many(("new", f"10.1.0.{i}"), 1, overflow) is False
    assert app._too_many(("new", "10.1.0.9"), 1, overflow) is False  # counted under the shared key
    assert overflow in app._hits and ("new", "10.1.0.9") not in app._hits
    assert app._too_many(("new", "10.1.0.10"), 1, overflow) is True  # the shared budget is used up
    # the players' own keys still have the other half: nobody gets "busy" because of the strangers
    assert app._too_many(("player", "P" * 22), 5) is False
    assert app._too_many(("player", "Q" * 22), 5) is False
    app._hits.clear()


def test_the_first_visit_uses_the_shared_budget(proxy):
    source = inspect.getsource(app._identify_player)
    assert 'NEW_PLAYER_LIMIT, overflow=("new", "many addresses")' in source


# ---- review finding 1 and the check in the log -----------------------------------------------------------

def test_the_measurement_line_stays_and_says_so():
    doc = inspect.getsource(app._log_proxy_chain)
    assert "Removed again once that is decided" not in doc and "It stays" in doc


@pytest.mark.parametrize("edge, expected", [
    (EDGE, "client address: entry 2 from the right is a Cloudflare address; the visitor is taken from entry 3 from the right"),
    ("198.51.100.1", "client address: entry 2 from the right is not a Cloudflare address; the visitor is taken from the last entry"),
])
def test_the_log_says_what_the_rule_makes_of_the_chain_without_an_address(proxy, monkeypatch, tmp_path, caplog, edge, expected):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    monkeypatch.setattr(app, "_chain_logged", [0])
    app._hits.clear()
    caplog.set_level(logging.WARNING)
    app.app.test_client().get("/", headers={"X-Forwarded-For": f"{VISITOR}, {edge}, {RENDER}"})
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("client address:")]
    assert lines == [expected]
    for record in caplog.records:
        for address in (VISITOR, edge, RENDER):
            assert address not in record.getMessage()


# ---- end to end ------------------------------------------------------------------------------------------

def test_end_to_end_the_limit_brakes_each_visitor_on_their_own(proxy, monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pgstore.reset()
    monkeypatch.setenv("CT_PUBLIC", "1")
    monkeypatch.setattr(app, "PLAYERS_DIR", tmp_path / "players")
    monkeypatch.setattr(app, "NEW_PLAYER_LIMIT", 1)
    app._hits.clear()
    first = app.app.test_client().get("/", headers={"X-Forwarded-For": CHAIN})
    assert first.status_code == 200
    # a second visitor behind the very same proxies: before this spec they shared one budget
    second = app.app.test_client().get("/", headers={"X-Forwarded-For": f"198.51.100.77, {EDGE}, {RENDER}"})
    assert second.status_code == 200
    again = app.app.test_client().get("/", headers={"X-Forwarded-For": f"9.9.9.9, {CHAIN}"})  # same visitor
    assert again.status_code == 429
    pgstore.reset()

"""The ``bsmm`` command line, driven with typer's CliRunner.

Every command that talks to the API is run against a REAL server (uvicorn on an ephemeral localhost port, from
``tests/live.py``) whose context reaches simulated miners; the command line itself is a blocking, synchronous client, so it
is run in a worker thread to keep the in-process server responsive. Nothing here starts a background process: commands that
would (``start``, ``serve``, ``setup`` without ``--url``) are either not run or are pointed at a running test server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

import httpx
import pytest
import typer
from click.testing import Result
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
from typer.testing import CliRunner

import bsmm.cli.main as cli_main
from bsmm import __version__
from bsmm.api.app import create_app
from bsmm.auth import AuthService
from bsmm.cli.client import CliError
from bsmm.cli.main import app
from bsmm.config import RuntimeConfig
from bsmm.drivers import registry
from bsmm.engine.network import NetworkState
from bsmm.settings import SettingsService
from bsmm.sim.axeos import AxeOSSim
from bsmm.storage.store import Store

from .live import serve

ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
PASSWORD = "correct horse battery"
ENV: dict[str, str | None] = {
    # a wide terminal so tables are not squeezed; nothing from the developer's own environment leaks in
    "COLUMNS": "200", "BSMM_URL": None, "BSMM_TOKEN": None, "BSMM_DATA_DIR": None, "BSMM_PORT": None,
    "BSMM_ADMIN_PASSWORD": None, "BSMM_RPC_USER": None, "BSMM_RPC_PASSWORD": None,
}
runner = CliRunner()


async def cli(*args: str, env: dict[str, str | None] | None = None, stdin: str | None = None) -> Result:
    """Run ``bsmm <args>`` like a shell would, on a worker thread (the test's event loop keeps serving requests).

    A command that fails on purpose exits through ``SystemExit``; anything else escaping a command is a crash, and is
    reported as one rather than as an ordinary non-zero exit code. ``stdin`` is what the user types at prompts.
    """
    res = await asyncio.to_thread(runner.invoke, app, list(args), input=stdin, env={**ENV, **(env or {})})
    if res.exception is not None and not isinstance(res.exception, SystemExit):
        raise AssertionError(f"`bsmm {' '.join(args)}` crashed with {res.exception!r}\nstdout: {res.stdout}\nstderr: {res.stderr}") from res.exception
    return res


def jout(res: Result) -> Any:
    """The command's whole stdout must be one JSON document (that is the point of --json)."""
    assert res.exit_code == 0, f"exit {res.exit_code}\nstdout: {res.stdout}\nstderr: {res.stderr}"
    return json.loads(res.stdout)


def flat(text: str) -> str:
    return " ".join(text.split())


def dead_url() -> str:
    """An address where nothing listens (a port that was just free)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return f"http://127.0.0.1:{port}"


class Server:
    def __init__(self, base: str, ctx, hosts) -> None:
        self.base = base
        self.ctx = ctx
        self.hosts = hosts

    async def miner(self, host: str = "gamma.test", *, name: str | None = None, seed: int = 1, mac: str = "AA:BB:CC:00:00:11"):
        self.hosts[host] = AxeOSSim("gamma", seed=seed, mac=mac).app()
        res = await self.ctx.fleet.add_by_host(host, drivers=["axeos"], name=name)  # (not the cgminer driver: it would resolve host names)
        await self.ctx.fleet._poll_once(self.ctx.fleet.runtimes[res.device.id])
        return res.device

    def network(self) -> None:
        self.ctx.network.state = NetworkState(available=True, source="test", height=972_175, difficulty=140_577_680_051_919.6,
                                              network_hashrate_hs=1.03e21, block_reward_btc=3.2, btc_price=82_000.0)

    async def lock(self) -> None:
        await self.ctx.auth.set_password(PASSWORD)
        await self.ctx.settings.update({"auth": {"mode": "password"}})

    @property
    def data_dir(self) -> str:
        return str(self.ctx.config.data_dir)


@pytest.fixture
async def server(lan, monkeypatch):
    ctx, hosts = lan
    monkeypatch.delitem(registry.DRIVER_CLASSES, "cgminer")  # fake host names must not be handed to the raw-socket driver
    async with serve(create_app(ctx=ctx)) as base:  # type: ignore[arg-type]
        yield Server(base, ctx, hosts)


@pytest.fixture
def quick(monkeypatch):
    """The commands poll a scan once a second; make that tick fast."""
    real_sleep = time.sleep
    monkeypatch.setattr(cli_main, "time", types.SimpleNamespace(sleep=lambda s: real_sleep(min(s, 0.005)), time=time.time))


# --- reading ----------------------------------------------------------------------------------------------------------------------------


async def test_list_json_returns_the_miners_with_live_readings(server):
    assert jout(await cli("list", "--json", "--url", server.base)) == []
    dev = await server.miner(name="Garage")
    devices = jout(await cli("list", "--json", "--url", server.base))
    assert [d["id"] for d in devices] == [dev.id]
    d = devices[0]
    assert (d["name"], d["status"], d["host"], d["family"]) == ("Garage", "online", "gamma.test", "bitaxe")
    assert d["telemetry"]["hashrate_hs"] > 1e12 and d["hashrate_smooth_hs"] > 1e12


async def test_list_can_filter_by_status(server):
    await server.miner(name="Garage")
    assert len(jout(await cli("list", "--json", "--status", "online", "--url", server.base))) == 1
    assert jout(await cli("list", "--json", "--status", "offline", "--url", server.base)) == []


async def test_list_prints_a_table_for_humans(server):
    empty = await cli("list", "--url", server.base)
    assert empty.exit_code == 0 and "No miners yet" in empty.stdout and "bsmm discover --add" in empty.stdout
    await server.miner(name="Garage")
    res = await cli("list", "--url", server.base)
    out = flat(res.stdout)
    assert res.exit_code == 0 and res.stderr == ""
    assert "Garage" in out and "Bitaxe Gamma" in out and "gamma.test" in out and "online" in out and "TH/s" in out and " W" in out


async def test_status_json_is_the_overview(server):
    await server.miner(name="Garage")
    o = jout(await cli("status", "--json", "--url", server.base))
    assert o["summary"]["devices_total"] == 1 and o["summary"]["devices_online"] == 1 and o["summary"]["hashrate_hs"] > 1e12
    assert o["odds"]["available"] is False and o["alerts"] == [] and o["blocks_found"] == [] and o["demo"] is False
    assert {"summary", "odds", "network", "alerts", "events", "blocks_found", "leaderboard"} <= set(o)
    server.network()
    o = jout(await cli("status", "--json", "--url", server.base))
    assert o["odds"]["available"] is True and o["network"]["height"] == 972_175


async def test_status_tells_a_human_what_matters(server):
    ctx = server.ctx
    await server.miner(name="Garage")
    server.network()
    plain = flat((await cli("status", "--url", server.base)).stdout)
    assert "1/1 miners online" in plain and "Hashrate" in plain and "TH/s" in plain
    assert "Block 972,175" in plain and "source: test" in plain and "Chance of a block this year:" in plain
    # an offline miner, an active alert and a block you found all show up
    server.hosts.pop("gamma.test")
    rt = next(iter(ctx.fleet.runtimes.values()))
    for _ in range(3):
        await ctx.fleet._poll_once(rt)
    await ctx.alerts.ensure_default_rules()
    await ctx.alerts.update_rule("rule_device_offline", {"params": {"for_s": 0}})
    await ctx.alerts.tick(time.time())
    await ctx.store.add_block_found(hash_="ab" * 32, height=972_000, ts=time.time(), device_id=None, address=ADDR, reward_sats=312_500_000, source="chain")
    o = jout(await cli("status", "--json", "--url", server.base))
    assert [a["title"] for a in o["alerts"]] == ["Garage is offline"] and len(o["blocks_found"]) == 1
    plain = flat((await cli("status", "--url", server.base)).stdout)
    assert "0/1 miners online" in plain and "1 offline" in plain and "! Garage is offline" in plain
    assert "You have found 1 block(s)!" in plain


async def test_odds_json_without_and_with_network_data(server):
    await server.miner()
    unknown = jout(await cli("odds", "--json", "--url", server.base))
    assert unknown["available"] is False and "difficulty is not known" in unknown["reason"]
    assert "difficulty is not known" in flat((await cli("odds", "--url", server.base)).stdout)
    server.network()
    live = jout(await cli("odds", "--json", "--url", server.base))
    assert live["available"] is True and live["live"] is True and 0 < live["horizons"]["year"]["probability"] < 1e-3
    what_if = jout(await cli("odds", "--json", "--hashrate-ths", "1000", "--difficulty", "1e14", "--url", server.base))
    assert what_if["live"] is False and what_if["hashrate"] == 1000e12 and what_if["difficulty"] == 1e14
    assert what_if["horizons"]["year"]["probability"] > live["horizons"]["year"]["probability"] * 100


async def test_odds_prints_a_table_and_plain_english(server):
    await server.miner()
    server.network()
    plain = flat((await cli("odds", "--url", server.base)).stdout)
    for row in ("day", "month", "year", "five years", "ten years"):
        assert row in plain
    assert "Within" in plain and "Chance" in plain and "1 in" in plain and "Expected wait:" in plain
    assert "of the network's hashrate" in plain  # the plain-English lines


async def test_odds_rejects_nonsense_input(server):
    res = await cli("odds", "--hashrate-ths=-5", "--url", server.base)
    assert res.exit_code == 1 and res.stdout == "" and "Error:" in res.stderr


async def test_version_and_help_need_no_server():
    res = await cli("version")
    assert res.exit_code == 0 and res.stdout.strip() == __version__
    helped = await cli("--help")
    assert helped.exit_code == 0
    for command in ("serve", "start", "stop", "status", "list", "odds", "doctor", "discover", "add", "setup", "token", "password", "mcp"):
        assert command in helped.stdout


# --- add / discover ----------------------------------------------------------------------------------------------------------------------


async def test_add_creates_a_miner_and_a_second_add_says_it_is_known(server):
    server.hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    first = jout(await cli("add", "gamma.test", "--name", "Garage", "--json", "--url", server.base))
    assert first["created"] is True and first["device"]["name"] == "Garage" and first["device"]["model"] == "Bitaxe Gamma"
    assert [v.name for v in server.ctx.fleet.views()] == ["Garage"]
    again = jout(await cli("add", "gamma.test", "--json", "--url", server.base))
    assert again["created"] is False and "already being monitored" in again["note"]
    human = await cli("add", "gamma.test", "--url", server.base)
    assert human.exit_code == 0 and "Garage is already being monitored." in flat(human.stdout)


async def test_add_says_what_it_did_in_words(server):
    server.hosts["nerd.test"] = AxeOSSim("nerdqaxe", seed=2, mac="AA:BB:CC:00:00:22").app()
    res = await cli("add", "nerd.test", "--name", "Shed", "--url", server.base)
    assert res.exit_code == 0 and flat(res.stdout) == "Added Shed (NerdQAxe++)."


async def test_add_explains_when_nothing_answers(server):
    res = await cli("add", "nowhere.test", "--url", server.base)
    assert res.exit_code == 1 and res.stdout == ""
    err = flat(res.stderr)
    assert err.startswith("Error: Nothing at nowhere.test looks like a supported miner.")
    assert "Open the miner's own web page in a browser" in err  # the hint


async def test_add_refuses_a_malformed_address(server):
    res = await cli("add", "not a host!", "--url", server.base)
    assert res.exit_code == 1 and "Error:" in res.stderr and "is not a valid host name" in flat(res.stderr)


@pytest.fixture
def lan_sweep(monkeypatch):
    """The scan's TCP sweep, answering 'open' on port 80 of the simulated miners only; the protocol probes stay real."""
    import bsmm.engine.discovery as discovery

    open_ports: set[tuple[str, int]] = set()

    async def fake_tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
        return (host, port) in open_ports

    monkeypatch.setattr(discovery, "tcp_open", fake_tcp_open)
    monkeypatch.setattr(discovery, "own_ipv4_addresses", set)
    return open_ports


async def test_discover_json_scans_and_reports_what_it_found(server, lan_sweep, quick):
    for i, host in enumerate(("10.9.8.2", "10.9.8.3"), start=1):
        server.hosts[host] = AxeOSSim("gamma", seed=i, mac=f"AA:BB:CC:00:00:{i:02X}").app()
        lan_sweep.add((host, 80))
    result = jout(await cli("discover", "--cidr", "10.9.8.0/29", "--json", "--url", server.base))
    scan = result["scan"]
    assert "adopted" not in result
    assert scan["status"] == "finished" and scan["cidrs"] == ["10.9.8.0/29"] and scan["total_hosts"] == 6 and scan["progress"] == 1.0
    assert sorted(m["host"] for m in scan["miners"]) == ["10.9.8.2", "10.9.8.3"]
    assert all(m["model"] == "Bitaxe Gamma" and m["already_added"] is None and m["duplicate_of"] is None for m in scan["miners"])
    assert server.ctx.fleet.views() == []  # looking is not adding


async def test_discover_add_starts_monitoring_what_is_new(server, lan_sweep, quick):
    for i, host in enumerate(("10.9.8.2", "10.9.8.3"), start=1):
        server.hosts[host] = AxeOSSim("gamma", seed=i, mac=f"AA:BB:CC:00:00:{i:02X}").app()
        lan_sweep.add((host, 80))
    result = jout(await cli("discover", "--cidr", "10.9.8.0/29", "--add", "--json", "--url", server.base))
    assert sorted(d["host"] for d in result["adopted"]["added"]) == ["10.9.8.2", "10.9.8.3"] and result["adopted"]["merged"] == []
    assert sorted(v.host for v in server.ctx.fleet.views()) == ["10.9.8.2", "10.9.8.3"]
    again = jout(await cli("discover", "--cidr", "10.9.8.0/29", "--add", "--json", "--url", server.base))
    assert all(m["already_added"] for m in again["scan"]["miners"]) and again["adopted"]["added"] == []


async def test_discover_prints_a_summary_and_a_hint_for_humans(server, lan_sweep, quick):
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    plain = flat((await cli("discover", "--cidr", "10.9.8.0/29", "--url", server.base)).stdout)
    assert "Found 1 miner(s) on 10.9.8.0/29" in plain and "10.9.8.2" in plain and "Bitaxe Gamma" in plain and "new" in plain
    assert "Add them with: bsmm discover --add" in plain
    added = flat((await cli("discover", "--cidr", "10.9.8.0/29", "--add", "--url", server.base)).stdout)
    assert "Added 1 miner(s)." in added
    known = flat((await cli("discover", "--cidr", "10.9.8.0/29", "--url", server.base)).stdout)
    assert "already monitored" in known and "Add them with" not in known


def pool_site() -> Starlette:
    """A Public Pool (the Umbrel solo pool) API: just the two documents the connection test reads."""
    fixtures = Path(__file__).parent / "fixtures" / "pools"

    async def answer(request):
        name = {"/api/network": "public_pool_network.json", "/api/pool": "public_pool_pool.json"}.get(request.url.path)
        return JSONResponse(json.loads((fixtures / name).read_text())) if name else JSONResponse({}, status_code=404)

    return Starlette(routes=[Route("/{p:path}", answer)])


async def test_discover_reports_the_node_and_pool_it_finds(server, lan_sweep, quick):
    server.hosts["10.9.8.4"] = pool_site()
    lan_sweep.update({("10.9.8.4", 2019), ("10.9.8.5", 8332)})
    plain = flat((await cli("discover", "--cidr", "10.9.8.0/29", "--url", server.base)).stdout)
    assert "Found 0 miner(s)" in plain
    assert "Node/pool: Public Pool on 10.9.8.4 at http://10.9.8.4:2019 (no login needed) - Public Pool's web/API port is open" in plain
    assert "Node/pool: Bitcoin node on 10.9.8.5 at http://10.9.8.5:8332 (needs RPC login) - Port 8332 (Bitcoin RPC) is open" in plain


async def test_discover_refuses_public_networks(server):
    res = await cli("discover", "--cidr", "8.8.8.0/24", "--url", server.base)
    assert res.exit_code == 1 and "is not a private network" in flat(res.stderr)


# --- doctor ----------------------------------------------------------------------------------------------------------------------------------


async def test_doctor_passes_on_a_healthy_install(server):
    await server.miner(name="Garage")
    server.network()
    diag = jout(await cli("doctor", "--json", "--url", server.base))  # exit code 0
    assert diag["ok"] is True and diag["version"] == __version__ and diag["data_dir"] == server.data_dir
    statuses = {c["id"]: c["status"] for c in diag["checks"]}
    assert statuses["database"] == "pass" and statuses["miners"] == "pass" and statuses["network-data"] == "pass"
    assert statuses["notifications"] == "warn" and statuses["auth"] == "warn"  # advice, not failures
    assert [d["name"] for d in diag["devices"]] == ["Garage"] and diag["devices"][0]["status"] == "online"
    human = await cli("doctor", "--url", server.base)
    plain = flat(human.stdout)
    assert human.exit_code == 0 and f"Bitcoin Solo Miner Monitor {__version__}" in plain
    assert "✓ The database is working." in plain and "! No password: anyone on the network can use this dashboard." in plain
    assert "Fix: Set one in Settings > Security." in plain


async def test_doctor_exits_non_zero_and_says_how_to_fix_a_failing_check(server):
    await server.miner(name="Garage")  # but no network data
    res = await cli("doctor", "--json", "--url", server.base)
    assert res.exit_code == 1
    diag = json.loads(res.stdout)  # the report is still complete
    assert diag["ok"] is False
    failing = [c for c in diag["checks"] if c["status"] == "fail"]
    assert [c["id"] for c in failing] == ["network-data"] and "Add a node/pool" in failing[0]["fix"]
    human = await cli("doctor", "--url", server.base)
    plain = flat(human.stdout)
    assert human.exit_code == 1 and "✗ Network difficulty is unknown, so odds cannot be shown." in plain and "Fix: Add a node/pool" in plain


async def test_doctor_lists_miners_that_are_offline(server):
    await server.miner(name="Garage")
    server.network()
    server.hosts.pop("gamma.test")
    rt = next(iter(server.ctx.fleet.runtimes.values()))
    for _ in range(3):
        await server.ctx.fleet._poll_once(rt)
    res = await cli("doctor", "--url", server.base)
    plain = flat(res.stdout)
    assert res.exit_code == 1 and "✗ Garage (gamma.test) is offline:" in plain


async def test_doctor_without_a_server_says_so_and_exits_non_zero(tmp_path):
    url = dead_url()
    res = await cli("doctor", "--json", "--url", url, "--data-dir", str(tmp_path / "nowhere"))
    assert res.exit_code == 1
    local = json.loads(res.stdout)
    assert local["server_running"] is False and local["data_dir"] == str(tmp_path / "nowhere") and local["data_dir_exists"] is False
    assert local["version"] == __version__ and "bsmm start" in local["hint"]
    human = await cli("doctor", "--url", url, "--data-dir", str(tmp_path))
    assert human.exit_code == 1 and "The server is not running." in human.stdout and str(tmp_path) in flat(human.stdout)


# --- a server that is not there / not ours ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "args",
    [["list"], ["status"], ["odds"], ["add", "192.168.1.5"], ["discover"], ["token", "list"], ["token", "revoke", "tok_x"]],
    ids="-".join,
)
async def test_without_a_server_every_command_says_so_plainly(args):
    url = dead_url()
    res = await cli(*args, "--url", url)
    assert res.exit_code == 1 and res.stdout == ""
    err = flat(res.stderr)
    assert f"Error: Can't reach the server at {url}." in err
    assert "Start it with `bsmm start` (background) or `bsmm serve` (foreground)." in err
    assert "Traceback" not in res.output


async def test_the_url_can_come_from_the_environment():
    url = dead_url()
    res = await cli("list", env={"BSMM_URL": url})
    assert res.exit_code == 1 and f"Can't reach the server at {url}." in flat(res.stderr)


async def test_a_server_that_is_not_ours_gives_a_short_error():
    async def teapot(request):
        return PlainTextResponse("I am a teapot", status_code=418)

    async with serve(Starlette(routes=[Route("/{p:path}", teapot)])) as base:  # type: ignore[arg-type]
        res = await cli("list", "--url", base)
        assert res.exit_code == 1 and flat(res.stderr) == "Error: HTTP 418"


# --- tokens and passwords ------------------------------------------------------------------------------------------------------------------


async def test_token_create_json_writes_a_usable_token_to_the_database(tmp_path):
    data = tmp_path / "data"
    made = jout(await cli("token", "create", "--json", "--data-dir", str(data)))
    assert made["name"] == "agent" and made["scope"] == "control" and made["token"].startswith("bsmm_") and made["id"].startswith("tok_")
    store = await Store.open(RuntimeConfig(data_dir=data))
    try:
        info = await store.verify_token(made["token"])
        assert info == {"id": made["id"], "name": "agent", "scope": "control"}
        [row] = await store.list_tokens()
        assert row["expires_at"] is None
        assert "bsmm_" not in json.dumps(await store.list_tokens())  # only a hash is stored
    finally:
        await store.close()


async def test_token_create_options_and_human_output(tmp_path):
    data = tmp_path / "data"
    before = time.time()
    made = jout(await cli("token", "create", "--name", "grafana", "--scope", "read", "--days", "2", "--json", "--data-dir", str(data)))
    assert (made["name"], made["scope"]) == ("grafana", "read")
    human = await cli("token", "create", "--scope", "admin", "--data-dir", str(data))
    assert human.exit_code == 0
    plain = flat(human.stdout)
    assert plain.startswith("Token bsmm_") and "Shown once." in plain and "Authorization: Bearer <token>" in plain
    store = await Store.open(RuntimeConfig(data_dir=data))
    try:
        rows = {r["name"]: r for r in await store.list_tokens()}
        assert rows["grafana"]["scope"] == "read" and before + 2 * 86400 - 5 <= rows["grafana"]["expires_at"] <= time.time() + 2 * 86400 + 5
        assert rows["agent"]["scope"] == "admin"  # the second token, which used the default name
    finally:
        await store.close()


async def test_token_create_rejects_an_unknown_scope_before_touching_anything(tmp_path):
    data = tmp_path / "data"
    res = await cli("token", "create", "--scope", "root", "--data-dir", str(data))
    assert res.exit_code == 1 and flat(res.stderr) == "Error: scope must be read, control or admin."
    assert not data.exists()


async def test_a_cli_made_token_unlocks_a_password_protected_server(server):
    await server.miner(name="Garage")
    await server.lock()
    denied = await cli("list", "--json", "--url", server.base)
    assert denied.exit_code == 2
    err = flat(denied.stderr)
    assert "Error: You need to sign in or send an API token." in err and "bsmm token create --scope control" in err

    made = jout(await cli("token", "create", "--scope", "read", "--name", "ci", "--json", "--data-dir", server.data_dir))
    token = made["token"]  # the server and the command line share one database; the token works at once
    assert [d["name"] for d in jout(await cli("list", "--json", "--url", server.base, "--token", token))] == ["Garage"]
    assert jout(await cli("status", "--json", "--url", server.base, env={"BSMM_TOKEN": token}))["summary"]["devices_total"] == 1

    # ... but only for what its scope allows
    forbidden = await cli("add", "gamma.test", "--url", server.base, "--token", token)
    assert forbidden.exit_code == 2
    assert "This needs the 'control' scope but you have 'read'." in flat(forbidden.stderr)
    wrong = await cli("list", "--url", server.base, "--token", "bsmm_not-a-real-token")
    assert wrong.exit_code == 2


async def test_token_list_and_revoke(server):
    made = jout(await cli("token", "create", "--name", "ci", "--scope", "read", "--json", "--data-dir", server.data_dir))
    tokens = jout(await cli("token", "list", "--json", "--url", server.base))
    assert [(t["id"], t["name"], t["scope"]) for t in tokens] == [(made["id"], "ci", "read")]
    assert "token" not in tokens[0] and "hash" not in tokens[0]  # never shown again
    human = flat((await cli("token", "list", "--url", server.base)).stdout)
    assert f"{made['id']} ci read" in human
    revoked = await cli("token", "revoke", made["id"], "--url", server.base)
    assert revoked.exit_code == 0 and flat(revoked.stdout) == "Revoked."
    assert jout(await cli("token", "list", "--json", "--url", server.base)) == []
    gone = await cli("token", "revoke", made["id"], "--url", server.base)
    assert gone.exit_code == 1 and "Error:" in gone.stderr


async def test_password_command_switches_protection_on_through_the_server(server):
    res = await cli("password", "--password", PASSWORD, "--url", server.base)
    assert res.exit_code == 0 and flat(res.stdout) == "Password set. The dashboard now asks for it."
    assert server.ctx.settings.current.auth.mode == "password" and await server.ctx.auth.check_password(PASSWORD)
    assert (await cli("list", "--url", server.base)).exit_code == 2  # and now the CLI needs a token


async def test_password_command_rejects_a_short_password(server):
    res = await cli("password", "--password", "short", "--url", server.base)
    assert res.exit_code == 1 and "Error:" in res.stderr
    assert server.ctx.settings.current.auth.mode == "none"


async def test_password_command_works_on_the_database_when_no_server_is_running(tmp_path):
    data = tmp_path / "data"
    res = await cli("password", "--password", PASSWORD, "--url", dead_url(), "--data-dir", str(data))
    assert res.exit_code == 0 and "Password set." in res.stdout
    store = await Store.open(RuntimeConfig(data_dir=data))
    try:
        settings = SettingsService(store)
        await settings.load()
        assert settings.current.auth.mode == "password"
        assert await AuthService(store).check_password(PASSWORD)
    finally:
        await store.close()


# --- agent guide, mcp, stop/start, service, migrate-legacy --------------------------------------------------------------------------------------


async def test_agent_guide_prints_what_the_running_server_serves(server):
    res = await cli("agent-guide", "--url", server.base)
    assert res.exit_code == 0 and res.stdout.startswith("# Bitcoin Solo Miner Monitor")
    assert f"This server: {server.base}" in res.stdout and f"{server.base}/api/v1/agent/guide" in res.stdout
    served = await asyncio.to_thread(httpx.get, f"{server.base}/llms.txt")
    assert res.stdout == served.text


async def test_agent_guide_works_without_a_server(tmp_path):
    url = dead_url()
    res = await cli("agent-guide", "--url", url)
    assert res.exit_code == 0 and res.stdout.startswith("# Bitcoin Solo Miner Monitor")
    assert f"This server: {url}" in res.stdout and "Set it up for a user" in res.stdout and "POST /api/v1/discovery" in res.stdout


async def test_the_mcp_command_explains_that_http_is_built_into_the_server():
    res = await cli("mcp", "--transport", "http", "--url", "http://127.0.0.1:9")
    assert res.exit_code == 1
    assert "Error: Only stdio is available here." in flat(res.stderr) and "http://127.0.0.1:9/mcp" in flat(res.stderr)


async def test_stop_with_nothing_started(tmp_path):
    res = jout(await cli("stop", "--json", "--data-dir", str(tmp_path)))
    assert res == {"stopped": False, "reason": "not started by `bsmm start`"}
    assert "Nothing to stop" in flat((await cli("stop", "--data-dir", str(tmp_path))).stdout)


async def test_stop_forgets_a_stale_pid_file_without_signalling_anyone(tmp_path):
    pidfile = tmp_path / "bsmm.pid"
    pidfile.write_text("2000000000")  # no such process
    res = jout(await cli("stop", "--json", "--data-dir", str(tmp_path)))
    assert res == {"stopped": True} and not pidfile.exists()


async def test_start_notices_a_server_that_is_already_running_and_starts_nothing(tmp_path):
    (tmp_path / "bsmm.pid").write_text(str(os.getpid()))  # a process that is certainly alive: this one
    res = jout(await cli("start", "--json", "--port", "8431", "--data-dir", str(tmp_path)))
    assert res == {"running": True, "already": True, "url": "http://localhost:8431"}
    assert flat((await cli("start", "--port", "8431", "--data-dir", str(tmp_path))).stdout) == "Already running at http://localhost:8431"


def fake_platform(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """Pretend to run on ``name``. ``shutil.which`` is stubbed too: from Python 3.12 it consults Windows-only APIs
    when ``sys.platform`` says win32, which do not exist on the Linux machine that runs these tests."""
    monkeypatch.setattr(sys, "platform", name)
    monkeypatch.setattr("shutil.which", lambda *_a, **_k: None)


@pytest.mark.parametrize(
    ("platform", "expected"),
    [
        ("linux", ["bsmm.service", "[Unit]", "ExecStart=", "serve --port 8431", "WantedBy=default.target", "systemctl --user enable --now bsmm"]),
        ("darwin", ["com.github.smokeysrh.bsmm.plist", "<key>RunAtLoad</key>", "<string>serve</string>", "launchctl load -w"]),
        ("win32", ["schtasks /Create /F /SC ONLOGON /TN BitcoinSoloMinerMonitor", "serve --port 8431"]),
    ],
)
async def test_service_install_only_prints_unless_applied(tmp_path, monkeypatch, platform, expected):
    fake_platform(monkeypatch, platform)
    res = await cli("service", "install", "--port", "8431", env={"HOME": str(tmp_path), "USERPROFILE": str(tmp_path)})
    assert res.exit_code == 0, res.output
    plain = flat(res.stdout)
    for fragment in expected:
        assert fragment in plain, fragment
    assert list(tmp_path.iterdir()) == []  # nothing was written anywhere


def make_old_database(path: Path, rows: list[str]) -> Path:
    """The v0.9 schema exactly as src/backend/services/data_storage.py of the old app creates it."""
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE miners (id TEXT PRIMARY KEY, config TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    con.executemany(
        "INSERT INTO miners (id, config, created_at, updated_at) VALUES (?, ?, '2025-11-03T14:00:00', '2025-11-03T14:00:00')",
        [(f"miner_{i}", r) for i, r in enumerate(rows)],
    )
    con.commit()
    con.close()
    return path


async def test_migrate_legacy_reads_changes_that_only_exist_in_the_wal_file(server, tmp_path):
    """The old app used WAL mode, so its newest miners may never have been copied into config.db itself."""
    server.hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    old = tmp_path / "config.db"
    keeper = sqlite3.connect(old)  # staying open stops SQLite from checkpointing the WAL away on close
    keeper.execute("PRAGMA journal_mode=WAL")
    keeper.execute("PRAGMA wal_autocheckpoint=0")
    keeper.execute("CREATE TABLE miners (id TEXT PRIMARY KEY, config TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    keeper.execute("INSERT INTO miners VALUES ('bitaxe_gamma_test', ?, 'x', 'x')", (json.dumps({"name": "In the WAL", "ip_address": "gamma.test", "port": None, "type": "Gamma", "factory_type": "bitaxe"}),))
    keeper.commit()
    try:
        assert Path(f"{old}-wal").stat().st_size > 0
        originals = {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in tmp_path.glob("config.db*")}
        report = jout(await cli("migrate-legacy", str(old), "--json", "--url", server.base))
        assert [r["host"] for r in report] == ["gamma.test"] and report[0]["ok"] is True
        assert [v.name for v in server.ctx.fleet.views()] == ["In the WAL"]
        assert {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in tmp_path.glob("config.db*")} == originals  # the original is untouched
    finally:
        keeper.close()


async def test_migrate_legacy_imports_the_miners_of_a_v09_database(server, tmp_path):
    server.hosts["gamma.test"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11").app()
    old = make_old_database(tmp_path / "config.db", [
        json.dumps({"ip_address": "gamma.test", "name": "Old Gamma"}),
        json.dumps({"ip": "gone.test", "port": 4028}),
        json.dumps({"name": "no address at all"}),
        "this is not json",
    ])
    report = jout(await cli("migrate-legacy", str(old), "--json", "--url", server.base))
    assert [r["host"] for r in report] == ["gamma.test", "gone.test"]  # unusable rows are skipped
    assert report[0]["ok"] is True and report[0]["created"] is True
    assert report[1]["ok"] is False and "looks like a supported miner" in report[1]["error"]
    assert "gone.test:4028" in report[1]["error"]  # a non-default port from the old database is kept
    assert [v.name for v in server.ctx.fleet.views()] == ["Old Gamma"]
    again = jout(await cli("migrate-legacy", str(old), "--json", "--url", server.base))
    assert again[0]["ok"] is True and again[0]["created"] is False  # running it twice does not duplicate anything
    human = flat((await cli("migrate-legacy", str(old), "--url", server.base)).stdout)
    assert "✓ gamma.test" in human and "✗ gone.test" in human


async def test_migrate_legacy_explains_missing_and_unreadable_databases(server, tmp_path):
    missing = await cli("migrate-legacy", str(tmp_path / "nope.db"), "--url", server.base)
    assert missing.exit_code == 1 and "does not exist" in flat(missing.stderr) and "config.db" in flat(missing.stderr)
    wrong = tmp_path / "other.db"
    sqlite3.connect(wrong).close()  # a valid SQLite file without a miners table
    unreadable = await cli("migrate-legacy", str(wrong), "--url", server.base)
    assert unreadable.exit_code == 1 and "Could not read the old database" in flat(unreadable.stderr)


# --- the setup wizard, unattended --------------------------------------------------------------------------------------------------------------


async def test_setup_does_everything_unattended_and_hands_back_a_token(server, lan_sweep, quick):
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--kwh-price", "0.09", "--address", ADDR, "--data-dir", server.data_dir))
    assert out["url"] == server.base
    steps = {s["step"]: s for s in out["steps"]}
    assert steps["miners"]["found"] == 1 and len(steps["miners"]["added"]) == 1
    assert steps["settings"]["energy"] == {"price_per_kwh": 0.09} and steps["settings"]["mining"] == {"addresses": [ADDR]}
    assert out["overview"]["devices"] == 1 and out["token"].startswith("bsmm_") and "Shown once" in out["token_note"]
    s = server.ctx.settings.current
    assert (s.energy.price_per_kwh, s.mining.addresses, s.general.onboarding_done) == (0.09, [ADDR], True)
    assert [v.host for v in server.ctx.fleet.views()] == ["10.9.8.2"]
    assert (await server.ctx.store.verify_token(out["token"]))["scope"] == "admin"


async def test_setup_can_protect_the_dashboard_and_still_finish(server, lan_sweep, quick):
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    out = jout(await cli("setup", "--yes", "--json", "--password", PASSWORD, "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir))
    assert {s["step"] for s in out["steps"]} >= {"miners", "settings", "security", "token"}
    assert server.ctx.settings.current.auth.mode == "password" and await server.ctx.auth.check_password(PASSWORD)
    # the dashboard is now closed to anonymous callers, and open to the token the wizard returned
    assert (await cli("list", "--url", server.base)).exit_code == 2
    assert len(jout(await cli("list", "--json", "--url", server.base, "--token", out["token"]))) == 1


async def test_setup_points_out_a_node_it_cannot_connect_by_itself(server, lan_sweep, quick):
    lan_sweep.add(("10.9.8.5", 8332))
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir))
    sources = next(s for s in out["steps"] if s["step"] == "sources")
    assert sources["added"] == [] and sources["node_candidates"] == ["http://10.9.8.5:8332"]
    human = flat((await cli("setup", "--yes", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir,
                            "--kwh-price", "0.1")).stdout)
    assert "A Bitcoin node answers at http://10.9.8.5:8332." in human and "--node-url http://10.9.8.5:8332" in human
    assert "All set." in human and "Next: `bsmm status`, `bsmm odds`, `bsmm doctor`." in human


async def test_setup_connects_a_node_when_given_its_address_and_login(server, lan_sweep, quick):
    from bsmm.sim.bitcoin_core import FakeBitcoinCore

    server.hosts["node.test"] = FakeBitcoinCore().app()
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir,
                         "--node-url", "http://node.test:8332", "--rpc-user", "umbrel", "--rpc-password", "secret"))
    sources = next(s for s in out["steps"] if s["step"] == "sources")
    assert sources["added"] == ["Bitcoin Core node (RPC)"]
    [src] = await server.ctx.store.list_sources()
    assert src.kind == "bitcoin_core" and src.url == "http://node.test:8332" and src.has_secret
    assert await server.ctx.store.source_secret(src.id) == {"rpc_user": "umbrel", "rpc_password": "secret"}


async def test_setup_gives_up_cleanly_when_the_given_server_is_not_there():
    url = dead_url()
    res = await cli("setup", "--yes", "--no-password", "--url", url)  # (with --url it never tries to start a server itself)
    assert res.exit_code == 1 and flat(res.stderr) == f"Error: No server answers at {url}."


async def test_setup_on_a_password_protected_server_mints_its_own_token(server, lan_sweep, quick):
    await server.lock()
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir))  # no --token: whoever can read the data folder is the admin
    assert out["overview"]["devices"] == 1 and out["token"].startswith("bsmm_")
    assert (await cli("list", "--url", server.base)).exit_code == 2  # still protected
    assert len(jout(await cli("list", "--json", "--url", server.base, "--token", out["token"]))) == 1


async def test_setup_connects_the_public_pool_it_finds(server, lan_sweep, quick):
    server.hosts["10.9.8.4"] = pool_site()
    lan_sweep.add(("10.9.8.4", 2019))
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir))
    assert next(s for s in out["steps"] if s["step"] == "sources")["added"] == ["Public Pool on 10.9.8.4"]
    [src] = await server.ctx.store.list_sources()
    assert (src.kind, src.url, src.name) == ("public_pool", "http://10.9.8.4:2019", "Public Pool on 10.9.8.4")


async def test_setup_prefers_a_pool_address_given_on_the_command_line(server, lan_sweep, quick):
    server.hosts["10.9.8.4"] = pool_site()  # found by the scan ...
    lan_sweep.add(("10.9.8.4", 2019))
    server.hosts["pool.test"] = pool_site()  # ... but the user named another
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir, "--pool-url", "http://pool.test:2019"))
    assert next(s for s in out["steps"] if s["step"] == "sources")["added"] == ["Public Pool (Umbrel / Start9 / self-hosted)"]
    [src] = await server.ctx.store.list_sources()
    assert src.url == "http://pool.test:2019"


async def test_setup_asks_before_it_acts_when_it_is_not_unattended(server, lan_sweep, quick):
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    res = await cli("setup", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir, stdin="y\n0.15\n")
    plain = flat(res.stdout)
    assert res.exit_code == 0, res.output
    assert "Start monitoring 1 miner(s)? [Y/n]:" in plain and "Electricity price per kWh [0.12]:" in plain and "All set." in plain
    assert [v.host for v in server.ctx.fleet.views()] == ["10.9.8.2"] and server.ctx.settings.current.energy.price_per_kwh == 0.15


async def test_setup_leaves_the_fleet_alone_when_you_decline(server, lan_sweep, quick):
    server.hosts["10.9.8.2"] = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:01").app()
    lan_sweep.add(("10.9.8.2", 80))
    res = await cli("setup", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir, stdin="n\n0.2\n")
    assert res.exit_code == 0, res.output
    assert server.ctx.fleet.views() == [] and server.ctx.settings.current.energy.price_per_kwh == 0.2


@pytest.fixture
def ntfy(server):
    """A stand-in for ntfy.sh (the simulated network resolves that name to this app)."""
    received: list[tuple[str, str | None, str]] = []
    reply = {"status": 200}

    async def accept(request: Request) -> PlainTextResponse:
        received.append((request.url.path, request.headers.get("title"), (await request.body()).decode()))
        return PlainTextResponse("ok", status_code=reply["status"])

    server.hosts["ntfy.sh"] = Starlette(routes=[Route("/{topic}", accept, methods=["POST"])])
    return types.SimpleNamespace(received=received, reply=reply)


async def test_setup_creates_a_phone_alert_channel_and_sends_a_test_message(server, ntfy, lan_sweep, quick):
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir, "--ntfy-topic", "my-miners-x7"))
    note = next(s for s in out["steps"] if s["step"] == "notifications")
    assert note["test_ok"] is True
    assert ntfy.received == [("/my-miners-x7", "Test notification", "If you can read this, alerts will reach you here.")]
    [ch] = await server.ctx.store.list_channels()
    assert (ch.kind, ch.name, ch.config, ch.id) == ("ntfy", "Phone (ntfy)", {"topic": "my-miners-x7"}, note["channel"])


async def test_setup_says_when_the_test_message_did_not_arrive(server, ntfy, lan_sweep, quick):
    ntfy.reply["status"] = 401  # (a client error, which is not retried)
    out = jout(await cli("setup", "--yes", "--json", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29",
                         "--data-dir", server.data_dir, "--ntfy-topic", "locked-topic"))
    assert next(s for s in out["steps"] if s["step"] == "notifications")["test_ok"] is False
    human = await cli("setup", "--yes", "--no-password", "--url", server.base, "--cidr", "10.9.8.0/29", "--data-dir", server.data_dir,
                      "--ntfy-topic", "locked-topic", "--kwh-price", "0.1")
    assert "ntfy test failed: the service rejected the message (HTTP 401)" in flat(human.stdout)


async def test_doctor_reports_an_authentication_problem_plainly(server):
    await server.miner(name="Garage")
    server.network()
    await server.lock()
    denied = await cli("doctor", "--url", server.base)  # the server answers (its health check is public) but wants a token
    assert denied.exit_code == 2 and "Error: You need to sign in or send an API token." in flat(denied.stderr)
    token = jout(await cli("token", "create", "--scope", "read", "--json", "--data-dir", server.data_dir))["token"]
    ok = await cli("doctor", "--json", "--url", server.base, "--token", token)
    assert ok.exit_code == 0 and json.loads(ok.stdout)["ok"] is True


# --- background start / stop and the auto-start service, with the operating system faked -----------------------------------------


class FakeProcess:
    pid = 2_000_000_000  # not a process that exists

    def __init__(self, exit_code: int | None = None) -> None:
        self.exit_code = exit_code

    def poll(self) -> int | None:
        return self.exit_code


@pytest.fixture
def popen(monkeypatch):
    """Nothing is ever launched: ``subprocess.Popen`` just records what it was asked to run."""
    started: list[tuple[list[str], dict[str, Any]]] = []
    state = {"process": FakeProcess()}

    def fake_popen(cmd, **kwargs):
        started.append((list(cmd), kwargs))
        return state["process"]

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    return types.SimpleNamespace(started=started, state=state)


async def test_start_launches_a_detached_server_and_waits_until_it_answers(server, popen, tmp_path):
    port = int(server.base.rsplit(":", 1)[1])  # (the test server stands in for the one that would have been started)
    data = tmp_path / "bg"
    out = jout(await cli("start", "--json", "--port", str(port), "--data-dir", str(data)))
    assert out == {"running": True, "pid": FakeProcess.pid, "url": f"http://localhost:{port}", "log": str(data / "bsmm.log")}
    [(cmd, kwargs)] = popen.started
    assert cmd == [sys.executable, "-m", "bsmm", "serve", "--port", str(port), "--data-dir", str(data), "--log-file", str(data / "bsmm.log")]
    assert kwargs["start_new_session"] is True
    assert (kwargs["stdin"], kwargs["stdout"], kwargs["stderr"]) == (subprocess.DEVNULL,) * 3  # it must not hold on to the terminal
    assert (data / "bsmm.pid").read_text() == str(FakeProcess.pid)
    human = await cli("start", "--port", str(port), "--data-dir", str(data))
    assert flat(human.stdout) == f"Started. Open http://localhost:{port} (log: {data / 'bsmm.log'})"


async def test_start_can_return_without_waiting(popen, tmp_path):
    out = jout(await cli("start", "--json", "--no-wait", "--port", "8432", "--data-dir", str(tmp_path)))
    assert out["running"] is True and out["url"] == "http://localhost:8432" and len(popen.started) == 1


async def test_start_reports_a_server_that_dies_immediately(popen, tmp_path, quick):
    popen.state["process"] = FakeProcess(exit_code=1)
    port = int(dead_url().rsplit(":", 1)[1])
    res = await cli("start", "--port", str(port), "--data-dir", str(tmp_path))
    err = flat(res.stderr)
    assert res.exit_code == 1 and "Error: The server stopped right after starting." in err and f"See the log: {tmp_path / 'bsmm.log'}" in err


async def test_start_gives_up_on_a_server_that_never_answers(popen, tmp_path, quick):
    port = int(dead_url().rsplit(":", 1)[1])
    res = await cli("start", "--port", str(port), "--data-dir", str(tmp_path))
    assert res.exit_code == 1 and "Error: The server did not answer within 30 seconds." in flat(res.stderr)


@pytest.mark.skipif(os.name == "nt", reason="stop uses taskkill on Windows")
async def test_stop_asks_a_running_background_server_to_terminate(tmp_path, monkeypatch):
    (tmp_path / "bsmm.pid").write_text(str(FakeProcess.pid))
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(cli_main, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(os, "kill", lambda pid, sig: signalled.append((pid, sig)))
    assert jout(await cli("stop", "--json", "--data-dir", str(tmp_path))) == {"stopped": True}
    assert signalled == [(FakeProcess.pid, signal.SIGTERM)] and not (tmp_path / "bsmm.pid").exists()


@pytest.fixture
def ran(monkeypatch):
    """``subprocess.run`` records the command instead of running it (systemctl, launchctl and schtasks must not be touched)."""
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append([str(c) for c in cmd])
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    return commands


async def test_service_install_apply_and_uninstall_on_linux(tmp_path, monkeypatch, ran):
    fake_platform(monkeypatch, "linux")
    env = {"HOME": str(tmp_path)}
    unit = tmp_path / ".config" / "systemd" / "user" / "bsmm.service"
    res = await cli("service", "install", "--apply", "--port", "8431", env=env)
    assert res.exit_code == 0, res.output
    text = unit.read_text()
    assert "[Service]" in text and "serve --port 8431" in text and "Restart=on-failure" in text and "WantedBy=default.target" in text
    assert ran == [["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "--now", "bsmm"]]
    assert flat(res.stdout) == f"Installed {unit} and started it."
    ran.clear()
    res = await cli("service", "uninstall", env=env)
    assert res.exit_code == 0 and flat(res.stdout) == "Removed." and not unit.exists()
    assert ran == [["systemctl", "--user", "disable", "--now", "bsmm"]]


async def test_service_install_apply_and_uninstall_on_macos(tmp_path, monkeypatch, ran):
    fake_platform(monkeypatch, "darwin")
    env = {"HOME": str(tmp_path)}
    plist = tmp_path / "Library" / "LaunchAgents" / "com.github.smokeysrh.bsmm.plist"
    res = await cli("service", "install", "--apply", "--port", "8431", env=env)
    assert res.exit_code == 0, res.output
    assert "<key>KeepAlive</key>" in plist.read_text() and ran == [["launchctl", "load", "-w", str(plist)]]
    assert flat(res.stdout) == f"Installed {plist}."
    ran.clear()
    res = await cli("service", "uninstall", env=env)
    assert res.exit_code == 0 and not plist.exists() and ran == [["launchctl", "unload", "-w", str(plist)]]


async def test_service_install_apply_and_uninstall_on_windows(tmp_path, monkeypatch, ran):
    fake_platform(monkeypatch, "win32")
    res = await cli("service", "install", "--apply", "--port", "8431", env={"HOME": str(tmp_path)})
    assert res.exit_code == 0, res.output
    [create] = ran
    assert create[:8] == ["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", "BitcoinSoloMinerMonitor", "/TR"]
    assert "serve --port 8431" in create[8] and create[9:] == ["/RL", "LIMITED"]
    assert flat(res.stdout) == "Scheduled task created: it starts at your next login."
    ran.clear()
    res = await cli("service", "uninstall")
    assert res.exit_code == 0 and ran == [["schtasks", "/Delete", "/F", "/TN", "BitcoinSoloMinerMonitor"]]


# --- small pieces that are easy to get wrong and cheap to check -------------------------------------------------------------------


async def test_start_ignores_a_pid_file_that_holds_no_number(popen, tmp_path):
    (tmp_path / "bsmm.pid").write_text("not a pid")  # left over from something else, or cut short
    out = jout(await cli("start", "--json", "--no-wait", "--port", "8433", "--data-dir", str(tmp_path)))
    assert out["running"] is True and "already" not in out and len(popen.started) == 1
    assert (tmp_path / "bsmm.pid").read_text() == str(FakeProcess.pid)  # replaced by the new server's


def test_lan_urls_are_the_addresses_a_phone_on_the_same_network_could_use(monkeypatch):
    import ifaddr

    def ip(addr: str, *, v4: bool = True) -> Any:
        return types.SimpleNamespace(ip=addr if v4 else (addr, 0, 0), is_IPv4=v4)

    adapters = [
        types.SimpleNamespace(ips=[ip("127.0.0.1"), ip("192.168.1.20"), ip("169.254.3.4"), ip("fe80::1", v4=False)]),
        types.SimpleNamespace(ips=[ip("10.0.0.5"), ip("10.0.0.6"), ip("10.0.0.7")]),
    ]
    monkeypatch.setattr(ifaddr, "get_adapters", lambda: adapters)
    # loopback, link-local and IPv6 addresses are no use to a phone; at most three are offered
    assert cli_main._lan_urls(8431) == ["http://192.168.1.20:8431", "http://10.0.0.5:8431", "http://10.0.0.6:8431"]
    monkeypatch.setattr(ifaddr, "get_adapters", lambda: [])
    assert cli_main._lan_urls(8431) == []


def test_logging_goes_to_a_rotating_file_when_asked_to(tmp_path):
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    chatty = ("httpx", "httpcore", "uvicorn.access", "mcp")
    saved_levels = {name: logging.getLogger(name).level for name in chatty}
    try:
        log_file = tmp_path / "not" / "yet" / "bsmm.log"  # the folder is created on the way
        cli_main._setup_logging("debug", log_file)
        logging.getLogger("bsmm.test").debug("written for the test")
        assert [type(h).__name__ for h in root.handlers] == ["RotatingFileHandler"] and root.level == logging.DEBUG
        for h in root.handlers:
            h.flush()
        written = log_file.read_text()
        assert "DEBUG" in written and "bsmm.test: written for the test" in written
        assert all(logging.getLogger(name).level == logging.WARNING for name in chatty)  # chatty libraries are turned down
        cli_main._setup_logging("nonsense")  # an unknown level means INFO; with no file it logs to the console
        assert [type(h).__name__ for h in root.handlers] == ["StreamHandler"] and root.level == logging.INFO
    finally:
        for h in root.handlers[:]:
            if h not in saved_handlers:
                h.close()
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
        for name, level in saved_levels.items():
            logging.getLogger(name).setLevel(level)


def test_the_console_entry_point_shows_a_stray_cli_error_as_a_plain_message(monkeypatch, capsys):
    def boom() -> None:
        raise CliError("It broke.", "Try turning it off and on again.", code=3)

    monkeypatch.setattr(cli_main, "app", boom)
    with pytest.raises(typer.Exit) as raised:
        cli_main.main()
    assert raised.value.exit_code == 3
    assert flat(capsys.readouterr().err) == "Error: It broke. Try turning it off and on again."

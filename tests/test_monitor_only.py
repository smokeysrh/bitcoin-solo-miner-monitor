"""HashHurdr is monitor-only: it reads from miners and never writes to them.

These guards cover every surface a write could come back through: the driver classes and their HTTP and TCP
traffic, the REST schema, the MCP tools and the CLI commands. They also check that data saved by earlier
releases (settings, config exports, stored miners) still loads now that the control settings are gone.
"""

from __future__ import annotations

import ast
import contextlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.main import get_command

from bsmm.capture import CGMINER_COMMANDS
from bsmm.cli.main import app as cli_app
from bsmm.drivers import base as driver_base
from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.base import Driver, DriverError
from bsmm.drivers.cgminer import CgminerDriver
from bsmm.drivers.http import request_json
from bsmm.drivers.sim import SimAxeOSDriver, SimCgminerDriver
from bsmm.mcp_server import build_server
from bsmm.models import Capability, DeviceInfo
from bsmm.net import make_http_client
from bsmm.settings import SettingsService
from bsmm.sim.axeos import AxeOSSim
from bsmm.sim.cgminer import CgminerSim

ROOT = Path(__file__).resolve().parent.parent
DRIVERS_DIR = ROOT / "src" / "bsmm" / "drivers"

#: Methods that used to change a miner. No driver class may offer any of them.
WRITE_METHOD_NAMES = (
    "restart",
    "identify",
    "pause",
    "resume",
    "set_pool",
    "set_fan",
    "set_tuning",
    "tuning_options",
    "validate_action",
    "verify_identity",
    "patch_settings",
    "set_hostname",
)
DRIVER_CLASSES = (Driver, AxeOSDriver, CgminerDriver, SimAxeOSDriver, SimCgminerDriver)
WRITE_HTTP_VERBS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Every command the cgminer driver and `bsmm capture` may send to a miner. All of them only read.
READ_ONLY_CGMINER_COMMANDS = frozenset({"version", "summary", "pools", "stats", "estats", "devdetails"})
PRIVILEGED_CGMINER_COMMANDS = frozenset({
    "addpool", "removepool", "enablepool", "disablepool", "switchpool", "poolpriority", "poolquota",
    "ascset", "pgaset", "setconfig", "privileged", "restart", "quit", "save", "zero", "debug", "fanctrl", "ledset",
})

CONTROL_OPERATION_IDS = frozenset({"runDeviceAction", "runBulkAction", "getDeviceTuning"})
FORBIDDEN_MCP_TOOLS = frozenset({"restart_miner", "identify_miner", "run_miner_action", "run_bulk_action"})
CONTROL_TOOL_NAME = re.compile(r"^(restart|reboot|identify|pause|resume|set_|run_|tune)")
CONTROL_CLI_WORDS = frozenset({
    "restart", "reboot", "identify", "pause", "resume", "tune", "tuning", "pool", "fan", "control", "action", "actions",
})


class RecordingTransport(httpx.AsyncBaseTransport):
    """Serves one simulated miner in-process and remembers every (method, path) it was asked for."""

    def __init__(self, app: Any) -> None:
        self._inner = httpx.ASGITransport(app=app)
        self.requests: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        return await self._inner.handle_async_request(request)


def _recording_client(sim: AxeOSSim) -> tuple[httpx.AsyncClient, RecordingTransport]:
    transport = RecordingTransport(sim.app())
    return httpx.AsyncClient(transport=transport, timeout=5.0), transport


def _string_constants(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}


# --- (a) the driver layer ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("driver_class", DRIVER_CLASSES, ids=lambda cls: cls.__name__)
def test_driver_classes_offer_no_write_methods(driver_class):
    assert [name for name in WRITE_METHOD_NAMES if hasattr(driver_class, name)] == []


def test_the_driver_contract_has_no_control_types():
    assert not hasattr(driver_base, "ActionResult")
    assert not hasattr(driver_base, "TuningOptions")
    assert not hasattr(driver_base, "ActionFailed")
    assert {member.value for member in Capability} <= {"scoreboard", "history"}


async def test_axeos_driver_only_sends_get_requests():
    client, transport = _recording_client(AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11"))
    async with client:
        probe = await AxeOSDriver.probe("miner.test", 80, client=client)
        assert probe is not None
        driver = AxeOSDriver("miner.test", 80, client=client, timeout=5.0, info=probe.info)
        await driver.poll()
        await driver.refresh_info()
        await driver.scoreboard()
        with contextlib.suppress(DriverError):  # the simulator has no statistics page; only the verb matters here
            await driver.statistics()
    assert transport.requests
    assert {method for method, _ in transport.requests} == {"GET"}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_the_shared_http_helper_refuses_every_method_but_get(method):
    client, transport = _recording_client(AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11"))
    async with client:
        with pytest.raises(ValueError):
            await request_json(client, method, "http://miner.test/api/system/restart", timeout=2.0)
    assert transport.requests == []  # refused before anything was sent


def test_driver_modules_never_name_a_write_http_verb():
    offenders = {path.name: sorted(_string_constants(path) & WRITE_HTTP_VERBS) for path in sorted(DRIVERS_DIR.glob("*.py"))}
    assert {name: verbs for name, verbs in offenders.items() if verbs} == {}


@pytest.mark.parametrize("profile", ["avalon_nano3", "antminer_s19", "braiins"])
async def test_cgminer_driver_only_sends_allowlisted_read_commands(profile):
    sim = await CgminerSim(profile, seed=1).start()
    try:
        async with make_http_client() as client:
            probe = await CgminerDriver.probe("127.0.0.1", sim.port, client=client, timeout=2.0)
            assert probe is not None
            driver = CgminerDriver("127.0.0.1", sim.port, client=client, timeout=2.0, info=probe.info)
            await driver.poll()
    finally:
        await sim.stop()
    sent = {command for command in sim.commands if command}  # (a bare connection carries no command)
    assert sent
    assert sent <= READ_ONLY_CGMINER_COMMANDS


def test_the_capture_command_list_is_read_only():
    assert set(CGMINER_COMMANDS) <= READ_ONLY_CGMINER_COMMANDS


def test_no_privileged_cgminer_command_is_named_in_the_driver_or_capture_code():
    named = _string_constants(DRIVERS_DIR / "cgminer.py") | _string_constants(ROOT / "src" / "bsmm" / "capture.py")
    assert named & PRIVILEGED_CGMINER_COMMANDS == set()


# --- (b) the REST schema -----------------------------------------------------------------------------------------


async def test_openapi_schema_has_no_device_control_routes(api):
    c, *_ = api
    spec = (await c.get("/openapi.json")).json()
    assert [path for path in spec["paths"] if "/actions" in path or "/tuning" in path] == []
    operation_ids = {op.get("operationId") for item in spec["paths"].values() for op in item.values() if isinstance(op, dict)}
    assert operation_ids & CONTROL_OPERATION_IDS == set()
    blob = json.dumps(spec)
    for term in ("allow_control", "allow_tuning", "Settings > Safety"):
        assert term not in blob


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/devices/{id}/actions/restart"),
        ("POST", "/devices/{id}/actions/set_pool"),
        ("POST", "/devices/actions"),
        ("GET", "/devices/{id}/tuning"),
    ],
)
async def test_removed_control_routes_are_gone_and_the_miner_is_never_written(api, method, path):
    c, ctx, hosts = api
    sim = AxeOSSim("gamma", seed=1, mac="AA:BB:CC:00:00:11")
    hosts["gamma.test"] = sim.app()
    added = await ctx.fleet.add_by_host("gamma.test", drivers=["axeos"])
    url = "/api/v1" + path.replace("{id}", added.device.id)
    response = await c.request(method, url, json={} if method == "POST" else None)
    assert response.status_code in (404, 405), response.text
    assert all(call[0] == "GET" for call in sim.calls)


# --- (c) the MCP server ------------------------------------------------------------------------------------------


class _NoBackend:
    async def call(self, *args: object, **kwargs: object) -> dict[str, object]:
        return {}


async def test_mcp_server_exposes_no_control_tools():
    names = [tool.name for tool in await build_server(_NoBackend()).list_tools()]
    assert names
    assert FORBIDDEN_MCP_TOOLS & set(names) == set()
    assert [name for name in names if CONTROL_TOOL_NAME.search(name) or "action" in name] == []


# --- (d) the CLI -------------------------------------------------------------------------------------------------


def _command_names(group: Any, prefix: str = "") -> list[str]:
    names: list[str] = []
    for name, command in getattr(group, "commands", {}).items():
        names.append(f"{prefix}{name}")
        names.extend(_command_names(command, f"{prefix}{name} "))
    return names


def test_cli_has_no_control_commands():
    names = _command_names(get_command(cli_app))
    assert "status" in names  # the walk found the real command tree
    words = {word for name in names for word in re.split(r"[\s-]+", name)}
    assert words & CONTROL_CLI_WORDS == set()


# --- data saved by earlier releases still loads ------------------------------------------------------------------

OLD_SAFETY_SETTINGS = {"allow_control": False, "allow_tuning": True, "max_temp_c": 70.0}
OLD_CONTROL_CAPABILITIES = ["restart", "identify", "set_pool", "set_fan", "set_frequency", "set_voltage", "set_hostname", "pause"]


async def test_saved_settings_with_safety_keys_still_load(lan):
    ctx, _ = lan
    await ctx.store.kv_set("settings", {"general": {"instance_name": "Kept"}, "safety": OLD_SAFETY_SETTINGS})
    loaded = await SettingsService(ctx.store).load()
    assert loaded.general.instance_name == "Kept"  # not the fail-closed fallback used for unreadable settings
    assert "safety" not in loaded.model_dump()


async def test_an_old_config_export_with_safety_and_allow_control_still_imports(api):
    c, ctx, _ = api
    legacy_export = {
        "format": "bsmm-config-v1",
        "settings": {"general": {"instance_name": "Imported"}, "safety": OLD_SAFETY_SETTINGS},
        "devices": [{
            "id": "dev_legacy", "name": "Legacy", "driver": "axeos", "family": "bitaxe", "model": "Gamma",
            "host": "legacy.test", "port": 80, "mac": "AA:BB:CC:00:00:99",
            "allow_control": False, "capabilities": [*OLD_CONTROL_CAPABILITIES, "scoreboard"],
        }],
    }
    response = await c.post("/api/v1/system/import", json=legacy_export)
    assert response.status_code == 200, response.text
    assert response.json()["added"]["devices"] == 1
    imported = await ctx.store.get_device("dev_legacy")
    assert imported is not None
    assert imported.capabilities == [Capability.SCOREBOARD]
    assert ctx.settings.current.general.instance_name == "Imported"
    assert "safety" not in await ctx.store.kv_get("settings")

    exported = (await c.get("/api/v1/system/export")).json()
    assert "safety" not in exported["settings"]
    assert all("allow_control" not in device for device in exported["devices"])


async def test_a_settings_update_that_still_names_safety_is_accepted_and_ignored(api):
    c, *_ = api
    response = await c.patch("/api/v1/settings", json={"safety": {"allow_tuning": True}})
    assert response.status_code == 200, response.text
    assert "safety" not in response.json()


async def test_a_stored_miner_with_control_capabilities_loads_and_keeps_its_saved_flag(lan):
    ctx, _ = lan
    info = DeviceInfo(driver="axeos", family="bitaxe", model="Gamma", host="legacy.test", port=80)
    stored = await ctx.store.add_device(info, name="Legacy")
    await ctx.store.db.execute(
        "UPDATE devices SET capabilities = ?, allow_control = 0 WHERE id = ?",
        (json.dumps([*OLD_CONTROL_CAPABILITIES, "scoreboard"]), stored.id),
    )
    loaded = await ctx.store.get_device(stored.id)
    assert loaded is not None
    assert loaded.capabilities == [Capability.SCOREBOARD]
    assert "allow_control" not in loaded.model_dump()

    await ctx.store.save_device(loaded)  # an ordinary edit must not rewrite the unused column
    row = await ctx.store.db.fetchone("SELECT allow_control FROM devices WHERE id = ?", (stored.id,))
    assert row is not None and row["allow_control"] == 0

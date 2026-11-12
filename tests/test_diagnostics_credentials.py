"""Read-scope raw miner diagnostics hide credentials at any depth and keep identity/diagnostic fields."""

from __future__ import annotations

import pytest

from tests.test_api import EX_ADDR, add_miner

HIDDEN = "<redacted>"
SECRET = "SYNTHETIC_PRIVATE_VALUE"


async def _read_raw(api, injected):
    """Make one polled simulated miner report ``injected`` extra fields and fetch /raw with a read token.

    Returns the parsed reply and the miner's own (unmodified) raw reply."""
    c, ctx, hosts = api
    dev = await add_miner(c, ctx, hosts)
    driver = ctx.fleet.runtimes[dev.id].driver
    original = dict(driver.last_raw)
    driver.last_raw = {**original, **injected}
    await ctx.auth.set_password("synthetic-test-password")
    await ctx.settings.update({"auth": {"mode": "password"}})
    _, token = await ctx.store.create_token("reader", "read")
    r = await c.get(f"/api/v1/devices/{dev.id}/raw", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    return r, original


async def test_raw_diagnostics_hide_nested_credentials_for_read_token(api):
    injected = {
        "wifiPass": f"{SECRET}-wifi",
        "Network": {"Wifi": {"PassWord": f"{SECRET}-nested", "label": "visible-label"}},
        "pools": [
            {
                "URL": f"stratum+tcp://worker1:{SECRET}-pool@pool.example.com:3333",
                "User": f"{EX_ADDR}.rig1",
                "Priority": 0,
                "Extra": [{"apiToken": f"{SECRET}-token", "Label": "pool-a"}],
            },
        ],
        "AuthToken": f"{SECRET}-auth",
        "CLIENT_SECRET": f"{SECRET}-client",
        "apiKey": f"{SECRET}-key",
        "note": f"fallback https://admin:{SECRET}-note@backup.example/path",
    }
    r, original = await _read_raw(api, injected)
    raw = r.json()["raw"]

    # no credential value survives anywhere in the response, at any depth
    assert SECRET not in r.text

    # credential-style fields are replaced, not dropped, and nested ones are reached
    assert raw["Network"]["Wifi"]["PassWord"] == HIDDEN
    assert raw["pools"][0]["Extra"][0]["apiToken"] == HIDDEN
    assert raw["AuthToken"] == HIDDEN
    assert raw["CLIENT_SECRET"] == HIDDEN
    assert raw["apiKey"] == HIDDEN

    # user info inside a URL is replaced while the address stays readable
    assert raw["pools"][0]["URL"] == f"stratum+tcp://{HIDDEN}@pool.example.com:3333"
    assert raw["note"] == f"fallback https://{HIDDEN}@backup.example/path"

    # model, identity and ordinary diagnostic fields are untouched
    assert raw["ASICModel"] == "BM1370" == original["ASICModel"]
    assert raw["macAddr"] == original["macAddr"] and raw["hostname"] == original["hostname"]
    assert raw["Network"]["Wifi"]["label"] == "visible-label"
    assert raw["pools"][0]["User"] == f"{EX_ADDR}.rig1" and raw["pools"][0]["Priority"] == 0
    assert raw["pools"][0]["Extra"][0]["Label"] == "pool-a"


@pytest.mark.parametrize(
    "name",
    ["password", "Pass", "PASSWORD", "wifiPass", "stratumPassword", "apiToken", "AUTH_TOKEN", "clientSecret", "api-key", "privateKey", "KEY"],
)
async def test_raw_diagnostics_hide_credential_names_in_any_case(api, name):
    r, _ = await _read_raw(api, {"outer": [{"inner": {name: f"{SECRET}-value"}}]})
    assert SECRET not in r.text
    assert r.json()["raw"]["outer"][0]["inner"][name] == HIDDEN

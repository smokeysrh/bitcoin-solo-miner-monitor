"""Card #2479: login limits use the client address the trusted proxy added to ``X-Forwarded-For``.

A proxy that appends to ``X-Forwarded-For`` writes the address it saw on the right-hand end, so the
right-most entry that is not a trusted proxy is the one that can be believed.
"""

from types import SimpleNamespace

import httpx
import pytest
from starlette.requests import Request

from bsmm.api.app import create_app
from bsmm.api.deps import client_ip

PROXY = "10.0.0.1"
SECOND_PROXY = "10.0.0.2"
PASSWORD = "correct horse battery"
WRONG_PASSWORD_LIMIT = 5


def _request(peer: str | None, forwarded: list[str], trusted: list[str]) -> Request:
    headers = [(b"x-forwarded-for", value.encode()) for value in forwarded]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": b"",
        "client": (peer, 40000) if peer else None,
        "app": SimpleNamespace(state=SimpleNamespace(ctx=SimpleNamespace(config=SimpleNamespace(trusted_proxies=trusted)))),
    }
    return Request(scope)


def test_trusted_peer_uses_the_address_the_proxy_appended():
    request = _request(PROXY, ["1.2.3.4, 10.0.0.9"], [PROXY])
    assert client_ip(request) == "10.0.0.9"


def test_trusted_hops_on_the_right_are_skipped():
    request = _request(PROXY, ["1.2.3.4, 203.0.113.7, 10.0.0.2"], [PROXY, SECOND_PROXY])
    assert client_ip(request) == "203.0.113.7"


def test_forwarded_header_sent_as_several_lines_is_read_as_one_list():
    request = _request(PROXY, ["1.2.3.4", "203.0.113.7"], [PROXY])
    assert client_ip(request) == "203.0.113.7"


def test_untrusted_peer_ignores_the_forwarded_header():
    request = _request("198.51.100.20", ["1.2.3.4, 10.0.0.9"], [PROXY])
    assert client_ip(request) == "198.51.100.20"


def test_no_trusted_proxies_ignores_the_forwarded_header():
    request = _request(PROXY, ["1.2.3.4"], [])
    assert client_ip(request) == PROXY


def test_missing_header_gives_the_peer():
    assert client_ip(_request(PROXY, [], [PROXY])) == PROXY


def test_all_entries_trusted_gives_the_peer():
    request = _request(PROXY, ["10.0.0.2, 10.0.0.1"], [PROXY, SECOND_PROXY])
    assert client_ip(request) == PROXY


def test_unreadable_entry_gives_the_peer():
    request = _request(PROXY, ["1.2.3.4, not-an-address"], [PROXY])
    assert client_ip(request) == PROXY


def test_same_address_written_differently_is_one_client():
    request = _request(PROXY, ["2001:DB8:0:0:0:0:0:1"], [PROXY])
    assert client_ip(request) == "2001:db8::1"


async def _wrong_logins(client: httpx.AsyncClient, leftmost_values: list[str], appended: str) -> list[int]:
    codes = []
    for leftmost in leftmost_values:
        r = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong password"},
            headers={"X-Forwarded-For": f"{leftmost}, {appended}"},
        )
        codes.append(r.status_code)
    return codes


async def test_login_limit_follows_the_proxy_appended_address(lan):
    ctx, _hosts = lan
    ctx.config.trusted_proxies = [PROXY]
    await ctx.auth.set_password(PASSWORD)
    transport = httpx.ASGITransport(app=create_app(ctx=ctx), client=(PROXY, 40000))
    async with httpx.AsyncClient(transport=transport, base_url="http://bsmm.test") as c:
        leftmost_values = [f"192.0.2.{n}" for n in range(1, WRONG_PASSWORD_LIMIT + 1)]
        codes = await _wrong_logins(c, leftmost_values, "203.0.113.50")
        assert codes == [401] * WRONG_PASSWORD_LIMIT

        locked = await c.post(
            "/api/v1/auth/login",
            json={"password": PASSWORD},
            headers={"X-Forwarded-For": "192.0.2.99, 203.0.113.50"},
        )
        assert locked.status_code == 429 and locked.json()["error"]["code"] == "rate_limited"

        other = await c.post(
            "/api/v1/auth/login",
            json={"password": PASSWORD},
            headers={"X-Forwarded-For": "192.0.2.99, 203.0.113.51"},
        )
        assert other.status_code == 200, other.text


@pytest.mark.parametrize("trusted", [[], ["10.9.9.9"]], ids=["no-proxies", "other-proxy"])
async def test_login_limit_uses_the_peer_when_the_header_is_not_trusted(lan, trusted):
    ctx, _hosts = lan
    ctx.config.trusted_proxies = trusted
    await ctx.auth.set_password(PASSWORD)
    transport = httpx.ASGITransport(app=create_app(ctx=ctx), client=(PROXY, 40000))
    async with httpx.AsyncClient(transport=transport, base_url="http://bsmm.test") as c:
        leftmost_values = [f"192.0.2.{n}" for n in range(1, WRONG_PASSWORD_LIMIT + 1)]
        await _wrong_logins(c, leftmost_values, "203.0.113.50")
        locked = await c.post(
            "/api/v1/auth/login",
            json={"password": PASSWORD},
            headers={"X-Forwarded-For": "192.0.2.99, 203.0.113.60"},
        )
        assert locked.status_code == 429

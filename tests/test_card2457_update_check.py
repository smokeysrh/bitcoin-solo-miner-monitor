"""Card #2457: the update check is one-way, bounded, and can be switched off.

The check makes exactly one anonymous GET to GitHub's releases address from a client made for that call alone, reads at
most 256 KB of the reply and keeps only a normal version, a link on this project's own GitHub page and the time. The
GitHub side is ``httpx.MockTransport`` (the app's own client forbids every request, so a check that used it would fail
here); nothing talks to the real GitHub.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest

from bsmm import __version__, updates
from bsmm.api.app import create_app
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.net import USER_AGENT
from bsmm.settings import Settings
from bsmm.updates import (
    KEY,
    MAX_REPLY_BYTES,
    RELEASES_PAGE_URL,
    RELEASES_URL,
    check_for_update,
    make_update_client,
    scrub_stored_update_info,
)

PROJECT = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor"
GOOD_LINK = f"{PROJECT}/releases/tag/v99.0.0"
RELEASE_TEXT = "RELEASE-TEXT-THAT-MUST-NOT-BE-KEPT"
RECORD_KEYS = {"current", "checked_at", "latest", "update_available", "url", "error"}
# What a plain request carries: the two headers the check sets and the ones HTTP itself needs.
ALLOWED_HEADERS = {"host", "user-agent", "accept", "accept-encoding", "connection"}
PASSWORD = "correct horse battery"
CHUNK = 64 * 1024


def release(**changes: object) -> dict[str, object]:
    body: dict[str, object] = {
        "tag_name": "v99.0.0",
        "html_url": GOOD_LINK,
        "name": RELEASE_TEXT,
        "body": RELEASE_TEXT,
        "notes": RELEASE_TEXT,
        "assets": [{"browser_download_url": "https://evil.example/app.exe"}],
    }
    body.update(changes)
    return body


class Github:
    """The mock GitHub: records every request it receives and answers with ``reply``."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.reply: Callable[[httpx.Request], httpx.Response] = lambda request: httpx.Response(200, json=release())

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.reply(request)

    def answer(self, response: httpx.Response) -> None:
        self.reply = lambda request: response


class Endless(httpx.AsyncByteStream):
    """A reply body that never ends; records how much of it was pulled and whether it was closed."""

    def __init__(self) -> None:
        self.pulled = 0
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b'{"tag_name": "v99.0.0", "pad": "'
        while True:
            self.pulled += CHUNK
            yield b"x" * CHUNK

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> Github:
    mock = Github()
    monkeypatch.setattr(updates, "_transport", httpx.MockTransport(mock))
    return mock


@pytest.fixture
async def make_ctx(tmp_path):
    """Builds an AppContext whose shared client fails the test on any request (the update check must not use it)."""
    built: list[AppContext] = []

    async def build(**config: Any) -> AppContext:
        def shared_client_must_stay_unused(request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"the update check used the shared client: {request.url}")

        http = httpx.AsyncClient(transport=httpx.MockTransport(shared_client_must_stay_unused))
        settings: dict[str, object] = {"offline": False, "no_update_check": False, "demo": False}
        cfg = RuntimeConfig(data_dir=tmp_path, allowed_hosts=["bsmm.test"], **{**settings, **config})
        ctx = await AppContext.create(cfg, http=http)
        built.append(ctx)
        return ctx

    yield build
    for ctx in built:
        await ctx.fleet.stop()
        await ctx.http.aclose()
        await ctx.store.close()


@pytest.fixture
async def ctx(make_ctx) -> AppContext:
    return await make_ctx()


def client_for(ctx: AppContext, **kwargs: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test", **kwargs)


async def stored(ctx: AppContext) -> dict[str, object]:
    return await ctx.store.kv_get(KEY)


# ------------------------------------------------------------------------------------- one request, nothing else


async def test_exactly_one_get_to_the_releases_address_with_nothing_attached(ctx, github):
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] == "99.0.0"
    assert len(github.requests) == 1
    request = github.requests[0]
    assert request.method == "GET"
    assert str(request.url) == RELEASES_URL
    assert request.url.query == b"" and request.content == b""
    names = {name.lower() for name in request.headers}
    assert names <= ALLOWED_HEADERS, f"unexpected headers: {names - ALLOWED_HEADERS}"
    assert "cookie" not in names and "authorization" not in names
    assert request.headers["user-agent"] == USER_AGENT
    assert request.headers["accept"] == "application/vnd.github+json"


async def test_a_cookie_from_one_reply_is_never_sent_with_the_next_check(ctx, github):
    github.answer(httpx.Response(200, json=release(), headers={"set-cookie": "session=abc; Path=/"}))
    await check_for_update(ctx.store, force=True)
    await check_for_update(ctx.store, force=True)
    assert len(github.requests) == 2
    assert all("cookie" not in request.headers for request in github.requests)


async def test_the_check_has_its_own_client_and_never_takes_the_shared_one():
    assert "http" not in inspect.signature(check_for_update).parameters
    client = make_update_client()
    try:
        assert client.follow_redirects is False
        assert client.timeout == httpx.Timeout(8.0)
        assert client.headers["user-agent"] == USER_AGENT
        assert client.headers["accept"] == "application/vnd.github+json"
        assert client.auth is None
        assert len(client.cookies) == 0
    finally:
        await client.aclose()


@pytest.mark.parametrize("status", [301, 302, 307])
async def test_a_redirect_is_not_followed(ctx, github, status):
    github.answer(httpx.Response(status, headers={"location": "https://evil.example/latest"}))
    result = await check_for_update(ctx.store, force=True)
    assert [str(r.url) for r in github.requests] == [RELEASES_URL]
    assert result["latest"] is None and result["update_available"] is False
    assert result["error"] == f"GitHub answered HTTP {status}"


# ------------------------------------------------------------------------------------- what is kept from the reply


async def test_only_version_link_and_time_are_kept_and_release_text_never_is(ctx, github):
    result = await check_for_update(ctx.store, force=True)
    assert set(result) == RECORD_KEYS
    assert result["latest"] == "99.0.0" and result["update_available"] is True
    assert result["url"] == GOOD_LINK and result["error"] is None
    assert isinstance(result["checked_at"], float)
    saved = await stored(ctx)
    assert set(saved) == RECORD_KEYS
    assert RELEASE_TEXT not in json.dumps(saved) and "evil.example" not in json.dumps(saved)
    assert "notes" not in result and "notes" not in saved


@pytest.mark.parametrize(
    "link",
    [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "https://evil.example/smokeysrh/bitcoin-solo-miner-monitor/releases",
        "https://github.com.evil.example/smokeysrh/bitcoin-solo-miner-monitor/releases",
        "https://github.com@evil.example/smokeysrh/bitcoin-solo-miner-monitor/releases",
        "https://user:pw@github.com/smokeysrh/bitcoin-solo-miner-monitor/releases",
        "http://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases/tag/v99.0.0",
        "https://github.com/someone-else/bitcoin-solo-miner-monitor/releases/tag/v99.0.0",
        "https://github.com/smokeysrh/bitcoin-solo-miner-monitor-fork/releases",
        "https://github.com/smokeysrh/bitcoin-solo-miner-monitor",
        f"{PROJECT}/../evil/repo",
        f"{PROJECT}/%2e%2e/evil/repo",
        f"{PROJECT}/releases?next=https://evil.example",
        f"{PROJECT}/releases#frag",
        f"{PROJECT}/releases/tag/v99 onclick=1",
        f"{PROJECT}/releases\\..\\evil",
        f"{PROJECT}/" + "a" * 300,
        "",
        None,
        42,
        ["https://github.com"],
    ],
)
async def test_a_link_off_this_projects_github_page_is_replaced_by_the_releases_page(ctx, github, link):
    github.answer(httpx.Response(200, json=release(html_url=link)))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] == "99.0.0"
    assert result["url"] == RELEASES_PAGE_URL == f"{PROJECT}/releases"
    assert (await stored(ctx))["url"] == RELEASES_PAGE_URL


async def test_a_reply_without_a_link_gets_the_releases_page(ctx, github):
    reply = release()
    del reply["html_url"]
    github.answer(httpx.Response(200, json=reply))
    assert (await check_for_update(ctx.store, force=True))["url"] == RELEASES_PAGE_URL


@pytest.mark.parametrize(
    "tag",
    [
        "",
        "latest",
        "nightly-build",
        "1.0; DROP TABLE kv",
        "<script>alert(1)</script>",
        "v" * 30 + "1.0",
        "99.0.0" + ".0" * 20,
        "99.0.0.0.0.0.0.0.0.00",  # 21 characters
        12345,
        None,
        ["99.0.0"],
        {"v": "99.0.0"},
    ],
)
async def test_a_version_that_is_not_a_normal_short_version_is_no_update_info(ctx, github, tag):
    github.answer(httpx.Response(200, json=release(tag_name=tag)))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] is None and result["update_available"] is False and result["url"] is None
    assert result["error"] is not None
    saved = await stored(ctx)
    assert set(saved) == RECORD_KEYS and saved["latest"] is None and saved["url"] is None
    if isinstance(tag, str) and tag:
        assert tag not in json.dumps(list(saved.values()))  # the junk text is nowhere in the saved record


async def test_a_version_of_exactly_twenty_characters_is_accepted(ctx, github):
    tag = "99.0.0.0.0.0.0.0.0.0"
    assert len(tag) == 20
    github.answer(httpx.Response(200, json=release(tag_name=tag)))
    assert (await check_for_update(ctx.store, force=True))["latest"] == tag


@pytest.mark.parametrize("content", [b"<html>not json</html>", b"[1, 2, 3]", b'"just a string"', b"null", b"\xff\xfe"])
async def test_a_reply_that_is_not_a_release_object_is_no_update_info(ctx, github, content):
    github.answer(httpx.Response(200, content=content))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] is None and result["update_available"] is False and result["error"] is not None
    assert set(await stored(ctx)) == RECORD_KEYS


async def test_a_declared_huge_reply_is_refused_without_reading_it(ctx, github):
    huge = b'{"tag_name": "v99.0.0", "pad": "' + b"x" * (MAX_REPLY_BYTES + 1) + b'"}'
    github.answer(httpx.Response(200, content=huge))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] is None and result["update_available"] is False
    assert result["error"] == "could not check (reply too large)"
    assert "xxxx" not in json.dumps(await stored(ctx))


async def test_an_endless_reply_is_read_only_up_to_the_budget_and_then_closed(ctx, github):
    body = Endless()
    github.answer(httpx.Response(200, stream=body))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] is None and result["error"] == "could not check (reply too large)"
    assert MAX_REPLY_BYTES == 256 * 1024
    assert body.pulled <= MAX_REPLY_BYTES + 2 * CHUNK
    assert body.closed


async def test_a_reply_just_under_the_budget_is_still_read(ctx, github):
    padding = "x" * (MAX_REPLY_BYTES - 1024)
    github.answer(httpx.Response(200, json=release(pad=padding)))
    result = await check_for_update(ctx.store, force=True)
    assert result["latest"] == "99.0.0"
    assert padding not in json.dumps(await stored(ctx))


@pytest.mark.parametrize(
    ("answer", "message"),
    [
        (httpx.Response(404), None),
        (httpx.Response(500), "GitHub answered HTTP 500"),
        (httpx.Response(403, json={"message": RELEASE_TEXT}), "GitHub answered HTTP 403"),
    ],
)
async def test_http_failures_are_reported_in_a_fixed_form(ctx, github, answer, message):
    github.answer(answer)
    result = await check_for_update(ctx.store, force=True)
    assert result["error"] == message and result["latest"] is None and result["update_available"] is False
    assert RELEASE_TEXT not in json.dumps(await stored(ctx))


async def test_an_unreachable_github_is_an_error_not_an_empty_success(ctx, github):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    github.reply = unreachable
    result = await check_for_update(ctx.store, force=True)
    assert result["error"] == "could not check (ConnectError)" and result["latest"] is None


async def test_a_fresh_result_is_reused_for_a_day_without_a_second_call(ctx, github):
    first = await check_for_update(ctx.store)
    second = await check_for_update(ctx.store)
    assert len(github.requests) == 1 and second == first


# ------------------------------------------------------------------ results saved by earlier releases carry release text


def old_saved_result(**changes: object) -> dict[str, object]:
    saved: dict[str, object] = {
        "current": "0.0.1",
        "checked_at": time.time(),
        "latest": "99.0.0",
        "update_available": True,
        "url": "javascript:alert(1)",
        "notes": RELEASE_TEXT,
        "error": None,
    }
    saved.update(changes)
    return saved


async def test_a_saved_result_from_an_earlier_release_is_returned_without_its_release_text(ctx, github):
    await ctx.store.kv_set(KEY, old_saved_result())
    result = await check_for_update(ctx.store)
    assert github.requests == []
    assert set(result) == RECORD_KEYS and RELEASE_TEXT not in json.dumps(result)
    assert result["url"] == RELEASES_PAGE_URL and result["current"] == __version__


async def test_scrubbing_rewrites_the_saved_result_without_release_text(ctx):
    await ctx.store.kv_set(KEY, old_saved_result())
    await scrub_stored_update_info(ctx.store)
    saved = await stored(ctx)
    assert set(saved) == RECORD_KEYS and RELEASE_TEXT not in json.dumps(saved)
    assert saved["latest"] == "99.0.0" and saved["url"] == RELEASES_PAGE_URL


async def test_scrubbing_with_nothing_saved_saves_nothing(ctx):
    await scrub_stored_update_info(ctx.store)
    assert await ctx.store.kv_get(KEY) is None


async def test_the_status_endpoint_never_returns_saved_release_text(ctx, github):
    await ctx.store.kv_set(KEY, old_saved_result())
    async with client_for(ctx) as c:
        body = (await c.get("/api/v1/system/update")).json()
    assert set(body) == RECORD_KEYS and RELEASE_TEXT not in json.dumps(body)


# --------------------------------------------------------------------------------- the Settings switch (background only)


def test_the_automatic_check_defaults_to_on():
    assert Settings().network.check_for_updates is True


async def test_the_switch_is_saved_and_survives_a_reload(ctx):
    assert ctx.settings.current.network.check_for_updates is True
    async with client_for(ctx) as c:
        patched = await c.patch("/api/v1/settings", json={"network": {"check_for_updates": False}})
        assert patched.status_code == 200 and patched.json()["network"]["check_for_updates"] is False
        assert (await c.get("/api/v1/settings")).json()["network"]["check_for_updates"] is False
    await ctx.settings.load()
    assert ctx.settings.current.network.check_for_updates is False
    assert ctx.settings.current.network.use_public_apis is True  # the neighbouring switch is untouched


async def test_the_background_check_calls_github_once_while_the_switch_is_on(ctx, github):
    await ctx._daily_update_check()
    assert [str(r.url) for r in github.requests] == [RELEASES_URL]
    assert (await stored(ctx))["latest"] == "99.0.0"


async def test_the_background_check_makes_no_call_while_the_switch_is_off(ctx, github):
    await ctx.settings.update({"network": {"check_for_updates": False}})
    await ctx._daily_update_check()
    assert github.requests == []
    assert await ctx.store.kv_get(KEY) is None


async def test_the_background_loop_waits_a_minute_before_its_first_call(ctx, github):
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(ctx._update_loop(), timeout=0.2)
    assert github.requests == []


@pytest.mark.parametrize("config", [{"offline": True}, {"no_update_check": True}, {"demo": True}])
async def test_offline_env_switch_and_demo_stop_the_background_loop_before_any_call(make_ctx, github, config):
    ctx = await make_ctx(**config)
    assert ctx.update_checks_blocked is True
    await asyncio.wait_for(ctx._update_loop(), timeout=1)  # returns at once; a live loop would sleep for a minute
    assert github.requests == []


async def test_nothing_blocks_the_check_in_the_normal_mode(ctx):
    assert ctx.update_checks_blocked is False


# ---------------------------------------------------------------- the button and the status endpoint with the switch off


async def test_the_button_still_checks_while_the_switch_is_off(ctx, github):
    await ctx.settings.update({"network": {"check_for_updates": False}})
    async with client_for(ctx) as c:
        response = await c.post("/api/v1/system/update/check")
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(github.requests) == 1
    assert set(body) == RECORD_KEYS and "notes" not in body
    assert body["latest"] == "99.0.0" and body["update_available"] is True and body["url"] == GOOD_LINK
    assert RELEASE_TEXT not in response.text


async def test_the_status_endpoint_is_cached_only_while_the_switch_is_off(ctx, github):
    await ctx.settings.update({"network": {"check_for_updates": False}})
    async with client_for(ctx) as c:
        first = await c.get("/api/v1/system/update")
        assert first.status_code == 200 and first.json()["latest"] is None
        assert github.requests == []  # opening Settings must not call out while automatic checks are off
        await c.post("/api/v1/system/update/check")
        again = (await c.get("/api/v1/system/update")).json()
    assert len(github.requests) == 1
    assert again["latest"] == "99.0.0" and set(again) == RECORD_KEYS


async def test_the_status_endpoint_still_checks_while_the_switch_is_on(ctx, github):
    async with client_for(ctx) as c:
        body = (await c.get("/api/v1/system/update")).json()
    assert len(github.requests) == 1 and body["latest"] == "99.0.0" and "notes" not in body


@pytest.mark.parametrize("config", [{"offline": True}, {"no_update_check": True}, {"demo": True}])
async def test_the_button_and_the_status_endpoint_make_no_call_when_checks_are_blocked(make_ctx, github, config):
    ctx = await make_ctx(**config)
    async with client_for(ctx) as c:
        refused = await c.post("/api/v1/system/update/check")
        status = await c.get("/api/v1/system/update")
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "disabled"
    assert status.json()["disabled"] is True and status.json()["update_available"] is False
    assert github.requests == []


# ------------------------------------------------------------------------------------------------------ who may press it


async def test_the_button_needs_control_scope_and_a_read_token_makes_no_call(ctx, github):
    async with client_for(ctx) as admin:
        assert (await admin.post("/api/v1/auth/password", json={"new_password": PASSWORD})).status_code == 200
        read = (await admin.post("/api/v1/auth/tokens", json={"name": "reader", "scope": "read"})).json()["token"]
        control = (await admin.post("/api/v1/auth/tokens", json={"name": "operator", "scope": "control"})).json()["token"]
    async with client_for(ctx, headers={"Authorization": f"Bearer {read}"}) as reader:
        denied = await reader.post("/api/v1/system/update/check")
        assert denied.status_code == 403 and denied.json()["error"]["code"] == "insufficient_scope"
        assert (await reader.get("/api/v1/system/update")).status_code == 200  # looking is still allowed
        forbidden = await reader.patch("/api/v1/settings", json={"network": {"check_for_updates": False}})
        assert forbidden.status_code == 403
    assert len(github.requests) == 1  # only the read token's GET (cache was empty); the refused POST sent nothing
    github.requests.clear()
    async with client_for(ctx, headers={"Authorization": f"Bearer {control}"}) as operator:
        allowed = await operator.post("/api/v1/system/update/check")
        assert allowed.status_code == 200 and "notes" not in allowed.json()
        changed = await operator.patch("/api/v1/settings", json={"network": {"check_for_updates": False}})
        assert changed.status_code == 403  # the switch is an admin setting
    assert len(github.requests) == 1
    assert ctx.settings.current.network.check_for_updates is True

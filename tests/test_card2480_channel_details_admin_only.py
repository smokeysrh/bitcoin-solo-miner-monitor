"""Card #2480: the notification channel list shows channel details (its saved settings) to admins only."""

from __future__ import annotations

import json

import httpx

from bsmm.api.app import create_app

NTFY_TOPIC = "card2480-example-topic"
EMAIL_HOST = "smtp.card2480.example"
EMAIL_USER = "card2480-user"
EMAIL_FROM = "sender-2480@example.com"
EMAIL_TO = "recipient-2480@example.com"
DETAIL_VALUES = (NTFY_TOPIC, EMAIL_HOST, EMAIL_USER, EMAIL_FROM, EMAIL_TO)
PASSWORD = "correct horse battery"
EXPECTED_KEYS = {"id", "kind", "name", "enabled", "min_severity", "has_secret", "created_at"}


async def _admin_with_channels(api):
    """The `api` client is the admin once a password is set (it holds the session cookie)."""
    c, ctx, _ = api
    assert (await c.post("/api/v1/auth/password", json={"new_password": PASSWORD})).status_code == 200
    ntfy = await c.post("/api/v1/notifications/channels",
                        json={"kind": "ntfy", "name": "Phone", "config": {"topic": NTFY_TOPIC}, "secret": {"token": "tk_card2480"}})
    assert ntfy.status_code == 200, ntfy.text
    mail = await c.post("/api/v1/notifications/channels",
                        json={"kind": "email", "name": "Inbox",
                              "config": {"host": EMAIL_HOST, "username": EMAIL_USER, "sender": EMAIL_FROM, "to": EMAIL_TO},
                              "secret": {"password": "pw_card2480"}})
    assert mail.status_code == 200, mail.text
    return c, ctx, ntfy.json()["channel"], mail.json()["channel"]


def _assert_no_details(response: httpx.Response) -> list[dict]:
    assert response.status_code == 200, response.text
    for value in DETAIL_VALUES:
        assert value not in response.text
    channels = response.json()["channels"]
    assert len(channels) == 2
    for ch in channels:
        assert "config" not in ch
        assert set(ch) == EXPECTED_KEYS
    return channels


async def test_read_token_channel_list_has_no_channel_details(api):
    c, ctx, ntfy, mail = await _admin_with_channels(api)
    tok = (await c.post("/api/v1/auth/tokens", json={"name": "viewer", "scope": "read"})).json()
    viewer = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test",
                               headers={"Authorization": f"Bearer {tok['token']}"})
    try:
        channels = _assert_no_details(await viewer.get("/api/v1/notifications/channels"))
    finally:
        await viewer.aclose()
    by_id = {ch["id"]: ch for ch in channels}
    assert by_id[ntfy["id"]]["kind"] == "ntfy" and by_id[ntfy["id"]]["name"] == "Phone"
    assert by_id[ntfy["id"]]["has_secret"] is True and by_id[ntfy["id"]]["enabled"] is True
    assert by_id[mail["id"]]["kind"] == "email" and by_id[mail["id"]]["min_severity"] == "info"


async def test_public_read_channel_list_has_no_channel_details(api):
    c, ctx, *_ = await _admin_with_channels(api)
    assert (await c.patch("/api/v1/settings", json={"auth": {"public_read": True}})).status_code == 200
    anon = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(ctx=ctx)), base_url="http://bsmm.test")
    try:
        _assert_no_details(await anon.get("/api/v1/notifications/channels"))
    finally:
        await anon.aclose()


async def test_admin_channel_list_keeps_channel_details(api):
    c, *_ = await _admin_with_channels(api)
    r = await c.get("/api/v1/notifications/channels")
    assert r.status_code == 200
    by_kind = {ch["kind"]: ch for ch in r.json()["channels"]}
    assert by_kind["ntfy"]["config"] == {"topic": NTFY_TOPIC}
    assert by_kind["email"]["config"]["host"] == EMAIL_HOST and by_kind["email"]["config"]["to"] == EMAIL_TO
    assert "tk_card2480" not in json.dumps(r.json()) and "pw_card2480" not in json.dumps(r.json())

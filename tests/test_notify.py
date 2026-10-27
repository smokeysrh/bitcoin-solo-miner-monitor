"""Notification channels (exact request shapes, error mapping) and the dispatcher (filters, quiet hours, retries).

The HTTP layer is replaced with ``httpx.MockTransport`` so every request a channel makes can be inspected
byte for byte; the SMTP layer is replaced with a recording fake. Nothing here touches a real network.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import smtplib
import sys
import types
from datetime import datetime
from types import SimpleNamespace
from urllib.parse import parse_qs

import httpx
import pytest

import bsmm.notify.dispatcher as dispatcher_mod
from bsmm import __version__
from bsmm.models import Channel, Severity
from bsmm.notify.channels import (
    CHANNEL_CLASSES,
    AppriseChannel,
    BaseChannel,
    ChannelError,
    DiscordChannel,
    EmailChannel,
    Notification,
    NtfyChannel,
    PushoverChannel,
    SlackChannel,
    TelegramChannel,
    WebhookChannel,
)
from bsmm.notify.dispatcher import DeliveryResult, Notifier, in_quiet_hours

TS = 1_700_000_000.0  # 2023-11-14T22:13:20Z
DISCORD_URL = "https://discord.test/api/webhooks/111/TOPSECRETDISCORD"
SLACK_URL = "https://hooks.slack.test/services/T000/B000/TOPSECRETSLACK"
HOOK_URL = "https://hook.test/in/TOPSECRETHOOK"
BOT_TOKEN = "123456:TOPSECRETBOT"
# spelled as escapes because two of them carry an invisible emoji-variation selector
ICON = {Severity.INFO: "\u2139\ufe0f", Severity.SUCCESS: "\u2705", Severity.WARNING: "\u26a0\ufe0f", Severity.CRITICAL: "\U0001f6a8"}

HOT = Notification(
    title="Gamma is running hot", body="ASIC 91 °C (limit 75)", severity=Severity.WARNING, type="temp_high",
    device_id="dev_1", ts=TS,
)


class Wire:
    """A fake remote service. Records every request and answers from a script.

    Script items are an HTTP status (int), an exception instance to raise, or a callable that builds the
    exception from the request (so a test can put the secret URL into the exception text, like some real
    errors do). The last item repeats forever.
    """

    def __init__(self, *script: int | Exception | object) -> None:
        self.script = list(script) or [200]
        self.requests: list[httpx.Request] = []
        self.clients: list[httpx.AsyncClient] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if callable(item):
            item = item(request)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(int(item), text="ok")  # type: ignore[arg-type]

    def client(self) -> httpx.AsyncClient:
        c = httpx.AsyncClient(transport=httpx.MockTransport(self))
        self.clients.append(c)
        return c

    def json(self, i: int = 0):
        return json.loads(self.requests[i].content)

    async def aclose(self) -> None:
        for c in self.clients:
            await c.aclose()


@pytest.fixture
async def make_wire():
    wires: list[Wire] = []

    def factory(*script) -> Wire:
        w = Wire(*script)
        wires.append(w)
        return w

    yield factory
    for w in wires:
        await w.aclose()


# --- Discord / Telegram / Slack: JSON posts --------------------------------------------------------------


async def test_discord_posts_an_embed(make_wire):
    wire = make_wire()
    await DiscordChannel({}, {"webhook_url": DISCORD_URL}, wire.client()).send(HOT)
    [req] = wire.requests
    assert req.method == "POST" and str(req.url) == DISCORD_URL
    assert wire.json() == {
        "username": "Solo Miner Monitor",
        "embeds": [{
            "title": f"{ICON[Severity.WARNING]} Gamma is running hot",
            "description": "ASIC 91 °C (limit 75)",
            "color": 0xF59E0B,
            "timestamp": "2023-11-14T22:13:20Z",
            "footer": {"text": f"Solo Miner Monitor {__version__}"},
        }],
    }


@pytest.mark.parametrize(
    ("severity", "color"),
    [(Severity.INFO, 0x3B82F6), (Severity.SUCCESS, 0x22C55E), (Severity.WARNING, 0xF59E0B), (Severity.CRITICAL, 0xEF4444)],
)
async def test_discord_colours_and_icons_follow_severity(make_wire, severity, color):
    wire = make_wire()
    await DiscordChannel({}, {"webhook_url": DISCORD_URL}, wire.client()).send(Notification(title="T", severity=severity, ts=TS))
    embed = wire.json()["embeds"][0]
    assert embed["title"] == f"{ICON[severity]} T" and embed["color"] == color


async def test_discord_links_the_embed_and_respects_its_length_limits(make_wire):
    wire = make_wire()
    n = Notification(title="t" * 400, body="b" * 5000, url="https://miners.test/dev_1", ts=TS)
    await DiscordChannel({}, {"webhook_url": DISCORD_URL}, wire.client()).send(n)
    embed = wire.json()["embeds"][0]
    assert embed["url"] == "https://miners.test/dev_1"
    assert len(embed["title"]) == 250 and len(embed["description"]) == 3800


async def test_telegram_sends_html_escaped_text_to_the_bot_api(make_wire):
    wire = make_wire()
    n = Notification(title='Gamma\'s <fan> & "heat"', body="x < y & z > w", severity=Severity.CRITICAL, ts=TS)
    await TelegramChannel({"chat_id": 42}, {"bot_token": BOT_TOKEN}, wire.client()).send(n)
    [req] = wire.requests
    assert str(req.url) == f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    assert wire.json() == {
        "chat_id": "42",
        "text": f"{ICON[Severity.CRITICAL]} <b>Gamma&#x27;s &lt;fan&gt; &amp; &quot;heat&quot;</b>\nx &lt; y &amp; z &gt; w",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }


async def test_telegram_omits_the_body_line_when_there_is_none_and_caps_the_length(make_wire):
    wire = make_wire()
    tg = TelegramChannel({"chat_id": "42"}, {"bot_token": BOT_TOKEN}, wire.client())
    await tg.send(Notification(title="Only a title", ts=TS))
    await tg.send(Notification(title="T", body="x" * 5000, ts=TS))
    assert wire.json(0)["text"] == f"{ICON[Severity.INFO]} <b>Only a title</b>"
    assert len(wire.json(1)["text"]) == 4000


async def test_telegram_never_cuts_an_html_entity_in_half(make_wire):
    """Every '&' becomes '&amp;', so a fixed-length cut can land inside one and Telegram rejects the whole message."""
    import re

    from bsmm.notify.channels import telegram_html

    for n in (3990, 3991, 3992, 3993, 3994, 3995, 4001, 6000):
        text = telegram_html("", "T", "&" * n)
        assert len(text) <= 4000
        # no stray ampersand that is not the start of a complete entity, and the single tag pair is intact
        assert not re.search(r"&(?!amp;|lt;|gt;|quot;|#x27;)", text)
        assert text.startswith("<b>T</b>") and text.count("<b>") == text.count("</b>") == 1
    assert telegram_html("", "T", "short") == "<b>T</b>\nshort"  # short messages are left alone


async def test_a_redirect_is_reported_as_a_failure_not_a_success(make_wire):
    wire = make_wire(301)
    with pytest.raises(ChannelError, match="redirect"):
        await SlackChannel({}, {"webhook_url": SLACK_URL}, wire.client()).send(HOT)


async def test_slack_posts_mrkdwn_text(make_wire):
    wire = make_wire()
    await SlackChannel({}, {"webhook_url": SLACK_URL}, wire.client()).send(HOT)
    [req] = wire.requests
    assert str(req.url) == SLACK_URL and req.method == "POST"
    assert wire.json() == {"text": f"{ICON[Severity.WARNING]} *Gamma is running hot*\nASIC 91 °C (limit 75)"}


# --- ntfy ----------------------------------------------------------------------------------------------------


async def test_ntfy_headers_encode_priority_and_tags(make_wire):
    wire = make_wire()
    await NtfyChannel({"topic": "my-miners-x7k2"}, {}, wire.client()).send(HOT)
    [req] = wire.requests
    assert req.method == "POST" and str(req.url) == "https://ntfy.sh/my-miners-x7k2"
    assert req.content == "ASIC 91 °C (limit 75)".encode()
    assert req.headers["title"] == "Gamma is running hot"
    assert req.headers["priority"] == "4" and req.headers["tags"] == "warning"
    assert "authorization" not in req.headers


@pytest.mark.parametrize(
    ("severity", "priority", "tag"),
    [
        (Severity.INFO, "2", "information_source"),
        (Severity.SUCCESS, "3", "white_check_mark"),
        (Severity.WARNING, "4", "warning"),
        (Severity.CRITICAL, "5", "rotating_light"),
    ],
)
async def test_ntfy_priority_ladder(make_wire, severity, priority, tag):
    wire = make_wire()
    await NtfyChannel({"topic": "t"}, {}, wire.client()).send(Notification(title="x", severity=severity))
    assert wire.requests[0].headers["priority"] == priority and wire.requests[0].headers["tags"] == tag


async def test_ntfy_uses_a_self_hosted_server_and_an_access_token(make_wire):
    wire = make_wire()
    ch = NtfyChannel({"topic": "alerts", "server": "https://ntfy.home.test/"}, {"token": "tk_secret"}, wire.client())
    await ch.send(HOT)
    req = wire.requests[0]
    assert str(req.url) == "https://ntfy.home.test/alerts"  # the trailing slash does not double up
    assert req.headers["authorization"] == "Bearer tk_secret"


async def test_ntfy_title_header_stays_ascii_and_the_body_stays_utf8(make_wire):
    wire = make_wire()
    ch = NtfyChannel({"topic": "t"}, {}, wire.client())
    await ch.send(Notification(title="Température élevée", body="Zażółć gęślą jaźń ☀"))
    await ch.send(Notification(title="🔥🔥", body=""))
    first, second = wire.requests
    assert first.headers["title"] == "Temprature leve"
    assert first.content.decode() == "Zażółć gęślą jaźń ☀"
    assert second.headers["title"] == "Solo Miner Monitor"  # nothing ASCII left, so fall back to a name
    assert second.content.decode() == "🔥🔥"  # an empty body falls back to the title text


# --- generic webhook / Pushover ---------------------------------------------------------------------------


async def test_webhook_posts_compact_json_with_a_verifiable_signature(make_wire):
    wire = make_wire()
    ch = WebhookChannel({}, {"url": HOOK_URL, "signing_secret": "s3cret"}, wire.client())
    n = Notification(title="Hot", body="b", severity=Severity.WARNING, type="temp_high", device_id="dev_1",
                     ts=TS, data={"rule_id": "rule_temp_high"})
    await ch.send(n)
    [req] = wire.requests
    assert str(req.url) == HOOK_URL
    assert req.headers["content-type"] == "application/json"
    assert req.headers["user-agent"] == f"bitcoin-solo-miner-monitor/{__version__}"
    assert req.content == json.dumps(n.to_json(), separators=(",", ":")).encode()
    assert wire.json() == {
        "title": "Hot", "body": "b", "severity": "warning", "type": "temp_high", "device_id": "dev_1", "url": None,
        "ts": TS, "resolved": False, "data": {"rule_id": "rule_temp_high"},
    }
    # the receiver recomputes the HMAC over the raw bytes and compares
    expected = hmac.new(b"s3cret", req.content, hashlib.sha256).hexdigest()
    assert hmac.compare_digest(req.headers["x-bsmm-signature"], expected)
    assert not hmac.compare_digest(req.headers["x-bsmm-signature"], hmac.new(b"other", req.content, hashlib.sha256).hexdigest())
    assert not hmac.compare_digest(req.headers["x-bsmm-signature"], hmac.new(b"s3cret", req.content + b" ", hashlib.sha256).hexdigest())


async def test_webhook_without_secrets_sends_no_signature_or_authorization(make_wire):
    wire = make_wire()
    await WebhookChannel({"url": HOOK_URL}, {}, wire.client()).send(HOT)
    headers = wire.requests[0].headers
    assert "x-bsmm-signature" not in headers and "authorization" not in headers


async def test_webhook_forwards_a_custom_authorization_header(make_wire):
    wire = make_wire()
    await WebhookChannel({}, {"url": HOOK_URL, "authorization": "Bearer abc123"}, wire.client()).send(HOT)
    assert wire.requests[0].headers["authorization"] == "Bearer abc123"


@pytest.mark.parametrize(
    ("severity", "priority"),
    [(Severity.INFO, "-1"), (Severity.SUCCESS, "0"), (Severity.WARNING, "0"), (Severity.CRITICAL, "1")],
)
async def test_pushover_form_fields(make_wire, severity, priority):
    wire = make_wire()
    ch = PushoverChannel({}, {"app_token": "app-tok", "user_key": "user-key"}, wire.client())
    await ch.send(Notification(title="Fan stopped", body="3000 rpm expected", severity=severity))
    [req] = wire.requests
    assert req.method == "POST" and str(req.url) == "https://api.pushover.net/1/messages.json"
    assert req.headers["content-type"] == "application/x-www-form-urlencoded"
    form = {k: v[0] for k, v in parse_qs(req.content.decode()).items()}
    assert form == {"token": "app-tok", "user": "user-key", "title": "Fan stopped", "message": "3000 rpm expected", "priority": priority}


async def test_pushover_truncates_and_falls_back_to_the_title(make_wire):
    wire = make_wire()
    ch = PushoverChannel({}, {"app_token": "a", "user_key": "u"}, wire.client())
    await ch.send(Notification(title="t" * 400, body=""))
    await ch.send(Notification(title="T", body="b" * 3000))
    first = parse_qs(wire.requests[0].content.decode())
    second = parse_qs(wire.requests[1].content.decode())
    assert len(first["title"][0]) == 250 and first["message"][0] == "t" * 400
    assert len(second["message"][0]) == 1000


# --- configuration handling ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("cls", "config", "missing"),
    [
        (DiscordChannel, {}, "webhook_url"),
        (TelegramChannel, {"chat_id": "1"}, "bot_token"),
        (TelegramChannel, {}, "bot_token, chat_id"),
        (NtfyChannel, {"server": "https://ntfy.sh"}, "topic"),
        (SlackChannel, {"webhook_url": "   "}, "webhook_url"),  # blank counts as missing
        (WebhookChannel, {}, "url"),
        (PushoverChannel, {"app_token": "x"}, "user_key"),
        (EmailChannel, {"port": 587}, "host, sender, to"),
        (AppriseChannel, {}, "urls"),
    ],
)
async def test_missing_settings_are_reported_by_name_and_nothing_is_sent(make_wire, cls, config, missing):
    wire = make_wire()
    with pytest.raises(ChannelError, match=f"^missing setting: {missing}$"):
        await cls(config, {}, wire.client()).send(HOT)
    assert wire.requests == []


async def test_secrets_win_over_config_and_values_are_trimmed(make_wire):
    wire = make_wire()
    ch = SlackChannel({"webhook_url": "https://old.test/x"}, {"webhook_url": f"  {SLACK_URL}  "}, wire.client())
    assert ch.value("webhook_url") == SLACK_URL
    await ch.send(HOT)
    assert str(wire.requests[0].url) == SLACK_URL
    assert SlackChannel({"webhook_url": " https://cfg.test/x "}, {}, wire.client()).value("webhook_url") == "https://cfg.test/x"
    assert SlackChannel({}, {}, wire.client()).value("nothing") == ""


def test_every_channel_describes_itself_for_the_ui_and_agents():
    assert set(CHANNEL_CLASSES) == {"discord", "telegram", "ntfy", "slack", "webhook", "pushover", "email", "apprise"}
    for kind, cls in CHANNEL_CLASSES.items():
        d = cls.describe()
        names = [f["name"] for f in d["fields"]]
        assert d["kind"] == kind == cls.kind and d["label"] and names and len(names) == len(set(names))
        json.dumps(d)  # the API returns this verbatim
    secret_fields = {
        kind: {f.name for f in cls.fields if f.secret} for kind, cls in CHANNEL_CLASSES.items()
    }
    assert secret_fields == {
        "discord": {"webhook_url"},
        "telegram": {"bot_token"},
        "ntfy": {"token"},
        "slack": {"webhook_url"},
        "webhook": {"url", "signing_secret", "authorization"},
        "pushover": {"app_token", "user_key"},
        "email": {"password"},
        "apprise": {"urls"},
    }


def test_notification_to_json_is_a_stable_flat_shape():
    n = Notification(title="t", body="b", severity=Severity.SUCCESS, type="x", device_id="d", url="u", ts=TS,
                     data={"k": 1}, resolved=True)
    assert n.to_json() == {"title": "t", "body": "b", "severity": "success", "type": "x", "device_id": "d", "url": "u",
                           "ts": TS, "resolved": True, "data": {"k": 1}}
    assert Notification(title="t").ts > 1_700_000_000  # stamped with "now" by default


# --- HTTP error mapping (and not leaking secrets) -------------------------------------------------------------------

SECRET_CHANNELS = {
    "discord": (DiscordChannel, {}, {"webhook_url": DISCORD_URL}),
    "telegram": (TelegramChannel, {"chat_id": "42"}, {"bot_token": BOT_TOKEN}),
    "ntfy": (NtfyChannel, {"topic": "TOPSECRETTOPIC"}, {"token": "TOPSECRETACCESS"}),
    "slack": (SlackChannel, {}, {"webhook_url": SLACK_URL}),
    "webhook": (WebhookChannel, {}, {"url": HOOK_URL, "signing_secret": "TOPSECRETSIGN", "authorization": "Bearer TOPSECRETAUTH"}),
    "pushover": (PushoverChannel, {}, {"app_token": "TOPSECRETAPP", "user_key": "TOPSECRETUSER"}),
}

LEAKY_ERRORS = {
    "timeout": (lambda req: httpx.ReadTimeout(f"timed out talking to {req.url}"), "the service did not answer in time"),
    "connect-timeout": (lambda req: httpx.ConnectTimeout(f"timed out connecting to {req.url}"), "the service did not answer in time"),
    "refused": (lambda req: httpx.ConnectError(f"All connection attempts failed for {req.url}"), "could not connect (ConnectError)"),
    "reset": (lambda req: httpx.ReadError(f"connection reset while posting {req.content!r}"), "could not connect (ReadError)"),
    "protocol": (lambda req: httpx.RemoteProtocolError(f"server sent junk after {req.url}"), "could not connect (RemoteProtocolError)"),
}


@pytest.mark.parametrize("kind", sorted(SECRET_CHANNELS))
@pytest.mark.parametrize("failure", sorted(LEAKY_ERRORS))
async def test_transport_failures_become_safe_messages(make_wire, kind, failure):
    cls, config, secret = SECRET_CHANNELS[kind]
    make_error, message = LEAKY_ERRORS[failure]
    wire = make_wire(make_error)
    with pytest.raises(ChannelError) as exc:
        await cls(config, secret, wire.client()).send(HOT)
    assert str(exc.value) == message
    assert "TOPSECRET" not in str(exc.value) and "TOPSECRET" not in repr(exc.value)
    assert len(wire.requests) == 1  # a channel never retries on its own; the dispatcher decides that


@pytest.mark.parametrize("kind", sorted(SECRET_CHANNELS))
@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 502, 503])
async def test_http_errors_report_only_the_status_code(make_wire, kind, status):
    cls, config, secret = SECRET_CHANNELS[kind]
    wire = make_wire(status)
    with pytest.raises(ChannelError) as exc:
        await cls(config, secret, wire.client()).send(HOT)
    assert str(exc.value) == f"the service rejected the message (HTTP {status})"
    assert "TOPSECRET" not in str(exc.value)


@pytest.mark.parametrize("status", [200, 201, 202, 204])
async def test_success_statuses_are_accepted(make_wire, status):
    wire = make_wire(status)
    await SlackChannel({}, {"webhook_url": SLACK_URL}, wire.client()).send(HOT)
    assert len(wire.requests) == 1


# --- email ----------------------------------------------------------------------------------------------------------


def install_fake_smtp(monkeypatch, *, fail_at: str | None = None, error: BaseException | None = None):
    """Replace smtplib.SMTP / SMTP_SSL with recorders. Returns the list of connections made."""
    connections: list[SimpleNamespace] = []

    def build(kind: str):
        class FakeSMTP:
            def __init__(self, host, port, timeout=None, context=None):
                if fail_at == "connect":
                    raise error  # type: ignore[misc]
                self.rec = SimpleNamespace(kind=kind, host=host, port=port, timeout=timeout, context=context, calls=[], messages=[])
                connections.append(self.rec)

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.rec.calls.append("quit")
                return False

            def starttls(self, context=None):
                if fail_at == "starttls":
                    raise error  # type: ignore[misc]
                self.rec.calls.append("starttls" if context is not None else "starttls-without-context")

            def login(self, user, password):
                if fail_at == "login":
                    raise error  # type: ignore[misc]
                self.rec.calls.append(("login", user, password))

            def send_message(self, msg):
                if fail_at == "send":
                    raise error  # type: ignore[misc]
                self.rec.messages.append(msg)
                self.rec.calls.append("send")

        return FakeSMTP

    monkeypatch.setattr(smtplib, "SMTP", build("plain"))
    monkeypatch.setattr(smtplib, "SMTP_SSL", build("ssl"))
    return connections


MAIL = {"host": "smtp.test", "port": 587, "security": "starttls", "username": "me@x.test", "sender": "miners@x.test",
        "to": "a@x.test, b@x.test"}


async def test_email_starttls_flow_builds_the_message(monkeypatch, make_wire):
    conns = install_fake_smtp(monkeypatch)
    await EmailChannel(MAIL, {"password": "hunter2"}, make_wire().client()).send(HOT)
    [c] = conns
    assert (c.kind, c.host, c.port, c.timeout) == ("plain", "smtp.test", 587, 15)
    assert c.calls == ["starttls", ("login", "me@x.test", "hunter2"), "send", "quit"]
    [msg] = c.messages
    assert msg["Subject"] == "[Solo Miner Monitor] Gamma is running hot"
    assert msg["From"] == "miners@x.test" and msg["To"] == "a@x.test, b@x.test"
    text = msg.get_content()
    assert "Gamma is running hot" in text and "ASIC 91 °C (limit 75)" in text
    assert text.rstrip().endswith(f"-- Solo Miner Monitor {__version__}")


async def test_email_ssl_uses_the_ssl_class_and_no_starttls(monkeypatch, make_wire):
    conns = install_fake_smtp(monkeypatch)
    cfg = {**MAIL, "port": "465", "security": "ssl"}  # the port arrives as text from a form
    await EmailChannel(cfg, {"password": "pw"}, make_wire().client()).send(HOT)
    [c] = conns
    assert (c.kind, c.port) == ("ssl", 465) and c.context is not None
    assert c.calls == [("login", "me@x.test", "pw"), "send", "quit"]


async def test_email_without_security_or_login_just_sends(monkeypatch, make_wire):
    conns = install_fake_smtp(monkeypatch)
    cfg = {"host": "relay.lan", "security": "none", "sender": "m@x.test", "to": "me@x.test"}
    await EmailChannel(cfg, {}, make_wire().client()).send(HOT)
    [c] = conns
    assert (c.kind, c.host, c.port) == ("plain", "relay.lan", 587)  # port defaults to 587
    assert c.calls == ["send", "quit"]


async def test_email_defaults_to_starttls_and_normalises_the_recipient_list(monkeypatch, make_wire):
    conns = install_fake_smtp(monkeypatch)
    cfg = {"host": "smtp.test", "sender": "m@x.test", "to": " a@x.test ,, b@x.test , "}
    await EmailChannel(cfg, {}, make_wire().client()).send(Notification(title="Température", body="é"))
    [c] = conns
    assert c.calls == ["starttls", "send", "quit"]
    assert c.messages[0]["To"] == "a@x.test, b@x.test"
    assert "Température" in c.messages[0].get_content()


@pytest.mark.parametrize(
    ("fail_at", "error", "message"),
    [
        ("login", smtplib.SMTPAuthenticationError(535, b"5.7.8 bad credentials hunter2"), "the mail server refused the user name or password"),
        ("connect", ConnectionRefusedError("connection refused by smtp.test:587"), "could not send the email (ConnectionRefusedError)"),
        ("connect", TimeoutError("timed out"), "could not send the email (TimeoutError)"),
        ("starttls", smtplib.SMTPServerDisconnected("Connection unexpectedly closed"), "could not send the email (SMTPServerDisconnected)"),
        ("send", smtplib.SMTPRecipientsRefused({"a@x.test": (550, b"no such user")}), "could not send the email (SMTPRecipientsRefused)"),
    ],
)
async def test_email_failures_are_mapped_without_leaking_the_password(monkeypatch, make_wire, fail_at, error, message):
    install_fake_smtp(monkeypatch, fail_at=fail_at, error=error)
    with pytest.raises(ChannelError) as exc:
        await EmailChannel(MAIL, {"password": "hunter2"}, make_wire().client()).send(HOT)
    assert str(exc.value) == message and "hunter2" not in str(exc.value)


async def test_email_refuses_to_build_a_message_with_an_injected_header(monkeypatch, make_wire):
    conns = install_fake_smtp(monkeypatch)
    evil = Notification(title="Gamma\r\nBcc: attacker@evil.test", body="x")
    with pytest.raises(ValueError):
        await EmailChannel(MAIL, {"password": "pw"}, make_wire().client()).send(evil)
    assert all(not c.messages for c in conns)  # nothing was handed to the mail server


# --- Apprise (optional dependency) -----------------------------------------------------------------------------------


class FakeApprise:
    instances: list[FakeApprise] = []
    succeed = True

    def __init__(self) -> None:
        self.urls: list[str] = []
        self.sent: list[dict] = []
        FakeApprise.instances.append(self)

    def add(self, url: str) -> bool:
        self.urls.append(url)
        return True

    def notify(self, title: str, body: str, notify_type: str) -> bool:
        self.sent.append({"title": title, "body": body, "notify_type": notify_type})
        return FakeApprise.succeed


@pytest.fixture
def fake_apprise(monkeypatch):
    FakeApprise.instances, FakeApprise.succeed = [], True
    module = types.ModuleType("apprise")
    module.Apprise = FakeApprise  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "apprise", module)
    return FakeApprise


async def test_apprise_gets_one_url_per_line_and_a_matching_notify_type(fake_apprise, make_wire):
    ch = AppriseChannel({}, {"urls": "matrix://u:p@h/#room\n\n  tgram://bot/chat  \n"}, make_wire().client())
    for severity in (Severity.INFO, Severity.SUCCESS, Severity.WARNING, Severity.CRITICAL):
        await ch.send(Notification(title="T", body="B", severity=severity))
    first = fake_apprise.instances[0]
    assert first.urls == ["matrix://u:p@h/#room", "tgram://bot/chat"]
    assert [s["notify_type"] for inst in fake_apprise.instances for s in inst.sent] == ["info", "success", "warning", "failure"]
    await ch.send(Notification(title="Only title"))
    assert fake_apprise.instances[-1].sent[0]["body"] == "Only title"


async def test_apprise_failures_have_clear_messages(fake_apprise, monkeypatch, make_wire):
    ch = AppriseChannel({}, {"urls": "matrix://u:p@h/#room"}, make_wire().client())
    fake_apprise.succeed = False
    with pytest.raises(ChannelError, match=r"^Apprise could not deliver the message$"):
        await ch.send(HOT)
    monkeypatch.setitem(sys.modules, "apprise", None)  # what `import apprise` sees when it is not installed
    with pytest.raises(ChannelError, match=r"^the 'apprise' package is not installed$"):
        await ch.send(HOT)


# --- quiet hours -------------------------------------------------------------------------------------------------------


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 3, 1, hour, minute)


OVERNIGHT = {"start": "22:00", "end": "07:00"}
DAYTIME = {"start": "09:00", "end": "17:00"}


@pytest.mark.parametrize(
    ("now", "quiet"),
    [(at(23), True), (at(22), True), (at(0), True), (at(3, 30), True), (at(6, 59), True),
     (at(7), False), (at(12), False), (at(21, 59), False)],
)
def test_overnight_quiet_hours_wrap_around_midnight(now, quiet):
    assert in_quiet_hours(OVERNIGHT, now) is quiet


@pytest.mark.parametrize(
    ("now", "quiet"),
    [(at(9), True), (at(12, 30), True), (at(16, 59), True), (at(17), False), (at(8, 59), False), (at(0), False), (at(23), False)],
)
def test_daytime_quiet_hours_include_the_start_and_exclude_the_end(now, quiet):
    assert in_quiet_hours(DAYTIME, now) is quiet


@pytest.mark.parametrize(
    "quiet",
    [None, {}, {"start": "22:00"}, {"end": "07:00"}, {"start": "", "end": ""}, {"start": "25:00", "end": "07:00"},
     {"start": "22:00", "end": "07:99"}, {"start": "late", "end": "early"}, {"start": 2200, "end": 700}, {"start": "22", "end": "7"}],
)
def test_missing_or_garbled_quiet_hours_never_mute(quiet):
    assert in_quiet_hours(quiet, at(23)) is False
    assert in_quiet_hours(quiet, at(3)) is False


def test_loosely_formatted_times_are_accepted():
    assert in_quiet_hours({"start": "9:5", "end": " 17:00 "}, at(9, 5)) is True
    assert in_quiet_hours({"start": "9:5", "end": " 17:00 "}, at(9, 4)) is False


class Frozen(datetime):
    """``datetime`` whose ``now()`` is always 23:30, so 'the current time' is predictable."""

    @classmethod
    def now(cls, tz=None):
        return cls(2026, 3, 1, 23, 30)


@pytest.fixture
def midnight(monkeypatch):
    """Freeze the dispatcher's wall clock at 23:30."""
    monkeypatch.setattr(dispatcher_mod, "datetime", Frozen)


def test_quiet_hours_default_to_the_current_time(midnight):
    assert in_quiet_hours(OVERNIGHT) is True
    assert in_quiet_hours(DAYTIME) is False


# --- the dispatcher ---------------------------------------------------------------------------------------------------------


@pytest.fixture
def sink(monkeypatch):
    """Registers a 'capture' channel kind that records deliveries, plus 'crash' which blows up."""
    delivered: list[tuple[str, Notification, dict]] = []

    class Capture(BaseChannel):
        kind = "capture"
        label = "Capture"

        async def send(self, n: Notification) -> None:
            if self.config.get("fail"):
                raise ChannelError(self.config["fail"])
            delivered.append((self.config["name"], n, dict(self.secret)))

    class Crash(BaseChannel):
        kind = "crash"
        label = "Crash"

        async def send(self, n: Notification) -> None:
            raise ZeroDivisionError("secret=hunter2")

    monkeypatch.setitem(CHANNEL_CLASSES, "capture", Capture)
    monkeypatch.setitem(CHANNEL_CLASSES, "crash", Crash)
    return delivered


async def add_channel(store, ch_id, kind="capture", *, secret=None, enabled=True, min_severity=Severity.INFO, **config):
    config.setdefault("name", ch_id)
    ch = Channel(id=ch_id, kind=kind, name=ch_id, enabled=enabled, config=config, min_severity=min_severity)
    await store.save_channel(ch, secret=secret)
    return ch


def names(delivered):
    return sorted(name for name, _, _ in delivered)


def by_channel(results):
    return {r.channel_id: r for r in results}


async def test_dispatch_reaches_every_enabled_channel(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "a")
    await add_channel(ctx.store, "b")
    await add_channel(ctx.store, "off", enabled=False)
    results = await ctx.notifier.dispatch(Notification(title="hello"))
    assert names(sink) == ["a", "b"]
    assert {r.channel_id for r in results} == {"a", "b"} and all(r.ok and r.skipped is None for r in results)


async def test_dispatch_can_be_limited_to_chosen_channels(lan, sink):
    ctx, _ = lan
    for ch_id in "abc":
        await add_channel(ctx.store, ch_id)
    await ctx.notifier.dispatch(Notification(title="x"), ["b", "c", "no-such-channel"])
    assert names(sink) == ["b", "c"]
    sink.clear()
    await ctx.notifier.dispatch(Notification(title="x"), [])  # an empty list means "everything", like a rule with no channels
    assert names(sink) == ["a", "b", "c"]
    sink.clear()
    assert await ctx.notifier.dispatch(Notification(title="x"), ["no-such-channel"]) == []


async def test_channel_secrets_are_decrypted_for_delivery_only(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "a", secret={"token": "plain-text-token"})
    await ctx.notifier.dispatch(Notification(title="x"))
    assert sink[0][2] == {"token": "plain-text-token"}
    row = await ctx.store.db.fetchone("SELECT secret_enc FROM channels WHERE id = 'a'")
    assert "plain-text-token" not in row["secret_enc"]


async def test_min_severity_filters_per_channel(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "everything")
    await add_channel(ctx.store, "warnings", min_severity=Severity.WARNING)
    await add_channel(ctx.store, "critical", min_severity=Severity.CRITICAL)
    expected = {Severity.INFO: {"everything"}, Severity.SUCCESS: {"everything"},
                Severity.WARNING: {"everything", "warnings"}, Severity.CRITICAL: {"everything", "warnings", "critical"}}
    for severity, receivers in expected.items():
        sink.clear()
        results = by_channel(await ctx.notifier.dispatch(Notification(title="x", severity=severity)))
        assert set(names(sink)) == receivers, severity
        for ch_id, r in results.items():  # filtered channels are reported as skipped, not as failures
            assert r.ok is True
            assert (r.skipped is None) == (ch_id in receivers)
    results = by_channel(await ctx.notifier.dispatch(Notification(title="x", severity=Severity.INFO)))
    assert results["critical"].skipped == "below this channel's minimum (critical)"


async def test_block_found_ignores_the_channel_minimum_and_quiet_hours(lan, sink, midnight):
    ctx, _ = lan
    await add_channel(ctx.store, "picky", min_severity=Severity.CRITICAL)
    await ctx.settings.update({"alerts": {"quiet_hours": OVERNIGHT}})  # 23:30 is inside it
    await ctx.notifier.dispatch(Notification(title="BLOCK FOUND", severity=Severity.INFO, type="block_found"))
    assert names(sink) == ["picky"]
    sink.clear()
    await ctx.notifier.dispatch(Notification(title="not a block", severity=Severity.INFO, type="new_best_share"))
    assert sink == []  # without the special type the same notification is held back


async def test_quiet_hours_mute_info_and_success_but_never_warnings(lan, sink, midnight):
    ctx, _ = lan
    await add_channel(ctx.store, "phone")
    await ctx.settings.update({"alerts": {"quiet_hours": OVERNIGHT}})
    for severity, delivered in ((Severity.INFO, False), (Severity.SUCCESS, False), (Severity.WARNING, True), (Severity.CRITICAL, True)):
        sink.clear()
        [res] = await ctx.notifier.dispatch(Notification(title="x", severity=severity))
        assert bool(sink) is delivered, severity
        assert res.ok is True and res.skipped == (None if delivered else "quiet hours")


async def test_quiet_hours_do_not_mute_block_found_or_a_window_that_has_ended(lan, sink, midnight):
    ctx, _ = lan
    await add_channel(ctx.store, "phone")
    await ctx.settings.update({"alerts": {"quiet_hours": OVERNIGHT}})
    await ctx.notifier.dispatch(Notification(title="BLOCK", severity=Severity.SUCCESS, type="block_found"))
    assert names(sink) == ["phone"]
    sink.clear()
    await ctx.settings.update({"alerts": {"quiet_hours": DAYTIME}})  # 23:30 is outside 09:00-17:00
    await ctx.notifier.dispatch(Notification(title="x", severity=Severity.INFO))
    assert names(sink) == ["phone"]


async def test_the_channel_minimum_is_reported_before_quiet_hours(lan, sink, midnight):
    ctx, _ = lan
    await add_channel(ctx.store, "picky", min_severity=Severity.WARNING)
    await ctx.settings.update({"alerts": {"quiet_hours": OVERNIGHT}})
    [res] = await ctx.notifier.dispatch(Notification(title="x", severity=Severity.INFO))
    assert res.skipped == "below this channel's minimum (warning)"


# --- retries and failure events ----------------------------------------------------------------------------------------------


@pytest.fixture
def napped(monkeypatch):
    """Make the dispatcher's retry back-off instant and record how long it wanted to wait."""
    naps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        naps.append(seconds)

    monkeypatch.setattr(dispatcher_mod, "asyncio", SimpleNamespace(sleep=fake_sleep, gather=asyncio.gather))
    return naps


async def ntfy_notifier(ctx, wire, *, events=True):
    await add_channel(ctx.store, "phone", "ntfy", secret={"token": "TOPSECRETACCESS"}, topic="miners")
    return Notifier(ctx.store, ctx.settings, wire.client(), ctx.events if events else None)


async def test_a_timeout_is_retried_once_after_a_pause(lan, make_wire, napped):
    ctx, _ = lan
    wire = make_wire(httpx.ReadTimeout("slow"), 200)
    notifier = await ntfy_notifier(ctx, wire)
    [res] = await notifier.dispatch(Notification(title="x", body="y"))
    assert res.ok is True and res.error is None
    assert len(wire.requests) == 2 and napped == [2]
    assert wire.requests[0].headers["authorization"] == "Bearer TOPSECRETACCESS"  # the stored secret was used
    assert await ctx.store.list_events(types=["notification_failed"]) == []


@pytest.mark.parametrize(
    ("script", "error"),
    [
        ((httpx.ReadTimeout("slow"),), "the service did not answer in time"),
        ((httpx.ConnectError("refused"),), "could not connect (ConnectError)"),
        ((503,), "the service rejected the message (HTTP 503)"),
        ((502, 500), "the service rejected the message (HTTP 500)"),
    ],
)
async def test_transient_failures_get_exactly_one_retry_and_then_give_up(lan, make_wire, napped, script, error):
    ctx, _ = lan
    wire = make_wire(*script)
    notifier = await ntfy_notifier(ctx, wire)
    [res] = await notifier.dispatch(Notification(title="x"))
    assert res.ok is False and res.error == error
    assert len(wire.requests) == 2 and napped == [2]


@pytest.mark.parametrize("status", [400, 401, 404, 429])
async def test_client_errors_are_not_retried(lan, make_wire, napped, status):
    ctx, _ = lan
    wire = make_wire(status)
    notifier = await ntfy_notifier(ctx, wire)
    [res] = await notifier.dispatch(Notification(title="x"))
    assert res.ok is False and res.error == f"the service rejected the message (HTTP {status})"
    assert len(wire.requests) == 1 and napped == []


async def test_a_failure_raises_a_deduplicated_notification_failed_event(lan, make_wire, napped):
    ctx, _ = lan
    wire = make_wire(401)
    notifier = await ntfy_notifier(ctx, wire)
    await notifier.dispatch(Notification(title="x"))
    await notifier.dispatch(Notification(title="y"))  # the same channel failing again within the hour
    events = await ctx.store.list_events(types=["notification_failed"])
    assert len(events) == 1
    ev = events[0]
    assert ev.severity == Severity.WARNING and ev.title == "Could not send to phone"
    assert ev.body == "the service rejected the message (HTTP 401)" and ev.data == {"channel_id": "phone"}
    assert "TOPSECRETACCESS" not in json.dumps(ev.model_dump(mode="json"))
    # once the dedupe window has passed, the next failure is reported again
    ctx.events._recent["notify-fail:phone"] -= 3601
    await notifier.dispatch(Notification(title="z"))
    assert len(await ctx.store.list_events(types=["notification_failed"])) == 2


async def test_each_failing_channel_gets_its_own_event_and_skips_never_count(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "bad1", fail="no luck")
    await add_channel(ctx.store, "bad2", fail="no luck either")
    await add_channel(ctx.store, "quiet", min_severity=Severity.CRITICAL)  # skipped, not failed
    await add_channel(ctx.store, "good")
    results = by_channel(await ctx.notifier.dispatch(Notification(title="x")))
    assert {k for k, r in results.items() if not r.ok} == {"bad1", "bad2"}
    assert results["quiet"].ok is True and results["quiet"].skipped is not None
    assert names(sink) == ["good"]  # one failure never blocks the others
    events = await ctx.store.list_events(types=["notification_failed"])
    assert sorted(e.data["channel_id"] for e in events) == ["bad1", "bad2"]


async def test_a_crashing_channel_is_contained_and_does_not_leak_its_message(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "boom", "crash")
    await add_channel(ctx.store, "fine")
    results = by_channel(await ctx.notifier.dispatch(Notification(title="x")))
    assert results["boom"].ok is False and results["boom"].error == "ZeroDivisionError"  # only the class name
    assert results["fine"].ok is True and names(sink) == ["fine"]
    [ev] = await ctx.store.list_events(types=["notification_failed"])
    assert "hunter2" not in (ev.body or "")


async def test_an_unknown_channel_type_fails_cleanly(lan, make_wire):
    ctx, _ = lan
    await add_channel(ctx.store, "legacy", "carrier-pigeon")
    notifier = Notifier(ctx.store, ctx.settings, make_wire().client(), ctx.events)
    [res] = await notifier.dispatch(Notification(title="x"))
    assert res.ok is False and res.error == "unknown channel type 'carrier-pigeon'"


async def test_dispatch_without_an_event_log_still_reports_failures(lan, make_wire, napped):
    ctx, _ = lan
    wire = make_wire(404)
    notifier = await ntfy_notifier(ctx, wire, events=False)
    [res] = await notifier.dispatch(Notification(title="x"))
    assert res.ok is False
    assert await ctx.store.list_events(types=["notification_failed"]) == []


# --- test messages -------------------------------------------------------------------------------------------------------------------


async def test_send_test_uses_the_saved_channel_and_ignores_the_filters(lan, sink, midnight):
    ctx, _ = lan
    await add_channel(ctx.store, "picky", min_severity=Severity.CRITICAL, enabled=False, secret={"k": "v"})
    await ctx.settings.update({"alerts": {"quiet_hours": OVERNIGHT}})
    res = await ctx.notifier.send_test("picky")
    assert isinstance(res, DeliveryResult) and res.ok is True and res.skipped is None
    [(name, n, secret)] = sink
    assert name == "picky" and secret == {"k": "v"}
    assert n.title == "Test notification" and n.severity == Severity.SUCCESS and n.type == "test"
    assert "alerts will reach you" in n.body


async def test_send_test_for_an_unknown_channel_raises_key_error(lan):
    ctx, _ = lan
    with pytest.raises(KeyError):
        await ctx.notifier.send_test("nope")


async def test_send_test_reports_failures_but_does_not_raise_an_event(lan, sink):
    ctx, _ = lan
    await add_channel(ctx.store, "bad", fail="bot was blocked by the user")
    res = await ctx.notifier.send_test("bad")
    assert res.ok is False and res.error == "bot was blocked by the user"
    assert await ctx.store.list_events(types=["notification_failed"]) == []


async def test_send_test_inline_tries_unsaved_settings(lan, make_wire):
    ctx, _ = lan
    wire = make_wire()
    notifier = Notifier(ctx.store, ctx.settings, wire.client(), ctx.events)
    res = await notifier.send_test_inline("webhook", {}, {"url": HOOK_URL})
    assert res.ok is True and res.channel_id == "inline" and res.kind == "webhook"
    body = wire.json()
    assert body["title"] == "Test notification" and body["type"] == "test" and body["severity"] == "success"
    assert await ctx.store.list_channels() == []  # nothing was saved


async def test_send_test_inline_surfaces_bad_settings(lan, make_wire):
    ctx, _ = lan
    notifier = Notifier(ctx.store, ctx.settings, make_wire().client(), ctx.events)
    bad = await notifier.send_test_inline("telegram", {"chat_id": "1"}, {})
    assert bad.ok is False and bad.error == "missing setting: bot_token"
    unknown = await notifier.send_test_inline("fax", {}, {})
    assert unknown.ok is False and unknown.error == "unknown channel type 'fax'"
    wire = make_wire(401)
    denied = await Notifier(ctx.store, ctx.settings, wire.client(), None).send_test_inline("slack", {}, {"webhook_url": SLACK_URL})
    assert denied.error == "the service rejected the message (HTTP 401)"
    assert denied.as_dict() == {"channel_id": "inline", "name": "Test", "kind": "slack", "ok": False,
                                "error": "the service rejected the message (HTTP 401)", "skipped": None}


async def test_send_test_inline_for_email_uses_the_given_secret(lan, make_wire, monkeypatch):
    ctx, _ = lan
    conns = install_fake_smtp(monkeypatch)
    notifier = Notifier(ctx.store, ctx.settings, make_wire().client(), ctx.events)
    res = await notifier.send_test_inline("email", MAIL, {"password": "hunter2"})
    assert res.ok is True
    assert conns[0].calls[1] == ("login", "me@x.test", "hunter2")
    assert conns[0].messages[0]["Subject"] == "[Solo Miner Monitor] Test notification"

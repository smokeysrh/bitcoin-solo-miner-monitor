"""Notification channels: Discord, Telegram, ntfy, Slack, generic webhook, email, Pushover, Apprise.

Each channel describes its own configuration fields, so the web UI renders the right form and an
AI agent can read exactly what it needs to ask the user for.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import html
import json
import smtplib
import ssl
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Any, ClassVar

import httpx

from bsmm import __version__
from bsmm.models import Severity


class ChannelError(Exception):
    """Delivery failed. The message is safe to show to the user (no secrets in it)."""


@dataclass(slots=True)
class Notification:
    title: str
    body: str = ""
    severity: Severity = Severity.INFO
    type: str = "info"
    device_id: str | None = None
    url: str | None = None
    ts: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)
    resolved: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "title": self.title, "body": self.body, "severity": self.severity.value, "type": self.type,
            "device_id": self.device_id, "url": self.url, "ts": self.ts, "resolved": self.resolved, "data": self.data,
        }


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"  # text | password | url | number | boolean | select | email
    secret: bool = False
    required: bool = True
    placeholder: str = ""
    help: str = ""
    default: Any = None
    options: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}


EMOJI = {Severity.INFO: "ℹ️", Severity.SUCCESS: "✅", Severity.WARNING: "⚠️", Severity.CRITICAL: "🚨"}
COLOR = {Severity.INFO: 0x3B82F6, Severity.SUCCESS: 0x22C55E, Severity.WARNING: 0xF59E0B, Severity.CRITICAL: 0xEF4444}


class BaseChannel:
    kind: ClassVar[str]
    label: ClassVar[str]
    help: ClassVar[str] = ""
    fields: ClassVar[tuple[FieldSpec, ...]] = ()

    def __init__(self, config: dict[str, Any], secret: dict[str, str], client: httpx.AsyncClient) -> None:
        self.config = config
        self.secret = secret
        self.client = client

    @classmethod
    def describe(cls) -> dict[str, Any]:
        return {"kind": cls.kind, "label": cls.label, "help": cls.help, "fields": [f.as_dict() for f in cls.fields]}

    def value(self, name: str) -> str:
        v = self.secret[name] if name in self.secret else self.config.get(name)
        text = str(v) if v is not None else ""
        # Passwords, tokens and signing keys are exact strings. URLs alone have
        # a documented surrounding-whitespace normalization, even when secret.
        spec = next((f for f in self.fields if f.name == name), None)
        return text if spec and spec.secret and spec.kind != "url" else text.strip()

    def require(self, *names: str) -> None:
        missing = [n for n in names if not self.value(n)]
        if missing:
            raise ChannelError(f"missing setting: {', '.join(missing)}")

    async def send(self, n: Notification) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def _post(self, url: str, **kw: Any) -> httpx.Response:
        try:
            resp = await self.client.post(url, timeout=10.0, **kw)
        except httpx.TimeoutException as e:
            raise ChannelError("the service did not answer in time") from e
        except httpx.TransportError as e:
            raise ChannelError(f"could not connect ({e.__class__.__name__})") from e
        if 300 <= resp.status_code < 400:
            # httpx does not follow redirects here; a 3xx means the message did not arrive (often http -> https)
            raise ChannelError(f"the address redirected (HTTP {resp.status_code}); use the final https:// address")
        if resp.status_code >= 400:
            raise ChannelError(f"the service rejected the message (HTTP {resp.status_code})")
        return resp


TELEGRAM_LIMIT = 4000  # the API allows 4096 characters per message


def telegram_html(prefix: str, title: str, body: str, limit: int = TELEGRAM_LIMIT) -> str:
    """Build the message and shorten the *plain* body until the escaped HTML fits.

    Cutting finished HTML at a fixed length can split an entity such as ``&amp;`` or leave a tag open,
    and Telegram then rejects the whole message. Escaping after trimming cannot do that.
    """

    def render(b: str) -> str:
        out = f"{prefix}<b>{html.escape(title[:300])}</b>"
        return out + (f"\n{html.escape(b)}" if b else "")

    text = render(body)
    if len(text) <= limit:
        return text
    lo, hi = 0, len(body)
    while lo < hi:  # longest prefix of the body whose escaped form (plus an ellipsis) still fits
        mid = (lo + hi + 1) // 2
        if len(render(body[:mid].rstrip() + "…")) <= limit:
            lo = mid
        else:
            hi = mid - 1
    return render(body[:lo].rstrip() + "…")


class DiscordChannel(BaseChannel):
    kind = "discord"
    label = "Discord"
    help = "Server settings > Integrations > Webhooks > New Webhook > Copy Webhook URL."
    fields = (FieldSpec("webhook_url", "Webhook URL", "url", secret=True, placeholder="https://discord.com/api/webhooks/..."),)

    async def send(self, n: Notification) -> None:
        self.require("webhook_url")
        embed: dict[str, Any] = {
            "title": f"{EMOJI[n.severity]} {n.title}"[:250],
            "description": n.body[:3800],
            "color": COLOR[n.severity],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(n.ts)),
            "footer": {"text": f"Solo Miner Monitor {__version__}"},
        }
        if n.url:
            embed["url"] = n.url
        await self._post(self.value("webhook_url"), json={"username": "Solo Miner Monitor", "embeds": [embed]})


class TelegramChannel(BaseChannel):
    kind = "telegram"
    label = "Telegram"
    help = "Talk to @BotFather to create a bot and get its token, send your bot a message, then use @userinfobot (or the getUpdates API) to find your chat id."
    fields = (
        FieldSpec("bot_token", "Bot token", "password", secret=True, placeholder="123456:ABC-DEF..."),
        FieldSpec("chat_id", "Chat id", "text", placeholder="123456789"),
    )

    async def send(self, n: Notification) -> None:
        self.require("bot_token", "chat_id")
        text = telegram_html(f"{EMOJI[n.severity]} ", n.title, n.body)
        await self._post(
            f"https://api.telegram.org/bot{self.value('bot_token')}/sendMessage",
            json={"chat_id": self.value("chat_id"), "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        )


class NtfyChannel(BaseChannel):
    kind = "ntfy"
    label = "ntfy (push to your phone)"
    help = "Install the ntfy app, subscribe to a hard-to-guess topic name, and enter it here. Self-hosted servers are supported."
    fields = (
        FieldSpec("server", "Server", "url", required=False, default="https://ntfy.sh", placeholder="https://ntfy.sh"),
        FieldSpec("topic", "Topic", "text", placeholder="my-solo-miners-x7k2"),
        FieldSpec("token", "Access token", "password", secret=True, required=False, help="Only for protected topics."),
    )

    async def send(self, n: Notification) -> None:
        self.require("topic")
        server = (self.value("server") or "https://ntfy.sh").rstrip("/")
        prio = {Severity.INFO: "2", Severity.SUCCESS: "3", Severity.WARNING: "4", Severity.CRITICAL: "5"}[n.severity]
        tags = {Severity.INFO: "information_source", Severity.SUCCESS: "white_check_mark", Severity.WARNING: "warning", Severity.CRITICAL: "rotating_light"}[n.severity]
        headers = {"Title": n.title.encode("ascii", "ignore").decode() or "Solo Miner Monitor", "Priority": prio, "Tags": tags}
        if self.value("token"):
            headers["Authorization"] = f"Bearer {self.value('token')}"
        await self._post(f"{server}/{self.value('topic')}", content=(n.body or n.title).encode(), headers=headers)


class SlackChannel(BaseChannel):
    kind = "slack"
    label = "Slack (incoming webhook)"
    fields = (FieldSpec("webhook_url", "Webhook URL", "url", secret=True, placeholder="https://hooks.slack.com/services/..."),)

    async def send(self, n: Notification) -> None:
        self.require("webhook_url")
        await self._post(self.value("webhook_url"), json={"text": f"{EMOJI[n.severity]} *{n.title}*\n{n.body}"})


class WebhookChannel(BaseChannel):
    kind = "webhook"
    label = "Generic webhook (JSON)"
    help = "POSTs the notification as JSON. If you set a signing secret, an X-BSMM-Signature header (hex HMAC-SHA256 of the body) is added."
    fields = (
        FieldSpec("url", "URL", "url", secret=True, placeholder="https://example.com/hook"),
        FieldSpec("signing_secret", "Signing secret", "password", secret=True, required=False),
        FieldSpec("authorization", "Authorization header", "password", secret=True, required=False, placeholder="Bearer ..."),
    )

    async def send(self, n: Notification) -> None:
        self.require("url")
        body = json.dumps(n.to_json(), separators=(",", ":")).encode()
        headers = {"Content-Type": "application/json", "User-Agent": f"bitcoin-solo-miner-monitor/{__version__}"}
        if self.value("signing_secret"):
            headers["X-BSMM-Signature"] = hmac.new(self.value("signing_secret").encode(), body, hashlib.sha256).hexdigest()
        if self.value("authorization"):
            headers["Authorization"] = self.value("authorization")
        await self._post(self.value("url"), content=body, headers=headers)


class PushoverChannel(BaseChannel):
    kind = "pushover"
    label = "Pushover"
    fields = (
        FieldSpec("app_token", "Application token", "password", secret=True),
        FieldSpec("user_key", "User key", "password", secret=True),
    )

    async def send(self, n: Notification) -> None:
        self.require("app_token", "user_key")
        prio = {Severity.INFO: -1, Severity.SUCCESS: 0, Severity.WARNING: 0, Severity.CRITICAL: 1}[n.severity]
        await self._post(
            "https://api.pushover.net/1/messages.json",
            data={"token": self.value("app_token"), "user": self.value("user_key"), "title": n.title[:250],
                  "message": (n.body or n.title)[:1000], "priority": prio},
        )


class EmailChannel(BaseChannel):
    kind = "email"
    label = "Email (SMTP)"
    help = "Gmail/Outlook need an app password. Use port 587 with STARTTLS, or 465 with SSL."
    fields = (
        FieldSpec("host", "SMTP server", "text", placeholder="smtp.example.com"),
        FieldSpec("port", "Port", "number", default=587),
        FieldSpec("security", "Security", "select", default="starttls", options=("starttls", "ssl", "none")),
        FieldSpec("username", "User name", "text", required=False),
        FieldSpec("password", "Password", "password", secret=True, required=False),
        FieldSpec("sender", "From address", "email"),
        FieldSpec("to", "To address(es)", "text", placeholder="me@example.com, partner@example.com"),
    )

    def _send_sync(self, n: Notification) -> None:
        host = self.value("host")
        port = int(self.value("port") or 587)
        security = self.value("security") or "starttls"
        msg = EmailMessage()
        msg["Subject"] = f"[Solo Miner Monitor] {n.title}"[:200]
        msg["From"] = self.value("sender")
        msg["To"] = ", ".join(a.strip() for a in self.value("to").split(",") if a.strip())
        msg.set_content(f"{n.title}\n\n{n.body}\n\n-- Solo Miner Monitor {__version__}")
        ctx = ssl.create_default_context()
        try:
            if security == "ssl":
                smtp: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=15, context=ctx)
            else:
                smtp = smtplib.SMTP(host, port, timeout=15)
            with smtp:
                if security == "starttls":
                    smtp.starttls(context=ctx)
                if self.value("username"):
                    smtp.login(self.value("username"), self.value("password"))
                refused = smtp.send_message(msg)
                if refused:
                    # SMTP already accepted the other recipients: never retry the
                    # whole envelope. Do not expose addresses or server replies.
                    raise ChannelError(f"partial email delivery: {len(refused)} recipient(s) refused; accepted recipients were not retried")
        except smtplib.SMTPAuthenticationError as e:
            raise ChannelError("the mail server refused the user name or password") from e
        except (smtplib.SMTPException, OSError, TimeoutError) as e:
            raise ChannelError(f"could not send the email ({e.__class__.__name__})") from e

    async def send(self, n: Notification) -> None:
        self.require("host", "sender", "to")
        await asyncio.to_thread(self._send_sync, n)


class AppriseChannel(BaseChannel):
    kind = "apprise"
    label = "Apprise (100+ services)"
    help = "Needs the optional 'apprise' Python extra; see docs/PACKAGING.md for installation from the official GitHub wheel. Not bundled in Windows. Paste one Apprise URL per line."
    fields = (FieldSpec("urls", "Apprise URLs", "password", secret=True, placeholder="matrix://user:pass@host/#room"),)

    def _send_sync(self, n: Notification) -> None:
        try:
            import apprise
        except ImportError as e:
            raise ChannelError("the 'apprise' package is not installed") from e
        a = apprise.Apprise()
        for url in self.value("urls").splitlines():
            if url.strip():
                a.add(url.strip())
        ntype = {Severity.INFO: "info", Severity.SUCCESS: "success", Severity.WARNING: "warning", Severity.CRITICAL: "failure"}[n.severity]
        if not a.notify(title=n.title, body=n.body or n.title, notify_type=ntype):
            raise ChannelError("Apprise could not deliver the message")

    async def send(self, n: Notification) -> None:
        self.require("urls")
        await asyncio.to_thread(self._send_sync, n)


CHANNEL_CLASSES: dict[str, type[BaseChannel]] = {
    c.kind: c
    for c in (DiscordChannel, TelegramChannel, NtfyChannel, SlackChannel, WebhookChannel, PushoverChannel, EmailChannel, AppriseChannel)
}

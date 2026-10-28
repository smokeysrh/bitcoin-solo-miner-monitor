"""Operations regressions: fake managers/transports, disposable loopback servers only."""
import asyncio
import hashlib
import hmac
import json
import plistlib
import smtplib
import subprocess
from types import SimpleNamespace

import httpx
import pytest
from typer.testing import CliRunner

import bsmm.cli.main as cli_main
from bsmm.cli import service
from bsmm.models import Channel
from bsmm.notify.channels import CHANNEL_CLASSES, BaseChannel, Notification
from bsmm.notify.dispatcher import Notifier
from tests.test_cli import PASSWORD, cli, fake_platform, server  # noqa: F401


async def test_ops03_existing_password_uses_current_password(server):  # noqa: F811 - imported pytest fixture
    await server.lock()
    _, token = await server.ctx.store.create_token("fixture", "admin")
    # Interactive current-password prompt works for an unattended new-password flag too.
    bad = await cli("password", "--password", "new correct horse", "--url", server.base,
                    "--token", token, stdin="incorrect\n")
    assert bad.exit_code != 0
    assert await server.ctx.auth.check_password(PASSWORD)
    good = await cli("password", "--password", "new correct horse", "--url", server.base,
                     "--token", token, stdin=PASSWORD + "\n")
    assert good.exit_code == 0, good.output
    assert await server.ctx.auth.check_password("new correct horse")
    assert not await server.ctx.auth.check_password(PASSWORD)


@pytest.mark.parametrize("via_env", [False, True])
def test_ops04_unreachable_explicit_target_never_opens_database(tmp_path, monkeypatch, via_env):
    monkeypatch.setattr(cli_main.Api, "is_up", lambda self: False)
    target = "http://127.0.0.1:1"
    args = ["password", "--password", PASSWORD, "--data-dir", str(tmp_path / "untouched")]
    env = {"BSMM_URL": target if via_env else None}
    if not via_env:
        args += ["--url", target]
    result = CliRunner().invoke(cli_main.app, args, env=env)
    assert result.exit_code != 0, result.output
    assert not (tmp_path / "untouched").exists()


@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
@pytest.mark.parametrize("operation", ["install", "uninstall"])
@pytest.mark.parametrize("code", [0, 5])
def test_ops05_service_results(tmp_path, monkeypatch, platform, operation, code):
    path = tmp_path / "definition"
    path.write_text("existing")
    monkeypatch.setattr(service, "systemd_path", lambda: path)
    monkeypatch.setattr(service, "launchd_path", lambda: path)
    calls = []

    def run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, code, stdout="", stderr="PRIVATE-OUTPUT")

    monkeypatch.setattr(subprocess, "run", run)
    fake_platform(monkeypatch, platform)
    result = CliRunner().invoke(cli_main.app, ["service", operation] + (["--apply"] if operation == "install" else []))
    assert bool(result.exit_code) == bool(code), result.output
    assert calls
    assert "PRIVATE-OUTPUT" not in result.output
    if code:
        assert "Installed" not in result.output and "Removed." not in result.output and "task created" not in result.output
        assert path.exists()  # failed unregister must preserve its recoverable definition
    elif operation == "uninstall" and platform != "win32":
        assert not path.exists()


def test_ops06_launchd_exact_arguments():
    args = ["/Apps/A&B <雪>/bsmm", "serve", "--data-dir", '/Data/space & < > " é']
    assert plistlib.loads(service.launchd_plist(args).encode())["ProgramArguments"] == args


class SetupAPI:
    token = None
    client = SimpleNamespace(headers={}, close=lambda: None)
    probes = 0

    def __init__(self, *args, **kwargs):
        pass

    def is_up(self):
        SetupAPI.probes += 1
        return SetupAPI.probes > 1

    def get(self, path):
        if path == "/meta":
            return {"auth": {"mode": "none"}, "version": "fixture"}
        return {"summary": {"devices_total": 0, "hashrate_hs": 0}, "odds": {}}

    def post(self, path, body):
        if path == "/discovery":
            return {"status": "finished", "miners": [], "sources": []}
        return {"token": "fake", "id": "fixture"}

    def patch(self, *args):
        pass


def test_ops07_cold_setup_one_document(tmp_path, monkeypatch):
    SetupAPI.probes = 0
    monkeypatch.setattr(cli_main, "Api", SetupAPI)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: SimpleNamespace(pid=424243, poll=lambda: None))
    # Lifecycle identity is faked only at the OS boundary when the repair is available.
    if hasattr(cli_main, "lifecycle"):
        monkeypatch.setattr(cli_main.lifecycle, "save_process", lambda *a, **kw: None)
        monkeypatch.setattr(cli_main.lifecycle, "owned_process", lambda *a: SimpleNamespace(is_running=lambda: True))
        monkeypatch.setattr(cli_main.lifecycle, "ready", lambda *a: True)
    result = CliRunner().invoke(cli_main.app, ["setup", "--yes", "--no-password", "--json", "--data-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["overview"]["devices"] == 0


@pytest.fixture
async def notifier(lan):
    ctx, _ = lan
    return Notifier(ctx.store, ctx.settings, ctx.http, ctx.events)


@pytest.mark.parametrize("refused", [False, True])
async def test_ops08_ops09_smtp_exact_secret_partial_delivery(notifier, api, monkeypatch, refused):
    calls = []
    password = "exact password" if refused else "  exact password \t"

    class SMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def login(self, user, supplied):
            calls.append(("login", supplied))

        def send_message(self, message):
            calls.append(("send", str(message["To"])))
            return {"private@example.invalid": (550, b"PRIVATE-REASON")} if refused else {}

    monkeypatch.setattr(smtplib, "SMTP", SMTP)
    config = {"host": " smtp.invalid ", "security": "none", "username": "fixture", "sender": "a@example.invalid", "to": "ok@example.invalid, private@example.invalid"}
    result = await notifier.send_test_inline("email", config, {"password": password})
    assert calls[0] == ("login", password)
    assert result.ok is not refused
    assert len([c for c in calls if c[0] == "send"]) == 1
    response = await api[0].post("/api/v1/notifications/test", json={"kind": "email", "name": "Fixture", "config": config, "secret": {"password": password}})
    assert response.status_code == 200 and response.json()["ok"] is not refused
    assert len([c for c in calls if c[0] == "send"]) == 2
    if refused:
        assert "partial" in result.error.lower()
        assert "PRIVATE-REASON" not in result.error and "private@" not in result.error
        ch = Channel(id="fixture", kind="email", name="Fixture", config=config)
        await notifier.store.save_channel(ch, {"password": password})
        results = await notifier.dispatch(Notification(title="Fixture"), [ch.id])
        assert not results[0].ok
        events = await notifier.store.list_events()
        assert any(e.type == "notification_failed" for e in events)


async def test_ops08_webhook_exact_hmac(notifier):
    requests = []
    secret = "  exact signing key\t"
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: (requests.append(r), httpx.Response(200))[1])) as client:
        notifier.http = client
        result = await notifier.send_test_inline("webhook", {}, {"url": " https://hook.invalid/ ", "signing_secret": secret})
    assert result.ok
    assert requests[0].headers["X-BSMM-Signature"] == hmac.new(secret.encode(), requests[0].content, hashlib.sha256).hexdigest()


@pytest.mark.parametrize("malformed", [False, True])
async def test_ops10_no_arbitrary_exception_secrets_in_logs(notifier, monkeypatch, caplog, malformed):
    marker = "FAKE_PRIVATE_MARKER"

    class Broken(BaseChannel):
        async def send(self, n):
            raise RuntimeError(marker) from ValueError(marker)

    if not malformed:
        monkeypatch.setitem(CHANNEL_CLASSES, "webhook", Broken)
    result = await notifier.send_test_inline("webhook", {}, {"url": f"https://example.invalid:{marker}/"})
    assert not result.ok
    assert marker not in result.error
    assert marker not in caplog.text
    assert all(r.exc_info is None for r in caplog.records)


async def test_ops10_cancellation_propagates(notifier, monkeypatch):
    class Cancelled(BaseChannel):
        async def send(self, n):
            raise asyncio.CancelledError

    monkeypatch.setitem(CHANNEL_CLASSES, "webhook", Cancelled)
    with pytest.raises(asyncio.CancelledError):
        await notifier.send_test_inline("webhook", {}, {})

"""The `bsmm` command line.

Everything except `serve`, `start`, `stop` and `token` is a thin wrapper over the REST API, so what
you can do here you can do from a script or an AI agent. Add `--json` to any command that prints
data to get machine-readable output (and nothing else) on stdout.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from bsmm import __version__
from bsmm.cli import lifecycle
from bsmm.cli import service as svc
from bsmm.cli.client import Api, CliError, default_url
from bsmm.config import DEFAULT_PORT, RuntimeConfig
from bsmm.units import format_duration, format_hashrate, format_odds, format_si

app = typer.Typer(
    name="bsmm",
    help="Bitcoin Solo Miner Monitor: find, monitor and tune your solo miners.\n\nNew here? Run `bsmm setup`. AI agent? Run `bsmm agent-guide`.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_show_locals=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
token_app = typer.Typer(help="Manage API tokens for scripts and AI agents.", no_args_is_help=True)
service_app = typer.Typer(help="Start automatically when you log in / boot.", no_args_is_help=True)
app.add_typer(token_app, name="token")
app.add_typer(service_app, name="service")

console = Console()
err = Console(stderr=True)

JSON = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON only")]
URL = Annotated[str | None, typer.Option("--url", envvar="BSMM_URL", help="Server address (default: this computer)")]
TOKEN = Annotated[str | None, typer.Option("--token", envvar="BSMM_TOKEN", help="API token (needed only when a password is set)")]
DATA = Annotated[Path | None, typer.Option("--data-dir", envvar="BSMM_DATA_DIR", help="Where the database lives")]


def _fail(e: CliError) -> None:
    err.print(f"[bold red]Error:[/] {e}")
    if e.hint:
        err.print(f"[dim]{e.hint}[/]")
    raise typer.Exit(e.code)


def _emit(data: Any, as_json: bool, human: Any = None) -> None:
    if as_json:
        sys.stdout.write(json.dumps(data, indent=2, default=str) + "\n")
    elif human:
        human(data)


def _api(url: str | None, token: str | None) -> Api:
    return Api(url, token)


def _config(data_dir: Path | None = None, **over: Any) -> RuntimeConfig:
    cfg = RuntimeConfig()
    if data_dir:
        cfg.data_dir = data_dir.expanduser()
    for k, v in over.items():
        if v is not None:
            setattr(cfg, k, v)
    return cfg


def _setup_logging(level: str, log_file: Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        from logging.handlers import RotatingFileHandler

        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers = [RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")]
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", handlers=handlers, force=True)
    for noisy in ("httpx", "httpcore", "uvicorn.access", "mcp"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _lan_urls(port: int) -> list[str]:
    from bsmm.net import local_ipv4_networks

    urls = []
    try:
        import ifaddr

        for ad in ifaddr.get_adapters():
            for ip in ad.ips:
                if ip.is_IPv4 and isinstance(ip.ip, str) and not ip.ip.startswith(("127.", "169.254.")):
                    urls.append(f"http://{ip.ip}:{port}")
    except Exception:  # pragma: no cover
        pass
    del local_ipv4_networks
    return urls[:3]


# ------------------------------------------------------------------------------------------ serve / start / stop


@app.command()
def serve(
    host: Annotated[str | None, typer.Option(help="Address to listen on (default 0.0.0.0 = every network card)")] = None,
    port: Annotated[int | None, typer.Option(help=f"Port (default {DEFAULT_PORT})")] = None,
    data_dir: DATA = None,
    demo: Annotated[bool, typer.Option("--demo", help="Run with a simulated fleet and throw-away data")] = False,
    offline: Annotated[bool, typer.Option("--offline", help="Never contact the internet (no mempool.space, prices or update checks)")] = False,
    open_browser: Annotated[bool, typer.Option("--open", help="Open the dashboard in your browser")] = False,
    no_ui: Annotated[bool, typer.Option("--no-ui", help="API only, no web interface")] = False,
    log_level: Annotated[str, typer.Option(help="DEBUG, INFO, WARNING, ERROR")] = "INFO",
    log_file: Annotated[Path | None, typer.Option(help="Write logs to this file instead of the console")] = None,
    managed_token: Annotated[str | None, typer.Option(hidden=True)] = None,
) -> None:
    """Run the dashboard and API in the foreground."""
    import uvicorn

    from bsmm.api.app import create_app

    cfg = _config(data_dir, host=host, port=port, demo=demo or None, offline=offline or None, serve_ui=False if no_ui else None, log_level=log_level.upper())
    _setup_logging(cfg.log_level, log_file)
    app_ = create_app(cfg)
    urls = _lan_urls(cfg.port) or [f"http://localhost:{cfg.port}"]
    console.print(f"[bold #F7931A]Bitcoin Solo Miner Monitor[/] {__version__}" + ("  [yellow](demo mode: simulated miners, nothing is saved)[/]" if cfg.demo else ""))
    console.print(f"  Open on this computer:  [link]http://localhost:{cfg.port}[/]")
    for u in urls:
        console.print(f"  Or from your phone/PC:  [link]{u}[/]")
    console.print(f"  Data folder:            {cfg.data_dir}" if not cfg.demo else "")
    console.print("  AI agents:              /llms.txt  ·  /docs  ·  /mcp\n")
    if open_browser:
        webbrowser.open(f"http://localhost:{cfg.port}")
    if managed_token:
        server = uvicorn.Server(uvicorn.Config(app_, host=cfg.host, port=cfg.port, log_level="warning", access_log=False, timeout_graceful_shutdown=8))
        asyncio.run(lifecycle.run_managed(server, cfg.data_dir, managed_token))
    else:
        uvicorn.run(app_, host=cfg.host, port=cfg.port, log_level="warning", access_log=False, timeout_graceful_shutdown=8)


def _pid_file(cfg: RuntimeConfig) -> Path:
    return cfg.data_dir / "bsmm.pid"


def _pid_alive(pid: int) -> bool:
    return lifecycle.alive(pid)


@app.command()
def start(
    port: Annotated[int | None, typer.Option()] = None,
    data_dir: DATA = None,
    wait: Annotated[bool, typer.Option(help="Wait until the server answers")] = True,
    as_json: JSON = False,
    host: Annotated[str | None, typer.Option()] = None,
    offline: Annotated[bool, typer.Option("--offline")] = False,
    open_browser: Annotated[bool, typer.Option("--open")] = False,
) -> None:
    """Start the server in the background and return immediately."""
    cfg = _config(data_dir, port=port, host=host, offline=offline or None)
    cfg.data_dir = cfg.data_dir.resolve()
    cfg.ensure_dirs()
    try:
        with lifecycle.locked(cfg.data_dir):
            result = _start(cfg, wait)
    except CliError as e:
        _fail(e)
    _emit(result, as_json, lambda d: console.print(f"{'Already running' if d.get('already') else 'Started'} at {d['url']}"))
    if open_browser:
        webbrowser.open(result["url"])


def _start(cfg: RuntimeConfig, wait: bool) -> dict[str, Any]:
    pidf = _pid_file(cfg)
    if pidf.exists():
        record = lifecycle.read_record(cfg.data_dir)
        if lifecycle.owned_process(cfg.data_dir, record) is not None:
            return {"running": True, "already": True, "pid": record["pid"], "url": f"http://localhost:{record['port']}"}
        lifecycle.clear(cfg.data_dir)
        raise CliError("Stale or unverified PID state removed; no process was stopped.", "Check for an older server before running start again.")
    token = uuid.uuid4().hex
    prefix = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, "-m", "bsmm"]
    cmd = [*prefix, "serve", "--port", str(cfg.port), "--host", cfg.host, "--data-dir", str(cfg.data_dir), "--log-file", str(cfg.data_dir / "bsmm.log"), "--managed-token", token]
    if cfg.offline:
        cmd.append("--offline")
    kwargs: dict[str, Any] = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kwargs)  # noqa: S603
    except OSError as e:
        raise CliError(f"Could not start the server ({type(e).__name__}).") from e
    url = f"http://localhost:{cfg.port}"
    try:
        lifecycle.save_process(cfg.data_dir, proc.pid, token, cfg.port)
        if wait:
            api = Api(f"http://127.0.0.1:{cfg.port}")
            try:
                for _ in range(lifecycle.START_ATTEMPTS):
                    if proc.poll() is not None:
                        raise CliError("The server stopped right after starting.", f"See the log: {cfg.data_dir / 'bsmm.log'}")
                    if lifecycle.ready(cfg.data_dir, token) and api.is_up():
                        break
                    time.sleep(lifecycle.POLL_SECONDS)
                else:
                    raise CliError("The server did not answer within 30 seconds.", f"See the log: {cfg.data_dir / 'bsmm.log'}")
            finally:
                api.client.close()
    except BaseException:
        # Cooperative request to our launch nonce only, never a guessed OS signal.
        # Retain identity if shutdown cannot finish, so stop can retry.
        if proc.poll() is None:
            lifecycle.request_stop(cfg.data_dir, token)
            try:
                proc.wait(timeout=lifecycle.STOP_SECONDS)
            except subprocess.TimeoutExpired:
                raise CliError("Start failed and shutdown is still pending; process state retained. Run bsmm stop for this data directory.") from None
        lifecycle.clear(cfg.data_dir)
        raise
    return {"running": True, "pid": proc.pid, "url": url, "log": str(cfg.data_dir / "bsmm.log")}


@app.command()
def stop(data_dir: DATA = None, as_json: JSON = False) -> None:
    """Stop the background server started with `bsmm start`."""
    cfg = _config(data_dir)
    pidf = _pid_file(cfg)
    if not cfg.data_dir.exists():
        _emit({"stopped": False, "reason": "not started by `bsmm start`"}, as_json, lambda d: console.print("Nothing to stop (no background server was started with `bsmm start`)."))
        return
    try:
        with lifecycle.locked(cfg.data_dir):
            if not pidf.exists():
                _emit({"stopped": False, "reason": "not started by `bsmm start`"}, as_json, lambda d: console.print("Nothing to stop (no background server was started with `bsmm start`)."))
                return
            record = lifecycle.read_record(cfg.data_dir)
            proc = lifecycle.owned_process(cfg.data_dir, record)
            if proc is None:
                lifecycle.clear(cfg.data_dir)
                _emit({"stopped": False, "reason": "stale or unverified PID state removed"}, as_json, lambda d: console.print(d["reason"]))
                return
            lifecycle.request_stop(cfg.data_dir, record["token"])
            deadline = time.monotonic() + lifecycle.STOP_SECONDS
            while lifecycle.owned_process(cfg.data_dir, record) is not None:
                if time.monotonic() >= deadline:
                    raise CliError("Shutdown did not finish; process state retained. No forced kill was attempted.")
                time.sleep(lifecycle.POLL_SECONDS)
            lifecycle.clear(cfg.data_dir)
    except CliError as e:
        _fail(e)
    _emit({"stopped": True}, as_json, lambda d: console.print("Stopped."))


@app.command()
def demo(port: Annotated[int | None, typer.Option()] = None, open_browser: Annotated[bool, typer.Option("--open")] = True) -> None:
    """Try the app with a simulated fleet (nothing is saved)."""
    serve(host=None, port=port, data_dir=None, demo=True, offline=True, open_browser=open_browser, no_ui=False, log_level="INFO", log_file=None)


# ------------------------------------------------------------------------------------------ read commands


@app.command("status")
def status_cmd(url: URL = None, token: TOKEN = None, as_json: JSON = False) -> None:
    """Fleet totals, your odds and anything that needs attention."""
    try:
        o = _api(url, token).get("/overview")
    except CliError as e:
        _fail(e)

    def human(d: dict[str, Any]) -> None:
        s, odds = d["summary"], d["odds"]
        console.print(f"[bold]{s['devices_online']}/{s['devices_total']} miners online[/]"
                      + (f", {s['devices_degraded']} need attention" if s["devices_degraded"] else "")
                      + (f", {s['devices_offline']} offline" if s["devices_offline"] else ""))
        console.print(f"Hashrate [bold]{format_hashrate(s['hashrate_hs'])}[/]"
                      + (f"  ·  {s['power_w']:.0f} W" if s.get("power_w") else "")
                      + (f"  ·  {s['efficiency_j_th']:.1f} J/TH" if s.get("efficiency_j_th") else ""))
        net = d["network"]
        if net.get("height"):
            console.print(f"Block {net['height']:,}  ·  difficulty {format_si(net.get('difficulty'))}  ·  source: {net.get('source')}")
        if odds.get("available"):
            y = odds["horizons"]["year"]
            console.print(f"Chance of a block this year: [bold]{format_odds(y['probability'])}[/]")
            for line in odds["plain_english"][:2]:
                console.print(f"[dim]{line}[/]")
        for a in d["alerts"]:
            console.print(f"[yellow]![/] {a['title']}")
        if d["blocks_found"]:
            console.print(f"[bold green]You have found {len(d['blocks_found'])} block(s)![/]")

    _emit(o, as_json, human)


@app.command("list")
def list_cmd(url: URL = None, token: TOKEN = None, as_json: JSON = False, status: Annotated[str | None, typer.Option()] = None) -> None:
    """List your miners."""
    try:
        devices = _api(url, token).get("/devices", status=status)
    except CliError as e:
        _fail(e)

    def human(devs: list[dict[str, Any]]) -> None:
        t = Table(box=None, header_style="bold")
        for col in ("ID", "Name", "Model", "Address", "Status", "Hashrate", "Temp", "Power", "Best share"):
            t.add_column(col)
        colors = {"online": "green", "degraded": "yellow", "offline": "red", "paused": "cyan"}
        for d in devs:
            tel = d.get("telemetry") or {}
            t.add_row(d["id"], d["name"], d["model"], d["host"], f"[{colors.get(d['status'], 'white')}]{d['status']}[/]",
                      format_hashrate(d.get("hashrate_smooth_hs") or tel.get("hashrate_hs")) if tel else "-",
                      f"{tel['temp_asic_c']:.0f} °C" if tel.get("temp_asic_c") else "-", f"{tel['power_w']:.0f} W" if tel.get("power_w") else "-",
                      format_si(tel.get("best_diff")) if tel.get("best_diff") else "-")
        console.print(t)
        if not devs:
            console.print("No miners yet. Run `bsmm discover --add`.")

    _emit(devices, as_json, human)


@app.command()
def odds(
    hashrate_ths: Annotated[float | None, typer.Option(help="What if you had this many TH/s?")] = None,
    difficulty: Annotated[float | None, typer.Option()] = None,
    url: URL = None, token: TOKEN = None, as_json: JSON = False,
) -> None:
    """Your chance of finding a block, in plain English."""
    try:
        d = _api(url, token).get("/odds", hashrate_ths=hashrate_ths, difficulty=difficulty)
    except CliError as e:
        _fail(e)

    def human(o: dict[str, Any]) -> None:
        if not o.get("available"):
            console.print(o["reason"])
            return
        t = Table(box=None, header_style="bold")
        t.add_column("Within")
        t.add_column("Chance", justify="right")
        for name in ("day", "month", "year", "five_years", "ten_years"):
            h = o["horizons"][name]
            t.add_row(name.replace("_", " "), format_odds(h["probability"]))
        console.print(t)
        console.print(f"Expected wait: {format_duration(o['expected_seconds'])}")
        for line in o["plain_english"]:
            console.print(f"[dim]- {line}[/]")

    _emit(d, as_json, human)


@app.command()
def doctor(url: URL = None, token: TOKEN = None, data_dir: DATA = None, as_json: JSON = False) -> None:
    """Check that everything works and say how to fix what doesn't."""
    api = _api(url, token)
    if not api.is_up():
        cfg = _config(data_dir)
        local = {
            "server_running": False, "data_dir": str(cfg.data_dir), "data_dir_exists": cfg.data_dir.exists(), "python": sys.version.split()[0],
            "version": __version__, "hint": "Start the server with `bsmm start` (background) or `bsmm serve`, then run `bsmm doctor` again.",
        }
        _emit(local, as_json, lambda d: console.print(f"[yellow]The server is not running.[/] {d['hint']}\nData folder: {d['data_dir']}"))
        raise typer.Exit(1)
    try:
        d = api.get("/system/diagnostics")
    except CliError as e:
        _fail(e)

    def human(diag: dict[str, Any]) -> None:
        icons = {"pass": "[green]✓[/]", "warn": "[yellow]![/]", "fail": "[red]✗[/]"}
        console.print(f"[bold]Bitcoin Solo Miner Monitor {diag['version']}[/]  (Python {diag['python']}, {diag['platform']})")
        for c in diag["checks"]:
            console.print(f"{icons[c['status']]} {c['message']}" + (f"\n    [dim]Fix: {c['fix']}[/]" if c.get("fix") else ""))
        for dev in diag["devices"]:
            if dev["status"] == "offline":
                console.print(f"[red]✗[/] {dev['name']} ({dev['host']}) is offline: {dev.get('last_error')}")

    _emit(d, as_json, human)
    if not d["ok"]:
        raise typer.Exit(1)


@app.command("agent-guide")
def agent_guide_cmd(url: URL = None) -> None:
    """Print the machine-readable guide AI agents use to set this app up for a user."""
    from bsmm.agent_docs import llms_txt

    try:
        text = Api(url).client.get(f"{Api(url).url}/llms.txt", timeout=3).text
    except Exception:
        text = llms_txt(url or default_url())
    sys.stdout.write(text)


# ------------------------------------------------------------------------------------------ discover / add


@app.command()
def discover(
    cidr: Annotated[list[str] | None, typer.Option("--cidr", help="Network to scan, e.g. 192.168.1.0/24 (repeatable). Default: this computer's networks")] = None,
    add: Annotated[bool, typer.Option("--add", help="Start monitoring everything new that is found")] = False,
    url: URL = None, token: TOKEN = None, as_json: JSON = False,
) -> None:
    """Scan the network for miners (and your node or pool)."""
    api = _api(url, token)
    try:
        job = api.post("/discovery", {"cidrs": cidr})
        with console.status("Scanning your network...", spinner="dots") if not as_json else _nullctx():
            while job["status"] == "running":
                time.sleep(1.0)
                job = api.get(f"/discovery/{job['id']}")
        result: dict[str, Any] = {"scan": job}
        if add:
            result["adopted"] = api.post(f"/discovery/{job['id']}/adopt", {})
    except CliError as e:
        _fail(e)

    def human(r: dict[str, Any]) -> None:
        j = r["scan"]
        t = Table(box=None, header_style="bold", title=f"Found {len(j['miners'])} miner(s) on {', '.join(j['cidrs'])}")
        for col in ("Address", "Model", "Firmware", "Hashrate", "Note"):
            t.add_column(col)
        for m in j["miners"]:
            note = "already monitored" if m["already_added"] else (f"same miner as {m['duplicate_of']}" if m["duplicate_of"] else "new")
            t.add_row(m["host"], m["model"], m.get("firmware") or "-", format_hashrate(m["hashrate_hs"]) if m.get("hashrate_hs") else "-", note)
        console.print(t)
        for s in j["sources"]:
            extra = "needs RPC login" if s["needs_credentials"] else "no login needed"
            console.print(f"[cyan]Node/pool:[/] {s['name']} at {s['url']} ({extra}) - {s['reason']}")
        if "adopted" in r:
            console.print(f"[green]Added {len(r['adopted']['added'])} miner(s).[/]")
        elif any(not m["already_added"] and not m["duplicate_of"] for m in j["miners"]):
            console.print("Add them with: [bold]bsmm discover --add[/]")

    _emit(result, as_json, human)


class _nullctx:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *a: Any) -> None:
        return None


@app.command()
def add(host: str, name: Annotated[str | None, typer.Option()] = None, url: URL = None, token: TOKEN = None, as_json: JSON = False) -> None:
    """Add one miner by IP address or host name."""
    try:
        r = _api(url, token).post("/devices", {"host": host, "name": name})
    except CliError as e:
        _fail(e)
    _emit(r, as_json, lambda d: console.print(f"Added {d['device']['name']} ({d['device']['model']})." if d["created"] else d["note"] or "Already monitored."))


# ------------------------------------------------------------------------------------------ setup wizard


@app.command()
def setup(
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Don't ask; do the sensible thing")] = False,
    cidr: Annotated[list[str] | None, typer.Option("--cidr")] = None,
    node_url: Annotated[str | None, typer.Option(help="Your Bitcoin node's RPC address, e.g. http://umbrel.local:8332")] = None,
    rpc_user: Annotated[str | None, typer.Option(envvar="BSMM_RPC_USER")] = None,
    rpc_password: Annotated[str | None, typer.Option(envvar="BSMM_RPC_PASSWORD")] = None,
    pool_url: Annotated[str | None, typer.Option(help="Public Pool API address, e.g. http://umbrel.local:2019")] = None,
    address: Annotated[str | None, typer.Option(help="Your Bitcoin payout address (used to recognise a block you find)")] = None,
    kwh_price: Annotated[float | None, typer.Option(help="Electricity price per kWh")] = None,
    password: Annotated[str | None, typer.Option(envvar="BSMM_ADMIN_PASSWORD", help="Protect the dashboard with this password")] = None,
    no_password: Annotated[bool, typer.Option("--no-password", help="Leave the dashboard open to the network")] = False,
    ntfy_topic: Annotated[str | None, typer.Option(help="Create a phone-alert channel on ntfy.sh with this topic")] = None,
    data_dir: DATA = None, port: Annotated[int | None, typer.Option()] = None,
    url: URL = None, token: TOKEN = None, as_json: JSON = False,
) -> None:
    """Guided first-time setup (also works unattended: add flags and --yes)."""
    cfg = _config(data_dir, port=port)
    base = url or f"http://127.0.0.1:{cfg.port}"
    api = Api(base, token)
    def log(message: str) -> None:
        if not as_json:  # unattended runs print one JSON document at the end and nothing else
            console.print(message)

    result: dict[str, Any] = {"url": base, "steps": []}

    def step(name: str, **info: Any) -> None:
        result["steps"].append({"step": name, **info})

    try:
        if not api.is_up():
            if url:
                raise CliError(f"No server answers at {url}.")
            log("Starting the server in the background...")
            # The nested command owns lifecycle, but setup owns its one result document.
            if as_json:
                with contextlib.redirect_stdout(io.StringIO()):
                    start(port=cfg.port, data_dir=data_dir, wait=True, as_json=True)
            else:
                start(port=cfg.port, data_dir=data_dir, wait=True, as_json=False)
        meta = api.get("/meta")
        if meta["auth"]["mode"] == "password" and not api.token:
            api.token = _local_admin_token(cfg)
            api.client.headers["Authorization"] = f"Bearer {api.token}"
        log(f"[bold #F7931A]Solo Miner Monitor[/] {meta['version']} is running.")

        log("Looking for miners on your network (about 20 seconds)...")
        job = api.post("/discovery", {"cidrs": cidr})
        while job["status"] == "running":
            time.sleep(1.0)
            job = api.get(f"/discovery/{job['id']}")
        new = [m for m in job["miners"] if not m["already_added"] and not m["duplicate_of"]]
        log(f"Found {len(job['miners'])} miner(s), {len(new)} new.")
        for m in job["miners"]:
            log(f"  {m['host']:<16} {m['model']}" + ("  (same miner as " + m["duplicate_of"] + ")" if m["duplicate_of"] else ""))
        adopted: dict[str, Any] = {"added": [], "merged": []}
        if new and (yes or typer.confirm(f"Start monitoring {len(new)} miner(s)?", default=True)):
            adopted = api.post(f"/discovery/{job['id']}/adopt", {})
        step("miners", found=len(job["miners"]), added=[d["name"] for d in adopted["added"]])

        added_sources: list[str] = []
        if node_url:
            body = {"kind": "bitcoin_core", "url": node_url, "secret": {k: v for k, v in {"rpc_user": rpc_user, "rpc_password": rpc_password}.items() if v}}
            added_sources.append(api.post("/sources", body)["source"]["name"])
        explicit_pool = pool_url
        verified = [s for s in job["sources"] if s["verified"] and s["kind"] == "public_pool"]
        if explicit_pool:
            added_sources.append(api.post("/sources", {"kind": "public_pool", "url": explicit_pool})["source"]["name"])
        elif verified and (yes or typer.confirm(f"Connect {verified[0]['name']} ({verified[0]['url']}) for pool stats?", default=True)):
            added_sources.append(api.post("/sources", {"kind": "public_pool", "url": verified[0]["url"], "name": verified[0]["name"]})["source"]["name"])
        core = [s for s in job["sources"] if s["kind"] == "bitcoin_core"]
        if core and not node_url:
            log(f"[yellow]A Bitcoin node answers at {core[0]['url']}.[/] Re-run with --node-url {core[0]['url']} --rpc-user ... --rpc-password ... to connect it.")
        step("sources", added=added_sources, node_candidates=[s["url"] for s in core])

        patch: dict[str, Any] = {"general": {"onboarding_done": True}}
        if kwh_price is not None:
            patch["energy"] = {"price_per_kwh": kwh_price}
        elif not yes and not as_json:
            patch["energy"] = {"price_per_kwh": typer.prompt("Electricity price per kWh", default=0.12, type=float)}
        if address:
            patch["mining"] = {"addresses": [address]}
        api.patch("/settings", patch)
        step("settings", **{k: v for k, v in patch.items() if k != "general"})

        if ntfy_topic:
            ch = api.post("/notifications/channels", {"kind": "ntfy", "name": "Phone (ntfy)", "config": {"topic": ntfy_topic}})["channel"]
            test = api.post(f"/notifications/channels/{ch['id']}/test")
            step("notifications", channel=ch["id"], test_ok=test["ok"])
            log("Sent a test notification to ntfy." if test["ok"] else f"[yellow]ntfy test failed: {test.get('error')}[/]")

        created_token: str | None = None
        if password or (not no_password and not yes and not as_json and typer.confirm("Protect the dashboard with a password?", default=True)):
            pw = password or typer.prompt("Choose a password (min 8 characters)", hide_input=True, confirmation_prompt=True)
            api.post("/auth/password", {"new_password": pw})
            step("security", password=True)
            log("Password set.")
            if token is None:
                # the old token (if any) keeps working; mint one for the caller to keep
                api.token = _local_admin_token(cfg)
                api.client.headers["Authorization"] = f"Bearer {api.token}"
        if yes or as_json:
            tok = api.post("/auth/tokens", {"name": "setup (agent)", "scope": "admin"})
            created_token = tok["token"]
            step("token", id=tok["id"], scope="admin")

        overview = api.get("/overview")
        result["overview"] = {"devices": overview["summary"]["devices_total"], "hashrate_hs": overview["summary"]["hashrate_hs"],
                              "odds_year": overview["odds"].get("horizons", {}).get("year", {}).get("probability")}
        if created_token:
            result["token"] = created_token
            result["token_note"] = "Shown once. Pass it as 'Authorization: Bearer <token>' or set BSMM_TOKEN."  # noqa: S105 - a hint about the token, not the token
        log(f"\n[bold green]All set.[/] Open [link]{base}[/] on any device on your network.")
        log("Next: `bsmm status`, `bsmm odds`, `bsmm doctor`.")
    except CliError as e:
        _fail(e)
    _emit(result, as_json)


def _local_admin_token(cfg: RuntimeConfig) -> str:
    """Whoever can read the data folder is already the admin: mint a throw-away admin token straight from the database."""
    from bsmm.storage.store import Store

    async def run() -> str:
        store = await Store.open(cfg)
        try:
            _, tok = await store.create_token("cli (local)", "admin", time.time() + 3600)
            return tok
        finally:
            await store.close()

    return asyncio.run(run())


# ------------------------------------------------------------------------------------------ tokens & password


@token_app.command("create")
def token_create(
    name: Annotated[str, typer.Option(help="What the token is for")] = "agent",
    scope: Annotated[str, typer.Option(help="read | control | admin")] = "control",
    days: Annotated[float | None, typer.Option(help="Expire after this many days")] = None,
    data_dir: DATA = None, as_json: JSON = False,
) -> None:
    """Create an API token (shown once). Works while the server is running or stopped."""
    if scope not in ("read", "control", "admin"):
        _fail(CliError("scope must be read, control or admin."))
    from bsmm.storage.store import Store

    async def run() -> tuple[str, str]:
        store = await Store.open(_config(data_dir))
        try:
            return await store.create_token(name, scope, time.time() + days * 86400 if days else None)
        finally:
            await store.close()

    tid, tok = asyncio.run(run())
    _emit({"id": tid, "name": name, "scope": scope, "token": tok}, as_json,
          lambda d: console.print(f"Token [bold]{d['token']}[/]\n[dim]Shown once. Use it as 'Authorization: Bearer <token>' or export BSMM_TOKEN.[/]"))


@token_app.command("list")
def token_list(url: URL = None, token: TOKEN = None, as_json: JSON = False) -> None:
    """List tokens (the secret values are never shown)."""
    try:
        toks = _api(url, token).get("/auth/tokens")["tokens"]
    except CliError as e:
        _fail(e)
    def show(ts: list[dict[str, Any]]) -> None:
        for t in ts:
            console.print(f"{t['id']}  {t['name']:<20} {t['scope']}")

    _emit(toks, as_json, show)


@token_app.command("revoke")
def token_revoke(token_id: str, url: URL = None, token: TOKEN = None) -> None:
    """Revoke a token by id."""
    try:
        _api(url, token).delete(f"/auth/tokens/{token_id}")
    except CliError as e:
        _fail(e)
    console.print("Revoked.")


@app.command()
def password(
    new: Annotated[str | None, typer.Option("--password", help="Don't prompt")] = None,
    current: Annotated[str | None, typer.Option("--current-password", envvar="BSMM_CURRENT_PASSWORD", help="Current password (otherwise prompted when needed)")] = None,
    offline_local: Annotated[bool, typer.Option("--offline-local", help="Explicit local password recovery; requires --data-dir and no --url")] = False,
    url: URL = None, token: TOKEN = None, data_dir: DATA = None,
) -> None:
    """Set or change the dashboard password and switch protection on."""
    if offline_local and (url or os.environ.get("BSMM_URL") or data_dir is None):
        _fail(CliError("Local recovery requires --data-dir and cannot be combined with --url or BSMM_URL."))
    pw = new if new is not None else typer.prompt("New password (min 8 characters)", hide_input=True, confirmation_prompt=True)
    api = _api(url, token)
    if not offline_local:
        try:
            meta = api.get("/meta")
            if meta["auth"]["password_set"] and current is None:
                current = typer.prompt("Current password", hide_input=True)
            api.post("/auth/password", {"new_password": pw, "current_password": current})
        except CliError as e:
            _fail(e)
    else:
        from bsmm.auth import AuthService
        from bsmm.storage.store import Store

        async def run() -> None:
            store = await Store.open(_config(data_dir))
            try:
                await AuthService(store).set_password(pw)
                from bsmm.settings import SettingsService

                s = SettingsService(store)
                await s.load()
                await s.update({"auth": {"mode": "password"}})
            finally:
                await store.close()

        asyncio.run(run())
        console.print(f"Local password set in {data_dir}. No remote server was changed.")
        return
    console.print("Password set. The dashboard now asks for it.")


# ------------------------------------------------------------------------------------------ mcp / service / misc


def _service_run(cmd: list[str]) -> None:
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
    except OSError as e:
        _fail(CliError(f"Could not run {cmd[0]} ({type(e).__name__}).", "Check that the platform service manager is available."))
        return
    if result.returncode:
        _fail(CliError(f"{cmd[0]} failed (exit {result.returncode}).", "The operation did not complete. Check your user service manager before retrying; definitions were retained."))


@app.command()
def mcp(
    url: URL = None, token: TOKEN = None,
    transport: Annotated[str, typer.Option(help="stdio (default) or http")] = "stdio",
) -> None:
    """Run the MCP server so an AI agent can operate the app (point your MCP client at this command)."""
    from bsmm.mcp_server import HttpBackend, build_server

    api_url = url or default_url()
    server = build_server(HttpBackend(api_url, token or os.environ.get("BSMM_TOKEN")))
    if transport != "stdio":
        _fail(CliError("Only stdio is available here.", f"The HTTP transport is built into the server at {api_url}/mcp."))
    server.run("stdio")


@service_app.command("install")
def service_install(
    apply: Annotated[bool, typer.Option("--apply", help="Actually install it (otherwise just print what would be done)")] = False,
    port: Annotated[int | None, typer.Option()] = None, data_dir: DATA = None,
) -> None:
    """Make the server start automatically (systemd user unit / launchd agent / Windows scheduled task)."""
    cmd = svc.exe_command(port, str(data_dir) if data_dir else None)
    if sys.platform.startswith("linux"):
        unit = svc.systemd_unit(cmd)
        path = svc.systemd_path()
        if not apply:
            console.print(f"[bold]{path}[/]\n{unit}\nThen run:\n  systemctl --user daemon-reload\n  systemctl --user enable --now bsmm\n  loginctl enable-linger $USER   [dim]# keep it running when logged out[/]")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(unit)
        _service_run(["systemctl", "--user", "daemon-reload"])
        _service_run(["systemctl", "--user", "enable", "--now", "bsmm"])
        console.print(f"Installed {path} and started it.")
    elif sys.platform == "darwin":
        path = svc.launchd_path()
        text = svc.launchd_plist(cmd)
        if not apply:
            console.print(f"[bold]{path}[/]\n{text}\nThen run: launchctl load -w {path}")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        _service_run(["launchctl", "load", "-w", str(path)])
        console.print(f"Installed {path}.")
    else:
        task = svc.windows_task(cmd)
        if not apply:
            console.print("Run this in a terminal to start at every login:\n  " + " ".join(task))
            return
        _service_run(task)
        console.print("Scheduled task created: it starts at your next login.")


@service_app.command("uninstall")
def service_uninstall() -> None:
    """Remove the auto-start entry."""
    if sys.platform.startswith("linux"):
        _service_run(["systemctl", "--user", "disable", "--now", "bsmm"])
        svc.systemd_path().unlink(missing_ok=True)
    elif sys.platform == "darwin":
        _service_run(["launchctl", "unload", "-w", str(svc.launchd_path())])
        svc.launchd_path().unlink(missing_ok=True)
    else:
        _service_run(["schtasks", "/Delete", "/F", "/TN", "BitcoinSoloMinerMonitor"])
    console.print("Removed.")


@app.command("migrate-legacy")
def migrate_legacy(
    path: Annotated[Path, typer.Argument(help="The old app's data/config.db (version 0.9.x)")],
    url: URL = None, token: TOKEN = None, as_json: JSON = False,
) -> None:
    """Import the miners from an old v0.9 installation."""
    if not path.exists():
        _fail(CliError(f"{path} does not exist.", "The old database is usually in the old app's data/ folder (config.db)."))
    rows: list[tuple[str, int, str | None]] = []
    # The old app ran SQLite in WAL mode, so recent changes may still sit in config.db-wal. Read a private copy of
    # the database together with its -wal/-shm files: that sees every change and never touches the original.
    scratch = tempfile.TemporaryDirectory(prefix="bsmm-legacy-")
    for suffix in ("", "-wal", "-shm"):
        src = path.with_name(path.name + suffix)
        if src.exists():
            shutil.copy2(src, Path(scratch.name) / ("legacy.db" + suffix))
    con = sqlite3.connect(Path(scratch.name) / "legacy.db")
    try:
        for (cfg_text,) in con.execute("SELECT config FROM miners"):
            try:
                c = json.loads(cfg_text)
            except ValueError:
                continue
            host = c.get("ip_address") or c.get("ip") or c.get("host")
            if host:
                rows.append((str(host), int(c.get("port") or 80), c.get("name") or c.get("custom_name")))
    except sqlite3.Error as e:
        _fail(CliError(f"Could not read the old database ({e}).", "Make sure it is the config.db from the v0.9 data/ folder."))
    finally:
        con.close()
        scratch.cleanup()
    api = _api(url, token)
    report = []
    for host, port, name in rows:
        try:
            r = api.post("/devices", {"host": host, "port": port if port not in (80,) else None, "name": name})
            report.append({"host": host, "ok": True, "created": r["created"], "note": r.get("note")})
        except CliError as e:
            report.append({"host": host, "ok": False, "error": str(e)})
    def show(rs: list[dict[str, Any]]) -> None:
        for r in rs:
            console.print(f"{'[green]✓[/]' if r['ok'] else '[red]✗[/]'} {r['host']} {r.get('note') or r.get('error') or ''}")

    _emit(report, as_json, show)


@app.command()
def capture(
    host: Annotated[str, typer.Argument(help="IP address or host name of the miner")],
    out: Annotated[Path | None, typer.Option("--out", "-o", help="Save the raw replies to this file")] = None,
    no_redact: Annotated[bool, typer.Option("--no-redact", help="Keep Wi-Fi name, MAC, pool users and addresses in the capture")] = False,
    timeout: Annotated[float, typer.Option(help="Seconds to wait for each reply")] = 4.0,
    as_json: JSON = False,
) -> None:
    """What does the app think this miner is, and why? Optionally save its replies (private data removed) to add a model.

    Read-only: it only asks questions, never changes anything on the miner.
    """
    from bsmm.capture import capture_sync

    result = capture_sync(host, timeout=timeout, scrub=not no_redact)
    if out:
        out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        out.chmod(0o600)

    def show(r: dict[str, Any]) -> None:
        if not r["recognised"]:
            console.print(f"[yellow]Nothing at {host} answered like a supported miner.[/]")
            console.print("[dim]Check the address, that the miner is on, and that it is on the same network as this computer.[/]")
        for p in r["recognised"]:
            mc = p.get("model_confidence")
            how = f"{round(mc * 100)}% sure of the model" if mc is not None else "model taken from what the device reports"
            console.print(f"[bold]{p['model']}[/]  ({p['driver']} on port {p['port']}, {how})")
            for line in p["model_evidence"] or p["evidence"]:
                console.print(f"  [dim]because[/] {line}")
        if out:
            note = "" if no_redact else " Private data was removed, but look it over before you share it."
            console.print(f"\nSaved the raw replies to {out}.{note}")
        else:
            console.print("\n[dim]Add --out FILE to save the raw replies, for example to ask for support for a new model.[/]")

    _emit(result, as_json, show)


@app.command()
def version() -> None:
    """Print the version."""
    console.print(__version__)


def main() -> None:
    try:
        app()
    except CliError as e:
        _fail(e)


if __name__ == "__main__":
    main()

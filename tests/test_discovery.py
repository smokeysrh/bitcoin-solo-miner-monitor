"""Network discovery: scanning, identifying, de-duplicating and adopting miners; finding the node and pool;
the private-range guard; and healing devices whose IP address changed.

Most tests start REAL servers on localhost: AxeOS simulators under uvicorn (one per address, ``127.0.0.x`` are all
loopback on Linux) and a cgminer simulator on a raw TCP socket, then scan them with the real TCP sweep and the real
protocol probes. A scan reports one miner per host (the best match across its ports), so scenarios that need several
miners use several loopback addresses and skip themselves where the machine does not offer them.

The node/pool/mempool detection looks at fixed well-known ports (8332, 2019, 3334, 3006) that may be taken on a
developer machine, so those tests swap only the TCP "is this port open" probe for a table and serve the HTTP side from
simulated sites.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

import bsmm.engine.discovery as discovery_mod
from bsmm.config import RuntimeConfig
from bsmm.context import AppContext
from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.registry import probe_host
from bsmm.engine.discovery import (
    NODE_PORTS,
    SWEEP_PORTS,
    DiscoveryJob,
    DiscoveryService,
    MinerCandidate,
    SourceCandidate,
    _identity_of,
    _is_ip,
)
from bsmm.models import Device, DeviceStatus, Severity
from bsmm.net import is_private_host, iter_hosts, make_http_client
from bsmm.sim.axeos import AxeOSSim
from bsmm.sim.cgminer import CgminerSim

from .live import serve

FIX = Path(__file__).parent / "fixtures"
ADDR = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
MAC_A, MAC_B = "AA:BB:CC:00:00:11", "AA:BB:CC:00:00:22"


# --- harness -----------------------------------------------------------------------------------------------------------


def fx(path: str) -> Any:
    return json.loads((FIX / path).read_text())


def site(routes: dict[str, Any]) -> Starlette:
    """A fake website: ``{path: json-able | text}``; anything else is a 404."""

    async def handler(request):
        val = routes.get(request.url.path)
        if val is None:
            return PlainTextResponse("nope", status_code=404)
        return PlainTextResponse(val) if isinstance(val, str) else JSONResponse(val)

    return Starlette(routes=[Route("/{p:path}", handler)])


def public_pool_site() -> Starlette:
    return site({"/api/network": fx("pools/public_pool_network.json"), "/api/pool": fx("pools/public_pool_pool.json")})


@asynccontextmanager
async def serve_at(app: Starlette, host: str) -> AsyncIterator[int]:
    """Like tests/live.py ``serve`` but on any loopback address; yields the port."""
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=0, log_level="warning", lifespan="on"))
    task = asyncio.create_task(server.serve())
    for _ in range(300):
        if server.started:
            break
        await asyncio.sleep(0.02)
    else:  # pragma: no cover
        task.cancel()
        raise RuntimeError(f"test server on {host} did not start")
    try:
        yield server.servers[0].sockets[0].getsockname()[1]  # type: ignore[union-attr]
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 10)


def require_loopback(*hosts: str) -> None:
    for h in hosts:
        s = socket.socket()
        try:
            s.bind((h, 0))
        except OSError:
            pytest.skip(f"{h} is not a usable loopback address on this machine")
        finally:
            s.close()


class Lab:
    """Real simulated miners listening on loopback addresses."""

    def __init__(self, stack: AsyncExitStack) -> None:
        self.stack = stack

    async def axeos(self, host: str, profile: str = "gamma", *, mac: str, seed: int = 1) -> tuple[AxeOSSim, int]:
        sim = AxeOSSim(profile, seed=seed, mac=mac)
        if host == "127.0.0.1":  # the stock helper binds exactly this address
            url = await self.stack.enter_async_context(serve(sim.app()))  # type: ignore[arg-type]
            return sim, int(url.rsplit(":", 1)[1])
        return sim, await self.stack.enter_async_context(serve_at(sim.app(), host))

    async def cgminer(self, host: str, profile: str = "avalon_nano3", seed: int = 3) -> tuple[CgminerSim, int]:
        sim = await CgminerSim(profile, seed=seed).start(host)
        self.stack.push_async_callback(sim.stop)
        return sim, sim.port

    async def decoy(self, host: str) -> int:
        """Something that listens and speaks HTTP but is not a miner."""
        return await self.stack.enter_async_context(serve_at(site({"/": "hello"}), host))


@pytest.fixture
async def lab():
    async with AsyncExitStack() as stack:
        yield Lab(stack)


async def _cancel_jobs(ctx: AppContext) -> None:
    for job in list(ctx.discovery.jobs.values()):
        if job._task is not None and not job._task.done():
            job._task.cancel()
            await asyncio.wait({job._task}, timeout=5)


@pytest.fixture
async def ctx(tmp_path):
    """An application context whose HTTP client is the real one (no simulated transport): it talks to real sockets."""
    c = await AppContext.create(RuntimeConfig(data_dir=tmp_path, offline=True), http=make_http_client())
    yield c
    await _cancel_jobs(c)
    await c.fleet.stop()
    await c.http.aclose()
    await c.store.close()


@pytest.fixture
def loopback(monkeypatch):
    """Let the scanner look at 127.0.0.x (normally it never scans the machine it runs on), with short protocol timeouts.

    On a port the user added to the scan every driver gets a try, so the cgminer probe is also sent to our HTTP simulators;
    an HTTP server waits for a proper request and says nothing, which the probe only gives up on after its four second
    timeout. Cutting that to half a second keeps these tests quick without changing anything else.
    """
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", set)
    real_probe = discovery_mod.probe_host

    async def quick_probe(host, port=None, *, client, timeout=4.0, drivers=None):
        return await real_probe(host, port, client=client, timeout=min(timeout, 0.5), drivers=drivers)

    monkeypatch.setattr(discovery_mod, "probe_host", quick_probe)


class FakeTCP:
    """Stands in for the TCP sweep: a table of (host, port) pairs that accept connections."""

    def __init__(self) -> None:
        self.open: set[tuple[str, int]] = set()
        self.calls: list[tuple[str, int]] = []

    async def __call__(self, host: str, port: int, timeout: float = 1.0) -> bool:
        self.calls.append((host, port))
        return (host, port) in self.open


@pytest.fixture
def tcp(monkeypatch):
    fake = FakeTCP()
    monkeypatch.setattr(discovery_mod, "tcp_open", fake)
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", set)
    return fake


async def finish(job: DiscoveryJob, timeout: float = 20.0) -> DiscoveryJob:
    assert job._task is not None
    _, pending = await asyncio.wait({job._task}, timeout=timeout)
    assert not pending, f"scan still {job.status} ({job.phase}) after {timeout}s"
    return job


def events_of(ctx: AppContext, *types: str):
    return ctx.store.list_events(types=list(types), limit=200)


# --- a real scan ----------------------------------------------------------------------------------------------------------------


async def test_a_scan_finds_axeos_and_cgminer_miners_names_them_and_flags_the_second_address(ctx, lab, loopback):
    require_loopback("127.0.0.2", "127.0.0.3", "127.0.0.4", "127.0.0.5")
    gamma, p1 = await lab.axeos("127.0.0.1", "gamma", mac=MAC_A)
    nerd, p2 = await lab.axeos("127.0.0.2", "nerdqaxe", mac=MAC_B, seed=2)
    clone, p3 = await lab.axeos("127.0.0.3", "gamma", mac=MAC_A, seed=3)  # the same box, answering on a second address
    nano, p4 = await lab.cgminer("127.0.0.4")
    decoy = await lab.decoy("127.0.0.5")
    sub = ctx.bus.subscribe({"discovery"})

    job = ctx.discovery.start(["127.0.0.0/29"], ports=[p1, p2, p3, p4, decoy], include_sources=False)
    assert job.status == "running" and job.id.startswith("scan_") and job.cidrs == ["127.0.0.0/29"]
    await finish(job)

    assert (job.status, job.phase, job.error) == ("finished", "done", None)
    assert job.total_hosts == job.scanned_hosts == 6 and job.finished_at is not None
    miners = {m.host: m for m in job.miners}
    assert sorted(miners) == ["127.0.0.1", "127.0.0.2", "127.0.0.3", "127.0.0.4"]  # not the decoy, not the empty addresses

    g = miners["127.0.0.1"]
    assert (g.driver, g.family, g.model, g.port) == ("axeos", "bitaxe", "Bitaxe Gamma", p1)
    assert (g.mac, g.identity, g.key) == (MAC_A, f"mac:{MAC_A}", f"127.0.0.1:{p1}")
    assert (g.hostname, g.firmware, g.serial) == ("sim-gamma", "v2.12.0", None)
    assert g.hashrate_hs == pytest.approx(1.15e12, rel=0.1)
    assert g.duplicate_of is None and g.already_added is None
    assert any("ESP-Miner" in line for line in g.evidence)

    n = miners["127.0.0.2"]
    assert (n.family, n.model, n.port, n.mac) == ("nerdqaxe", "NerdQAxe++", p2, MAC_B) and n.duplicate_of is None

    c = miners["127.0.0.3"]
    assert c.identity == g.identity and c.duplicate_of == "127.0.0.1" and c.port == p3  # listed, but marked as the same miner

    a = miners["127.0.0.4"]
    assert (a.driver, a.family, a.model, a.port, a.mac) == ("cgminer", "avalon", "Avalon Nano 3", p4, None)
    assert a.serial == "0123456789abcdef" and a.identity == "serial:0123456789abcdef" and a.hashrate_hs == pytest.approx(3.9e12, rel=0.05)
    assert a.firmware == "4.11.1"

    # discovery only ever reads from a miner
    for sim in (gamma, nerd, clone):
        assert {(method, path) for method, path, _ in sim.calls} <= {("GET", "/api/system/info"), ("GET", "/api/system/asic")}
    asked = {c for c in nano.commands if c and " " not in c}  # (the rest are bare connections and the AxeOS probe's HTTP request)
    assert {"version", "estats"} <= asked <= {"version", "estats", "summary", "pools"}

    # the UI/API view of the job
    as_dict = job.as_dict()
    assert as_dict["progress"] == 1.0 and as_dict["status"] == "finished" and len(as_dict["miners"]) == 4
    assert as_dict["miners"][0].keys() >= {"host", "port", "driver", "model", "identity", "already_added", "duplicate_of", "key", "evidence"}
    json.dumps(as_dict)

    # and the live stream saw it through to the end
    messages = []
    while not sub.queue.empty():
        messages.append(sub.queue.get_nowait().data)
    sub.close()
    assert messages[-1]["status"] == "finished" and messages[-1]["phase"] == "done" and len(messages[-1]["miners"]) == 4
    phases = [m["phase"] for m in messages]
    assert "identifying" in phases and "looking for your node" not in phases  # include_sources=False
    counts = [len(m["miners"]) for m in messages]
    assert counts == sorted(counts)  # the list only ever grows

    # adopting: everything new, once; the second address of the Gamma is not added again
    results = await ctx.discovery.adopt(job.id, tags=["lab"])
    assert sorted(r.device.host for r in results) == ["127.0.0.1", "127.0.0.2", "127.0.0.4"] and all(r.created for r in results)
    stored = {d.host: d for d in await ctx.store.list_devices()}
    assert all(d.tags == ["lab"] for d in stored.values()) and stored["127.0.0.1"].mac == MAC_A and stored["127.0.0.1"].port == p1
    assert stored["127.0.0.4"].driver == "cgminer" and stored["127.0.0.4"].serial == "0123456789abcdef"
    assert len(ctx.fleet.views()) == 3 and len(await events_of(ctx, "device_added")) == 3
    again = await ctx.discovery.adopt(job.id)  # adopting the same results twice changes nothing
    assert len(again) == 3 and all(r.created is False for r in again) and len(ctx.fleet.views()) == 3

    # a second scan recognises what is already monitored (and still sees the clone as the same box)
    job2 = ctx.discovery.start(["127.0.0.0/29"], ports=[p1, p2, p3, p4, decoy], include_sources=False)
    await finish(job2)
    flags = {m.host: m.already_added for m in job2.miners}
    ids = {d.host: d.id for d in stored.values()}
    assert flags == {"127.0.0.1": ids["127.0.0.1"], "127.0.0.2": ids["127.0.0.2"], "127.0.0.3": ids["127.0.0.1"], "127.0.0.4": ids["127.0.0.4"]}
    assert await ctx.discovery.adopt(job2.id) == []  # nothing new
    assert await ctx.discovery.adopt(job2.id, keys=[]) == []  # an explicit empty selection means none, not all
    [merged] = await ctx.discovery.adopt(job2.id, keys=[f"127.0.0.3:{p3}"])  # explicitly asking for the duplicate
    assert merged.created is False and merged.merged is True and "also answers on 127.0.0.3" in (merged.note or "")
    assert ctx.fleet.runtimes[ids["127.0.0.1"]].device.alt_hosts == ["127.0.0.3"] and len(ctx.fleet.views()) == 3


async def test_two_ports_of_the_same_host_make_one_candidate(ctx, lab, loopback):
    _, p1 = await lab.axeos("127.0.0.1", mac=MAC_A)
    _, p2 = await lab.axeos("127.0.0.1", mac=MAC_A, seed=2)  # (a simulator on a second port, same hardware identity)
    job = ctx.discovery.start(["127.0.0.1/32"], ports=[p1, p2], include_sources=False)
    await finish(job)
    [m] = job.miners  # one miner per address: the best match across its ports
    assert m.host == "127.0.0.1" and m.port in (p1, p2) and m.duplicate_of is None


async def test_a_miner_that_is_already_monitored_is_flagged_before_adopting(ctx, lab, loopback):
    _, port = await lab.axeos("127.0.0.1", mac=MAC_A)
    added = await ctx.fleet.add_by_host("127.0.0.1", port, drivers=["axeos"], name="Garage")
    job = ctx.discovery.start(["127.0.0.1/32"], ports=[port], include_sources=False)
    await finish(job)
    [m] = job.miners
    assert m.already_added == added.device.id
    assert await ctx.discovery.adopt(job.id) == []
    [res] = await ctx.discovery.adopt(job.id, keys=[m.key])
    assert res.created is False and res.device.id == added.device.id and "already being monitored" in (res.note or "")


async def test_non_miners_and_empty_ranges_produce_no_candidates(ctx, lab, loopback):
    require_loopback("127.0.0.2")
    decoy = await lab.decoy("127.0.0.2")
    job = ctx.discovery.start(["127.0.0.0/30"], ports=[decoy], include_sources=False)  # 127.0.0.1 and 127.0.0.2
    await finish(job)
    assert (job.status, job.miners, job.sources, job.total_hosts, job.scanned_hosts) == ("finished", [], [], 2, 2)
    assert job.as_dict()["progress"] == 1.0


async def test_the_scanner_never_scans_the_machine_it_runs_on(ctx, monkeypatch):
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", lambda: {"127.0.0.1", "192.168.9.15"})
    job = ctx.discovery.start(["192.168.9.15/32"], include_sources=False)
    assert job.total_hosts == 0  # this address is ours: skipped
    await finish(job)
    assert job.status == "finished" and job.miners == [] and job.as_dict()["progress"] == 1.0


async def test_an_explicit_loopback_request_is_honoured(ctx, monkeypatch):
    """A node or pool on the same computer is a normal setup, so asking for 127.0.0.1 must scan it."""
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", lambda: {"127.0.0.1", "192.168.9.15"})
    job = ctx.discovery.start(["127.0.0.1/32"], include_sources=False)
    assert job.total_hosts == 1
    await finish(job)


# --- scanning rules: private ranges only, bounded size --------------------------------------------------------------------------


async def test_public_address_ranges_are_refused(ctx):
    for cidr in ("8.8.8.0/24", "1.1.1.1/32", "93.184.216.0/30", "172.15.0.0/24", "172.32.0.0/24", "192.169.0.0/24"):
        with pytest.raises(ValueError, match="is not a private network"):
            ctx.discovery.start([cidr])
    with pytest.raises(ValueError, match=r"8\.8\.4\.0/30 is not a private network"):
        ctx.discovery.start(["10.0.0.0/30", "8.8.4.0/30"])  # one bad range spoils the lot
    assert ctx.discovery.jobs == {}  # and nothing was started


@pytest.mark.parametrize("cidr", ["10.1.2.0/24", "172.16.5.0/24", "172.31.255.0/24", "192.168.1.0/24", "100.64.1.0/24", "169.254.7.0/24",
                                  "127.0.0.0/24"])
def test_home_and_lab_ranges_are_private(cidr):
    assert all(is_private_host(h) for h in list(iter_hosts(cidr))[:3])


@pytest.mark.parametrize(("host", "private"), [
    ("192.168.1.9", True), ("10.0.0.1", True), ("8.8.8.8", False), ("umbrel.local", True), ("printer.lan", True), ("nas", True),
    ("mempool.space", False), ("solo.ckpool.org", False), ("fe80::1", True), ("2606:4700:4700::1111", False),
])
def test_is_private_host(host, private):
    assert is_private_host(host) is private


async def test_a_public_range_can_be_scanned_only_when_explicitly_allowed(ctx, tcp):
    with pytest.raises(ValueError, match="is not a private network"):
        ctx.discovery.start(["8.8.4.0/30"], include_sources=False)
    job = ctx.discovery.start(["8.8.4.0/30"], allow_public=True, include_sources=False)  # (the TCP sweep is faked: nothing is contacted)
    await finish(job)
    assert job.total_hosts == 2 and job.status == "finished"
    assert {h for h, _ in tcp.calls} == {"8.8.4.1", "8.8.4.2"}


@pytest.mark.parametrize(
    ("cidrs", "message"),
    [
        (["10.0.0.0/19"], r"has 8190 addresses; scanning more than 4096 at once is not allowed"),
        (["10.0.0.0/8"], r"scanning more than 4096"),
        (["banana"], r"'banana' is not a valid network"),
        (["10.0.0.0/33"], r"is not a valid network"),
        (["fe80::/64"], r"only IPv4 ranges can be scanned"),
    ],
)
async def test_oversize_and_malformed_ranges_are_refused(ctx, tcp, cidrs, message):
    with pytest.raises(ValueError, match=message):
        ctx.discovery.start(cidrs, allow_public=True)  # the size/shape limits apply even when public ranges are allowed
    assert ctx.discovery.jobs == {}


def test_iter_hosts_edges():
    assert list(iter_hosts("10.0.0.5")) == ["10.0.0.5"]  # a bare address is a /32
    assert list(iter_hosts("10.0.0.4/31")) == ["10.0.0.4", "10.0.0.5"]
    assert list(iter_hosts(" 10.0.0.0/30 ")) == ["10.0.0.1", "10.0.0.2"]  # network and broadcast excluded
    assert list(iter_hosts("10.0.0.7/30")) == ["10.0.0.5", "10.0.0.6"]  # host bits are ignored
    assert len(list(iter_hosts("10.0.0.0/20"))) == 4094  # the largest range allowed
    with pytest.raises(ValueError, match="scanning more than 100"):
        list(iter_hosts("10.0.0.0/24", limit=100))


async def test_the_largest_allowed_range_is_accepted(ctx, stuck):
    job = ctx.discovery.start(["10.8.0.0/20"], include_sources=False)  # 4094 addresses: right at the limit
    assert job.total_hosts == 4094 and job.status == "running"
    ctx.discovery.cancel(job.id)


async def test_extra_ports_are_cleaned_up_and_capped(ctx, tcp):
    job = ctx.discovery.start(["10.7.7.5/32"], ports=[0, -5, 70000, 80, 4028, 8080, 8080, 9000, "9001"], include_sources=False)  # type: ignore[list-item]
    await finish(job)
    assert {p for _, p in tcp.calls} == set(SWEEP_PORTS) | {8080, 9000, 9001}  # junk, the standard miner ports and duplicates dropped
    with pytest.raises(ValueError, match="at most 8 extra ports"):
        ctx.discovery.start(["10.7.7.5/32"], ports=list(range(9001, 9010)))
    tcp.calls.clear()
    job = ctx.discovery.start(["10.7.7.5/32"], ports=list(range(9001, 9009)), include_sources=False)  # exactly 8 is fine
    await finish(job)
    assert {p for _, p in tcp.calls} == set(SWEEP_PORTS) | set(range(9001, 9009))


async def test_the_default_range_comes_from_the_networks_this_computer_is_on(ctx, tcp, monkeypatch):
    nets = [ipaddress.ip_network(n) for n in ("10.7.7.0/29", "10.8.8.0/29", "10.9.9.0/29")]
    monkeypatch.setattr(discovery_mod, "local_ipv4_networks", lambda: nets)
    assert ctx.discovery.suggest_cidrs() == ["10.7.7.0/29", "10.8.8.0/29", "10.9.9.0/29"]
    job = ctx.discovery.start(include_sources=False)
    await finish(job)
    assert job.cidrs == ["10.7.7.0/29", "10.8.8.0/29"]  # the first two, to keep the scan short
    assert job.total_hosts == 12


def test_suggest_cidrs(monkeypatch):
    svc = DiscoveryService(None, None, None, None, None)  # type: ignore[arg-type]
    monkeypatch.setattr(discovery_mod, "local_ipv4_networks", lambda: [])
    assert svc.suggest_cidrs() == ["192.168.1.0/24", "192.168.0.0/24", "192.168.9.0/24", "10.0.0.0/24"]  # e.g. Docker bridge networking
    monkeypatch.undo()
    real = svc.suggest_cidrs()
    assert real and all(ipaddress.ip_network(c).prefixlen >= 24 and is_private_host(str(ipaddress.ip_network(c).network_address + 1)) for c in real)


# --- job control -------------------------------------------------------------------------------------------------------------------


@pytest.fixture
def stuck(monkeypatch):
    """A TCP sweep that never returns until released, so a job stays 'running' for as long as the test wants."""
    gate = asyncio.Event()

    async def hang(host: str, port: int, timeout: float = 1.0) -> bool:
        await gate.wait()
        return False

    monkeypatch.setattr(discovery_mod, "tcp_open", hang)
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", set)
    yield gate
    gate.set()


async def test_only_one_scan_runs_at_a_time_and_it_can_be_cancelled(ctx, stuck):
    job = ctx.discovery.start(["10.7.7.0/30"], include_sources=False)
    await asyncio.sleep(0.05)
    assert job.status == "running" and job.phase == "sweeping"
    assert ctx.discovery.start(["10.9.9.0/29"]) is job  # asking again while one runs hands back the running one
    sub = ctx.bus.subscribe({"discovery"})
    assert ctx.discovery.cancel(job.id) is True
    assert job.status == "cancelled" and job.phase == "cancelled" and job.finished_at is not None
    await finish(job, timeout=5)
    assert job.status == "cancelled" and job.phase == "cancelled" and job.finished_at is not None
    assert sub.queue.qsize() >= 1 and sub.queue.get_nowait().data["status"] == "cancelled"  # listeners are told
    sub.close()
    assert ctx.discovery.cancel(job.id) is False  # already over
    assert ctx.discovery.cancel("scan_nope") is False
    nxt = ctx.discovery.start(["10.7.7.0/30"], include_sources=False)  # a new scan may start now
    assert nxt is not job and nxt.status == "running"


async def test_cancelling_before_the_scan_has_started_is_clean(ctx, stuck):
    job = ctx.discovery.start(["10.7.7.0/30"], include_sources=False)
    assert ctx.discovery.cancel(job.id) is True  # the task has not even begun
    await finish(job, timeout=5)
    assert job.status == "cancelled" and job.miners == []


async def test_a_scan_that_crashes_reports_why_and_does_not_block_the_next_one(ctx, tcp, monkeypatch):
    tcp.open.add(("10.7.7.2", 80))

    async def kaput(*args, **kwargs):
        raise RuntimeError("kaput")

    monkeypatch.setattr(discovery_mod, "probe_host", kaput)
    job = ctx.discovery.start(["10.7.7.0/30"], include_sources=False)
    await finish(job)
    assert (job.status, job.phase, job.error) == ("failed", "failed", "RuntimeError: kaput")
    assert job.finished_at is not None and job.as_dict()["error"] == "RuntimeError: kaput"
    nxt = ctx.discovery.start(["10.7.7.0/30"], include_sources=False)
    assert nxt is not job
    await finish(nxt)


async def test_only_the_five_most_recent_scans_are_remembered(ctx, monkeypatch):
    monkeypatch.setattr(discovery_mod, "own_ipv4_addresses", lambda: {"10.7.7.1"})  # every scan is empty and instant
    ids = []
    for _ in range(7):
        job = ctx.discovery.start(["10.7.7.1/32"], include_sources=False)
        await finish(job)
        ids.append(job.id)
    assert list(ctx.discovery.jobs) == ids[2:]


def test_job_progress_is_scanned_over_total():
    job = DiscoveryJob(id="scan_x", cidrs=["10.0.0.0/24"], total_hosts=6, scanned_hosts=3)
    assert job.as_dict()["progress"] == 0.5
    empty = DiscoveryJob(id="scan_y", cidrs=[])
    assert empty.as_dict()["progress"] == 0.0  # nothing known yet
    empty.status = "finished"
    assert empty.as_dict()["progress"] == 1.0  # nothing to scan is a finished scan
    assert "_probes" not in empty.as_dict() and "_task" not in empty.as_dict()


async def test_adopting_from_an_unknown_scan_raises(ctx):
    with pytest.raises(KeyError):
        await ctx.discovery.adopt("scan_nope")


# --- duplicates and identities, as pure functions ----------------------------------------------------------------------------------


def cand(host: str, identity: str, port: int = 80) -> MinerCandidate:
    return MinerCandidate(host=host, port=port, driver="axeos", family="bitaxe", model="m", mac=None, serial=None, firmware=None,
                          hostname=None, identity=identity, hashrate_hs=None, evidence=[], key=f"{host}:{port}")


def test_the_lowest_address_is_the_original_and_the_rest_are_duplicates():
    job = DiscoveryJob(id="scan_x", cidrs=[])
    job.miners = [cand("10.0.0.252", "mac:A"), cand("10.0.0.88", "mac:A"), cand("10.0.0.9", "mac:A"), cand("10.0.0.50", "mac:B")]
    DiscoveryService._mark_duplicates(job)
    assert {m.host: m.duplicate_of for m in job.miners} == {"10.0.0.252": "10.0.0.9", "10.0.0.88": "10.0.0.9", "10.0.0.9": None, "10.0.0.50": None}


def test_miners_without_a_hardware_identity_are_never_called_duplicates():
    job = DiscoveryJob(id="scan_x", cidrs=[])
    job.miners = [cand("10.0.0.5", "host:10.0.0.5:80"), cand("10.0.0.5", "host:10.0.0.5:80", port=8080), cand("miner.local", "serial:S1"),
                  cand("10.0.0.7", "serial:S1")]
    DiscoveryService._mark_duplicates(job)
    assert [m.duplicate_of for m in job.miners] == [None, None, None, "miner.local"]  # a host name sorts before any address


def test_identity_helpers():
    dev = Device(id="d", name="n", driver="axeos", family="bitaxe", model="m", host="10.0.0.5", port=80)
    assert _identity_of(dev) == "host:10.0.0.5:80"
    assert _identity_of(dev.model_copy(update={"serial": "SN1"})) == "serial:SN1"
    assert _identity_of(dev.model_copy(update={"serial": "SN1", "mac": "aa:bb:cc:00:00:11"})) == "mac:AA:BB:CC:00:00:11"
    assert [_is_ip(h) for h in ("10.0.0.5", "::1", "miner.local", "10.0.0", "")] == [True, True, False, False, False]


def test_candidate_dicts_carry_every_field():
    assert cand("10.0.0.5", "mac:A").as_dict().keys() == set(MinerCandidate.__dataclass_fields__)
    sc = SourceCandidate("bitcoin_core", "http://10.0.0.5:8332", "Bitcoin node", True, "because", False)
    assert sc.as_dict() == {"kind": "bitcoin_core", "url": "http://10.0.0.5:8332", "name": "Bitcoin node", "needs_credentials": True,
                            "reason": "because", "verified": False}


# --- finding the node, the pool and the mempool ---------------------------------------------------------------------------------------


async def test_a_scan_also_finds_the_node_pool_and_mempool_on_the_lan(lan, tcp):
    ctx, hosts = lan
    sim = AxeOSSim("gamma", seed=1, mac=MAC_A, pool=("10.7.7.4", 2018, f"{ADDR}.gamma"))  # mines to 10.7.7.4:2018
    hosts["10.7.7.2"] = sim.app()
    hosts["10.7.7.3"] = site({})  # port 3334 is open but it is not a pool
    hosts["10.7.7.4"] = public_pool_site()  # Umbrel: Public Pool's API on 2019
    hosts["10.7.7.6"] = site({"/api/blocks/tip/height": "972175"})  # a mempool explorer on 3006
    tcp.open |= {("10.7.7.2", 80), ("10.7.7.3", 3334), ("10.7.7.4", 2019), ("10.7.7.4", 8332), ("10.7.7.5", 8332), ("10.7.7.6", 3006)}
    try:
        job = ctx.discovery.start(["10.7.7.0/29"])
        await finish(job)
        assert job.status == "finished" and [m.host for m in job.miners] == ["10.7.7.2"] and job.miners[0].port == 80
        found = {(s.kind, s.url): s for s in job.sources}
        assert set(found) == {
            ("public_pool", "http://10.7.7.4:2019"), ("bitcoin_core", "http://10.7.7.4:8332"),
            ("bitcoin_core", "http://10.7.7.5:8332"), ("mempool_space", "http://10.7.7.6:3006"),
        }
        pool = found[("public_pool", "http://10.7.7.4:2019")]
        assert (pool.name, pool.needs_credentials, pool.verified, pool.reason) == (
            "Public Pool on 10.7.7.4", False, True, "Your miners are mining to 10.7.7.4:2018")
        near = found[("bitcoin_core", "http://10.7.7.4:8332")]  # the node next to the pool the miners use
        assert (near.name, near.needs_credentials, near.verified) == ("Bitcoin node on 10.7.7.4", True, False)
        assert near.reason == "Your miners are mining to 10.7.7.4:2018; a node answers on port 8332"
        stray = found[("bitcoin_core", "http://10.7.7.5:8332")]
        assert (stray.name, stray.needs_credentials, stray.verified, stray.reason) == (
            "Bitcoin node on 10.7.7.5", True, False, "Port 8332 (Bitcoin RPC) is open")
        mempool = found[("mempool_space", "http://10.7.7.6:3006")]
        assert (mempool.name, mempool.needs_credentials, mempool.verified, mempool.reason) == (
            "mempool on 10.7.7.6", False, True, "A mempool explorer answers here")
        assert len(job.sources) == 4  # (the pool's address is reached by two routes but listed once)
        assert [s["kind"] for s in job.as_dict()["sources"]].count("bitcoin_core") == 2
    finally:
        await _cancel_jobs(ctx)


async def test_a_node_is_not_hidden_by_another_node_whose_address_merely_starts_the_same_way(lan, tcp):
    ctx, hosts = lan
    hosts["10.7.7.2"] = AxeOSSim("gamma", seed=1, mac=MAC_A, pool=("10.7.7.40", 2018, f"{ADDR}.gamma")).app()  # mines to a pool outside the range
    hosts["10.7.7.40"] = site({})
    tcp.open |= {("10.7.7.2", 80), ("10.7.7.4", 8332), ("10.7.7.40", 8332)}  # a node next to that pool, and a different one at .4
    try:
        job = ctx.discovery.start(["10.7.7.0/29"])
        await finish(job)
        nodes = [s.url for s in job.sources if s.kind == "bitcoin_core"]
        assert len(nodes) == 2 and set(nodes) == {"http://10.7.7.4:8332", "http://10.7.7.40:8332"}
    finally:
        await _cancel_jobs(ctx)


async def test_miners_you_already_monitor_point_the_scan_at_your_pool_even_outside_the_scanned_range(lan, tcp):
    ctx, hosts = lan
    hosts["10.7.7.2"] = AxeOSSim("gamma", seed=1, mac=MAC_A, pool=("umbrel.local", 2018, f"{ADDR}.gamma")).app()
    res = await ctx.fleet.add_by_host("10.7.7.2", drivers=["axeos"])
    await ctx.fleet._poll_once(ctx.fleet.runtimes[res.device.id])  # now the fleet knows where this miner mines
    hosts["umbrel.local"] = public_pool_site()
    tcp.open.add(("umbrel.local", 8332))  # ... and a node answers there too
    job = ctx.discovery.start(["10.9.9.0/30"])  # nothing at all lives in the range being scanned
    await finish(job)
    assert job.miners == []
    # (no port was seen open, so both of Public Pool's usual API ports are tried; the simulated host answers on either)
    assert {(s.kind, s.url, s.verified) for s in job.sources} == {
        ("public_pool", "http://umbrel.local:2019", True), ("public_pool", "http://umbrel.local:3334", True),
        ("bitcoin_core", "http://umbrel.local:8332", False)}
    assert ("umbrel.local", 8332) in tcp.calls  # likewise the node port was asked about directly


async def test_a_pool_on_the_internet_is_never_probed(lan, tcp):
    ctx, hosts = lan
    spy = AxeOSSim("gamma", seed=9, mac=MAC_B)
    hosts["solo.ckpool.org"] = spy.app()  # would answer, if anyone asked
    hosts["10.7.7.2"] = AxeOSSim("gamma", seed=1, mac=MAC_A, pool=("solo.ckpool.org", 3333, f"{ADDR}.gamma")).app()
    tcp.open.add(("10.7.7.2", 80))
    job = ctx.discovery.start(["10.7.7.0/30"])
    await finish(job)
    assert [m.host for m in job.miners] == ["10.7.7.2"] and job.sources == []
    assert spy.calls == [] and not any(h == "solo.ckpool.org" for h, _ in tcp.calls)


async def test_a_port_that_is_open_but_not_a_mempool_explorer_is_ignored(lan, tcp):
    ctx, hosts = lan
    hosts["10.7.7.3"] = site({})  # answers, but with a 404
    hosts["10.7.7.4"] = site({"/api/blocks/tip/height": "not a number"})
    tcp.open |= {("10.7.7.1", 3006), ("10.7.7.3", 3006), ("10.7.7.4", 3006)}  # (10.7.7.1 does not answer at all)
    job = ctx.discovery.start(["10.7.7.0/29"])
    await finish(job)
    assert job.status == "finished" and job.sources == []


async def test_a_host_answering_on_both_standard_ports_is_listed_once_as_its_best_match(lan, tcp, monkeypatch):
    from bsmm.models import DeviceInfo, ProbeResult

    ctx, _ = lan

    def result(driver: str, host: str, port: int, confidence: float, model: str) -> ProbeResult:
        info = DeviceInfo(driver=driver, family="x", model=model, host=host, port=port)
        return ProbeResult(info=info, confidence=confidence)

    asked: list[tuple[str, int | None, tuple[str, ...]]] = []

    async def fake_probe(host, port=None, *, client, timeout=4.0, drivers=None):
        asked.append((host, port, tuple(drivers or ())))
        if port == 80:
            return [result("axeos", host, 80, 0.98, "AxeOS box")]
        return [result("cgminer", host, 4028, 0.7, "Plain cgminer")]

    monkeypatch.setattr(discovery_mod, "probe_host", fake_probe)
    tcp.open |= {("10.7.7.2", 80), ("10.7.7.2", 4028), ("10.7.7.3", 4028)}
    job = ctx.discovery.start(["10.7.7.0/29"], include_sources=False)
    await finish(job)
    assert {m.host: (m.driver, m.port, m.model) for m in job.miners} == {
        "10.7.7.2": ("axeos", 80, "AxeOS box"), "10.7.7.3": ("cgminer", 4028, "Plain cgminer")}
    # each standard port is asked only about the family that lives there
    assert sorted(asked) == [("10.7.7.2", 80, ("axeos",)), ("10.7.7.2", 4028, ("cgminer",)), ("10.7.7.3", 4028, ("cgminer",))]


async def test_adopt_skips_a_candidate_whose_probe_result_is_gone(ctx):
    job = DiscoveryJob(id="scan_x", cidrs=[])
    job.miners = [cand("10.0.0.5", "mac:A")]
    ctx.discovery.jobs[job.id] = job
    assert await ctx.discovery.adopt(job.id) == [] and await ctx.discovery.adopt(job.id, keys=["10.0.0.5:80"]) == []


async def test_no_candidates_when_include_sources_is_off(lan, tcp):
    ctx, hosts = lan
    hosts["10.7.7.4"] = public_pool_site()
    tcp.open |= {("10.7.7.4", 2019), ("10.7.7.4", 8332)}
    job = ctx.discovery.start(["10.7.7.0/29"], include_sources=False)
    await finish(job)
    assert job.sources == [] and job.phase == "done"


async def test_a_quiet_range_finishes_with_nothing_found(lan, tcp):
    ctx, _ = lan
    job = ctx.discovery.start(["10.7.7.0/29"])
    await finish(job)
    assert (job.status, job.miners, job.sources, job.total_hosts, job.scanned_hosts) == ("finished", [], [], 6, 6)
    assert {h for h, _ in tcp.calls} == {f"10.7.7.{i}" for i in range(1, 7)}
    assert {p for _, p in tcp.calls} == set(SWEEP_PORTS)


def test_the_node_ports_are_the_well_known_ones():
    assert set(NODE_PORTS) == {8332, 2019, 3334, 3006}  # bitcoin RPC, Public Pool API (2), mempool explorer


# --- healing devices that changed address --------------------------------------------------------------------------------------------------


async def lost_miner(ctx, sim_port: int, mac: str = MAC_A, old_host: str = "127.0.0.5", name: str = "Garage"):
    """Register a miner at an address where nothing listens, and let the fleet discover it is offline (real refused connections)."""
    probe = (await probe_host("127.0.0.1", sim_port, client=ctx.http, drivers=["axeos"]))[0]
    stale = probe.model_copy(update={"info": probe.info.model_copy(update={"host": old_host, "port": 80, "mac": mac})})
    res = await ctx.fleet.add_from_probe(stale, name=name)
    rt = ctx.fleet.runtimes[res.device.id]
    for _ in range(3):
        await ctx.fleet._poll_once(rt)
    assert rt.status == DeviceStatus.OFFLINE
    return rt


@pytest.fixture
def standard_ports_are_the_simulators(monkeypatch):
    """The healing scan looks on the standard miner ports only; point it at an ephemeral port instead (set per test)."""

    def apply(port: int) -> None:
        monkeypatch.setattr(AxeOSDriver, "probe_ports", (port,))
        monkeypatch.setattr(discovery_mod, "MINER_PORTS", (port, 4028))

    return apply


async def test_a_miner_that_changed_address_is_found_again_by_its_identity(ctx, standard_ports_are_the_simulators):
    sim = AxeOSSim("gamma", seed=1, mac=MAC_A)
    async with serve(sim.app()) as base:  # type: ignore[arg-type]
        port = int(base.rsplit(":", 1)[1])
        standard_ports_are_the_simulators(port)
        rt = await lost_miner(ctx, port)
        assert (rt.device.host, rt.device.port) == ("127.0.0.5", 80)

        moved = await ctx.discovery.heal_moved_devices(min_offline_s=0)

        assert moved == [rt.device.id]
        assert (rt.device.host, rt.device.port) == ("127.0.0.1", port) and rt.device.alt_hosts == ["127.0.0.5"]
        assert rt.driver is None and rt.wake.is_set()  # next poll builds a driver for the new address
        stored = await ctx.store.get_device(rt.device.id)
        assert (stored.host, stored.port, stored.alt_hosts) == ("127.0.0.1", port, ["127.0.0.5"])
        [ev] = await events_of(ctx, "device_moved")
        assert ev.title == "Garage moved from 127.0.0.5 to 127.0.0.1" and ev.severity == Severity.INFO and ev.device_id == rt.device.id
        assert ev.body == "Found it again by its hardware identity after a DHCP change."
        await ctx.fleet._poll_once(rt)  # and it really is reachable there
        assert rt.status == DeviceStatus.ONLINE and rt.telemetry is not None and rt.telemetry.hashrate_hs
        assert await ctx.discovery.heal_moved_devices(min_offline_s=0) == []  # it is online now: nothing more to do


async def test_healing_waits_until_a_miner_has_been_offline_long_enough(ctx, standard_ports_are_the_simulators, monkeypatch):
    sim = AxeOSSim("gamma", seed=1, mac=MAC_A)
    async with serve(sim.app()) as base:  # type: ignore[arg-type]
        port = int(base.rsplit(":", 1)[1])
        standard_ports_are_the_simulators(port)
        rt = await lost_miner(ctx, port)
        real = discovery_mod.tcp_open
        probed: list[tuple[str, int]] = []

        async def spy(host, p, timeout=1.0):
            probed.append((host, p))
            return await real(host, p, timeout)

        monkeypatch.setattr(discovery_mod, "tcp_open", spy)
        assert await ctx.discovery.heal_moved_devices() == []  # default: five minutes
        assert await ctx.discovery.heal_moved_devices(min_offline_s=3600) == []
        assert probed == [] and rt.device.host == "127.0.0.5"  # no scan was even started
        rt.status_since -= 301  # it has now been gone for just over five minutes
        assert await ctx.discovery.heal_moved_devices() == [rt.device.id]
        assert probed  # (the default threshold is 300 seconds)


async def test_a_miner_that_is_nowhere_to_be_found_stays_as_it_was(ctx, standard_ports_are_the_simulators):
    other = AxeOSSim("gamma", seed=2, mac=MAC_B)  # a different box answers on the network
    async with serve(other.app()) as base:  # type: ignore[arg-type]
        port = int(base.rsplit(":", 1)[1])
        standard_ports_are_the_simulators(port)
        rt = await lost_miner(ctx, port, mac=MAC_A)  # the lost miner is MAC_A; only MAC_B is out there
        assert await ctx.discovery.heal_moved_devices(min_offline_s=0) == []
        assert (rt.device.host, rt.device.alt_hosts, rt.status) == ("127.0.0.5", [], DeviceStatus.OFFLINE)
        assert await events_of(ctx, "device_moved") == []


async def test_only_the_miner_whose_identity_matches_is_moved(ctx, standard_ports_are_the_simulators):
    sim = AxeOSSim("gamma", seed=1, mac=MAC_A)
    async with serve(sim.app()) as base:  # type: ignore[arg-type]
        port = int(base.rsplit(":", 1)[1])
        standard_ports_are_the_simulators(port)
        mine = await lost_miner(ctx, port, mac=MAC_A, old_host="127.0.0.5", name="Mine")
        yours = await lost_miner(ctx, port, mac=MAC_B, old_host="127.0.0.6", name="Yours")
        moved = await ctx.discovery.heal_moved_devices(min_offline_s=0)
        assert moved == [mine.device.id]
        assert yours.device.host == "127.0.0.6" and yours.status == DeviceStatus.OFFLINE


async def test_a_miner_is_never_moved_onto_an_address_another_device_already_has(ctx, standard_ports_are_the_simulators):
    sim = AxeOSSim("gamma", seed=1, mac=MAC_A)
    async with serve(sim.app()) as base:  # type: ignore[arg-type]
        port = int(base.rsplit(":", 1)[1])
        standard_ports_are_the_simulators(port)
        rt = await lost_miner(ctx, port, mac=MAC_A)
        neighbour = Device(id="dev_other", name="Other", driver="axeos", family="bitaxe", model="m", host="127.0.0.1", port=8080, mac=MAC_B)
        await ctx.store.save_device(neighbour, create=True)
        ctx.fleet._spawn(neighbour)  # another monitored device already lives on the address where the identity turns up
        assert await ctx.discovery.heal_moved_devices(min_offline_s=0) == []
        assert rt.device.host == "127.0.0.5" and await events_of(ctx, "device_moved") == []


async def test_demo_miners_and_host_names_are_not_healed(ctx, monkeypatch):
    seen: list[tuple[str, int]] = []

    async def spy(host, port, timeout=1.0):
        seen.append((host, port))
        return False

    monkeypatch.setattr(discovery_mod, "tcp_open", spy)
    old = time.time() - 10_000
    for dev_id, driver, host in (("dev_demo", "sim", "10.0.0.5"), ("dev_named", "axeos", "miner.local")):
        dev = Device(id=dev_id, name=dev_id, driver=driver, family="bitaxe", model="m", host=host, port=80, mac=MAC_A)
        await ctx.store.save_device(dev, create=True)
        rt = ctx.fleet._spawn(dev)
        rt.status, rt.status_since = DeviceStatus.OFFLINE, old
    assert await ctx.discovery.heal_moved_devices(min_offline_s=0) == []
    assert seen == []  # a demo device has no real address, and a host name has no subnet to look in


async def test_healing_ignores_miners_that_are_online(ctx):
    dev = Device(id="dev_ok", name="ok", driver="axeos", family="bitaxe", model="m", host="127.0.0.9", port=80, mac=MAC_A)
    await ctx.store.save_device(dev, create=True)
    rt = ctx.fleet._spawn(dev)
    rt.status = DeviceStatus.ONLINE
    assert await ctx.discovery.heal_moved_devices(min_offline_s=0) == []

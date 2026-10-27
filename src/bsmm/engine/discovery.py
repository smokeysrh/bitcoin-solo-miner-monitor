"""Find miners (and the node / pool they mine to) on the local network.

Two phases keep it fast and polite: a quick TCP sweep of a few well-known ports, then a real
protocol probe only on hosts that answered. Results are de-duplicated by the device's own identity
(MAC / chip serial), which is what stops one miner that answers on two IP addresses from being
listed twice.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.cgminer import CgminerDriver
from bsmm.drivers.registry import probe_host
from bsmm.engine.bus import EventBus
from bsmm.engine.events import EventLog
from bsmm.engine.fleet import AddResult, Fleet
from bsmm.models import ProbeResult, Severity, Source
from bsmm.net import is_private_host, iter_hosts, local_ipv4_networks, own_ipv4_addresses, tcp_open
from bsmm.sources.base import SourceError
from bsmm.sources.public_pool import PublicPoolSource
from bsmm.storage.store import Store, new_id

log = logging.getLogger(__name__)

MINER_PORTS = (80, 4028)
NODE_PORTS = (8332, 2019, 3334, 3006)
SWEEP_PORTS = MINER_PORTS + NODE_PORTS


@dataclass(slots=True)
class MinerCandidate:
    host: str
    port: int
    driver: str
    family: str
    model: str
    mac: str | None
    serial: str | None
    firmware: str | None
    hostname: str | None
    identity: str
    hashrate_hs: float | None
    evidence: list[str]
    already_added: str | None = None  # device id
    duplicate_of: str | None = None  # host of the candidate this is a second address of
    key: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


@dataclass(slots=True)
class SourceCandidate:
    kind: str  # bitcoin_core | public_pool | mempool_space
    url: str
    name: str
    needs_credentials: bool = False
    reason: str = ""
    verified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {f: getattr(self, f) for f in self.__dataclass_fields__}


@dataclass(slots=True)
class DiscoveryJob:
    id: str
    cidrs: list[str]
    status: str = "running"  # running | finished | cancelled | failed
    phase: str = "starting"
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    total_hosts: int = 0
    scanned_hosts: int = 0
    miners: list[MinerCandidate] = field(default_factory=list)
    sources: list[SourceCandidate] = field(default_factory=list)
    error: str | None = None
    _probes: dict[str, ProbeResult] = field(default_factory=dict, repr=False)
    _task: asyncio.Task[None] | None = field(default=None, repr=False)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "cidrs": self.cidrs, "status": self.status, "phase": self.phase, "started_at": self.started_at,
            "finished_at": self.finished_at, "total_hosts": self.total_hosts, "scanned_hosts": self.scanned_hosts,
            "progress": (self.scanned_hosts / self.total_hosts) if self.total_hosts else (1.0 if self.status == "finished" else 0.0),
            "miners": [m.as_dict() for m in self.miners], "sources": [s.as_dict() for s in self.sources], "error": self.error,
        }


class DiscoveryService:
    def __init__(self, store: Store, bus: EventBus, events: EventLog, fleet: Fleet, http: httpx.AsyncClient) -> None:
        self.store = store
        self.bus = bus
        self.events = events
        self.fleet = fleet
        self.http = http
        self.jobs: dict[str, DiscoveryJob] = {}

    def suggest_cidrs(self) -> list[str]:
        cidrs = [str(n) for n in local_ipv4_networks()]
        if not cidrs:  # e.g. Docker bridge networking: we cannot see the LAN, so offer the usual suspects
            cidrs = ["192.168.1.0/24", "192.168.0.0/24", "192.168.9.0/24", "10.0.0.0/24"]
        return cidrs

    def start(self, cidrs: list[str] | None = None, *, allow_public: bool = False, include_sources: bool = True,
              ports: list[int] | None = None) -> DiscoveryJob:
        running = [j for j in self.jobs.values() if j.status == "running"]
        if running:
            return running[0]
        extra_ports = sorted({int(p) for p in (ports or []) if 1 <= int(p) <= 65535 and int(p) not in MINER_PORTS})
        if len(extra_ports) > 8:
            raise ValueError("Scan at most 8 extra ports at a time.")
        cidrs = cidrs or self.suggest_cidrs()[:2]
        hosts: list[str] = []
        for c in cidrs:
            part = list(iter_hosts(c))
            if not allow_public and not all(is_private_host(h) for h in part[:3] or part):
                raise ValueError(f"{c} is not a private network. Scanning public addresses is blocked (use a home/office range such as 192.168.1.0/24).")
            hosts.extend(part)
        # skip this computer's own LAN addresses (it is not a miner), but honour an explicit request for
        # loopback: that is how you find a Bitcoin node or pool running on the very same machine
        own = {a for a in own_ipv4_addresses() if not a.startswith("127.")}
        hosts = [h for h in dict.fromkeys(hosts) if h not in own]
        job = DiscoveryJob(id=new_id("scan"), cidrs=cidrs, total_hosts=len(hosts))
        self.jobs[job.id] = job
        job._task = asyncio.create_task(self._run(job, hosts, include_sources, extra_ports), name=f"discovery-{job.id}")
        for old in sorted(self.jobs.values(), key=lambda j: j.started_at)[:-5]:
            self.jobs.pop(old.id, None)
        return job

    def cancel(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job._task and job.status == "running":
            job._task.cancel()
            job.status, job.phase = "cancelled", "cancelled"
            job.finished_at = time.time()
            self._publish(job)
            return True
        return False

    def _publish(self, job: DiscoveryJob) -> None:
        self.bus.publish("discovery", job.as_dict())

    async def _run(self, job: DiscoveryJob, hosts: list[str], include_sources: bool, extra_ports: list[int] | None = None) -> None:
        extra = list(extra_ports or [])
        try:
            job.phase = "sweeping"
            open_ports: dict[str, set[int]] = {}
            sem = asyncio.Semaphore(500)
            last_pub = 0.0
            sweep = tuple(dict.fromkeys((*SWEEP_PORTS, *extra)))

            async def check(host: str) -> None:
                nonlocal last_pub
                found: set[int] = set()

                async def one(port: int) -> None:
                    async with sem:
                        if await tcp_open(host, port, 0.9):
                            found.add(port)

                await asyncio.gather(*(one(p) for p in sweep))
                if found:
                    open_ports[host] = found
                job.scanned_hosts += 1
                if time.monotonic() - last_pub > 0.4:
                    last_pub = time.monotonic()
                    self._publish(job)

            await asyncio.gather(*(check(h) for h in hosts))

            job.phase = "identifying"
            self._publish(job)
            probe_sem = asyncio.Semaphore(16)

            async def probe(host: str, ports: set[int]) -> None:
                async with probe_sem:
                    jobs = []
                    if 80 in ports:
                        jobs.append(probe_host(host, 80, client=self.http, timeout=4.0, drivers=[AxeOSDriver.name]))
                    if 4028 in ports:
                        jobs.append(probe_host(host, 4028, client=self.http, timeout=4.0, drivers=[CgminerDriver.name]))
                    for p in ports & set(extra):  # user-supplied ports: let every driver have a go
                        jobs.append(probe_host(host, p, client=self.http, timeout=4.0))
                    found: list[ProbeResult] = [r for batch in await asyncio.gather(*jobs) for r in batch]
                    found.sort(key=lambda r: r.confidence, reverse=True)
                    for res in found[:1]:
                        await self._add_candidate(job, res)

            miner_ports = set(MINER_PORTS) | set(extra)
            await asyncio.gather(*(probe(h, p) for h, p in open_ports.items() if p & miner_ports))
            self._mark_duplicates(job)

            if include_sources:
                job.phase = "looking for your node"
                self._publish(job)
                await self._find_sources(job, open_ports)
            job.status, job.phase = "finished", "done"
        except asyncio.CancelledError:
            job.status, job.phase = "cancelled", "cancelled"
            raise
        except Exception as e:
            log.exception("discovery failed")
            job.status, job.phase, job.error = "failed", "failed", f"{e.__class__.__name__}: {e}"
        finally:
            job.finished_at = time.time()
            self._publish(job)

    async def _add_candidate(self, job: DiscoveryJob, res: ProbeResult) -> None:
        info = res.info
        existing = await self.store.find_device(info)
        key = f"{info.host}:{info.port}"
        cand = MinerCandidate(
            host=info.host, port=info.port, driver=info.driver, family=info.family, model=info.model, mac=info.mac,
            serial=info.serial, firmware=info.firmware, hostname=info.hostname, identity=info.identity_key,
            hashrate_hs=res.telemetry.hashrate_hs if res.telemetry else None, evidence=res.evidence,
            already_added=existing.id if existing else None, key=key)
        job.miners.append(cand)
        job._probes[key] = res
        self._publish(job)

    @staticmethod
    def _mark_duplicates(job: DiscoveryJob) -> None:
        first: dict[str, MinerCandidate] = {}
        for m in sorted(job.miners, key=lambda c: ipaddress.ip_address(c.host) if _is_ip(c.host) else ipaddress.ip_address("0.0.0.0")):
            if m.identity.startswith("host:"):
                continue
            if m.identity in first:
                m.duplicate_of = first[m.identity].host
            else:
                first[m.identity] = m

    async def _find_sources(self, job: DiscoveryJob, open_ports: dict[str, set[int]]) -> None:
        # 1. where do the miners point? (found miners + miners we already monitor)
        pool_hosts: dict[str, str] = {}
        for res in job._probes.values():
            if res.telemetry:
                for p in res.telemetry.pools:
                    if p.url and p.active:
                        pool_hosts[p.url] = f"{p.url}:{p.port}"
        for v in self.fleet.views():
            if v.telemetry:
                ap = v.telemetry.active_pool()
                if ap and ap.url:
                    pool_hosts.setdefault(ap.url, f"{ap.url}:{ap.port}")
        seen: set[str] = set()

        async def try_public_pool(host: str, port: int, reason: str) -> None:
            url = f"http://{host}:{port}"
            if url in seen:
                return
            seen.add(url)
            src = PublicPoolSource(Source(id="probe", kind="public_pool", name="probe", url=url), {}, self.http, timeout=3.0)
            try:
                res = await src.test()
            except SourceError:
                return
            if res.ok:
                job.sources.append(SourceCandidate("public_pool", url, f"Public Pool on {host}", False, reason, True))

        for host, endpoint in pool_hosts.items():
            if not is_private_host(host):
                continue
            ports = open_ports.get(host) or set()
            for api_port in (2019, 3334):
                if api_port in ports or not ports:
                    await try_public_pool(host, api_port, f"Your miners are mining to {endpoint}")
            if 8332 in ports or await tcp_open(host, 8332, 0.8):
                job.sources.append(SourceCandidate("bitcoin_core", f"http://{host}:8332", f"Bitcoin node on {host}", True,
                                                   f"Your miners are mining to {endpoint}; a node answers on port 8332", False))
        # 2. anything else on the LAN that looks like a node, pool or mempool
        for host, ports in open_ports.items():
            if 8332 in ports and not any(s.kind == "bitcoin_core" and s.url == f"http://{host}:8332" for s in job.sources):
                job.sources.append(SourceCandidate("bitcoin_core", f"http://{host}:8332", f"Bitcoin node on {host}", True,
                                                   "Port 8332 (Bitcoin RPC) is open", False))
            for api_port in (2019, 3334):
                if api_port in ports:
                    await try_public_pool(host, api_port, "Public Pool's web/API port is open")
            if 3006 in ports:
                url = f"http://{host}:3006"
                try:
                    r = await self.http.get(f"{url}/api/blocks/tip/height", timeout=3.0)
                    if r.status_code == 200 and r.text.strip().isdigit():
                        job.sources.append(SourceCandidate("mempool_space", url, f"mempool on {host}", False, "A mempool explorer answers here", True))
                except httpx.HTTPError:
                    pass
        self._publish(job)

    # -- adopting results -------------------------------------------------------------------------------

    async def adopt(self, job_id: str, keys: list[str] | None = None, *, tags: list[str] | None = None) -> list[AddResult]:
        """Start monitoring discovered miners (``keys`` are ``host:port``; default: every new, non-duplicate one)."""
        job = self.jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        results: list[AddResult] = []
        for cand in job.miners:
            if keys is not None and cand.key not in keys:
                continue
            if keys is None and (cand.already_added or cand.duplicate_of):
                continue
            probe = job._probes.get(cand.key)
            if probe is None:
                continue
            results.append(await self.fleet.add_from_probe(probe, tags=tags))
        return results

    # -- IP changes ---------------------------------------------------------------------------------------

    async def heal_moved_devices(self, min_offline_s: float = 300.0) -> list[str]:
        """Offline for a while? Maybe DHCP gave it a new address: look for the same identity nearby."""
        now = time.time()
        lost = [v for v in self.fleet.views() if v.status.value == "offline" and v.driver != "sim"
                and v.status_since and now - v.status_since >= min_offline_s]
        if not lost:
            return []
        subnets: set[str] = set()
        for v in lost:
            if _is_ip(v.host):
                subnets.add(str(ipaddress.ip_network(f"{v.host}/24", strict=False)))
        moved: list[str] = []
        for cidr in subnets:
            hosts = [h for h in iter_hosts(cidr)]
            sem = asyncio.Semaphore(300)

            async def alive(h: str, sem: asyncio.Semaphore = sem) -> str | None:
                async with sem:
                    for p in MINER_PORTS:
                        if await tcp_open(h, p, 0.7):
                            return h
                return None

            candidates = [h for h in await asyncio.gather(*(alive(h) for h in hosts)) if h]
            for h in candidates:
                if any(h == v.host for v in self.fleet.views()):
                    continue
                for res in (await probe_host(h, client=self.http, timeout=3.0))[:1]:
                    for v in lost:
                        if res.info.identity_key == _identity_of(v) and v.host != h:
                            rt = self.fleet.runtimes[v.id]
                            old = rt.device.host
                            rt.device.host, rt.device.port = h, res.info.port
                            if old not in rt.device.alt_hosts:
                                rt.device.alt_hosts.append(old)
                            await self.store.save_device(rt.device)
                            rt.driver = None
                            rt.wake.set()
                            await self.events.emit("device_moved", f"{v.name} moved from {old} to {h}", severity=Severity.INFO,
                                                   device_id=v.id, body="Found it again by its hardware identity after a DHCP change.")
                            moved.append(v.id)
        return moved


def _identity_of(v: Any) -> str:
    if v.mac:
        return f"mac:{v.mac.upper()}"
    if v.serial:
        return f"serial:{v.serial}"
    return f"host:{v.host}:{v.port}"


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False

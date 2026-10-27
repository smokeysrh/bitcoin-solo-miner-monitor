"""In-process demo miners.

These run the *real* drivers (AxeOS HTTP / cgminer parsing) against the simulators, but over an
in-memory transport, so demo mode needs no network ports and exercises the same code paths as
production. Control actions work too, they just change the simulated device.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx

from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.base import Unreachable
from bsmm.drivers.cgminer import CgminerDriver
from bsmm.models import DeviceInfo, ProbeResult, Telemetry
from bsmm.sim.axeos import AxeOSSim
from bsmm.sim.cgminer import CgminerSim

_AXEOS: dict[str, AxeOSSim] = {}
_CGMINER: dict[str, CgminerSim] = {}


def reset_sims() -> None:
    _AXEOS.clear()
    _CGMINER.clear()


def get_axeos_sim(key: str, profile: str, seed: int | None, **kw: Any) -> AxeOSSim:
    if key not in _AXEOS:
        _AXEOS[key] = AxeOSSim(profile, seed=seed, **kw)
    return _AXEOS[key]


def get_cgminer_sim(key: str, profile: str, seed: int | None) -> CgminerSim:
    if key not in _CGMINER:
        _CGMINER[key] = CgminerSim(profile, seed=seed)
    return _CGMINER[key]


class SimAxeOSDriver(AxeOSDriver):
    name: ClassVar[str] = "sim"
    label: ClassVar[str] = "Demo miner (AxeOS)"
    probe_ports: ClassVar[tuple[int, ...]] = ()

    def __init__(self, host: str, port: int, *, info: DeviceInfo | None = None, timeout: float = 8.0, **_: Any) -> None:
        sim = _AXEOS.get(host)
        if sim is None:
            raise Unreachable("demo device is gone")
        self.sim = sim
        client = httpx.AsyncClient(transport=httpx.ASGITransport(app=sim.app()), timeout=timeout)
        super().__init__(host, port, client=client, timeout=timeout, info=info)

    @property
    def base(self) -> str:  # host is a demo key, not a real address
        return "http://sim"

    @classmethod
    async def probe(cls, *a: Any, **k: Any) -> ProbeResult | None:  # never discovered on a network
        return None

    async def close(self) -> None:
        await self.client.aclose()


class SimCgminerDriver(CgminerDriver):
    name: ClassVar[str] = "sim"
    label: ClassVar[str] = "Demo miner (cgminer)"
    probe_ports: ClassVar[tuple[int, ...]] = ()

    def __init__(self, host: str, port: int, *, info: DeviceInfo | None = None, timeout: float = 8.0, **_: Any) -> None:
        sim = _CGMINER.get(host)
        if sim is None:
            raise Unreachable("demo device is gone")
        self.sim = sim
        super().__init__(host, port, client=None, timeout=timeout, info=info)  # type: ignore[arg-type]

    async def _call(self, command: str) -> dict[str, Any]:
        return self.sim.reply(command)

    @classmethod
    async def probe(cls, *a: Any, **k: Any) -> ProbeResult | None:
        return None

    async def poll(self) -> Telemetry:
        t = await super().poll()
        return t

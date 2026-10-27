"""Finding the right driver: by stored device record, or by probing a host."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from bsmm.drivers.axeos import AxeOSDriver
from bsmm.drivers.base import Driver
from bsmm.drivers.cgminer import CgminerDriver
from bsmm.drivers.sim import SimAxeOSDriver, SimCgminerDriver
from bsmm.models import Device, DeviceInfo, ProbeResult

DRIVER_CLASSES: dict[str, type[Driver]] = {
    AxeOSDriver.name: AxeOSDriver,
    CgminerDriver.name: CgminerDriver,
}
#: ports the discovery scanner should check, mapped to the drivers that can answer there
SCAN_PORTS: tuple[int, ...] = tuple(sorted({p for d in DRIVER_CLASSES.values() for p in d.probe_ports}))


def device_info(device: Device) -> DeviceInfo:
    return DeviceInfo(
        driver=device.driver,
        family=device.family,
        model=device.display_model,
        host=device.host,
        port=device.port,
        mac=device.mac,
        hostname=device.hostname,
        serial=device.serial,
        firmware=device.firmware,
        asic_model=device.asic_model,
        asic_count=device.asic_count,
        board_version=device.board_version,
        capabilities=list(device.capabilities),
        extra=dict(device.extra),
    )


def driver_for(device: Device, client: httpx.AsyncClient, timeout: float = 8.0) -> Driver:
    info = device_info(device)
    if device.driver == "sim":
        if device.extra.get("sim_kind") == "cgminer":
            return SimCgminerDriver(device.host, device.port, info=info, timeout=timeout)
        return SimAxeOSDriver(device.host, device.port, info=info, timeout=timeout)
    cls = DRIVER_CLASSES.get(device.driver)
    if cls is None:
        raise ValueError(f"unknown driver {device.driver!r}")
    return cls(device.host, device.port, client=client, timeout=timeout, info=info)


async def probe_host(
    host: str,
    port: int | None = None,
    *,
    client: httpx.AsyncClient,
    timeout: float = 4.0,
    drivers: list[str] | None = None,
) -> list[ProbeResult]:
    """Ask every driver whether ``host`` is one of theirs. Best match first."""
    jobs: list[asyncio.Future[Any]] = []
    for name, cls in DRIVER_CLASSES.items():
        if drivers and name not in drivers:
            continue
        ports = (port,) if port else cls.probe_ports
        for p in ports:
            jobs.append(asyncio.ensure_future(cls.probe(host, p, client=client, timeout=timeout)))
    results = await asyncio.gather(*jobs, return_exceptions=True)
    found = [r for r in results if isinstance(r, ProbeResult)]
    found.sort(key=lambda r: r.confidence, reverse=True)
    return found

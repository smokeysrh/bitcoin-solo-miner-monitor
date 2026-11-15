"""Driver contract: how the engine talks to a family of miners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import httpx

from bsmm.models import Device, DeviceInfo, ProbeResult, Telemetry


class DriverError(Exception):
    """Base class. ``code`` is stable and safe to show to API clients."""

    code = "driver_error"


class Unreachable(DriverError):
    code = "unreachable"


class BadResponse(DriverError):
    code = "bad_response"


class AuthRequired(DriverError):
    code = "auth_required"


class IdentityMismatch(BadResponse):
    code = "identity_mismatch"


def check_identity(expected: Device | DeviceInfo, observed: DeviceInfo) -> None:
    """Missing identity is compatible; contradictory stable identity is not."""
    mac_conflict = expected.mac and observed.mac and expected.mac.upper() != observed.mac.upper()
    serial_conflict = expected.serial and observed.serial and expected.serial != observed.serial
    if mac_conflict or serial_conflict:
        raise IdentityMismatch("miner identity changed at this address; remove the old miner and adopt the replacement separately")


class Driver(ABC):
    """One instance talks to one physical miner."""

    #: stable identifier stored in the database ("axeos", "cgminer", "sim")
    name: ClassVar[str]
    label: ClassVar[str]
    default_port: ClassVar[int]
    #: ports the discovery scanner should look at to find this kind of device
    probe_ports: ClassVar[tuple[int, ...]]

    def __init__(
        self,
        host: str,
        port: int,
        *,
        client: httpx.AsyncClient,
        timeout: float = 8.0,
        info: DeviceInfo | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.client = client
        self.timeout = timeout
        self.info = info
        #: last raw payload (for the "raw data" debug view); never persisted
        self.last_raw: dict[str, Any] | None = None

    # -- discovery / reading --------------------------------------------------------------------

    @classmethod
    @abstractmethod
    async def probe(
        cls, host: str, port: int, *, client: httpx.AsyncClient, timeout: float = 4.0
    ) -> ProbeResult | None:
        """Return a result if (and only if) host:port is a device this driver understands."""

    @abstractmethod
    async def poll(self) -> Telemetry:
        """Read the current state. Raises :class:`DriverError` when the device cannot be read."""

    async def refresh_info(self) -> DeviceInfo | None:
        """Re-read static facts (firmware, model). Optional."""
        return self.info

    async def close(self) -> None:  # pragma: no cover - drivers with sockets override
        return None

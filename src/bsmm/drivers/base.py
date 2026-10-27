"""Driver contract: how the engine talks to a family of miners."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

import httpx

from bsmm.models import Capability, DeviceInfo, ProbeResult, Telemetry


class DriverError(Exception):
    """Base class. ``code`` is stable and safe to show to API clients."""

    code = "driver_error"


class Unreachable(DriverError):
    code = "unreachable"


class BadResponse(DriverError):
    code = "bad_response"


class Unsupported(DriverError):
    code = "unsupported"


class AuthRequired(DriverError):
    code = "auth_required"


class ActionFailed(DriverError):
    code = "action_failed"


@dataclass(slots=True)
class ActionResult:
    ok: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TuningOptions:
    """What a device allows for frequency / voltage (so the UI and agents stay inside safe limits)."""

    frequency_mhz: list[int] = field(default_factory=list)
    core_voltage_mv: list[int] = field(default_factory=list)
    default_frequency_mhz: int | None = None
    default_core_voltage_mv: int | None = None
    max_power_w: float | None = None
    max_temp_c: float | None = None


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

    # -- control (all optional; the capability list says which are real) ---------------------------

    @property
    def capabilities(self) -> set[Capability]:
        return set(self.info.capabilities) if self.info else set()

    async def restart(self) -> ActionResult:
        raise Unsupported("restart is not supported by this device")

    async def identify(self) -> ActionResult:
        raise Unsupported("identify is not supported by this device")

    async def pause(self) -> ActionResult:
        raise Unsupported("pause is not supported by this device")

    async def resume(self) -> ActionResult:
        raise Unsupported("resume is not supported by this device")

    async def set_pool(
        self,
        *,
        url: str,
        port: int,
        user: str,
        password: str = "x",  # noqa: S107 - the conventional stratum password
        role: str = "primary",
        tls: bool | None = None,
    ) -> ActionResult:
        raise Unsupported("changing pools is not supported by this device")

    async def set_fan(
        self, *, auto: bool | None = None, speed_pct: int | None = None, temp_target_c: int | None = None
    ) -> ActionResult:
        raise Unsupported("fan control is not supported by this device")

    async def set_tuning(
        self, *, frequency_mhz: int | None = None, core_voltage_mv: int | None = None
    ) -> ActionResult:
        raise Unsupported("tuning is not supported by this device")

    async def tuning_options(self) -> TuningOptions | None:
        return None

    async def close(self) -> None:  # pragma: no cover - drivers with sockets override
        return None

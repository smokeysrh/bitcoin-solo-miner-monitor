"""Core domain models shared by drivers, the engine, the API and the MCP tools.

Field names carry their unit (``hashrate_hs``, ``power_w``, ``temp_asic_c``...) so that an API
consumer, a chart, or an AI agent never has to guess.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DeviceStatus(StrEnum):
    ONLINE = "online"  # polled fine and hashing
    DEGRADED = "degraded"  # reachable, but something needs attention (no hashrate, pool down, hot...)
    OFFLINE = "offline"  # not answering
    PAUSED = "paused"  # mining paused on the device
    UNKNOWN = "unknown"  # not polled yet
    DISABLED = "disabled"  # user switched polling off


class Capability(StrEnum):
    """What a driver can do with a device. The UI and agents only offer what is supported."""

    RESTART = "restart"
    IDENTIFY = "identify"
    PAUSE = "pause"
    SET_POOL = "set_pool"
    SET_FAN = "set_fan"
    SET_FREQUENCY = "set_frequency"
    SET_VOLTAGE = "set_voltage"
    SET_HOSTNAME = "set_hostname"
    SCOREBOARD = "scoreboard"
    HISTORY = "history"  # device keeps its own history we can backfill from


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PoolInfo(_Model):
    """One configured stratum endpoint on a miner."""

    role: str = "primary"  # primary | fallback
    url: str | None = None
    port: int | None = None
    user: str | None = None
    address: str | None = None  # payout address extracted from the stratum user (validated)
    worker: str | None = None
    active: bool | None = None  # the miner is currently using this one
    connected: bool | None = None
    difficulty: float | None = None  # share difficulty assigned by the pool
    ping_ms: float | None = None
    tls: bool | None = None
    protocol: str | None = None  # sv1 | sv2

    @property
    def endpoint(self) -> str | None:
        if not self.url:
            return None
        return f"{self.url}:{self.port}" if self.port else self.url


class Telemetry(_Model):
    """One normalised reading from a miner. Every numeric field is optional: drivers fill what exists."""

    ts: float = Field(default_factory=time.time, description="Unix time (seconds) the reading was taken")
    online: bool = True

    # hashing
    hashrate_hs: float | None = Field(None, description="Current hashrate in H/s")
    hashrate_1m_hs: float | None = None
    hashrate_10m_hs: float | None = None
    hashrate_1h_hs: float | None = None
    hashrate_1d_hs: float | None = None
    hashrate_avg_hs: float | None = Field(None, description="Average since boot, for firmwares that only report that")
    hashrate_expected_hs: float | None = Field(None, description="Hashrate the settings should deliver, if known")
    hw_error_pct: float | None = Field(None, description="Hardware (hash) error percentage, 0-100")

    # power / thermals
    power_w: float | None = None
    power_source: str | None = Field(None, description="device = reported by the miner, manual = set by the user")
    voltage_in_v: float | None = None
    current_a: float | None = None
    efficiency_j_th: float | None = Field(None, description="Joules per terahash (= watts per TH/s). Lower is better")
    temp_asic_c: float | None = None
    temp_vr_c: float | None = None
    temp_board_c: float | None = None
    fan_pct: float | None = None
    fan_rpm: float | None = None
    fan2_rpm: float | None = None

    # tuning
    frequency_mhz: float | None = None
    frequency_actual_mhz: float | None = None
    core_voltage_mv: float | None = None
    core_voltage_actual_mv: float | None = None

    # shares
    shares_accepted: int | None = None
    shares_rejected: int | None = None
    reject_rate_pct: float | None = Field(None, description="rejected / (accepted + rejected) * 100")
    best_diff: float | None = Field(None, description="Best share difficulty since the device was last reset (all time)")
    best_session_diff: float | None = None
    rejected_reasons: dict[str, int] | None = None

    # pool
    pools: list[PoolInfo] = Field(default_factory=list)
    using_fallback: bool | None = None
    pool_connected: bool | None = None
    pool_difficulty: float | None = None
    pool_ping_ms: float | None = None

    # health
    uptime_s: int | None = None
    firmware: str | None = None
    wifi_rssi_dbm: float | None = None
    free_heap_bytes: int | None = None
    cpu_usage_pct: float | None = None
    mining_paused: bool | None = None
    overheat: bool | None = None
    fault: str | None = None

    # chain facts some firmwares report themselves
    blocks_found: int | None = Field(None, description="Blocks found counter kept by the firmware (AxeOS 2.x)")
    block_height: int | None = None
    network_difficulty: float | None = None

    def active_pool(self) -> PoolInfo | None:
        for p in self.pools:
            if p.active:
                return p
        return self.pools[0] if self.pools else None


class DeviceInfo(_Model):
    """Static facts about a miner learned by probing it."""

    driver: str
    family: str  # bitaxe | nerdqaxe | luckyminer | magicminer | avalon | antminer | cgminer | axeos | sim
    model: str
    host: str
    port: int
    mac: str | None = None
    hostname: str | None = None
    serial: str | None = None  # chip DNA / board serial where exposed
    firmware: str | None = None
    asic_model: str | None = None
    asic_count: int | None = None
    board_version: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def identity_key(self) -> str:
        """Stable identity used to recognise the same physical box on a different IP."""
        if self.mac:
            return f"mac:{self.mac.upper()}"
        if self.serial:
            return f"serial:{self.serial}"
        return f"host:{self.host}:{self.port}"


class Device(_Model):
    """A miner the user monitors (persisted)."""

    id: str
    name: str
    driver: str
    family: str
    model: str
    host: str
    port: int
    mac: str | None = None
    hostname: str | None = None
    serial: str | None = None
    firmware: str | None = None
    asic_model: str | None = None
    asic_count: int | None = None
    board_version: str | None = None
    capabilities: list[Capability] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    group: str | None = None
    notes: str | None = None
    enabled: bool = True
    allow_control: bool = True
    poll_interval_s: float | None = None
    model_override: str | None = None
    created_at: float = Field(default_factory=time.time)
    last_seen_at: float | None = None
    #: alternative addresses the same physical device answers on (e.g. wired + wifi)
    alt_hosts: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def display_model(self) -> str:
        return self.model_override or self.model

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}" if self.port != 80 else f"http://{self.host}"


class DeviceView(Device):
    """A device plus its live state (what the API returns)."""

    status: DeviceStatus = DeviceStatus.UNKNOWN
    status_since: float | None = None
    status_reason: str | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    telemetry: Telemetry | None = None
    web_url: str | None = None
    #: hashrate smoothed over ~45 s (what headline numbers should use; raw readings jump around)
    hashrate_smooth_hs: float | None = None
    #: the last ~30 hashrate readings (H/s) for instant sparklines
    spark_hashrate_hs: list[float | None] = Field(default_factory=list)
    last_poll_ms: float | None = None


class ProbeResult(_Model):
    """What a driver learned when it recognised a device."""

    info: DeviceInfo
    telemetry: Telemetry | None = None
    confidence: float = 1.0
    evidence: list[str] = Field(default_factory=list)


def compute_efficiency(power_w: float | None, hashrate_hs: float | None) -> float | None:
    """J/TH from watts and H/s. ``None`` unless both are positive."""
    if power_w is None or hashrate_hs is None or power_w <= 0 or hashrate_hs <= 0:
        return None
    return power_w / (hashrate_hs / 1e12)


def compute_reject_rate(accepted: int | None, rejected: int | None) -> float | None:
    if accepted is None or rejected is None:
        return None
    total = accepted + rejected
    if total <= 0:
        return None
    return rejected / total * 100.0


# --- events, alerting, integrations --------------------------------------------------------------------


class Severity(StrEnum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"info": 0, "success": 1, "warning": 2, "critical": 3}[self.value]


class Event(_Model):
    id: int | None = None
    ts: float = Field(default_factory=time.time)
    type: str
    severity: Severity = Severity.INFO
    device_id: str | None = None
    title: str
    body: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    dedupe_key: str | None = None
    ack_ts: float | None = None


class AlertRule(_Model):
    id: str
    name: str
    kind: str
    enabled: bool = True
    severity: Severity = Severity.WARNING
    #: {"all": true} | {"device_ids": [...]} | {"tags": [...]}
    scope: dict[str, Any] = Field(default_factory=lambda: {"all": True})
    params: dict[str, Any] = Field(default_factory=dict)
    channel_ids: list[str] = Field(default_factory=list)  # empty = every enabled channel
    cooldown_s: float = 3600.0
    builtin: bool = False
    created_at: float = Field(default_factory=time.time)


class Channel(_Model):
    """A place notifications go (Discord, Telegram, ntfy, email, webhook...). Secrets are write-only."""

    id: str
    kind: str
    name: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    has_secret: bool = False
    min_severity: Severity = Severity.INFO
    created_at: float = Field(default_factory=time.time)


class Source(_Model):
    """An external data source: a Bitcoin node, a pool, mempool.space..."""

    id: str
    kind: str  # bitcoin_core | public_pool | ckpool | mempool_space
    name: str
    url: str | None = None
    enabled: bool = True
    options: dict[str, Any] = Field(default_factory=dict)
    has_secret: bool = False
    created_at: float = Field(default_factory=time.time)


class PoolUsage(_Model):
    endpoint: str
    devices: int
    is_fallback: bool = False


class FleetSummary(_Model):
    """One-glance totals across every monitored miner."""

    updated_at: float = Field(default_factory=time.time)
    devices_total: int = 0
    devices_online: int = 0
    devices_degraded: int = 0
    devices_offline: int = 0
    devices_paused: int = 0
    hashrate_hs: float = 0.0  # smoothed
    hashrate_raw_hs: float = 0.0
    #: sum of what the settings should deliver, for the miners that say (not every firmware does)
    expected_hashrate_hs: float | None = None
    #: actual / expected * 100, counting only the miners that report an expectation, so a mixed fleet isn't skewed
    performance_pct: float | None = None
    power_w: float | None = None
    power_wall_w: float | None = None  # power_w plus the PSU overhead from settings
    efficiency_j_th: float | None = None
    temp_avg_c: float | None = None
    temp_max_c: float | None = None
    shares_accepted: int = 0
    shares_rejected: int = 0
    reject_rate_pct: float | None = None
    best_diff: float | None = None
    best_diff_device_id: str | None = None
    best_session_diff: float | None = None
    blocks_found_by_devices: int = 0
    pools: list[PoolUsage] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    demo: bool = False

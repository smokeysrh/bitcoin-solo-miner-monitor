"""User-facing settings: typed, validated, persisted in the database and changeable at runtime."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from bsmm.bitcoin_address import is_valid_address
from bsmm.storage.store import Store


class _S(BaseModel):
    model_config = ConfigDict(extra="ignore", validate_assignment=True)


class GeneralSettings(_S):
    instance_name: str = Field("My solo mining fleet", max_length=60)
    onboarding_done: bool = False
    first_run_at: float | None = None


class UnitSettings(_S):
    temperature: Literal["c", "f"] = "c"
    hashrate: Literal["auto", "th", "gh", "ph"] = "auto"
    currency: str = Field("USD", min_length=3, max_length=3)
    locale: str | None = None


class PollingSettings(_S):
    interval_s: float = Field(10.0, ge=2.0, le=600.0)
    offline_interval_s: float = Field(30.0, ge=5.0, le=3600.0)
    timeout_s: float = Field(6.0, ge=1.0, le=60.0)
    concurrency: int = Field(24, ge=1, le=200)
    offline_after_failures: int = Field(3, ge=1, le=30)


class EnergySettings(_S):
    price_per_kwh: float = Field(0.12, ge=0.0, le=10.0)
    #: wall power is higher than what the miner reports (PSU losses); 0 = trust the device
    psu_overhead_pct: float = Field(0.0, ge=0.0, le=50.0)


class NetworkSettings(_S):
    use_public_apis: bool = True
    mempool_url: str = "https://mempool.space"
    price_source: Literal["mempool", "manual", "none"] = "mempool"
    manual_btc_price: float | None = Field(None, ge=0)
    difficulty_growth_per_year: float = Field(0.0, ge=-0.9, le=10.0)
    avg_block_fees_btc: float | None = Field(None, ge=0, le=100)

    @field_validator("mempool_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip().rstrip("/")
        if not v.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://")
        return v


class MiningSettings(_S):
    #: payout addresses used to recognise your blocks (miners' own pool users are added automatically)
    addresses: list[str] = Field(default_factory=list)

    @field_validator("addresses")
    @classmethod
    def _addresses(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for raw in v:
            a = raw.strip()
            if not a:
                continue
            if not is_valid_address(a):
                raise ValueError(f"{a!r} is not a valid Bitcoin address (check for typos)")
            if a not in out:
                out.append(a)
        return out


class RetentionSettings(_S):
    raw_days: float = Field(2, ge=0.25, le=30)
    minute_days: float = Field(90, ge=1, le=730)
    hour_days: float = Field(730, ge=7, le=3650)
    event_days: float = Field(180, ge=7, le=3650)


class SafetySettings(_S):
    """Guard rails for anything that writes to a miner."""

    allow_control: bool = True
    allow_tuning: bool = False  # frequency / voltage changes stay off until you switch them on
    max_temp_c: float = Field(80.0, ge=50, le=110)


class AlertDefaults(_S):
    temp_warn_c: float = Field(75.0, ge=40, le=120)
    temp_crit_c: float = Field(85.0, ge=40, le=130)
    vr_temp_warn_c: float = Field(85.0, ge=40, le=130)
    hashrate_drop_pct: float = Field(30.0, ge=5, le=95)
    reject_rate_pct: float = Field(5.0, ge=0.5, le=50)
    offline_after_s: float = Field(120.0, ge=10, le=86400)
    quiet_hours: dict[str, Any] | None = None  # {"start": "23:00", "end": "07:00"} (info/success only are muted)


class UiSettings(_S):
    theme: Literal["system", "dark", "light", "amoled"] = "dark"
    accent: str = Field("#F7931A", pattern=r"^#[0-9a-fA-F]{6}$")
    density: Literal["comfortable", "compact"] = "comfortable"
    view_miners: Literal["grid", "table"] = "grid"
    reduce_motion: bool = False
    sound_on_block: bool = False
    simple_mode: bool = False
    dashboard: dict[str, Any] | None = None  # widget layout (opaque to the server)
    kiosk: dict[str, Any] | None = None


class AuthSettings(_S):
    mode: Literal["none", "password"] = "none"
    #: allow anyone on the network to *read* the dashboard (wall displays) while writes need a login
    public_read: bool = False


class Settings(_S):
    general: GeneralSettings = Field(default_factory=GeneralSettings)
    units: UnitSettings = Field(default_factory=UnitSettings)
    polling: PollingSettings = Field(default_factory=PollingSettings)
    energy: EnergySettings = Field(default_factory=EnergySettings)
    network: NetworkSettings = Field(default_factory=NetworkSettings)
    mining: MiningSettings = Field(default_factory=MiningSettings)
    retention: RetentionSettings = Field(default_factory=RetentionSettings)
    safety: SafetySettings = Field(default_factory=SafetySettings)
    alerts: AlertDefaults = Field(default_factory=AlertDefaults)
    ui: UiSettings = Field(default_factory=UiSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)


KEY = "settings"
log = logging.getLogger(__name__)
Listener = Callable[[Settings, Settings], Awaitable[None] | None]


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and k not in ("dashboard", "kiosk", "quiet_hours"):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class SettingsService:
    def __init__(self, store: Store) -> None:
        self.store = store
        self._current = Settings()
        self._listeners: list[Listener] = []
        self._lock = asyncio.Lock()

    async def load(self) -> Settings:
        # kv_get's tolerant JSON fallback cannot distinguish corrupt persistence from first run.
        row = await self.store.db.fetchone("SELECT value FROM kv WHERE key = ?", (KEY,))
        raw = None
        try:
            raw = json.loads(row["value"]) if row is not None else {}
            self._current = Settings.model_validate(raw)
        except (ValidationError, json.JSONDecodeError):
            # Recover preferences without interpreting corruption as passwordless consent.
            auth = AuthSettings(mode="password", public_read=False)
            if isinstance(raw, dict) and isinstance(raw.get("auth"), dict) and "mode" in raw["auth"]:
                try:
                    auth = AuthSettings.model_validate(raw["auth"], strict=True)
                except ValidationError:
                    log.warning("Invalid saved authentication settings; password protection required.")
            log.warning("Invalid saved settings; using default preferences and preserved/fail-closed authentication.")
            self._current = Settings(auth=auth)
        return self._current

    @property
    def current(self) -> Settings:
        return self._current

    def on_change(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def update(self, patch: dict[str, Any]) -> Settings:
        """Merge ``patch`` into the settings. Raises ``pydantic.ValidationError`` if invalid."""
        async with self._lock:
            old = self._current
            merged = deep_merge(old.model_dump(), patch)
            new = Settings.model_validate(merged)
            await self.store.kv_set(KEY, new.model_dump())
            self._current = new
        for listener in self._listeners:
            res = listener(new, old)
            if asyncio.iscoroutine(res):
                await res
        return new

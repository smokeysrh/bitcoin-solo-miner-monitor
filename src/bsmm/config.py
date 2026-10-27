"""Process-level configuration (where data lives, which port to bind). User-facing settings live in
the database (see :mod:`bsmm.settings`); this module only holds what is needed *before* it opens.

Everything can be set with environment variables (``BSMM_*``) so Docker, systemd and agents can
configure the app without touching files.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import platformdirs

APP_NAME = "bitcoin-solo-miner-monitor"
DEFAULT_PORT = 8420
DEFAULT_HOST = "0.0.0.0"


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def default_data_dir() -> Path:
    override = os.environ.get("BSMM_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if Path("/data").is_dir() and os.environ.get("BSMM_IN_DOCKER"):
        return Path("/data")
    return Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))


@dataclass(slots=True)
class RuntimeConfig:
    data_dir: Path = field(default_factory=default_data_dir)
    host: str = field(default_factory=lambda: os.environ.get("BSMM_HOST", DEFAULT_HOST))
    port: int = field(default_factory=lambda: int(os.environ.get("BSMM_PORT", DEFAULT_PORT)))
    log_level: str = field(default_factory=lambda: os.environ.get("BSMM_LOG_LEVEL", "INFO").upper())
    demo: bool = field(default_factory=lambda: _env_bool("BSMM_DEMO"))
    #: "none" | "password". When set via env it wins over what the setup wizard stored.
    auth_mode: str | None = field(default_factory=lambda: os.environ.get("BSMM_AUTH"))
    #: initial admin password (optional; handy for Docker / agents). Never logged.
    admin_password: str | None = field(default_factory=lambda: os.environ.get("BSMM_ADMIN_PASSWORD"))
    #: use only local sources (no mempool.space / price lookups) until the user opts in
    offline: bool = field(default_factory=lambda: _env_bool("BSMM_OFFLINE"))
    #: skip the background update check
    no_update_check: bool = field(default_factory=lambda: _env_bool("BSMM_NO_UPDATE_CHECK"))
    #: extra CORS origins, comma separated (the bundled UI is same-origin and needs none)
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.environ.get("BSMM_CORS_ORIGINS", "").split(",") if o.strip()]
    )
    #: serve the web UI (disable for headless / API-only deployments)
    serve_ui: bool = field(default_factory=lambda: _env_bool("BSMM_SERVE_UI", True))
    #: trust X-Forwarded-For from these proxies (comma separated IPs); empty = never trust it
    trusted_proxies: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.environ.get("BSMM_TRUSTED_PROXIES", "").split(",") if o.strip()]
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "bsmm.db"

    @property
    def key_path(self) -> Path:
        return self.data_dir / "secret.key"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):  # Windows / odd filesystems have no POSIX permissions
            os.chmod(self.data_dir, 0o700)

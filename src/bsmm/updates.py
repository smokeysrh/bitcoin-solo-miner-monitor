"""'Is there a newer release?' check. Opt-out, once a day, one anonymous GET to GitHub's public API."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from packaging.version import InvalidVersion, Version

from bsmm import __version__
from bsmm.storage.store import Store

log = logging.getLogger(__name__)
RELEASES_URL = "https://api.github.com/repos/smokeysrh/bitcoin-solo-miner-monitor/releases/latest"
KEY = "update.check"


def is_newer(latest: str, current: str = __version__) -> bool:
    try:
        return Version(latest.lstrip("v")) > Version(current)
    except InvalidVersion:
        return False


async def check_for_update(store: Store, http: httpx.AsyncClient, *, force: bool = False) -> dict[str, Any]:
    cached = await store.kv_get(KEY, {})
    if cached and not force and time.time() - cached.get("checked_at", 0) < 86400:
        return dict(cached)
    result: dict[str, Any] = {"current": __version__, "checked_at": time.time(), "latest": None, "update_available": False, "url": None, "error": None}
    try:
        resp = await http.get(RELEASES_URL, timeout=8.0, headers={"Accept": "application/vnd.github+json"})
        if resp.status_code == 404:
            result["error"] = None  # no release published yet
        elif resp.status_code != 200:
            result["error"] = f"GitHub answered HTTP {resp.status_code}"
        else:
            data = resp.json()
            tag = str(data.get("tag_name", ""))
            result.update(latest=tag.lstrip("v"), update_available=is_newer(tag), url=data.get("html_url"), notes=str(data.get("body", ""))[:2000])
    except (httpx.HTTPError, ValueError) as e:
        result["error"] = f"could not check ({e.__class__.__name__})"
    await store.kv_set(KEY, result)
    return result

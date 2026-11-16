"""'Is there a newer release?' check: one anonymous, one-way GET to GitHub's public API.

The whole exchange, so it can be checked by reading:

* One request: ``GET`` :data:`RELEASES_URL`, no query string, no body, sent by a client made for this call alone
  (:func:`make_update_client`). It has no cookies, no credentials and no shared connection pool, and its only headers are
  ``User-Agent`` and ``Accept`` (plus the ones HTTP itself needs). It does not follow redirects and it checks the TLS
  certificate. It never uses the app's shared client, so nothing set up for miners, pools or nodes can ride along.
* The reply is read through the app's bounded reader, at most :data:`MAX_REPLY_BYTES`, and then dropped.
* Only three things are kept from it: a version that parses as a normal version, a link on this project's own GitHub
  page, and when the check ran. Release text, titles and any other field are never read into the saved record.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
from packaging.version import InvalidVersion, Version

from bsmm import __version__
from bsmm.net import USER_AGENT, ResponseTooLarge, request_bounded
from bsmm.storage.store import Store

log = logging.getLogger(__name__)
RELEASES_URL = "https://api.github.com/repos/smokeysrh/bitcoin-solo-miner-monitor/releases/latest"
#: Where "See what is new" goes when the reply carries no usable link of its own.
RELEASES_PAGE_URL = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor/releases"
#: A release link from the reply is accepted only below this address.
RELEASE_LINK_PREFIX = "https://github.com/smokeysrh/bitcoin-solo-miner-monitor/"
KEY = "update.check"
ACCEPT = "application/vnd.github+json"
TIMEOUT_S = 8.0
CHECK_INTERVAL_S = 86400.0
#: A real release reply is a few KB; anything larger is not read further.
MAX_REPLY_BYTES = 256 * 1024
MAX_VERSION_CHARS = 20
MAX_LINK_CHARS = 200

#: Tests replace this with a ``httpx.MockTransport``; the client's other settings stay the real ones.
_transport: httpx.AsyncBaseTransport | None = None


def make_update_client() -> httpx.AsyncClient:
    """A client for exactly one request: nothing but ``User-Agent`` and ``Accept``, no redirects, certificate checked."""
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
        timeout=TIMEOUT_S,
        follow_redirects=False,
        verify=True,
        transport=_transport,
    )


def parse_version(text: object) -> Version | None:
    """The version in ``text`` (a leading ``v`` is allowed), or None when it is not a normal version or is too long."""
    if not isinstance(text, str) or not text or len(text) > MAX_VERSION_CHARS:
        return None
    try:
        return Version(text.lstrip("v"))
    except InvalidVersion:
        return None


def _newer_than(version: Version, current: str) -> bool:
    try:
        return version > Version(current)
    except InvalidVersion:
        return False


def is_newer(latest: str, current: str = __version__) -> bool:
    version = parse_version(latest)
    return version is not None and _newer_than(version, current)


def safe_release_url(value: object) -> str:
    """``value`` when it is a plain link below this project's GitHub page, otherwise the releases page."""
    if not isinstance(value, str) or not value.startswith(RELEASE_LINK_PREFIX):
        return RELEASES_PAGE_URL
    if len(value) > MAX_LINK_CHARS or not value.isascii() or not value.isprintable() or any(c in value for c in " \\"):
        return RELEASES_PAGE_URL
    try:
        parts = urlsplit(value)
    except ValueError:
        return RELEASES_PAGE_URL
    if parts.scheme != "https" or parts.netloc != "github.com" or parts.query or parts.fragment:
        return RELEASES_PAGE_URL
    # A browser resolves dot segments (also when percent-encoded), which could leave this project's page.
    if any(segment in (".", "..") for segment in unquote(parts.path).split("/")):
        return RELEASES_PAGE_URL
    return value


def _record(*, checked_at: float | None, version: Version | None, link: object, error: str | None) -> dict[str, Any]:
    """The only shape that is stored or returned. Release text has no place in it."""
    return {
        "current": __version__,
        "checked_at": checked_at,
        "latest": str(version) if version else None,
        "update_available": version is not None and _newer_than(version, __version__),
        "url": safe_release_url(link) if version else None,
        "error": error,
    }


def sanitize(stored: object) -> dict[str, Any]:
    """A saved check result rebuilt in the current shape. Nothing saved is trusted: an earlier release also kept the
    release text and took the link as it came, so the version and link go through the same rules as a fresh reply."""
    data: dict[str, Any] = stored if isinstance(stored, dict) else {}
    checked_at = data.get("checked_at")
    error = data.get("error")
    return _record(
        checked_at=float(checked_at) if isinstance(checked_at, int | float) and not isinstance(checked_at, bool) else None,
        version=parse_version(data.get("latest")),
        link=data.get("url"),
        error=error if isinstance(error, str) else None,
    )


async def stored_update_status(store: Store) -> dict[str, Any]:
    """What the last check found, without contacting anyone."""
    return sanitize(await store.kv_get(KEY, {}))


async def scrub_stored_update_info(store: Store) -> None:
    """Rewrite a result saved by an earlier release without its release text (and without any other stray field)."""
    stored = await store.kv_get(KEY, None)
    if stored is None:
        return
    clean = sanitize(stored)
    if clean != stored:
        await store.kv_set(KEY, clean)


async def check_for_update(store: Store, *, force: bool = False) -> dict[str, Any]:
    cached = await stored_update_status(store)
    if cached["checked_at"] is not None and not force and time.time() - cached["checked_at"] < CHECK_INTERVAL_S:
        return cached
    version: Version | None = None
    link: object = None
    error: str | None = None
    try:
        async with make_update_client() as client:
            resp = await request_bounded(client, "GET", RELEASES_URL, timeout=TIMEOUT_S, max_bytes=MAX_REPLY_BYTES)
        if resp.status_code == 404:
            pass  # no release published yet
        elif resp.status_code != 200:
            error = f"GitHub answered HTTP {resp.status_code}"
        else:
            reply = resp.json()
            if isinstance(reply, dict):
                version, link = parse_version(reply.get("tag_name")), reply.get("html_url")
            if version is None:
                error = "could not check (unusable reply)"
    except ResponseTooLarge:
        error = "could not check (reply too large)"
    except (httpx.HTTPError, ValueError) as e:
        error = f"could not check ({e.__class__.__name__})"
    result = _record(checked_at=time.time(), version=version, link=link, error=error)
    await store.kv_set(KEY, result)
    return result

"""Safety alert for changed pool or payout settings: what counts as a change, and how it is worded.

HashHurdr only reads. It keeps its own record (a baseline) of the pool settings each miner reports and compares every
new reading with it. A reading counts as a change only when the same different settings are seen on several polls in a
row (see ``PoolSightings``); the engine in ``fleet.py`` does the bookkeeping. Nothing in here talks to a miner.

The comparison keeps three facts per pool: host, port and payout address. Worker names, passwords, TLS flags and the
active/connected state are not part of it, and neither is spelling (case, surrounding spaces).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from bsmm.engine import pool_change_text as text
from bsmm.models import PoolChangeItem, PoolInfo

log = logging.getLogger(__name__)

#: event type, and also the kind of the built-in alert rule that turns the event into a notification
EVENT_TYPE = "pool_settings_changed"

SETTING_POOL_ADDRESS = "pool_address"
SETTING_POOL_PORT = "pool_port"
SETTING_PAYOUT_ADDRESS = "payout_address"
#: (fingerprint field, setting name) in the order changes are listed
_FIELDS = (("host", SETTING_POOL_ADDRESS), ("port", SETTING_POOL_PORT), ("payout", SETTING_PAYOUT_ADDRESS))
_SLOT_ORDER = {"primary": 0, "fallback": 1}
_LAST_RANK = len(_SLOT_ORDER)
#: bech32 addresses are case insensitive (and are written in lower case); base58 ones are case sensitive
_BECH32_PREFIXES = ("bc1", "tb1", "bcrt1")
#: addresses are shortened to their first and last characters in notifications; mirrors ``shortAddress`` in web/src/lib/format.ts
SHORT_HEAD = 8
SHORT_TAIL = 6

Fingerprint = list[dict[str, Any]]


class PoolChangeNotPending(Exception):
    """The change the user wants to accept is already answered, was replaced by a newer one, or never existed."""


@dataclass(slots=True)
class PoolSightings:
    """Consecutive polls that reported the same settings, when those differ from what HashHurdr last confirmed."""

    seen: Fingerprint | None = None
    polls: int = 0

    def note(self, current: Fingerprint) -> int:
        """Count this reading; returns how many polls in a row have now reported exactly these settings."""
        if current == self.seen:
            self.polls += 1
        else:
            self.seen, self.polls = current, 1
        return self.polls

    def reset(self) -> None:
        self.seen, self.polls = None, 0


def _clean_host(url: str | None) -> str | None:
    host = (url or "").strip().lower().rstrip(".")
    return host or None


def _clean_payout(pool: PoolInfo) -> str | None:
    # Drivers fill ``address`` only for a checksum-valid wallet address. Pools that use an account name instead
    # identify the payout by that account (the part before the first dot), so a change of it counts the same way.
    value = (pool.address or (pool.user or "").strip().partition(".")[0]).strip()
    if not value:
        return None
    return value.lower() if value.lower().startswith(_BECH32_PREFIXES) else value


def _slot_rank(slot: str) -> int:
    return _SLOT_ORDER.get(slot.partition(" ")[0], _LAST_RANK)


def fingerprint(pools: Sequence[PoolInfo]) -> Fingerprint:
    """The part of a miner's reported pools that HashHurdr watches. Empty when the miner reported no usable pool."""
    seen: dict[str, int] = {}
    slots: Fingerprint = []
    for pool in pools:
        host = _clean_host(pool.url)
        if host is None:
            continue
        role = pool.role if pool.role in _SLOT_ORDER else "other"
        seen[role] = seen.get(role, 0) + 1
        slot = role if seen[role] == 1 else f"{role} {seen[role]}"
        slots.append({"slot": slot, "host": host, "port": pool.port, "payout": _clean_payout(pool)})
    slots.sort(key=lambda s: _slot_rank(s["slot"]))  # stable: pools of one kind keep the order the miner reported
    return slots


def _as_text(value: Any) -> str | None:
    return None if value is None else str(value)


def diff(old: Fingerprint, new: Fingerprint) -> list[PoolChangeItem]:
    """Every watched setting that differs, with full old and new values. A pool that appears or disappears counts."""
    old_by_slot = {s["slot"]: s for s in old}
    new_by_slot = {s["slot"]: s for s in new}
    changes: list[PoolChangeItem] = []
    for slot in sorted(old_by_slot.keys() | new_by_slot.keys(), key=lambda s: (_slot_rank(s), s)):
        before, after = old_by_slot.get(slot, {}), new_by_slot.get(slot, {})
        for field_name, setting in _FIELDS:
            if before.get(field_name) != after.get(field_name):
                changes.append(PoolChangeItem(slot=slot, setting=setting, old=_as_text(before.get(field_name)),
                                              new=_as_text(after.get(field_name))))
    return changes


# --- wording --------------------------------------------------------------------------------------------------------------


def shorten_address(value: str, head: int = SHORT_HEAD, tail: int = SHORT_TAIL) -> str:
    """``bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq`` -> ``bc1qar0s…wf5mdq``. Short values stay as they are."""
    return value if len(value) <= head + tail + 1 else f"{value[:head]}…{value[-tail:]}"


def slot_label(slot: str) -> str:
    base, _, number = slot.partition(" ")
    label = text.SLOT_LABELS.get(base) or text.OTHER_SLOT_LABEL.format(slot=base)
    return f"{label} {number}" if number else label


def _maybe_short(change: PoolChangeItem, value: str | None, *, short: bool) -> str | None:
    if value is None or not short or change.setting != SETTING_PAYOUT_ADDRESS:
        return value
    return shorten_address(value)


def _shown(change: PoolChangeItem, value: str | None, *, short: bool) -> str:
    shown = _maybe_short(change, value, short=short)
    return text.ABSENT_VALUE if shown is None else shown


def describe_changes(changes: Sequence[PoolChangeItem], *, short: bool) -> str:
    """One line per changed setting. ``short`` shortens payout addresses (notifications); the dashboard shows them in full."""
    return "\n".join(
        text.CHANGE_LINE.format(slot=slot_label(c.slot), setting=text.SETTING_LABELS.get(c.setting, c.setting),
                                old=_shown(c, c.old, short=short), new=_shown(c, c.new, short=short))
        for c in changes
    )


def event_title(miner: str) -> str:
    return text.EVENT_TITLE.format(miner=miner)


def changes_of(ev: dict[str, Any]) -> list[PoolChangeItem]:
    """The changes a ``pool_settings_changed`` event carries (an unreadable entry is logged and left out)."""
    raw = (ev.get("data") or {}).get("changes") or []
    changes: list[PoolChangeItem] = []
    for item in raw:
        try:
            changes.append(PoolChangeItem.model_validate(item))
        except ValidationError:
            log.warning("pool settings event %s has an unreadable change entry; it is left out of the notification", ev.get("id"))
    return changes


def notification_content(ev: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Title, body and data of the notification for a ``pool_settings_changed`` event. Payout addresses are shortened."""
    changes = changes_of(ev)
    short = [c.model_copy(update={"old": _maybe_short(c, c.old, short=True), "new": _maybe_short(c, c.new, short=True)})
             for c in changes]
    title = str(ev.get("title") or text.RULE_LABEL)
    return title, describe_changes(changes, short=True), {"changes": [c.model_dump() for c in short]}

"""Every user-visible word of the pool and payout settings alert that the backend produces, in one place.

The wording below is the final copy (card #2442); nothing else in the code base spells these sentences out. Do not copy
these strings anywhere else.
"""

from __future__ import annotations

# --- the built-in alert rule (Settings > Alerts, GET /api/v1/alerts/rule-types) ------------------------------------------
RULE_LABEL = "Pool or payout settings change"
RULE_DESCRIPTION = (
    "A miner reports a pool address, port or payout address that differs from what HashHurdr has on record."
)

# --- the event (activity log, GET /api/v1/events) and the notification built from it ---------------------------------------
#: ``{miner}`` is the miner's name.
EVENT_TITLE = "{miner}: pool or payout settings changed"
#: one line per changed setting. ``{slot}`` is a SLOT_LABELS value, ``{setting}`` a SETTING_LABELS value,
#: ``{old}`` and ``{new}`` are values or ABSENT_VALUE.
CHANGE_LINE = "{slot}: {setting} changed from {old} to {new}."
#: shown in place of a value when a pool was not there before (``old``) or is gone now (``new``)
ABSENT_VALUE = "none"
SETTING_LABELS = {
    "pool_address": "pool address",
    "pool_port": "pool port",
    "payout_address": "payout address",
}
#: first letter of the slot name is not capitalised here; extra pools of one kind are numbered, e.g. "fallback pool 2"
SLOT_LABELS = {
    "primary": "primary pool",
    "fallback": "fallback pool",
}
#: used for a slot that is neither primary nor fallback; ``{slot}`` is the slot name as reported
OTHER_SLOT_LABEL = "pool {slot}"

# --- Accept (POST /api/v1/events/{id}/accept-pool-change) -----------------------------------------------------------------
ACCEPT_SUMMARY = "Say that a miner's changed pool or payout settings are intended"
ACCEPT_DESCRIPTION = (
    "Makes the settings HashHurdr last confirmed on the miner its record and resolves the event. "
    "Nothing is sent to the miner. Only the user can say whether a change was intended."
)
#: ``not_found(EVENT_NOT_FOUND, EVENT_NOT_FOUND_HINT)`` renders "<EVENT_NOT_FOUND> was not found."
EVENT_NOT_FOUND = "That pool settings event"
EVENT_NOT_FOUND_HINT = "List them with GET /api/v1/events?type=pool_settings_changed&unacked=true"
NOT_PENDING_MESSAGE = "That change was already answered, or a newer one replaced it."
NOT_PENDING_HINT = "Read the miner again with GET /api/v1/devices/{id} and use the event id in its pool_change."

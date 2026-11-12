"""Shared walker for removing private values from nested miner data.

Two kinds of filtering stay separate. ``bsmm.capture`` hides personal and identifying details (Wi-Fi name,
MAC, pool users) before a file is shared. ``redact_credentials`` below hides only secrets, so diagnostics the
app shows its own user keep the model, hostname and MAC that make them useful.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

REDACTED = "<redacted>"

#: Parts of a field name (lower case, punctuation removed) that mark its value as a secret.
_CREDENTIAL_NAME_PARTS = ("pass", "token", "secret", "credential", "authorization")
#: Names that end in "key" (apiKey, private_key, key) hold secrets; "key" inside a longer word does not count.
_CREDENTIAL_NAME_SUFFIX = "key"
_NON_ALNUM = re.compile(r"[^a-z0-9]")
#: ``scheme://user:secret@host`` -> the part between ``://`` and the last ``@`` before the path.
_URL_USERINFO = re.compile(r"(?P<scheme>\b[A-Za-z][A-Za-z0-9+.-]*://)[^/\s]*@")


def redact_tree(
    value: Any,
    *,
    hide_key: Callable[[str], bool],
    scrub_text: Callable[[str], str] | None = None,
) -> Any:
    """A copy of ``value`` where every dictionary entry whose key ``hide_key`` accepts is replaced, at any depth.

    Lists are walked too. ``scrub_text`` (optional) rewrites each remaining string value.
    """
    if isinstance(value, dict):
        return {
            k: REDACTED if hide_key(str(k)) else redact_tree(v, hide_key=hide_key, scrub_text=scrub_text)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact_tree(v, hide_key=hide_key, scrub_text=scrub_text) for v in value]
    if isinstance(value, str) and scrub_text is not None:
        return scrub_text(value)
    return value


def is_credential_key(name: str) -> bool:
    """True for field names that hold a password, token, secret or key, whatever their case or punctuation."""
    plain = _NON_ALNUM.sub("", name.lower())
    return plain.endswith(_CREDENTIAL_NAME_SUFFIX) or any(part in plain for part in _CREDENTIAL_NAME_PARTS)


def scrub_url_credentials(text: str) -> str:
    """Replace the user name and password in any ``scheme://user:password@host`` inside ``text``."""
    return _URL_USERINFO.sub(lambda m: f"{m['scheme']}{REDACTED}@", text)


def redact_credentials(value: Any) -> Any:
    """A copy of ``value`` with secrets removed and everything else (model, hostname, MAC...) left as it is."""
    return redact_tree(value, hide_key=is_credential_key, scrub_text=scrub_url_credentials)

"""Encryption at rest for credentials (node RPC passwords, SMTP passwords, bot tokens...).

A random key lives next to the database with owner-only permissions (or in ``BSMM_SECRET_KEY``).
That protects against the common leaks (a backup, a copied database, a screenshot of a table) but
is not a defence against someone who already controls the machine; the docs say so plainly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)
_PREFIX = "enc:v1:"


class SecretBox:
    def __init__(self, key: bytes) -> None:
        self._fernet = Fernet(key)

    @classmethod
    def load_or_create(cls, key_path: Path) -> SecretBox:
        env = os.environ.get("BSMM_SECRET_KEY")
        if env:
            return cls(env.encode())
        if key_path.exists():
            return cls(key_path.read_bytes().strip())
        key = Fernet.generate_key()
        key_path.parent.mkdir(parents=True, exist_ok=True)
        # Create with owner-only permissions from the start (no window where it is world readable).
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(key)
        return cls(key)

    def encrypt(self, plaintext: str | None) -> str | None:
        if plaintext is None or plaintext == "":
            return None
        return _PREFIX + self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str | None) -> str | None:
        if not token:
            return None
        if not token.startswith(_PREFIX):
            return None  # never treat unknown data as a secret
        try:
            return self._fernet.decrypt(token[len(_PREFIX) :].encode()).decode()
        except InvalidToken:
            log.error("A stored secret could not be decrypted (the secret key changed?). Re-enter it in Settings.")
            return None

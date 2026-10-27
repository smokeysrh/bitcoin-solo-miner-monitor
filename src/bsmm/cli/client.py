"""Synchronous API client used by the command line (so every CLI command is just a REST call)."""

from __future__ import annotations

import os
from typing import Any

import httpx

from bsmm.config import DEFAULT_PORT


class CliError(Exception):
    """A problem to show the user as a plain sentence (no traceback)."""

    def __init__(self, message: str, hint: str | None = None, code: int = 1) -> None:
        super().__init__(message)
        self.hint = hint
        self.code = code


def default_url() -> str:
    return os.environ.get("BSMM_URL") or f"http://127.0.0.1:{os.environ.get('BSMM_PORT', DEFAULT_PORT)}"


class Api:
    def __init__(self, url: str | None = None, token: str | None = None, timeout: float = 30.0) -> None:
        self.url = (url or default_url()).rstrip("/")
        self.token = token or os.environ.get("BSMM_TOKEN")
        self.client = httpx.Client(timeout=timeout, headers={"Authorization": f"Bearer {self.token}"} if self.token else {})

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None) -> Any:
        try:
            resp = self.client.request(method, f"{self.url}/api/v1{path}", params={k: v for k, v in (params or {}).items() if v is not None}, json=json)
        except httpx.ConnectError as e:
            raise CliError(f"Can't reach the server at {self.url}.", "Start it with `bsmm start` (background) or `bsmm serve` (foreground).") from e
        except httpx.HTTPError as e:
            raise CliError(f"Request to {self.url} failed ({e.__class__.__name__}).") from e
        try:
            data = resp.json()
        except ValueError:
            data = None
        if resp.status_code >= 400:
            err = (data or {}).get("error", {}) if isinstance(data, dict) else {}
            raise CliError(err.get("message") or f"HTTP {resp.status_code}", err.get("hint"), code=2 if resp.status_code in (401, 403) else 1)
        return data

    def get(self, path: str, **params: Any) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any = None, **params: Any) -> Any:
        return self.request("POST", path, params=params, json=body if body is not None else {})

    def patch(self, path: str, body: Any) -> Any:
        return self.request("PATCH", path, json=body)

    def delete(self, path: str, **params: Any) -> Any:
        return self.request("DELETE", path, params=params)

    def is_up(self) -> bool:
        try:
            return self.client.get(f"{self.url}/api/v1/health", timeout=2.0).status_code == 200
        except httpx.HTTPError:
            return False

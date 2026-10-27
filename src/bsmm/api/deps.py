"""Request dependencies: the app context and authentication / authorisation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from bsmm.api.errors import ApiError
from bsmm.auth import COOKIE_NAME, Principal
from bsmm.context import AppContext

_bearer = HTTPBearer(auto_error=False, description="API token (create one in Settings > Agents & API or with `bsmm token create`).")
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore[no-any-return]


def client_ip(request: Request) -> str:
    ctx: AppContext = request.app.state.ctx
    peer = request.client.host if request.client else "unknown"
    if peer in ctx.config.trusted_proxies:
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return peer


async def resolve_principal(request: Request, creds: HTTPAuthorizationCredentials | None) -> Principal | None:
    ctx = get_ctx(request)
    token = creds.credentials if creds else request.headers.get("x-api-key")
    session = request.cookies.get(COOKIE_NAME)
    mode = ctx.settings.current.auth.mode
    found = await ctx.auth.principal_from(bearer=token, session=session)
    if found:
        return found
    if mode == "none":
        return Principal("local", "admin", "none")
    if ctx.settings.current.auth.public_read and request.method in SAFE_METHODS:
        return Principal("public", "read", "public")
    return None


def require(scope: str = "read") -> Callable[..., Awaitable[Principal]]:
    async def dependency(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal:
        principal = getattr(request.state, "principal", None) or await resolve_principal(request, creds)
        if principal is None:
            raise ApiError(401, "auth_required", "You need to sign in or send an API token.",
                           "Send 'Authorization: Bearer <token>'. Create one with `bsmm token create --scope control`, or sign in at /login.",
                           headers={"WWW-Authenticate": "Bearer"})
        # cookie sessions are ambient credentials: block cross-site form posts
        if principal.via == "session" and request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host", ""):
                raise ApiError(403, "cross_site_blocked", "Cross-site requests are not allowed with a browser session.")
        if not principal.allows(scope):
            raise ApiError(403, "insufficient_scope", f"This needs the '{scope}' scope but you have '{principal.scope}'.",
                           "Use a token created with a higher scope.")
        request.state.principal = principal
        return principal

    return dependency

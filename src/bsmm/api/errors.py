"""One predictable error shape for humans, scripts and AI agents.

    {"error": {"code": "not_found", "message": "...", "hint": "...", "status": 404}}

``code`` is stable (switch on it), ``message`` is plain English, ``hint`` says what to do next.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from bsmm.drivers.base import ActionFailed, AuthRequired, BadResponse, DriverError, Unreachable, Unsupported
from bsmm.sources.base import SourceError


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, hint: str | None = None, details: Any = None,
                 headers: dict[str, str] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.hint = hint
        self.details = details
        self.headers = headers or {}


def not_found(what: str, hint: str | None = None) -> ApiError:
    return ApiError(404, "not_found", f"{what} was not found.", hint)


def bad_request(message: str, hint: str | None = None, details: Any = None) -> ApiError:
    return ApiError(400, "bad_request", message, hint, details)


def body(status: int, code: str, message: str, hint: str | None = None, details: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message, "status": status}
    if hint:
        err["hint"] = hint
    if details is not None:
        err["details"] = details
    return {"error": err}


_HINTS = {
    401: "Send a token as 'Authorization: Bearer <token>' (create one with `bsmm token create` or in Settings > Agents & API).",
    403: "This token or session is not allowed to do that. Control actions need a token with the 'control' scope.",
    404: "List what exists with the matching GET endpoint, or see /openapi.json.",
    405: "That method is not supported on this path. See /openapi.json.",
    429: "Wait a moment and try again.",
}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(body(exc.status, exc.code, exc.message, exc.hint, exc.details), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "auth_required", 403: "forbidden", 404: "not_found", 405: "method_not_allowed", 429: "rate_limited"}.get(exc.status_code, "http_error")
        return JSONResponse(body(exc.status_code, code, str(exc.detail), _HINTS.get(exc.status_code)), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        problems = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "problem": e["msg"]} for e in exc.errors()]
        first = problems[0] if problems else {"field": "?", "problem": "invalid"}
        return JSONResponse(
            body(422, "validation_error", f"{first['field'] or 'request'}: {first['problem']}", "Fix the listed fields and retry. The schema is in /openapi.json.", problems),
            status_code=422,
        )

    @app.exception_handler(PydanticValidationError)
    async def _pyd(_: Request, exc: PydanticValidationError) -> JSONResponse:
        problems = [{"field": ".".join(str(p) for p in e["loc"]), "problem": e["msg"]} for e in exc.errors()]
        first = problems[0] if problems else {"field": "?", "problem": "invalid"}
        return JSONResponse(body(422, "validation_error", f"{first['field']}: {first['problem']}", "Fix the listed fields and retry.", problems),
                            status_code=422)

    @app.exception_handler(Unsupported)
    async def _unsupported(_: Request, exc: Unsupported) -> JSONResponse:
        return JSONResponse(body(409, "unsupported", str(exc), "Check the device's capabilities list."), status_code=409)

    @app.exception_handler(ActionFailed)
    async def _action(_: Request, exc: ActionFailed) -> JSONResponse:
        return JSONResponse(body(422, "action_rejected", str(exc)), status_code=422)

    @app.exception_handler(Unreachable)
    async def _unreachable(_: Request, exc: Unreachable) -> JSONResponse:
        return JSONResponse(body(502, "device_unreachable", str(exc), "Check that the miner is powered and on the network."), status_code=502)

    @app.exception_handler(AuthRequired)
    async def _devauth(_: Request, exc: AuthRequired) -> JSONResponse:
        return JSONResponse(body(502, "device_refused", str(exc)), status_code=502)

    @app.exception_handler(BadResponse)
    async def _badresp(_: Request, exc: BadResponse) -> JSONResponse:
        return JSONResponse(body(502, "device_bad_response", str(exc)), status_code=502)

    @app.exception_handler(DriverError)
    async def _driver(_: Request, exc: DriverError) -> JSONResponse:
        return JSONResponse(body(502, exc.code, str(exc)), status_code=502)

    @app.exception_handler(SourceError)
    async def _source(_: Request, exc: SourceError) -> JSONResponse:
        return JSONResponse(body(502, exc.code, str(exc)), status_code=502)

    @app.exception_handler(PermissionError)
    async def _perm(_: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(body(403, "not_allowed", str(exc), "Change the relevant switch in Settings > Safety if you really want this."), status_code=403)

    @app.exception_handler(KeyError)
    async def _key(_: Request, exc: KeyError) -> JSONResponse:
        return JSONResponse(body(404, "not_found", f"{exc.args[0] if exc.args else 'item'} was not found."), status_code=404)

    @app.exception_handler(LookupError)
    async def _lookup(_: Request, exc: LookupError) -> JSONResponse:
        return JSONResponse(body(404, "not_found", str(exc)), status_code=404)

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(body(400, "bad_request", str(exc)), status_code=400)

"""Run the real ASGI app under uvicorn on an ephemeral localhost port (for SSE, MCP and CLI tests)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI


@asynccontextmanager
async def serve(app: FastAPI) -> AsyncIterator[str]:
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning", lifespan="on")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(300):
        if server.started:
            break
        await asyncio.sleep(0.02)
    else:  # pragma: no cover
        task.cancel()
        raise RuntimeError("test server did not start")
    port = server.servers[0].sockets[0].getsockname()[1]  # type: ignore[union-attr]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        await asyncio.wait_for(task, 10)

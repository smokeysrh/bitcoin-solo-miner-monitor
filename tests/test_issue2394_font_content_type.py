"""Card #2394: the bundled web fonts are served with a font content type.

Python 3.11 to 3.13 ``mimetypes`` does not know ``.woff2``, so the file server fell back to a guessed text type.
The built UI is faked with a small directory (index page plus one font file), so no npm build is needed.
"""

from __future__ import annotations

import httpx

from bsmm.api import app as app_module
from bsmm.api.app import create_app

FONT_PATH = "/fonts/Inter-latin.woff2"
FONT_BYTES = b"wOF2" + bytes(64)  # only the file extension decides the type, not the content


async def test_woff2_is_served_as_a_font(lan, tmp_path, monkeypatch):
    ctx, _ = lan
    web = tmp_path / "built-ui"
    (web / "fonts").mkdir(parents=True)
    (web / "index.html").write_text('<!doctype html><div id="app"></div>', encoding="utf-8")
    (web / "fonts" / "Inter-latin.woff2").write_bytes(FONT_BYTES)
    monkeypatch.setattr(app_module, "WEB_DIR", web)
    app = create_app(ctx=ctx)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://bsmm.test") as client:
        response = await client.get(FONT_PATH)
    assert response.status_code == 200
    assert response.content == FONT_BYTES
    assert response.headers["content-type"].startswith("font/woff2")

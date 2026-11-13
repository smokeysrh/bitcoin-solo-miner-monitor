"""Card #2390 (umbrella #2244): people and agents see HashHurdr; every technical identifier stays as it was.

The first half checks the display name where the backend shows it. The second half pins what must NOT change
(package, command, data and install identities) and the shipped brand files, which are official marks used as
supplied: the tests check their presence, names and pixel sizes, never their contents.
"""

from __future__ import annotations

import json
import re
import struct
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from bsmm.agent_docs import agent_guide, llms_txt
from bsmm.cli.main import app

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "web" / "public"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
FAVICON_SIZES = {16, 32, 48}


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE, f"{path} is not a PNG"
    width, height = struct.unpack(">II", data[16:24])  # IHDR follows the signature and the chunk header
    return width, height


def ico_sizes(path: Path) -> set[int]:
    data = path.read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1), f"{path} is not an ICO file"
    return {data[6 + 16 * i] or 256 for i in range(count)}  # the width byte is 0 for 256 px


# --- the name people and agents read ---------------------------------------------------------------------------------------------------------------


def test_agent_documents_introduce_hashhurdr_and_still_name_the_project():
    text = llms_txt("http://x:8420")
    assert text.startswith("# HashHurdr\n")
    assert "HashHurdr, the Bitcoin Solo Miner Monitor" in text.split("\n\n", 2)[1]
    assert agent_guide("http://x:8420")["name"] == "HashHurdr"


def test_command_line_help_shows_hashhurdr_under_the_unchanged_command_name():
    res = CliRunner().invoke(app, ["--help"], env={"COLUMNS": "200"})
    assert res.exit_code == 0
    assert "HashHurdr" in res.stdout and "bsmm setup" in res.stdout
    assert app.info.name == "bsmm"


def test_mcp_server_shows_hashhurdr_but_keeps_its_machine_name():
    # The MCP SDK object does not expose its title through a stable public attribute, so read the one place it is set.
    source = (ROOT / "src/bsmm/mcp_server.py").read_text(encoding="utf-8")
    assert 'title="HashHurdr"' in source
    assert 'name: str = "bitcoin-solo-miner-monitor"' in source


def test_background_service_description_shows_hashhurdr_but_keeps_its_commands():
    source = (ROOT / "src/bsmm/cli/service.py").read_text(encoding="utf-8")
    assert "Description=HashHurdr\n" in source
    assert '"BitcoinSoloMinerMonitor"' in source  # the Windows scheduled-task name is an identity, not a label


# --- identifiers that must not change --------------------------------------------------------------------------------------------------------------


def test_package_command_and_install_identities_are_unchanged():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "bitcoin-solo-miner-monitor"
    assert project["scripts"] == {"bsmm": "bsmm.cli.main:main", "bitcoin-solo-miner-monitor": "bsmm.cli.main:main"}
    installer = (ROOT / "installer/windows/bsmm.iss").read_text(encoding="utf-8")
    assert "AppId={{EC42155A-D71C-4609-A40A-18FBBE0D91B2}" in installer
    assert "DefaultDirName={localappdata}\\Programs\\Bitcoin Solo Miner Monitor" in installer
    assert "OutputBaseFilename=bsmm-{#AppVersion}-windows-setup" in installer
    umbrel = (ROOT / "packaging/umbrel/umbrel-app.yml").read_text(encoding="utf-8")
    assert "\nid: bitcoin-solo-miner-monitor\n" in umbrel and "\nname: HashHurdr\n" in umbrel
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "  bsmm:\n    image: ghcr.io/smokeysrh/bitcoin-solo-miner-monitor:latest" in compose


def test_installer_uses_the_supplied_icon_for_setup_and_the_program():
    icon = ROOT / "installer/windows/hashhurdr.ico"
    assert ico_sizes(icon) == FAVICON_SIZES
    assert "SetupIconFile=hashhurdr.ico" in (ROOT / "installer/windows/bsmm.iss").read_text(encoding="utf-8")
    assert "hashhurdr.ico" in (ROOT / "installer/windows/build.py").read_text(encoding="utf-8")


# --- web identity files ----------------------------------------------------------------------------------------------------------------------------


def test_manifest_names_hashhurdr_and_keeps_its_install_identity():
    manifest = json.loads((PUBLIC / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["name"] == "HashHurdr" and manifest["short_name"] == "HashHurdr"
    assert "Built for Plebs, By Plebs." in manifest["description"]
    assert manifest["start_url"] == "/" and manifest["scope"] == "/"
    sizes = {icon["src"]: icon["sizes"] for icon in manifest["icons"] if icon["src"].endswith(".png")}
    assert sizes == {"/icons/icon-192.png": "192x192", "/icons/icon-512.png": "512x512", "/icons/icon-maskable-512.png": "512x512"}
    for src, declared in sizes.items():
        width, height = png_size(PUBLIC / src.lstrip("/"))
        assert f"{width}x{height}" == declared, src


def test_no_script_writes_the_supplied_app_icon_files():
    scripts = [path for path in (ROOT / "web" / "scripts").rglob("*") if path.is_file()]
    assert scripts, "web/scripts has no files to scan"
    icon_names = ("icon-192.png", "icon-512.png", "icon-maskable-512.png")
    offenders = sorted(
        f"{path.relative_to(ROOT).as_posix()} names {name}"
        for path in scripts
        for name in icon_names
        if name in path.read_text(encoding="utf-8", errors="replace")
    )
    assert offenders == [], "a script could overwrite the supplied kit icons"


def test_page_head_uses_the_name_and_the_supplied_favicons():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert "<title>HashHurdr</title>" in html
    assert "<noscript>HashHurdr needs JavaScript." in html
    assert '<link rel="icon" href="/favicon.ico" sizes="16x16 32x32 48x48" />' in html
    assert '<link rel="icon" type="image/svg+xml" href="/favicon.svg" />' in html
    assert '<link rel="apple-touch-icon" href="/apple-touch-icon-180.png" />' in html
    assert ico_sizes(PUBLIC / "favicon.ico") == FAVICON_SIZES
    assert png_size(PUBLIC / "apple-touch-icon-180.png") == (180, 180)
    assert "HashHurdr" in (PUBLIC / "favicon.svg").read_text(encoding="utf-8")


def test_service_worker_messages_use_the_name_and_keep_the_cache_prefix():
    worker = (PUBLIC / "sw.js").read_text(encoding="utf-8")
    assert "HashHurdr is not reachable right now." in worker
    assert "Solo Miner Monitor" not in worker
    assert "const CACHE_PREFIX = 'bsmm-shell-'" in worker


def test_sidebar_logos_are_present_for_dark_and_light_backgrounds():
    brand = PUBLIC / "brand"
    for name in ("hashhurdr-symbol.svg", "hashhurdr-lockup-horizontal-dark.svg", "hashhurdr-lockup-horizontal-light.svg"):
        assert (brand / name).is_file(), name


# --- documents -------------------------------------------------------------------------------------------------------------------------------------


def test_brand_policy_is_in_the_repository_and_linked_from_the_readme():
    brand = (ROOT / "BRAND.md").read_text(encoding="utf-8")
    assert "docs/brand/BRAND-POLICY.md" in brand and "MIT" in brand
    policy = (ROOT / "docs/brand/BRAND-POLICY.md").read_text(encoding="utf-8")
    assert policy.startswith("# HashHurdr brand policy\n")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "(BRAND.md)" in readme
    assert "<picture>" in readme.split("\n# ", 1)[0]  # the banner sits above the title
    for path in re.findall(r'(?:srcset|src)="(docs/brand/[^"]+)"', readme):
        assert (ROOT / path).is_file(), path
    assert png_size(ROOT / "docs/brand/readme-banner-dark-1280x320.png") == (1280, 320)
    assert png_size(ROOT / "docs/brand/readme-banner-light-1280x320.png") == (1280, 320)

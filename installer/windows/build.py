"""Build current Python/Vue CLI, never the retired Electron/Flask installer.

Run in the project environment after npm ci && npm run build in web/.
The onedir portable distribution avoids onefile's throwaway extraction process:
bsmm.exe remains the identity of the live server for its entire lifetime.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def package_version() -> str:
    tree = ast.parse((ROOT / "src/bsmm/__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            value = ast.literal_eval(node.value)
            if isinstance(value, str) and re.fullmatch(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", value):
                return value
    raise ValueError("Canonical package version is missing or unsupported")


def version_resource(version: str) -> str:
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if match is None:
        raise ValueError("A numeric version is required for Windows resources")
    parts = (*(int(p) for p in match.groups()), 0)
    strings = {"CompanyName": "Bitcoin Solo Miner Monitor", "FileDescription": "Bitcoin Solo Miner Monitor CLI",
               "FileVersion": version, "InternalName": "bsmm", "OriginalFilename": "bsmm.exe",
               "ProductName": "Bitcoin Solo Miner Monitor", "ProductVersion": version}
    entries = ",\n".join(f"StringStruct({key!r}, {value!r})" for key, value in strings.items())
    return (f"VSVersionInfo(ffi=FixedFileInfo(filevers={parts!r}, prodvers={parts!r}, mask=0x3f, "
            "flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)), "
            f"kids=[StringFileInfo([StringTable('040904B0', [{entries}])]), "
            "VarFileInfo([VarStruct('Translation', [1033, 1200])])])\n")


def build(output: Path, *, installer: bool = False) -> list[Path]:
    version = package_version()
    if not (ROOT / "src/bsmm/web/index.html").is_file() or not list((ROOT / "src/bsmm/web/assets").glob("*.js")):
        raise RuntimeError("Build the Vue UI first: npm ci && npm run build in web/")
    output.mkdir(parents=True, exist_ok=True)
    work = output / "work"
    work.mkdir(exist_ok=True)
    resource = work / "version.txt"
    resource.write_text(version_resource(version), encoding="utf-8")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--name", "bsmm",
               "--distpath", str(output / "portable"), "--workpath", str(work / "pyinstaller"),
               "--specpath", str(work), "--paths", str(ROOT / "src"),
               "--collect-all", "bsmm", "--collect-all", "mcp", "--collect-submodules", "uvicorn",
               "--copy-metadata", "bitcoin-solo-miner-monitor"]
    if sys.platform == "win32":
        command += ["--version-file", str(resource)]
    command += [str(ROOT / "installer/windows/entry.py")]
    subprocess.run(command, cwd=ROOT, check=True)  # noqa: S603
    bundle = output / "portable/bsmm"
    # Generated from the same source as /llms.txt, not a second hand-maintained guide.
    from bsmm.agent_docs import llms_txt
    (bundle / "AGENT-GUIDE.txt").write_text(llms_txt("http://localhost:8420"), encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", bundle / "LICENSE.txt")
    archive = Path(shutil.make_archive(str(output / f"bsmm-{version}-{sys.platform}-portable"), "zip", bundle.parent, bundle.name))
    artifacts = [archive]
    if installer:
        if sys.platform != "win32":
            raise RuntimeError("Windows installers require a native Windows runner; no cross-build claim")
        iscc = shutil.which("ISCC.exe") or str(Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Inno Setup 6/ISCC.exe")
        numeric = ".".join(str(part) for part in (*Version(version).release, 0))
        subprocess.run([iscc, f"/DAppVersion={version}", f"/DFileVersion={numeric}", f"/DBundleDir={bundle}", f"/O{output}",  # noqa: S603
                        str(ROOT / "installer/windows/bsmm.iss")], check=True)
        artifacts.append(output / f"bsmm-{version}-windows-setup.exe")
    checksums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in artifacts)
    (output / "SHA256SUMS").write_text(checksums, encoding="ascii")
    return artifacts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/windows")
    parser.add_argument("--installer", action="store_true")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(package_version())
    else:
        for artifact in build(args.output.resolve(), installer=args.installer):
            print(artifact)

#!/usr/bin/env python3
"""Verify and install the bundled Pretendard fonts at user scope."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
BUNDLE = PLUGIN_ROOT / "assets" / "fonts" / "pretendard"
MANIFEST = BUNDLE / "manifest.json"
LICENSE = BUNDLE / "LICENSE.txt"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def load_bundle(bundle: Path = BUNDLE) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    manifest_path = bundle / "manifest.json"
    license_path = bundle / "LICENSE.txt"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {}, [f"cannot read Pretendard manifest: {error}"]
    if manifest.get("schemaVersion") != "1.0.0":
        errors.append("Pretendard manifest schemaVersion must be 1.0.0")
    if manifest.get("family") != "Pretendard":
        errors.append("Pretendard manifest family mismatch")
    if manifest.get("version") != "1.3.9":
        errors.append("Pretendard manifest version mismatch")
    try:
        license_text = license_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        errors.append(f"Pretendard license is missing: {error}")
    else:
        if "SIL OPEN FONT LICENSE Version 1.1" not in license_text:
            errors.append("Pretendard SIL Open Font License 1.1 text is invalid")
    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        errors.append("Pretendard manifest files must be a non-empty array")
        records = []
    seen_paths: set[str] = set()
    seen_weights: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            errors.append("Pretendard file record must be an object")
            continue
        relative = record.get("path")
        weight = record.get("weight")
        if (
            not isinstance(relative, str)
            or Path(relative).name != relative
            or not relative.endswith(".otf")
        ):
            errors.append(f"invalid Pretendard font path: {relative!r}")
            continue
        if relative in seen_paths:
            errors.append(f"duplicate Pretendard font path: {relative}")
        seen_paths.add(relative)
        if not isinstance(weight, int) or weight not in {400, 500, 600, 700}:
            errors.append(f"invalid Pretendard font weight: {weight!r}")
        elif weight in seen_weights:
            errors.append(f"duplicate Pretendard font weight: {weight}")
        seen_weights.add(weight)
        font_path = bundle / relative
        if not font_path.is_file():
            errors.append(f"bundled Pretendard font is missing: {relative}")
            continue
        if font_path.read_bytes()[:4] != b"OTTO":
            errors.append(f"bundled Pretendard font is not OpenType: {relative}")
        if record.get("sha256") != sha256(font_path):
            errors.append(f"bundled Pretendard font digest mismatch: {relative}")
    if seen_weights != {400, 500, 600, 700}:
        errors.append("bundled Pretendard weights must be exactly 400, 500, 600, 700")
    return manifest, errors


def default_target() -> Path:
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise ValueError("LOCALAPPDATA is required for user-scope Windows fonts")
        return Path(local_app_data) / "Microsoft" / "Windows" / "Fonts"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Fonts"
    data_home = os.environ.get("XDG_DATA_HOME")
    return (Path(data_home) if data_home else Path.home() / ".local" / "share") / "fonts"


def installed_state(
    manifest: dict[str, Any],
    target: Path,
) -> tuple[bool, list[dict[str, Any]]]:
    records = []
    all_installed = True
    for record in manifest.get("files", []):
        destination = target / record["path"]
        valid = destination.is_file() and sha256(destination) == record["sha256"]
        all_installed = all_installed and valid
        records.append(
            {
                "path": str(destination),
                "weight": record["weight"],
                "installed": valid,
                "sha256": sha256(destination) if destination.is_file() else None,
            }
        )
    return all_installed, records


def register_windows_fonts(manifest: dict[str, Any], target: Path) -> None:
    import winreg

    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
        for record in manifest["files"]:
            stem = Path(record["path"]).stem.replace("Pretendard-", "")
            name = f"Pretendard {stem} (OpenType)"
            winreg.SetValueEx(
                key,
                name,
                0,
                winreg.REG_SZ,
                str((target / record["path"]).resolve()),
            )
    hwnd_broadcast = 0xFFFF
    wm_fontchange = 0x001D
    smto_abortifhung = 0x0002
    result = ctypes.c_size_t()
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_fontchange,
        0,
        0,
        smto_abortifhung,
        5000,
        ctypes.byref(result),
    )


def refresh_font_cache(target: Path) -> None:
    if sys.platform == "win32":
        return
    executable = shutil.which("fc-cache")
    if executable:
        subprocess.run(
            [executable, "-f", str(target)],
            check=True,
            capture_output=True,
            text=True,
        )


def windows_registration_state(
    manifest: dict[str, Any],
    target: Path,
) -> bool:
    if sys.platform != "win32":
        return True
    import winreg

    registry_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
            for record in manifest["files"]:
                stem = Path(record["path"]).stem.replace("Pretendard-", "")
                value, value_type = winreg.QueryValueEx(
                    key,
                    f"Pretendard {stem} (OpenType)",
                )
                if (
                    value_type != winreg.REG_SZ
                    or Path(value).resolve()
                    != (target / record["path"]).resolve()
                ):
                    return False
    except (FileNotFoundError, OSError):
        return False
    return True


def install_fonts(
    bundle: Path = BUNDLE,
    target: Path | None = None,
    register: bool = True,
) -> dict[str, Any]:
    manifest, errors = load_bundle(bundle)
    if errors:
        return {"status": "BLOCK", "errors": errors}
    destination_root = (target or default_target()).expanduser().resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    changed = []
    for record in manifest["files"]:
        source = bundle / record["path"]
        destination = destination_root / record["path"]
        if not destination.is_file() or sha256(destination) != record["sha256"]:
            shutil.copyfile(source, destination)
            changed.append(record["path"])
    if register and target is None and sys.platform == "win32":
        register_windows_fonts(manifest, destination_root)
    elif register and target is None:
        refresh_font_cache(destination_root)
    installed, files = installed_state(manifest, destination_root)
    registered = (
        windows_registration_state(manifest, destination_root)
        if register and target is None
        else True
    )
    return {
        "status": "PASS" if installed and registered else "BLOCK",
        "family": manifest["family"],
        "version": manifest["version"],
        "license": manifest["license"],
        "target": str(destination_root),
        "changed": changed,
        "installed": installed,
        "registered": registered,
        "files": files,
        "errors": (
            []
            if installed and registered
            else ["installed font digest or user-scope registration verification failed"]
        ),
    }


def report_for(action: str, target: Path | None) -> dict[str, Any]:
    manifest, errors = load_bundle()
    if action == "verify-bundle":
        return {
            "status": "PASS" if not errors else "BLOCK",
            "family": manifest.get("family"),
            "version": manifest.get("version"),
            "bundle": str(BUNDLE),
            "errors": errors,
        }
    if errors:
        return {"status": "BLOCK", "errors": errors}
    destination = (target or default_target()).expanduser().resolve()
    if action == "check":
        installed, files = installed_state(manifest, destination)
        registered = (
            windows_registration_state(manifest, destination)
            if target is None
            else True
        )
        return {
            "status": "PASS" if installed and registered else "BLOCK",
            "family": manifest["family"],
            "version": manifest["version"],
            "target": str(destination),
            "installed": installed,
            "registered": registered,
            "files": files,
            "errors": (
                []
                if installed and registered
                else ["Pretendard is not installed and registered at user scope"]
            ),
        }
    return install_fonts(target=target, register=target is None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify or install bundled Pretendard fonts at user scope."
    )
    parser.add_argument("action", choices=("verify-bundle", "check", "install"))
    parser.add_argument(
        "--target-dir",
        type=Path,
        help="isolated target for tests; skips OS font registration",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    report = report_for(args.action, args.target_dir)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

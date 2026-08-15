from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


class RollbackError(ValueError):
    pass


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RollbackError(f"cannot read rollback record: {exc}") from exc


def safe_members(archive: zipfile.ZipFile) -> list[str]:
    names = archive.namelist()
    if not names or len(names) != len(set(names)):
        raise RollbackError("rollback archive member list is empty or duplicated")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "" in path.parts:
            raise RollbackError(f"unsafe rollback archive member: {name}")
    return names


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "dayoun-rollback-rehearsal/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except OSError as exc:
        raise RollbackError(f"cannot download immutable last-verified artifact: {exc}") from exc


def rehearse(record: dict[str, Any], *, target: str, candidate: Path | None) -> dict[str, Any]:
    if record.get("target") != target:
        raise RollbackError("rollback record belongs to another target")
    status = record.get("status")
    if status == "IMMUTABLE_RELEASE":
        data = download(str(record.get("artifactUrl", "")))
        if digest_bytes(data) != record.get("artifactDigest"):
            raise RollbackError("last-verified artifact digest mismatch")
        archive_name = str(record.get("artifactName", "last-verified.zip"))
    elif status == "BOOTSTRAP_NO_PREVIOUS_RELEASE":
        if candidate is None:
            raise RollbackError("bootstrap rollback requires the qualified candidate directory")
        archives = list(candidate.glob("*.zip"))
        if len(archives) != 1:
            raise RollbackError("bootstrap rollback requires exactly one candidate archive")
        archive_name = archives[0].name
        data = archives[0].read_bytes()
    else:
        raise RollbackError("unsupported rollback record status")
    temp_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix=f"dayoun-rollback-{target}-") as directory:
        temp_path = Path(directory)
        archive_path = temp_path / archive_name
        archive_path.write_bytes(data)
        installed = temp_path / "installed"
        installed.mkdir()
        try:
            with zipfile.ZipFile(archive_path) as archive:
                safe_members(archive)
                archive.extractall(installed)
        except zipfile.BadZipFile as exc:
            raise RollbackError("rollback artifact is not a valid ZIP") from exc
        archive_root = installed / str(record.get("archiveRoot", ""))
        for relative in record.get("requiredPaths", []):
            if not (archive_root / relative).exists():
                raise RollbackError(f"rollback smoke path missing: {relative}")
        for relative in record.get("forbiddenPaths", []):
            if (archive_root / relative).exists():
                raise RollbackError(f"rollback smoke found forbidden path: {relative}")
        plugin_path = record.get("pluginManifest")
        if plugin_path:
            plugin = load(archive_root / str(plugin_path))
            if plugin.get("name") != record.get("pluginName"):
                raise RollbackError("rollback plugin identity mismatch")
        shutil.rmtree(installed)
        if installed.exists():
            raise RollbackError("rollback uninstall/remove rehearsal failed")
    if temp_path is None or temp_path.exists():
        raise RollbackError("rollback clean-home was not removed")
    return {
        "status": "PASS",
        "target": target,
        "rollbackRecordStatus": status,
        "artifactDigest": digest_bytes(data),
        "installSmokeRemove": True,
        "cleanHomeRemoved": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehearse immutable target rollback in a clean temporary home")
    parser.add_argument("--target", required=True)
    parser.add_argument("--last-verified", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--clean-home", action="store_true")
    parser.add_argument("--install-smoke-remove", action="store_true")
    parser.add_argument("--ppt-modes")
    args = parser.parse_args()
    if not args.clean_home or not args.install_smoke_remove:
        print("BLOCK: rollback must use clean-home install/smoke/remove", file=sys.stderr)
        return 2
    try:
        result = rehearse(load(args.last_verified), target=args.target, candidate=args.candidate)
    except RollbackError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "business-plan-writer"
EXPECTED_SKILLS = 8
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def run_check(script_name: str) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{script_name} failed:\n{result.stdout}{result.stderr}")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    relative_paths = [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    missing = [path for path in relative_paths if not (ROOT / path).is_file()]
    if missing:
        raise RuntimeError(f"tracked files missing from worktree: {missing[:3]}")
    return sorted(relative_paths, key=lambda path: path.as_posix())


def validate_release_tree(version: str) -> None:
    skill_dirs = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
    if len(skill_dirs) != EXPECTED_SKILLS or "create-business-documents" not in skill_dirs:
        raise RuntimeError(f"expected {EXPECTED_SKILLS} skills including create-business-documents, got {skill_dirs}")
    for manifest in (
        PLUGIN / "plugin.json",
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
    ):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if payload.get("version") != version:
            raise RuntimeError(f"version mismatch in {manifest.relative_to(ROOT)}")


def build(output_dir: Path) -> Path:
    run_check("sync_starter_skills.py")
    run_check("sync_starter_project.py")
    version = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))["version"]
    validate_release_tree(version)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"dayoun-marketplace-v{version}.zip"
    root_name = f"dayoun-marketplace-v{version}"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for relative in tracked_files():
            info = zipfile.ZipInfo(f"{root_name}/{relative.as_posix()}", FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, (ROOT / relative).read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    print(f"ARCHIVE: {archive}")
    print(f"SHA256: {digest}")
    print(f"SKILLS: {EXPECTED_SKILLS}")
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic marketplace release archive.")
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()
    try:
        build(Path(args.output_dir))
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

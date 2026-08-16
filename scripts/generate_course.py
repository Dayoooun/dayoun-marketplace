from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "course-src"
OUTPUT_ROOT = REPO_ROOT / "course"
CONTRACT_ROOT = REPO_ROOT / "contracts"


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def comparable_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if b"\0" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"missing authored course source: {source}")
    shutil.copytree(
        source,
        target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"),
    )


def build_course(target: Path) -> dict[str, object]:
    target.mkdir(parents=True, exist_ok=True)
    copy_tree(SOURCE_ROOT / "content", target)
    copy_tree(SOURCE_ROOT / "starter-project", target / "starter-project")
    plugin_skills = REPO_ROOT / "plugins" / "business-plan-writer" / "skills"
    copy_tree(plugin_skills, target / "starter-project" / ".agents" / "skills")
    copy_tree(plugin_skills, target / "starter-project" / ".claude" / "skills")
    plugin_validators = REPO_ROOT / "plugins" / "business-plan-writer" / "validators"
    copy_tree(plugin_validators, target / "starter-project" / ".dayoun" / "validators")
    copy_tree(
        CONTRACT_ROOT / "schemas",
        target / "starter-project" / ".dayoun" / "_contracts" / "schemas",
    )
    copy_tree(
        CONTRACT_ROOT / "policies",
        target / "starter-project" / ".dayoun" / "_contracts" / "policies",
    )
    copy_tree(SOURCE_ROOT / "completed-project", target / "completed-project")
    copy_tree(SOURCE_ROOT / "offline-evidence-pack", target / "offline-evidence-pack")
    copy_tree(CONTRACT_ROOT / "schemas", target / "_contracts" / "schemas")
    copy_tree(CONTRACT_ROOT / "policies", target / "_contracts" / "policies")
    forbidden = [path for path in target.rglob("*") if "internal" in path.parts or "materials-backlog" in path.name]
    if forbidden:
        raise ValueError(f"internal course files leaked: {[str(path) for path in forbidden]}")
    members = {
        path.relative_to(target).as_posix(): file_sha256(path)
        for path in sorted(target.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schemaVersion": "1.0.0",
        "artifact": "business-plan-course-kit",
        "version": "0.1.0",
        "members": members,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def compare_directories(expected: Path, actual: Path) -> list[str]:
    expected_files = {
        path.relative_to(expected).as_posix(): comparable_bytes(path)
        for path in expected.rglob("*")
        if path.is_file()
    }
    actual_files = {
        path.relative_to(actual).as_posix(): comparable_bytes(path)
        for path in actual.rglob("*")
        if path.is_file()
    }
    issues: list[str] = []
    for name in sorted(set(expected_files) | set(actual_files)):
        if name not in expected_files:
            issues.append(f"unexpected:{name}")
        elif name not in actual_files:
            issues.append(f"missing:{name}")
        elif expected_files[name] != actual_files[name]:
            issues.append(f"drift:{name}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the public course kit from authored sources")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="dayoun-course-") as directory:
            expected = Path(directory) / "course"
            build_course(expected)
            issues = compare_directories(expected, OUTPUT_ROOT)
        if issues:
            print("BLOCK: generated course drift: " + ", ".join(issues), file=sys.stderr)
            return 1
        print("PASS: generated course matches authored sources")
        return 0
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    build_course(OUTPUT_ROOT)
    print(f"Generated {OUTPUT_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

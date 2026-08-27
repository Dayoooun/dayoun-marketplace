from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "course-src"
OUTPUT_ROOT = REPO_ROOT / "course"
CONTRACT_ROOT = REPO_ROOT / "contracts"


def comparable_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if b"\0" in data:
        return data
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(comparable_bytes(path)).hexdigest()


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
    plugin_fonts = REPO_ROOT / "plugins" / "business-plan-writer" / "assets" / "fonts"
    copy_tree(plugin_fonts, target / "starter-project" / ".agents" / "assets" / "fonts")
    copy_tree(plugin_fonts, target / "starter-project" / ".claude" / "assets" / "fonts")
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
        # manifest 키도 NFC 로 고정한다. macOS 에서 만든 매니페스트와
        # Linux CI 에서 만든 매니페스트가 같은 digest 집합을 갖게 한다.
        unicodedata.normalize("NFC", path.relative_to(target).as_posix()): file_sha256(path)
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
    # macOS(APFS)는 파일명을 NFD 로 저장하고 Linux/Windows 는 입력한 NFC 를 유지한다.
    # 경로를 정규화하지 않고 비교하면 같은 한글 파일이 서로 다른 키가 되어
    # 전 파일이 missing+unexpected 로 잡힌다 — 내용은 동일한데 BLOCK 이 난다.
    # 임시 디렉터리에 새로 빌드한 쪽과 워킹트리 쪽의 정규화가 갈릴 때 재현된다.
    def collect(root: Path) -> dict[str, bytes]:
        return {
            unicodedata.normalize("NFC", path.relative_to(root).as_posix()): comparable_bytes(path)
            for path in root.rglob("*")
            if path.is_file()
        }

    expected_files = collect(expected)
    actual_files = collect(actual)
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

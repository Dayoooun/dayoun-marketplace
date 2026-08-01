#!/usr/bin/env python3
"""Keep the offline starter skills byte-identical to the plugin skills."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins" / "modoo-startup-plan" / "skills"
TARGET = ROOT / "fallback" / "starter-project" / ".agents" / "skills"


def files(root: Path) -> dict[str, Path]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): path
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="플러그인 스킬과 스타터 스킬 동기화")
    parser.add_argument(
        "--write",
        action="store_true",
        help="누락되거나 다른 스타터 파일을 플러그인 원본으로 갱신",
    )
    args = parser.parse_args()

    source_files = files(SOURCE)
    target_files = files(TARGET)
    missing = sorted(set(source_files) - set(target_files))
    extra = sorted(set(target_files) - set(source_files))
    different = sorted(
        relative
        for relative in set(source_files) & set(target_files)
        if source_files[relative].read_bytes() != target_files[relative].read_bytes()
    )

    if args.write:
        for relative in missing + different:
            target = TARGET / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_files[relative], target)
            print(f"SYNCED: {relative}")
        if extra:
            print("EXTRA files are never deleted automatically:")
            for relative in extra:
                print(f"  - {relative}")
            return 2
        print(f"SYNC_COMPLETE: {len(missing) + len(different)}")
        return 0

    if missing or extra or different:
        for label, items in (
            ("MISSING", missing),
            ("EXTRA", extra),
            ("DIFFERENT", different),
        ):
            for relative in items:
                print(f"{label}: {relative}")
        return 1

    print(f"SYNC_OK: {len(source_files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

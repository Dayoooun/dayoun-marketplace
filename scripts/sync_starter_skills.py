#!/usr/bin/env python3
"""Keep every offline starter skill tree byte-identical to plugin skills."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins" / "business-plan-writer" / "skills"
TARGETS = {
    "agents": ROOT / "fallback" / "starter-project" / ".agents" / "skills",
    "claude": ROOT / "fallback" / "starter-project" / ".claude" / "skills",
}


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
    has_error = False
    changed = 0

    for target_name, target_root in TARGETS.items():
        target_files = files(target_root)
        missing = sorted(set(source_files) - set(target_files))
        extra = sorted(set(target_files) - set(source_files))
        different = sorted(
            relative
            for relative in set(source_files) & set(target_files)
            if source_files[relative].read_bytes()
            != target_files[relative].read_bytes()
        )

        if args.write:
            for relative in missing + different:
                target = target_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_files[relative], target)
                print(f"SYNCED [{target_name}]: {relative}")
                changed += 1
            if extra:
                print(f"EXTRA files in [{target_name}] are never deleted automatically:")
                for relative in extra:
                    print(f"  - {relative}")
                has_error = True
            continue

        if missing or extra or different:
            has_error = True
            for label, items in (
                ("MISSING", missing),
                ("EXTRA", extra),
                ("DIFFERENT", different),
            ):
                for relative in items:
                    print(f"{label} [{target_name}]: {relative}")
        else:
            print(f"SYNC_OK [{target_name}]: {len(source_files)} files")

    if args.write:
        print(f"SYNC_COMPLETE: {changed}")
    return 2 if has_error and args.write else int(has_error)


if __name__ == "__main__":
    raise SystemExit(main())

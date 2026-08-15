from __future__ import annotations

import argparse
import sys
from pathlib import Path

from generate_course import OUTPUT_ROOT, main as generate_main

FORBIDDEN_NAMES = {"materials-backlog.md"}
FORBIDDEN_PARTS = {"internal", "fallback"}


def find_forbidden(root: Path) -> list[str]:
    return [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if any(part in FORBIDDEN_PARTS for part in path.relative_to(root).parts)
        or path.name in FORBIDDEN_NAMES
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check generated course drift and internal-file exclusion")
    parser.add_argument("--forbid-internal", action="store_true")
    args = parser.parse_args()
    if args.forbid_internal:
        forbidden = find_forbidden(OUTPUT_ROOT)
        if forbidden:
            print("BLOCK: internal course files leaked: " + ", ".join(forbidden), file=sys.stderr)
            return 1
    original = sys.argv
    try:
        sys.argv = ["generate_course.py", "--check"]
        return generate_main()
    finally:
        sys.argv = original


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def only(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern} in {directory}, got {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two deterministic target artifact builds")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--target", required=True)
    parser.add_argument("--compare-archive-sha", action="store_true")
    parser.add_argument("--compare-member-manifests", action="store_true")
    args = parser.parse_args()
    try:
        left_archive = only(args.left, "*.zip")
        right_archive = only(args.right, "*.zip")
        blockers: list[str] = []
        if args.compare_archive_sha and digest(left_archive) != digest(right_archive):
            blockers.append("archive-sha-mismatch")
        if args.compare_member_manifests:
            left_manifest = json.loads(only(args.left, "*.members.json").read_text(encoding="utf-8"))
            right_manifest = json.loads(only(args.right, "*.members.json").read_text(encoding="utf-8"))
            if left_manifest != right_manifest:
                blockers.append("member-manifest-mismatch")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    result = {"status": "BLOCK" if blockers else "PASS", "target": args.target, "blockers": blockers}
    print(json.dumps(result, indent=2))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())

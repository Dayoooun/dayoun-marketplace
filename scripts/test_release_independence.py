from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def evaluate(target: str, unavailable: set[str], failed: set[str]) -> dict[str, object]:
    manifest_path = REPO_ROOT / "release" / "manifests" / f"{target}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = set(manifest["required"])
    forbidden = set(manifest["forbiddenReads"])
    access_log = sorted(required)
    blockers = sorted((unavailable | failed) & required)
    illegal_reads = sorted(set(access_log) & forbidden)
    if illegal_reads:
        blockers.extend(f"forbidden-read:{name}" for name in illegal_reads)
    return {
        "target": target,
        "required": sorted(required),
        "forbiddenReads": sorted(forbidden),
        "accessLog": access_log,
        "status": "BLOCK" if blockers else "PASS",
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove target-scoped release independence")
    parser.add_argument("--target", required=True)
    parser.add_argument("--unavailable", default="")
    parser.add_argument("--fail", default="")
    parser.add_argument("--expect-pass", action="store_true")
    parser.add_argument("--expect-block", action="store_true")
    parser.add_argument("--expect-zero-read", default="")
    args = parser.parse_args()
    try:
        unavailable = {item for item in args.unavailable.split(",") if item}
        failed = {item for item in args.fail.split(",") if item}
        result = evaluate(args.target, unavailable, failed)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    zero_read = {item for item in args.expect_zero_read.split(",") if item}
    read_names = set(result["accessLog"])
    if zero_read & read_names:
        result["status"] = "BLOCK"
        result["blockers"].append(f"unexpected-read:{','.join(sorted(zero_read & read_names))}")
    expected = "PASS" if args.expect_pass else "BLOCK" if args.expect_block else None
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if expected and result["status"] != expected:
        return 1
    return 0 if result["status"] == "PASS" else (0 if args.expect_block else 1)


if __name__ == "__main__":
    raise SystemExit(main())

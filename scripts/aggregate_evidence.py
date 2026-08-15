from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class AggregateError(ValueError):
    pass


def load_pass(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AggregateError(f"missing or invalid evidence {path}: {exc}") from exc
    if data.get("status") != "PASS":
        raise AggregateError(f"evidence is not PASS: {path.name}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate target-scoped release evidence")
    parser.add_argument("--target", required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-approved-tuple", action="store_true")
    parser.add_argument("--require-mode-evidence")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    if not args.strict or not args.require_approved_tuple:
        print("BLOCK: strict approved-tuple aggregation is mandatory", file=sys.stderr)
        return 2
    try:
        closure = json.loads(args.closure.read_text(encoding="utf-8"))
        if closure.get("target") != args.target:
            raise AggregateError("closure target mismatch")
        required = {
            "business-plan-writer": ["provider-summary.json", "course-summary.json", "beta-summary.json", "visual-summary.json"],
            "business-documents": ["documents-summary.json"],
            "course-kit": ["course-summary.json"],
            "contracts": ["contracts-summary.json"],
        }[args.target]
        records = {name: load_pass(args.evidence / name) for name in required}
        if args.target == "business-plan-writer" and records["provider-summary.json"].get("runCount") != 30:
            raise AggregateError("writer requires 30 real-provider runs")
        if args.require_mode_evidence:
            expected_modes = set(args.require_mode_evidence.split(","))
            actual_modes = set(records.get("visual-summary.json", {}).get("rendererModes", []))
            if actual_modes != expected_modes:
                raise AggregateError("visual evidence does not cover both approved PPT modes")
        forbidden = set(closure.get("forbiddenReads", []))
        if forbidden & set(closure.get("required", [])):
            raise AggregateError("closure requires a forbidden unrelated artifact")
        result = {
            "schemaVersion": "1.0.0",
            "status": "PASS",
            "target": args.target,
            "requiredClosure": closure.get("required", []),
            "forbiddenReads": sorted(forbidden),
            "evidenceFiles": required,
        }
    except (OSError, json.JSONDecodeError, KeyError, AggregateError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

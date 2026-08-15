from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validator_common import ValidatorError, load_json, verdict, write_result


def _unique_ids(items: Any, label: str, blockers: list[str]) -> set[str]:
    if not isinstance(items, list):
        blockers.append(f"{label}-not-list")
        return set()
    values = [str(item.get("id", "")) for item in items if isinstance(item, dict)]
    if len(values) != len(items) or "" in values or len(values) != len(set(values)):
        blockers.append(f"{label}-duplicate-or-empty-id")
    return set(values)


def validate_facts(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    evidence_ids = _unique_ids(payload.get("evidence"), "evidence", blockers)
    _unique_ids(payload.get("facts"), "facts", blockers)
    _unique_ids(payload.get("requirements"), "requirements", blockers)
    _unique_ids(payload.get("decisions"), "decisions", blockers)
    _unique_ids(payload.get("businessVerdicts"), "business-verdicts", blockers)
    for fact in payload.get("facts", []):
        missing = set(fact.get("evidenceRefs", [])) - evidence_ids
        if missing:
            blockers.append(f"fact-{fact.get('id')}-unknown-evidence:{','.join(sorted(missing))}")
    for item in payload.get("businessVerdicts", []):
        missing = set(item.get("evidenceRefs", [])) - evidence_ids
        if missing:
            blockers.append(f"verdict-{item.get('id')}-unknown-evidence:{','.join(sorted(missing))}")
        if item.get("status") in {"BLOCK", "NOT_REVIEWED"}:
            blockers.append(f"verdict-{item.get('id')}-{item.get('status')}")
    for step in payload.get("contentSteps", []):
        missing = set(step.get("evidenceRefs", [])) - evidence_ids
        if missing:
            blockers.append(f"step-{step.get('id')}-unknown-evidence:{','.join(sorted(missing))}")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent evidence-reference and fact validator")
    parser.add_argument("payload", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = load_json(args.payload)
        result = verdict("fact-validator", args.payload, validate_facts(payload))
        write_result(result, args.output)
    except ValidatorError as exc:
        print(f"BLOCK: {exc}")
        return 1
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

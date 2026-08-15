from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from validator_common import ValidatorError, load_json, verdict, write_result

EMBEDDED_POLICY = Path(__file__).resolve().parents[1] / "_contracts" / "policies" / "scope-steps.json"


def validate_structure(payload: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    scope = payload.get("scope")
    scope_policy = policy.get("scopes", {}).get(scope)
    if not isinstance(scope_policy, dict):
        return [f"unsupported-scope:{scope}"]
    steps = payload.get("contentSteps")
    if not isinstance(steps, list):
        return ["content-steps-not-list"]
    step_ids = [str(item.get("id", "")) for item in steps if isinstance(item, dict)]
    if len(step_ids) != len(steps) or "" in step_ids or len(step_ids) != len(set(step_ids)):
        blockers.append("content-step-duplicate-or-empty-id")
    by_id = {str(item.get("id")): item for item in steps if isinstance(item, dict)}
    required = set(scope_policy["requiredContentSteps"])
    all_known = {
        step_id
        for item in policy.get("scopes", {}).values()
        for step_id in item.get("requiredContentSteps", [])
    }
    unknown = set(by_id) - all_known
    if unknown:
        blockers.append("unknown-content-steps:" + ",".join(sorted(unknown)))
    for step_id in sorted(required):
        if by_id.get(step_id, {}).get("status") != "PASS":
            blockers.append(f"required-step-not-pass:{step_id}")
    for step_id in sorted(set(by_id) - required):
        if by_id[step_id].get("status") != "NOT_REVIEWED":
            blockers.append(f"out-of-scope-step-not-not-reviewed:{step_id}")
    if scope == "SECTION" and not payload.get("sectionId"):
        blockers.append("section-id-missing")
    outputs = payload.get("outputs", {})
    mode = payload.get("rendererMode")
    if outputs.get("ppt") is True and mode not in {"scene-deck", "image-first"}:
        blockers.append("ppt-renderer-mode-missing")
    if outputs.get("ppt") is not True and mode is not None:
        blockers.append("renderer-mode-without-ppt")
    if set(outputs) != {"hwpx", "ppt"} or not all(isinstance(value, bool) for value in outputs.values()):
        blockers.append("output-selection-invalid")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent scope and output-structure validator")
    parser.add_argument("payload", type=Path)
    parser.add_argument("--policy", type=Path, default=EMBEDDED_POLICY)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = load_json(args.payload)
        policy = load_json(args.policy)
        result = verdict("structure-validator", args.payload, validate_structure(payload, policy))
        write_result(result, args.output)
    except ValidatorError as exc:
        print(f"BLOCK: {exc}")
        return 1
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

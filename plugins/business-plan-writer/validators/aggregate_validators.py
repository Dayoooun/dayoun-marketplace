from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validator_common import ValidatorError, load_json

EXPECTED = {
    "fact": "fact-validator",
    "structure": "structure-validator",
    "contract": "contract-validator",
}


def aggregate(
    records: dict[str, dict[str, Any]],
    outputs: dict[str, Any],
    *,
    cycle_id: str,
    approval_revision: int,
    approval_digest: str,
    attempt: int,
) -> dict[str, Any]:
    blockers: list[str] = []
    artifact_digests: set[str] = set()
    validator_records: dict[str, Any] = {}
    for role, validator_id in EXPECTED.items():
        record = records.get(role, {})
        if record.get("validatorId") != validator_id:
            blockers.append(f"validator-identity:{role}")
        if record.get("status") != "PASS":
            blockers.append(f"validator-not-pass:{role}")
        if record.get("artifactDigest"):
            artifact_digests.add(str(record["artifactDigest"]))
        validator_records[role] = {
            key: record[key]
            for key in ("status", "validatorId", "validatorVersion", "evidenceRefs", "artifactDigest", "reason")
            if key in record
        }
    if len(artifact_digests) != 1:
        blockers.append("validator-artifact-digest-disagreement")
    if set(outputs) != {"hwpx", "ppt"}:
        blockers.append("output-verdict-axes-invalid")
    for output, record in outputs.items():
        if not record.get("requested"):
            if record.get("automationStatus") != "NOT_REQUESTED" or record.get("visualStatus") != "NOT_REQUESTED":
                blockers.append(f"unrequested-output-not-not-requested:{output}")
        elif record.get("automationStatus") != "PASS" or record.get("visualStatus") != "PASS":
            blockers.append(f"requested-output-not-pass:{output}")
    stale_approval = "STALE_APPROVAL" in str(records.get("contract", {}).get("reason", ""))
    if stale_approval:
        status = "STALE_APPROVAL"
    elif attempt == 2 and blockers:
        status = "REJECTED"
    else:
        status = "PASS" if not blockers else "BLOCK"
    return {
        "schemaVersion": "1.0.0",
        "cycleId": cycle_id,
        "approvalRevision": approval_revision,
        "approvalEnvelopeDigest": approval_digest,
        "attempt": attempt,
        "validators": validator_records,
        "outputs": outputs,
        "approvalStatus": "STALE" if stale_approval else "CURRENT",
        "aggregateStatus": status,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict no-override aggregation of three independent validators")
    parser.add_argument("--fact", type=Path, required=True)
    parser.add_argument("--structure", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--approval-revision", type=int, required=True)
    parser.add_argument("--approval-digest", required=True)
    parser.add_argument("--attempt", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = aggregate(
            {
                "fact": load_json(args.fact),
                "structure": load_json(args.structure),
                "contract": load_json(args.contract),
            },
            load_json(args.outputs),
            cycle_id=args.cycle_id,
            approval_revision=args.approval_revision,
            approval_digest=args.approval_digest,
            attempt=args.attempt,
        )
    except ValidatorError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["aggregateStatus"])
    return 0 if result["aggregateStatus"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any
from contract_utils import canonical_digest

PROVIDER_ALLOCATION = {"codex": 4, "claude-code": 3, "antigravity": 3}
SCOPE_ALLOCATION = {"QUICK": 5, "SECTION": 5}
CRITICAL_CODES = {f"C{number}" for number in range(1, 7)}


class BetaEvidenceError(ValueError):
    pass


def _digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("sha256:")
        and len(value) == 71
    )


def _passed_evidence(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("status") == "PASS"
        and _digest(value.get("evidenceDigest"))
        and isinstance(value.get("evidenceRef"), str)
        and bool(value["evidenceRef"])
    )


def aggregate_beta(evidence: dict[str, Any]) -> dict[str, Any]:
    participants = evidence.get("participants")
    if not isinstance(participants, list) or len(participants) != 10:
        raise BetaEvidenceError("external beta requires exactly ten frozen ITT participants")
    roster = evidence.get("roster")
    if not isinstance(roster, list) or len(roster) != 10:
        raise BetaEvidenceError("external beta requires a frozen ten-person roster")
    if evidence.get("rosterDigest") != canonical_digest(roster):
        raise BetaEvidenceError("beta roster digest mismatch")
    try:
        roster_frozen_at = datetime.fromisoformat(str(evidence["rosterFrozenAt"]))
    except (KeyError, ValueError) as exc:
        raise BetaEvidenceError("beta roster freeze timestamp is invalid") from exc
    roster_ids = [str(item.get("participantId", "")) for item in roster]
    participant_ids = [str(item.get("participantId", "")) for item in participants]
    if (
        "" in roster_ids
        or len(set(roster_ids)) != 10
        or "" in participant_ids
        or len(set(participant_ids)) != 10
    ):
        raise BetaEvidenceError("roster and participant identities must be non-empty and unique")
    roster_assignment = {
        str(item["participantId"]): (item.get("provider"), item.get("scope"))
        for item in roster
    }
    participant_assignment = {
        str(item["participantId"]): (item.get("provider"), item.get("scope"))
        for item in participants
    }
    if participant_assignment != roster_assignment:
        raise BetaEvidenceError("participant assignments changed after ITT roster freeze")
    for participant in participants:
        try:
            started_at = datetime.fromisoformat(str(participant["startedAt"]))
        except (KeyError, ValueError) as exc:
            raise BetaEvidenceError("participant start timestamp is invalid") from exc
        if started_at <= roster_frozen_at:
            raise BetaEvidenceError("participant started before the roster freeze")
    provider_counts = collections.Counter(str(item.get("provider")) for item in participants)
    scope_counts = collections.Counter(str(item.get("scope")) for item in participants)
    blockers: list[str] = []
    if dict(provider_counts) != PROVIDER_ALLOCATION:
        blockers.append(f"provider-allocation:{dict(provider_counts)}")
    if dict(scope_counts) != SCOPE_ALLOCATION:
        blockers.append(f"scope-allocation:{dict(scope_counts)}")
    completed = 0
    completed_by_provider: collections.Counter[str] = collections.Counter()
    results: list[dict[str, Any]] = []
    for item in participants:
        participant_id = str(item.get("participantId", ""))
        if not participant_id or item.get("consent") is not True or item.get("preRecord") is not True:
            blockers.append(f"invalid-itt-starter:{participant_id or '<missing>'}")
        attempts = item.get("attempts", [])
        if not isinstance(attempts, list) or not attempts or len(attempts) > 2:
            blockers.append(f"invalid-attempt-count:{participant_id}")
            attempts = []
        if len(attempts) == 2 and attempts[0].get("failureClass") != "INFRASTRUCTURE":
            blockers.append(f"non-infrastructure-retry:{participant_id}")
        final = attempts[-1] if attempts else {}
        selected = final.get("selectedOutputs")
        if (
            not isinstance(selected, dict)
            or set(selected) != {"hwpx", "ppt"}
            or any(type(value) is not bool for value in selected.values())
            or not any(selected.values())
        ):
            blockers.append(f"invalid-selected-outputs:{participant_id}")
            selected = {"hwpx": False, "ppt": False}
        outputs_pass = True
        for output, requested in selected.items():
            if not requested:
                continue
            automation = final.get("outputAutomation", {}).get(output, {})
            visual = final.get("outputVisual", {}).get(output, {})
            if not _passed_evidence(automation) or not _passed_evidence(visual):
                outputs_pass = False
        validators = final.get("validators", {})
        validators_pass = all(
            _passed_evidence(validators.get(role))
            for role in ("fact", "structure", "contract")
        )
        complete = bool(final.get("scopeComplete")) and outputs_pass and validators_pass
        if complete:
            completed += 1
            completed_by_provider[str(item.get("provider"))] += 1
        results.append({"participantId": participant_id, "complete": complete})
    if completed < 8:
        blockers.append(f"completion:{completed}<8")
    for provider in PROVIDER_ALLOCATION:
        if completed_by_provider[provider] < 2:
            blockers.append(f"provider-floor:{provider}:{completed_by_provider[provider]}<2")
    defects = evidence.get("criticalDefects")
    if not isinstance(defects, list):
        blockers.append("missing-critical-defect-ledger")
        defects = []
    for defect in defects:
        code = defect.get("code")
        if code not in CRITICAL_CODES:
            blockers.append(f"unknown-critical-code:{code}")
        else:
            if not defect.get("qaLeadDecision") or not defect.get("releaseOwnerRecord"):
                blockers.append(f"unowned-critical-defect:{code}")
            blockers.append(f"critical-defect:{code}")
    return {
        "schemaVersion": "1.0.0",
        "participants": 10,
        "providerAllocation": PROVIDER_ALLOCATION,
        "scopeAllocation": SCOPE_ALLOCATION,
        "complete": completed,
        "completedByProvider": dict(completed_by_provider),
        "participantResults": results,
        "status": "BLOCK" if blockers else "PASS",
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate the locked external beta release gate")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = aggregate_beta(json.loads(args.evidence.read_text(encoding="utf-8")))
        result["sourceEvidenceDigest"] = (
            "sha256:" + hashlib.sha256(args.evidence.read_bytes()).hexdigest()
        )
        result["sourceEvidenceRef"] = args.evidence.name
    except (OSError, json.JSONDecodeError, BetaEvidenceError, TypeError, ValueError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

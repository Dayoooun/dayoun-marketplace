from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from datetime import datetime
from typing import Any
from contract_utils import canonical_digest
REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_FIXTURE = REPO_ROOT / "contracts" / "fixtures" / "course-calibration.json"

RUBRIC_KEYS = ("gapDiagnosis", "evidenceRecord", "changeRecord", "actionCard")
SAFETY_CODES = ("S1", "S2", "S3", "S4")


class CourseEvidenceError(ValueError):
    pass


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _scores(value: Any, label: str) -> list[int]:
    if not isinstance(value, dict) or set(value) != set(RUBRIC_KEYS):
        raise CourseEvidenceError(f"{label} must contain exactly {RUBRIC_KEYS}")
    scores = [value[key] for key in RUBRIC_KEYS]
    if any(type(score) is not int for score in scores):
        raise CourseEvidenceError(f"{label} scores must be JSON integers")
    if any(score < 0 or score > 3 for score in scores):
        raise CourseEvidenceError(f"{label} scores must be integers 0..3")
    return scores


def _calibration_passes(evidence: dict[str, Any]) -> bool:
    assessors = evidence.get("assessors")
    if not isinstance(assessors, list) or len(assessors) != 2:
        return False
    assessor_ids = [str(assessor.get("id", "")) for assessor in assessors]
    if "" in assessor_ids or len(set(assessor_ids)) != 2:
        return False
    if evidence.get("calibrationFixtureDigest") != _file_digest(CALIBRATION_FIXTURE):
        return False
    calibration = json.loads(CALIBRATION_FIXTURE.read_text(encoding="utf-8"))
    golden_scores = {
        str(artifact["artifactId"]): artifact["rubric"]
        for artifact in calibration["goldenArtifacts"]
    }
    safety_answers = {
        str(case["caseId"]): case["expected"]
        for case in calibration["safetyCases"]
    }
    for artifact_id, rubric in golden_scores.items():
        try:
            _scores(rubric, f"calibration.{artifact_id}")
        except CourseEvidenceError:
            return False
    for assessor in assessors:
        if assessor.get("blind") is not True:
            return False
        if assessor.get("artifactScores") != golden_scores:
            return False
        if assessor.get("safetyClassifications") != safety_answers:
            return False
    return True


def aggregate_course(evidence: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if not _calibration_passes(evidence):
        blockers.append("assessor-calibration")
    participants = evidence.get("participants")
    if not isinstance(participants, list):
        raise CourseEvidenceError("participants must be a list")
    roster = evidence.get("roster")
    if not isinstance(roster, list):
        raise CourseEvidenceError("roster must be a frozen list")
    if evidence.get("rosterDigest") != canonical_digest(roster):
        raise CourseEvidenceError("course roster digest mismatch")
    try:
        roster_frozen_at = datetime.fromisoformat(str(evidence["rosterFrozenAt"]))
    except (KeyError, ValueError) as exc:
        raise CourseEvidenceError("course roster freeze timestamp is invalid") from exc
    roster_ids = [str(item.get("participantId", "")) for item in roster]
    participant_ids = [str(item.get("participantId", "")) for item in participants]
    if (
        "" in roster_ids
        or len(roster_ids) != len(set(roster_ids))
        or "" in participant_ids
        or len(participant_ids) != len(set(participant_ids))
        or set(roster_ids) != set(participant_ids)
    ):
        raise CourseEvidenceError("roster and participant identities must be unique and identical")
    for participant in participants:
        try:
            started_at = datetime.fromisoformat(str(participant["startedAt"]))
        except (KeyError, ValueError) as exc:
            raise CourseEvidenceError("course participant start timestamp is invalid") from exc
        if started_at <= roster_frozen_at:
            raise CourseEvidenceError("course participant started before roster freeze")
    valid = [
        item
        for item in participants
        if item.get("consent") is True
        and type(item.get("firstActionSeconds")) is int
        and item["firstActionSeconds"] <= 600
        and isinstance(item.get("preRubric"), dict)
    ]
    n = len(valid)
    if n < 10:
        blockers.append(f"valid-starters:{n}<10")
    complete_count = 0
    improved_count = 0
    participant_results: list[dict[str, Any]] = []
    for participant in valid:
        participant_id = str(participant.get("participantId", ""))
        pre = _scores(participant["preRubric"], f"{participant_id}.preRubric")
        post_value = participant.get("postRubric")
        artifact_value = participant.get("artifactRubric")
        completed_value = participant.get("completedAtSeconds")
        completed_on_time = type(completed_value) is int and completed_value <= 6600
        complete = False
        improved = False
        if isinstance(artifact_value, dict) and isinstance(post_value, dict):
            artifact_scores = _scores(artifact_value, f"{participant_id}.artifactRubric")
            post = _scores(post_value, f"{participant_id}.postRubric")
            complete = completed_on_time and all(score >= 2 for score in artifact_scores)
            improved = statistics.median(post) - statistics.median(pre) >= 1.0
        if complete:
            complete_count += 1
        if improved:
            improved_count += 1
        participant_results.append(
            {"participantId": participant_id, "complete": complete, "improved": improved}
        )
    required_complete = math.ceil(0.80 * n)
    required_improved = math.ceil(0.70 * n)
    if complete_count < required_complete:
        blockers.append(f"completion:{complete_count}<{required_complete}")
    if improved_count < required_improved:
        blockers.append(f"improvement:{improved_count}<{required_improved}")
    incidents = evidence.get("safetyIncidents")
    if not isinstance(incidents, list):
        blockers.append("missing-safety-ledger")
        incidents = []
    for incident in incidents:
        code = incident.get("code")
        if code not in SAFETY_CODES:
            blockers.append(f"unknown-safety-code:{code}")
        else:
            blockers.append(f"safety-incident:{code}")
    transitions = evidence.get("fallbackTransitions")
    if not isinstance(transitions, list):
        blockers.append("missing-fallback-ledger")
        transitions = []
    for transition in transitions:
        duration = int(transition.get("durationSeconds", 10**9))
        if duration > 300:
            blockers.append(f"fallback-over-300s:{transition.get('id', '<unknown>')}")
    return {
        "schemaVersion": "1.0.0",
        "validStarters": n,
        "requiredComplete": required_complete,
        "complete": complete_count,
        "requiredImproved": required_improved,
        "improved": improved_count,
        "participantResults": participant_results,
        "status": "BLOCK" if blockers else "PASS",
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate the locked two-hour course gate")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        result = aggregate_course(evidence)
        result["sourceEvidenceDigest"] = (
            "sha256:" + hashlib.sha256(args.evidence.read_bytes()).hexdigest()
        )
        result["sourceEvidenceRef"] = args.evidence.name
    except (OSError, json.JSONDecodeError, CourseEvidenceError, TypeError, ValueError) as exc:
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

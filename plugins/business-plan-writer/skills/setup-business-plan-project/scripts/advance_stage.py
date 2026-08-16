from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from create_project import FOLDERS, STAGES


STATE_PATH = Path("00. 시작하기") / "단계상태.json"
COLLABORATION_PATH = Path("00. 시작하기") / "사용자협업상태.json"
INTERACTION_MODES = {"DEMO", "PARTIAL", "REAL"}
TERMINAL = {"PASS", "NOT_REQUESTED"}
ALLOWED = {"NOT_STARTED", "IN_PROGRESS", "PASS", "BLOCK", "NOT_REQUESTED"}
ALLOWED_METADATA_DIRS = {".agents", ".claude", ".dayoun", ".git"}
STAGE_EVIDENCE_PREFIXES = {
    1: ("02. 목적 및 요구사항", "03. 사업계획서양식"),
    2: ("01. 사업정보",),
    3: ("02. 목적 및 요구사항", "04. 조사자료"),
    4: ("04. 조사자료",),
    5: ("05. 작성초안",),
    6: ("05. 작성초안",),
    7: ("05. 작성초안", "06. 검토결과"),
    8: ("03. 사업계획서양식/작업용 HWPX", "07. 최종본"),
    9: ("06. 검토결과", "07. 최종본"),
    10: ("08. 발표덱",),
}


class StageGateError(RuntimeError):
    pass


def required_top_level() -> tuple[str, ...]:
    return tuple(dict.fromkeys(Path(folder).parts[0] for folder in FOLDERS))


def state_file(project: Path) -> Path:
    return project / STATE_PATH


def load_state(project: Path) -> dict[str, Any]:
    path = state_file(project)
    if not path.is_file():
        raise StageGateError(f"missing stage state: {path}")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StageGateError(f"invalid stage state: {error}") from error
    return state


def load_collaboration(project: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    if state.get("interactionMode") != "REAL":
        return None
    path = project / COLLABORATION_PATH
    if not path.is_file():
        raise StageGateError(f"missing REAL collaboration state: {path}")
    try:
        collaboration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StageGateError(f"invalid collaboration state: {error}") from error
    if collaboration.get("interactionMode") != "REAL":
        raise StageGateError("REAL collaboration state mode does not match stage state")
    return collaboration


def validate_structure(project: Path, state: dict[str, Any]) -> None:
    missing = [name for name in required_top_level() if not (project / name).is_dir()]
    if missing:
        raise StageGateError(f"missing required project folders: {', '.join(missing)}")
    expected = set(required_top_level())
    actual = {path.name for path in project.iterdir() if path.is_dir()}
    unexpected = sorted(actual - expected - ALLOWED_METADATA_DIRS)
    if unexpected:
        raise StageGateError(
            f"unexpected top-level project folders: {', '.join(unexpected)}"
        )
    if state.get("interactionMode") not in INTERACTION_MODES:
        raise StageGateError(
            f"interactionMode must be one of {', '.join(sorted(INTERACTION_MODES))}"
        )
    stages = state.get("stages")
    if not isinstance(stages, list) or len(stages) != len(STAGES):
        raise StageGateError("stage state must contain exactly 10 stages")
    for index, (record, expected_name) in enumerate(zip(stages, STAGES), 1):
        if not isinstance(record, dict):
            raise StageGateError(f"stage {index} record is not an object")
        if record.get("id") != index or record.get("name") != expected_name:
            raise StageGateError(f"stage {index} identity changed")
        if record.get("status") not in ALLOWED:
            raise StageGateError(f"stage {index} has invalid status: {record.get('status')}")
        if not isinstance(record.get("evidence"), list):
            raise StageGateError(f"stage {index} evidence must be an array")


def normalized_evidence(project: Path, values: list[str]) -> list[str]:
    result: list[str] = []
    root = project.resolve()
    for value in values:
        candidate = Path(value)
        resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as error:
            raise StageGateError(f"evidence escapes project root: {value}") from error
        if not resolved.is_file():
            raise StageGateError(
                f"evidence must be an existing file: {relative.as_posix()}"
            )
        result.append(relative.as_posix())
    return sorted(dict.fromkeys(result))


def validate_stage_evidence(
    state: dict[str, Any],
    stage: int,
    evidence: list[str],
) -> None:
    prefixes = STAGE_EVIDENCE_PREFIXES[stage]
    invalid = [
        item
        for item in evidence
        if not any(item == prefix or item.startswith(prefix + "/") for prefix in prefixes)
    ]
    if invalid:
        raise StageGateError(
            f"stage {stage} evidence is outside its output folders: {', '.join(invalid)}"
        )
    prior = {
        item
        for record in state["stages"][: stage - 1]
        for item in record.get("evidence", [])
    }
    reused = sorted(set(evidence) & prior)
    if reused:
        raise StageGateError(
            f"stage {stage} evidence was already used by a prior stage: {', '.join(reused)}"
        )


def first_open_stage(state: dict[str, Any]) -> int | None:
    for record in state["stages"]:
        if record["status"] not in TERMINAL:
            return int(record["id"])
    return None


def assert_prior_terminal(state: dict[str, Any], stage: int) -> None:
    for record in state["stages"][: stage - 1]:
        if record["status"] not in TERMINAL:
            raise StageGateError(
                f"stage {stage} blocked by stage {record['id']} status {record['status']}"
            )


def update_current_stage(state: dict[str, Any]) -> None:
    state["currentStage"] = first_open_stage(state)


def save_state(project: Path, state: dict[str, Any]) -> None:
    update_current_stage(state)
    path = state_file(project)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temp, path)


def start_stage(project: Path, stage: int) -> dict[str, Any]:
    state = load_state(project)
    validate_structure(project, state)
    if not 1 <= stage <= len(STAGES):
        raise StageGateError(f"stage must be 1-{len(STAGES)}")
    assert_prior_terminal(state, stage)
    record = state["stages"][stage - 1]
    if record["status"] in TERMINAL:
        raise StageGateError(f"stage {stage} is already terminal: {record['status']}")
    if record["status"] not in {"NOT_STARTED", "BLOCK"}:
        raise StageGateError(f"stage {stage} cannot start from {record['status']}")
    record["status"] = "IN_PROGRESS"
    record["evidence"] = []
    save_state(project, state)
    return state



def require_confirmation(
    record: dict[str, Any],
    *,
    expected_status: str,
    label: str,
    required_fields: tuple[str, ...],
) -> None:
    if record.get("status") != expected_status:
        raise StageGateError(f"REAL mode requires {label} status {expected_status}")
    missing = [field for field in required_fields if not record.get(field)]
    if missing:
        raise StageGateError(
            f"REAL mode {label} is missing confirmation fields: {', '.join(missing)}"
        )


def enforce_real_collaboration(
    project: Path,
    state: dict[str, Any],
    stage: int,
    status: str,
) -> None:
    collaboration = load_collaboration(project, state)
    if collaboration is None:
        return
    if stage == 3 and status == "PASS":
        record = collaboration.get("questionRound", {})
        require_confirmation(
            record,
            expected_status="CONFIRMED",
            label="question round",
            required_fields=("answers", "confirmedBy", "confirmedAt", "sourceQuote"),
        )
    elif stage == 5 and status == "PASS":
        record = collaboration.get("strategyDecision", {})
        require_confirmation(
            record,
            expected_status="CONFIRMED",
            label="strategy decision",
            required_fields=("selectedOption", "confirmedBy", "confirmedAt", "sourceQuote"),
        )
    elif stage == 7 and status == "PASS":
        record = collaboration.get("contentApproval", {})
        require_confirmation(
            record,
            expected_status="APPROVED",
            label="content approval",
            required_fields=("approvedFile", "approvedBy", "approvedAt", "sourceQuote"),
        )
        normalized_evidence(project, [str(record["approvedFile"])])
    elif stage == 8 and status in TERMINAL:
        record = collaboration.get("hwpxChoice", {})
        expected = "REQUESTED" if status == "PASS" else "NOT_REQUESTED"
        require_confirmation(
            record,
            expected_status=expected,
            label="HWPX choice",
            required_fields=("confirmedBy", "confirmedAt", "sourceQuote"),
        )
    elif stage == 10 and status in TERMINAL:
        record = collaboration.get("presentationChoice", {})
        expected = "REQUESTED" if status == "PASS" else "NOT_REQUESTED"
        require_confirmation(
            record,
            expected_status=expected,
            label="presentation choice",
            required_fields=("confirmedBy", "confirmedAt", "sourceQuote"),
        )

def complete_stage(
    project: Path,
    stage: int,
    status: str,
    evidence: list[str],
) -> dict[str, Any]:
    state = load_state(project)
    validate_structure(project, state)
    if not 1 <= stage <= len(STAGES):
        raise StageGateError(f"stage must be 1-{len(STAGES)}")
    status = status.upper()
    if status not in {"PASS", "BLOCK", "NOT_REQUESTED"}:
        raise StageGateError("completion status must be PASS, BLOCK, or NOT_REQUESTED")
    if stage <= 7 and status == "NOT_REQUESTED":
        raise StageGateError("stages 1-7 are mandatory and cannot be NOT_REQUESTED")
    if (
        state.get("interactionMode") in {"DEMO", "PARTIAL"}
        and stage >= 7
        and status != "BLOCK"
    ):
        raise StageGateError(
            f"{state['interactionMode']} mode cannot approve or select stages 7-10"
        )
    assert_prior_terminal(state, stage)
    record = state["stages"][stage - 1]
    if record["status"] != "IN_PROGRESS":
        raise StageGateError(f"stage {stage} must be IN_PROGRESS before completion")
    if stage == 9 and state["stages"][7]["status"] == "NOT_REQUESTED" and status != "NOT_REQUESTED":
        raise StageGateError("stage 9 must be NOT_REQUESTED when stage 8 is NOT_REQUESTED")
    normalized = normalized_evidence(project, evidence)
    if status in {"PASS", "BLOCK"} and not normalized:
        raise StageGateError(f"{status} requires at least one existing evidence file")
    if status == "NOT_REQUESTED" and normalized:
        raise StageGateError("NOT_REQUESTED must not claim output evidence")
    if normalized:
        validate_stage_evidence(state, stage, normalized)
    enforce_real_collaboration(project, state, stage, status)
    record["status"] = status
    record["evidence"] = normalized
    save_state(project, state)
    return state


def receipt(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "project": str(project),
        "interactionMode": state.get("interactionMode"),
        "currentStage": state.get("currentStage"),
        "stages": [
            {
                "id": record["id"],
                "name": record["name"],
                "status": record["status"],
                "evidence": record["evidence"],
            }
            for record in state["stages"]
        ],
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Enforce the sequential 10-stage business-plan workflow")
    commands = root.add_subparsers(dest="command", required=True)
    for command in ("check", "start", "complete"):
        sub = commands.add_parser(command)
        sub.add_argument("project", type=Path)
        if command != "check":
            sub.add_argument("stage", type=int)
        if command == "complete":
            sub.add_argument("--status", required=True)
            sub.add_argument("--evidence", action="append", default=[])
    return root


def main() -> int:
    args = parser().parse_args()
    project = args.project.expanduser().resolve()
    try:
        if args.command == "check":
            state = load_state(project)
            validate_structure(project, state)
            update_current_stage(state)
        elif args.command == "start":
            state = start_stage(project, args.stage)
        else:
            state = complete_stage(project, args.stage, args.status, args.evidence)
    except (OSError, StageGateError) as error:
        print(json.dumps({"status": "BLOCK", "error": str(error)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(receipt(project, state), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VALIDATOR_VERSION = "dayoun-validator-v1"


class ValidatorError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidatorError(f"cannot read {path}: {exc}") from exc


def digest_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def verdict(validator_id: str, payload_path: Path, blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "BLOCK" if blockers else "PASS",
        "validatorId": validator_id,
        "validatorVersion": VALIDATOR_VERSION,
        "evidenceRefs": [digest_file(payload_path)],
        "artifactDigest": digest_file(payload_path),
        "reason": "; ".join(blockers) if blockers else "independent validator passed",
        "blockers": blockers,
    }


def write_result(result: dict[str, Any], output: Path | None) -> None:
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")

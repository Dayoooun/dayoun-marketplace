from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_KINDS = {"quote", "profile", "official", "notice", "poster"}


class DocumentsEvidenceError(ValueError):
    pass


def _digest(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("sha256:") and len(value) == 71


def _evidence(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and _digest(value.get("evidenceDigest"))
        and isinstance(value.get("evidenceRef"), str)
        and bool(value["evidenceRef"])
    )


def aggregate_documents(evidence: dict[str, Any]) -> dict[str, Any]:
    cases = evidence.get("cases")
    blockers: list[str] = []
    if not isinstance(cases, list):
        raise DocumentsEvidenceError("cases must be a list")
    by_kind = {str(case.get("kind")): case for case in cases}
    if set(by_kind) != REQUIRED_KINDS or len(cases) != len(REQUIRED_KINDS):
        blockers.append("kind-matrix")
    for kind in sorted(REQUIRED_KINDS):
        case = by_kind.get(kind, {})
        if case.get("rendererStatus") != "PASS":
            blockers.append(f"renderer:{kind}")
        if case.get("browserVisualStatus") != "PASS":
            blockers.append(f"browser-visual:{kind}")
        if (
            not _evidence(case.get("inputEvidence"))
            or not _evidence(case.get("artifactEvidence"))
        ):
            blockers.append(f"artifact-provenance:{kind}")
        if not _evidence(case.get("screenshotEvidence")):
            blockers.append(f"screenshot-provenance:{kind}")
        if case.get("remoteUrls") not in (0, []):
            blockers.append(f"remote-url:{kind}")
        if case.get("privacyFindings") not in (0, []):
            blockers.append(f"privacy:{kind}")
    defects = evidence.get("criticalDefects")
    if not isinstance(defects, list):
        blockers.append("missing-critical-defect-ledger")
        defects = []
    if defects:
        blockers.extend(f"critical-defect:{item.get('code', '<unknown>')}" for item in defects)
    return {
        "schemaVersion": "1.0.0",
        "rendererStatus": "PASS" if not any(item.startswith("renderer:") for item in blockers) else "BLOCK",
        "browserVisualStatus": "PASS" if not any(item.startswith("browser-visual:") for item in blockers) else "BLOCK",
        "criticalDefects": len(defects),
        "status": "BLOCK" if blockers else "PASS",
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate independent business-documents release evidence")
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = aggregate_documents(json.loads(args.evidence.read_text(encoding="utf-8")))
        result["sourceEvidenceDigest"] = (
            "sha256:" + hashlib.sha256(args.evidence.read_bytes()).hexdigest()
        )
        result["sourceEvidenceRef"] = args.evidence.name
    except (OSError, json.JSONDecodeError, DocumentsEvidenceError, TypeError, ValueError) as exc:
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

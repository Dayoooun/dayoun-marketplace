from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PPT_SCRIPTS = PLUGIN_ROOT / "skills" / "ppt-editorial" / "scripts"
if str(PPT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PPT_SCRIPTS))

from approved_inputs import ApprovalError, resolve_approved_bundle, resolve_value  # noqa: E402
from validator_common import ValidatorError, load_json, verdict, write_result  # noqa: E402

EMBEDDED_CONTRACTS = PLUGIN_ROOT / "_contracts"


def _schema_blockers(instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        f"{label}:{'.'.join(map(str, error.absolute_path)) or '<root>'}:{error.message}"
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    ]


def validate_contract(
    payload: dict[str, Any],
    *,
    contracts_root: Path,
    approval_digest: str | None,
    approval_store: Path | None,
    require_approval: bool,
) -> list[str]:
    blockers = _schema_blockers(
        payload,
        load_json(contracts_root / "schemas" / "canonical.schema.json"),
        "canonical",
    )
    if require_approval and (not approval_digest or approval_store is None):
        blockers.append("approval-required")
        return blockers
    if approval_digest and approval_store is not None:
        try:
            envelope = resolve_value(approval_store, approval_digest)
            blockers.extend(
                _schema_blockers(
                    envelope,
                    load_json(contracts_root / "schemas" / "approval-envelope.schema.json"),
                    "approval-envelope",
                )
            )
            approved_payload, _briefs, _manifest = resolve_approved_bundle(
                approval_store, envelope
            )
            if approved_payload != payload:
                blockers.append("canonical-payload-does-not-match-approval")
        except ApprovalError as exc:
            blockers.append(str(exc))
    elif approval_digest or approval_store is not None:
        blockers.append("approval-digest-store-pair-required")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent schema and approval-tuple validator")
    parser.add_argument("payload", type=Path)
    parser.add_argument("--contracts", type=Path, default=EMBEDDED_CONTRACTS)
    parser.add_argument("--approval-digest")
    parser.add_argument("--approval-store", type=Path)
    parser.add_argument("--require-approval", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        payload = load_json(args.payload)
        blockers = validate_contract(
            payload,
            contracts_root=args.contracts,
            approval_digest=args.approval_digest,
            approval_store=args.approval_store,
            require_approval=args.require_approval,
        )
        result = verdict("contract-validator", args.payload, blockers)
        write_result(result, args.output)
    except ValidatorError as exc:
        print(f"BLOCK: {exc}")
        return 1
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

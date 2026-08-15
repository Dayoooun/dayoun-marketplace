from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import rfc8785
from jsonschema import Draft202012Validator, FormatChecker

DIGEST_PREFIX = "sha256:"


class ContractError(ValueError):
    """Raised when a contract cannot be trusted or validated."""


def _reject_duplicate_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: str | Path) -> Any:
    source = Path(path)
    try:
        return json.loads(
            source.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ContractError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON contract {source}: {exc}") from exc


def canonical_bytes(value: Any) -> bytes:
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
        raise ContractError(f"RFC 8785 canonicalization failed: {exc}") from exc


def canonical_digest(value: Any) -> str:
    return DIGEST_PREFIX + hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: str | Path) -> str:
    return DIGEST_PREFIX + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_schema(instance: Any, schema: Any, *, label: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.absolute_path))
    if errors:
        details = "; ".join(
            f"{'.'.join(map(str, error.absolute_path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise ContractError(f"{label} failed schema validation: {details}")


def validate_file(instance_path: str | Path, schema_path: str | Path) -> Any:
    instance = load_json(instance_path)
    schema = load_json(schema_path)
    validate_schema(instance, schema, label=str(instance_path))
    return instance


def aggregate_validation(record: dict[str, Any]) -> str:
    """Derive, never override, the strict validation aggregate."""
    if set(record.get("validators", {})) != {"fact", "structure", "contract"}:
        return "REJECTED" if record.get("attempt") == 2 else "BLOCK"
    if set(record.get("outputs", {})) != {"hwpx", "ppt"}:
        return "REJECTED" if record.get("attempt") == 2 else "BLOCK"
    if record.get("approvalStatus") == "STALE":
        return "STALE_APPROVAL"
    validators = record["validators"]
    blocked = any(item["status"] != "PASS" for item in validators.values())
    for output in record["outputs"].values():
        if not output["requested"]:
            if output["automationStatus"] != "NOT_REQUESTED" or output["visualStatus"] != "NOT_REQUESTED":
                blocked = True
            continue
        if output["automationStatus"] != "PASS" or output["visualStatus"] != "PASS":
            blocked = True
    if blocked:
        return "REJECTED" if record.get("attempt") == 2 else "BLOCK"
    return "PASS"


def assert_declared_aggregate(record: dict[str, Any]) -> None:
    derived = aggregate_validation(record)
    if record["aggregateStatus"] != derived:
        raise ContractError(
            f"declared aggregate {record['aggregateStatus']} does not match strict aggregate {derived}"
        )

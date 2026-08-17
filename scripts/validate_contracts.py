from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, exceptions as jsonschema_exceptions

from contract_utils import ContractError, canonical_digest, load_json

SCHEMA_FILES = (
    "canonical.schema.json",
    "approval-envelope.schema.json",
    "validation.schema.json",
    "provider-run.schema.json",
    "visible-text-manifest.schema.json",
    "ocr-evidence.schema.json",
    "render-receipt.schema.json",
    "deck-output-receipt.schema.json",
    "scene-receipt.schema.json",
    "scene-placement-receipt.schema.json",
    "release-manifest.schema.json",
    "toolchain-lock.schema.json",
)
POLICY_FILES = ("state-machine.json", "scope-steps.json", "release-gates.json")


def validate_contract_tree(root: Path) -> dict[str, str]:
    schemas = root / "schemas"
    policies = root / "policies"
    digests: dict[str, str] = {}
    for name in SCHEMA_FILES:
        path = schemas / name
        schema = load_json(path)
        try:
            Draft202012Validator.check_schema(schema)
        except jsonschema_exceptions.SchemaError as exc:
            raise ContractError(f"{name} is not a valid Draft 2020-12 schema: {exc.message}") from exc
        digests[path.relative_to(root).as_posix()] = canonical_digest(schema)
    manifest_path = root / "manifest.json"
    manifest = load_json(manifest_path)
    if (
        manifest.get("name") != "dayoun-contracts"
        or manifest.get("canonicalization") != "RFC8785-JCS"
        or manifest.get("schemaVersion") != "1.0.0"
    ):
        raise ContractError("contracts manifest identity or canonicalization is invalid")
    digests["manifest.json"] = canonical_digest(manifest)
    for name in POLICY_FILES:
        path = policies / name
        policy = load_json(path)
        if policy.get("schemaVersion") != "1.0.0":
            raise ContractError(f"{name} must declare schemaVersion 1.0.0")
        digests[path.relative_to(root).as_posix()] = canonical_digest(policy)
    release_manifest_validator = Draft202012Validator(
        load_json(schemas / "release-manifest.schema.json")
    )
    release_manifests = root.parent / "release" / "manifests"
    for path in sorted(release_manifests.glob("*.json")):
        errors = sorted(
            release_manifest_validator.iter_errors(load_json(path)),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            raise ContractError(
                f"{path.name} failed release manifest schema: "
                + "; ".join(error.message for error in errors)
            )
    toolchain_validator = Draft202012Validator(
        load_json(schemas / "toolchain-lock.schema.json")
    )
    toolchain_errors = list(
        toolchain_validator.iter_errors(
            load_json(root.parent / "release" / "toolchains.lock.json")
        )
    )
    if toolchain_errors:
        raise ContractError(
            "toolchains.lock.json failed schema: "
            + "; ".join(error.message for error in toolchain_errors)
        )
    matrix = load_json(root / "fixtures" / "release" / "matrix.json")
    cases = matrix.get("cases", [])
    providers = matrix.get("providers", [])
    if len(cases) != 10 or providers != ["codex", "claude-code", "antigravity"]:
        raise ContractError("release matrix must contain ten ordered cases and the three approved providers")
    if matrix.get("expectedRunCount") != len(cases) * len(providers):
        raise ContractError("release matrix expectedRunCount does not match case/provider product")
    canonical_validator = Draft202012Validator(load_json(schemas / "canonical.schema.json"))
    for case in cases:
        fixture_path = root / "fixtures" / "release" / case["id"] / "canonical.json"
        payload = load_json(fixture_path)
        errors = sorted(
            canonical_validator.iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
        if errors:
            detail = "; ".join(error.message for error in errors)
            raise ContractError(f"{case['id']} canonical fixture is invalid: {detail}")
        expected = {
            "scope": case["scope"],
            "sectionId": case.get("sectionId"),
            "outputs": case["outputs"],
            "rendererMode": case.get("rendererMode"),
        }
        actual = {
            "scope": payload["scope"],
            "sectionId": payload.get("sectionId"),
            "outputs": payload["outputs"],
            "rendererMode": payload.get("rendererMode"),
        }
        if actual != expected:
            raise ContractError(f"{case['id']} canonical fixture does not match matrix: {actual}")
        digests[fixture_path.relative_to(root).as_posix()] = canonical_digest(payload)
    digests["fixtures/release/matrix.json"] = canonical_digest(matrix)
    return dict(sorted(digests.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the authored Dayoun contract tree")
    parser.add_argument("root", nargs="?", default="contracts", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        digests = validate_contract_tree(args.root.resolve())
    except ContractError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    result = {"status": "PASS", "contractDigests": digests}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else f"PASS: {len(digests)} contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

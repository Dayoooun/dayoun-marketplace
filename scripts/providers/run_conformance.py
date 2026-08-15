from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

from provider_common import (
    PROVIDERS,
    ProviderEvidenceError,
    canonical_projection,
    canonical_digest,
    load_json,
    required_run_ids,
    resolve_real_executable,
    sha256_bytes,
    verify_evidence_record,
)


def validate_evidence(matrix_path: Path, fixtures_root: Path, evidence_root: Path) -> dict[str, object]:
    matrix = load_json(matrix_path)
    identities = required_run_ids(matrix)
    provider_schema = load_json(
        Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "provider-run.schema.json"
    )
    provider_validator = Draft202012Validator(provider_schema, format_checker=FormatChecker())
    seen_provenance: set[str] = set()
    seen_run_ids: set[str] = set()
    records: list[dict[str, object]] = []
    adapter_paths = {
        "codex": Path(__file__).resolve().with_name("codex_runner.py"),
        "claude-code": Path(__file__).resolve().with_name("claude_code_runner.py"),
        "antigravity": Path(__file__).resolve().with_name("antigravity_runner.py"),
    }
    for fixture_id, provider in identities:
        payload = load_json(fixtures_root / fixture_id / "canonical.json")
        expected_projection = canonical_projection(payload)
        evidence_path = evidence_root / f"{fixture_id}--{provider}.json"
        record = load_json(evidence_path)
        schema_errors = sorted(
            provider_validator.iter_errors(record),
            key=lambda error: list(error.absolute_path),
        )
        if schema_errors:
            detail = "; ".join(error.message for error in schema_errors)
            raise ProviderEvidenceError(f"{evidence_path.name} schema violation: {detail}")
        verify_evidence_record(
            record,
            expected_fixture=fixture_id,
            expected_provider=provider,
            expected_projection=expected_projection,
            evidence_root=evidence_root,
            expected_adapter=adapter_paths[provider],
        )
        provenance = str(record["provenanceId"])
        if provenance in seen_provenance:
            raise ProviderEvidenceError(f"duplicate provider provenance: {provenance}")
        seen_provenance.add(provenance)
        run_id = str(record["runId"])
        if run_id in seen_run_ids:
            raise ProviderEvidenceError(f"duplicate provider run ID: {run_id}")
        seen_run_ids.add(run_id)
        records.append(record)
    source_evidence_digest = canonical_digest(
        sorted(records, key=lambda record: str(record["runId"]))
    )
    executable_paths = {provider: resolve_real_executable(provider) for provider in PROVIDERS}
    return {
        "status": "PASS",
        "runCount": len(records),
        "providers": list(PROVIDERS),
        "executables": executable_paths,
        "provenanceCount": len(seen_provenance),
        "runIdCount": len(seen_run_ids),
        "sourceEvidenceDigest": source_evidence_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify 30 recorded runs from real Codex, Claude Code, and Antigravity providers"
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=Path("contracts/fixtures/release/matrix.json"),
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("contracts/fixtures/release"),
    )
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--require-real-providers", action="store_true")
    parser.add_argument("--expect-runs", type=int, default=30)
    parser.add_argument("--source-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()
    if not args.require_real_providers:
        print("BLOCK: --require-real-providers is mandatory", file=sys.stderr)
        return 2
    try:
        result = validate_evidence(
            args.matrix.resolve(), args.fixtures.resolve(), args.evidence.resolve()
        )
        counts = (result["runCount"], result["provenanceCount"], result["runIdCount"])
        if counts != (args.expect_runs, args.expect_runs, args.expect_runs):
            raise ProviderEvidenceError(
                f"expected {args.expect_runs} distinct runs/provenances, got {counts}"
            )
    except ProviderEvidenceError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    identities = required_run_ids(load_json(args.matrix.resolve()))
    records = []
    raw_outputs = {}
    approval_envelopes = {}
    visible_manifests = {}
    for fixture_id, provider in identities:
        record = load_json(args.evidence.resolve() / f"{fixture_id}--{provider}.json")
        records.append(record)
        raw_ref = record["rawOutputRef"]
        raw_outputs[raw_ref] = (
            args.evidence.resolve() / raw_ref
        ).read_text(encoding="utf-8")
        approval_digest = record["approvedTuple"]["approvalEnvelopeDigest"]
        approval_envelopes[approval_digest] = load_json(
            args.evidence.resolve() / "approvals" / f"{approval_digest[7:]}.json"
        )
        visible_digest = record["approvedTuple"]["visibleTextManifestDigest"]
        if visible_digest:
            visible_manifests[visible_digest] = load_json(
                args.evidence.resolve() / "manifests" / f"{visible_digest[7:]}.json"
            )
    source = {
        "schemaVersion": "1.0.0",
        "records": records,
        "rawOutputs": raw_outputs,
        "approvalEnvelopes": approval_envelopes,
        "visibleTextManifests": visible_manifests,
    }
    args.source_output.parent.mkdir(parents=True, exist_ok=True)
    args.source_output.write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result["sourceEvidenceDigest"] = sha256_bytes(args.source_output.read_bytes())
    result["sourceEvidenceRef"] = args.source_output.name
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

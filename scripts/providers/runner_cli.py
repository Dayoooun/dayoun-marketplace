from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

from provider_common import (
    ProviderEvidenceError,
    canonical_digest,
    load_json,
    record_real_run,
)


def run(provider: str) -> int:
    parser = argparse.ArgumentParser(description=f"Record one real {provider} conformance run")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--command-json", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--normalized-output", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--approval-envelope", type=Path, required=True)
    parser.add_argument("--visible-text-manifest", type=Path)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        command = load_json(args.command_json)
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            raise ProviderEvidenceError("command JSON must be an argv string array")
        canonical = load_json(args.canonical)
        envelope = load_json(args.approval_envelope)
        repo_root = Path(__file__).resolve().parents[2]
        canonical_errors = list(
            Draft202012Validator(
                load_json(repo_root / "contracts" / "schemas" / "canonical.schema.json")
            ).iter_errors(canonical)
        )
        envelope_errors = list(
            Draft202012Validator(
                load_json(repo_root / "contracts" / "schemas" / "approval-envelope.schema.json"),
                format_checker=FormatChecker(),
            ).iter_errors(envelope)
        )
        if canonical_errors or envelope_errors:
            first = (canonical_errors or envelope_errors)[0]
            raise ProviderEvidenceError("provider approval input fails contract schema: " + first.message)
        payload_digest = canonical_digest(canonical)
        approval_digest = canonical_digest(envelope)
        if envelope.get("payloadDigest") != payload_digest:
            raise ProviderEvidenceError("approval envelope does not bind the canonical fixture")
        if (
            envelope.get("rendererMode") != canonical.get("rendererMode")
            or envelope.get("selectedOutputs") != canonical.get("outputs")
            or envelope.get("cycleId") != canonical.get("cycle", {}).get("cycleId")
            or envelope.get("approvalRevision") != canonical.get("cycle", {}).get("currentRevision")
        ):
            raise ProviderEvidenceError("approval envelope disagrees with fixture execution choices")
        visible_digest = envelope.get("visibleTextManifestDigest")
        if (canonical.get("rendererMode") == "image-first") != bool(visible_digest):
            raise ProviderEvidenceError("approval visible-text binding disagrees with renderer mode")
        if visible_digest:
            if args.visible_text_manifest is None:
                raise ProviderEvidenceError("image-first approval requires the visible-text manifest")
            visible_manifest = load_json(args.visible_text_manifest)
            if canonical_digest(visible_manifest) != visible_digest:
                raise ProviderEvidenceError("visible-text manifest digest mismatch")
            manifest_errors = list(
                Draft202012Validator(
                    load_json(repo_root / "contracts" / "schemas" / "visible-text-manifest.schema.json")
                ).iter_errors(visible_manifest)
            )
            if manifest_errors:
                raise ProviderEvidenceError(
                    "visible-text manifest fails contract schema: " + manifest_errors[0].message
                )
            manifest_store = args.evidence.resolve() / "manifests"
            manifest_store.mkdir(parents=True, exist_ok=True)
            (manifest_store / f"{visible_digest[7:]}.json").write_text(
                json.dumps(visible_manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        elif args.visible_text_manifest is not None:
            raise ProviderEvidenceError("non-image fixture must not supply a visible-text manifest")
        approved_tuple = {
            "payloadDigest": payload_digest,
            "approvalEnvelopeDigest": approval_digest,
            "visibleTextManifestDigest": envelope.get("visibleTextManifestDigest"),
        }
        approval_store = args.evidence.resolve() / "approvals"
        approval_store.mkdir(parents=True, exist_ok=True)
        (approval_store / f"{approval_digest[7:]}.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        record = record_real_run(
            provider=provider,
            fixture_id=args.fixture,
            command=command,
            workspace=args.workspace.resolve(),
            normalized_output=args.normalized_output.resolve(),
            approved_tuple=approved_tuple,
            adapter_path=Path(sys.argv[0]).resolve(),
            evidence_root=args.evidence.resolve(),
            timeout_seconds=args.timeout,
        )
        output = args.evidence / f"{args.fixture}--{provider}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ProviderEvidenceError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0

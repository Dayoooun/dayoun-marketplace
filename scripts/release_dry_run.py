from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
import unicodedata
from datetime import datetime
from typing import Any
import fitz
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator, FormatChecker

from aggregate_beta_evidence import aggregate_beta
from aggregate_course_evidence import aggregate_course
from aggregate_documents_evidence import aggregate_documents
from contract_utils import canonical_digest
from providers.provider_common import (
    ProviderEvidenceError,
    adapter_source_digest,
    canonical_projection,
    executable_version,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGETS = {"contracts", "business-plan-writer", "business-documents", "course-kit"}
DIGEST_LENGTH = len("sha256:") + 64


class ReleaseGateError(ValueError):
    pass


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _normalize_ocr_text(text: str) -> str:
    value = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [re.sub(r"[\t \f\v]+", " ", line).strip() for line in value.split("\n")]
    return "\n".join(lines).strip()


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_nonfinite,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ReleaseGateError(f"cannot read {path}: {exc}") from exc


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _is_digest(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == DIGEST_LENGTH
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )
def _is_windows_reserved_filename(name: str) -> bool:
    stem = name.rstrip(" .").split(".", 1)[0].rstrip(" ").casefold()
    reserved = {"con", "prn", "aux", "nul"}
    reserved.update(f"com{index}" for index in range(1, 10))
    reserved.update(f"lpt{index}" for index in range(1, 10))
    return stem in reserved

def _valid_region(region: Any) -> bool:
    return (
        isinstance(region, list)
        and len(region) == 4
        and all(
            not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(float(value))
            for value in region
        )
        and 0 <= region[0] < region[2] <= 1
        and 0 <= region[1] < region[3] <= 1
    )


def _region_center(region: list[float]) -> tuple[float, float]:
    return ((region[0] + region[2]) / 2, (region[1] + region[3]) / 2)


def _inside_approved_region(detection: Any, approved: Any) -> bool:
    if not _valid_region(detection) or not _valid_region(approved):
        return False
    x, y = _region_center(detection)
    overlap_width = max(0.0, min(detection[2], approved[2]) - max(detection[0], approved[0]))
    overlap_height = max(0.0, min(detection[3], approved[3]) - max(detection[1], approved[1]))
    detection_area = (detection[2] - detection[0]) * (detection[3] - detection[1])
    overlap = (overlap_width * overlap_height) / detection_area
    return (
        approved[0] <= x <= approved[2]
        and approved[1] <= y <= approved[3]
        and overlap >= 0.50
    )


def _relation_geometry_valid(
    relation: dict[str, Any],
    mapped_by_id: dict[str, dict[str, Any]],
    detection_by_id: dict[str, dict[str, Any]],
) -> bool:
    endpoints = (str(relation.get("fromTextId", "")), str(relation.get("toTextId", "")))
    if any(endpoint not in mapped_by_id for endpoint in endpoints):
        return False
    centers: list[tuple[float, float]] = []
    for endpoint in endpoints:
        boxes = [
            detection_by_id.get(detection_id, {}).get("region")
            for detection_id in mapped_by_id[endpoint].get("detectionIds", [])
        ]
        if not boxes or any(not _valid_region(box) for box in boxes):
            return False
        box_centers = [_region_center(box) for box in boxes]
        centers.append(
            (
                sum(center[0] for center in box_centers) / len(box_centers),
                sum(center[1] for center in box_centers) / len(box_centers),
            )
        )
    from_center, to_center = centers
    geometry = relation.get("geometry")
    if geometry == "same-row-left-to-right":
        return abs(from_center[1] - to_center[1]) <= 0.05 and from_center[0] < to_center[0]
    if geometry == "top-to-bottom":
        return from_center[1] < to_center[1]
    if geometry == "adjacent":
        return math.dist(from_center, to_center) <= 0.5
    return False



def _rule_matches(path: str, rule: str) -> bool:
    normalized = rule.rstrip("/")
    return path == normalized or path.startswith(normalized + "/")


def _validate_evidence_shape(name: str, record: dict[str, Any]) -> None:
    if record.get("status") != "PASS":
        raise ReleaseGateError(f"{name} evidence is not PASS")
    if not _is_digest(record.get("sourceEvidenceDigest")) or not record.get("sourceEvidenceRef"):
        raise ReleaseGateError(f"{name} is not bound to source evidence")
    if name == "provider-summary.json":
        counts = (record.get("runCount"), record.get("provenanceCount"), record.get("runIdCount"))
        if counts != (30, 30, 30):
            raise ReleaseGateError(f"provider evidence requires 30 distinct runs/provenances, got {counts}")
        if record.get("providers") != ["codex", "claude-code", "antigravity"]:
            raise ReleaseGateError("provider evidence does not cover the approved provider set")
    elif name == "course-summary.json":
        if (
            type(record.get("validStarters")) is not int
            or record["validStarters"] < 10
            or record.get("complete", 0) < record.get("requiredComplete", 10**9)
            or record.get("improved", 0) < record.get("requiredImproved", 10**9)
            or record.get("blockers")
        ):
            raise ReleaseGateError("course evidence does not meet the locked N/completion/improvement gate")
    elif name == "beta-summary.json":
        allocation = record.get("providerAllocation")
        scopes = record.get("scopeAllocation")
        completed = record.get("completedByProvider", {})
        if (
            record.get("participants") != 10
            or allocation != {"codex": 4, "claude-code": 3, "antigravity": 3}
            or scopes != {"QUICK": 5, "SECTION": 5}
            or record.get("complete", 0) < 8
            or any(completed.get(provider, 0) < 2 for provider in allocation or {})
            or record.get("blockers")
        ):
            raise ReleaseGateError("external beta evidence does not meet ITT allocation and completion gates")
    elif name == "visual-summary.json":
        if (
            set(record.get("rendererModes", [])) != {"scene-deck", "image-first"}
            or record.get("caseCount") != 10
            or set(record.get("imageFirstCases", [])) != {"R04-I", "R07-I"}
            or record.get("externalVisualPass") is not True
            or record.get("criticalDefects") != 0
        ):
            raise ReleaseGateError("visual evidence does not cover the locked matrix and both renderer modes")
    elif name == "documents-summary.json":
        if (
            record.get("rendererStatus") != "PASS"
            or record.get("browserVisualStatus") != "PASS"
            or record.get("criticalDefects") != 0
        ):
            raise ReleaseGateError("business-documents automation and browser visual evidence are incomplete")


def _compare_aggregate(summary: dict[str, Any], derived: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if summary.get(key) != derived.get(key):
            raise ReleaseGateError(f"evidence summary does not match raw aggregate: {key}")


def _validate_provider_source(source: dict[str, Any], summary: dict[str, Any]) -> None:
    records = source.get("records")
    raw_outputs = source.get("rawOutputs")
    approval_envelopes = source.get("approvalEnvelopes")
    visible_manifests = source.get("visibleTextManifests")
    if (
        not isinstance(records, list)
        or len(records) != 30
        or not isinstance(raw_outputs, dict)
        or not isinstance(approval_envelopes, dict)
        or not isinstance(visible_manifests, dict)
    ):
        raise ReleaseGateError("provider source must contain 30 complete records, raw outputs, and approval envelopes")
    matrix = _load(REPO_ROOT / "contracts" / "fixtures" / "release" / "matrix.json")
    expected = {
        (case["id"], provider)
        for case in matrix["cases"]
        for provider in matrix["providers"]
    }
    schema = _load(REPO_ROOT / "contracts" / "schemas" / "provider-run.schema.json")
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    approval_validator = Draft202012Validator(
        _load(REPO_ROOT / "contracts" / "schemas" / "approval-envelope.schema.json"),
        format_checker=FormatChecker(),
    )
    visible_validator = Draft202012Validator(
        _load(REPO_ROOT / "contracts" / "schemas" / "visible-text-manifest.schema.json")
    )
    identities: set[tuple[str, str]] = set()
    run_ids: set[str] = set()
    provenances: set[str] = set()
    raw_refs: set[str] = set()
    for record in records:
        errors = list(validator.iter_errors(record))
        if errors:
            raise ReleaseGateError("provider source record fails schema: " + errors[0].message)
        if record["timeout"] is not False or record["exitCode"] != 0:
            raise ReleaseGateError("provider source contains a failed or timed-out run")
        try:
            started = datetime.fromisoformat(record["startedAt"])
            finished = datetime.fromisoformat(record["finishedAt"])
        except (TypeError, ValueError) as exc:
            raise ReleaseGateError("provider source timestamp is invalid") from exc
        if finished < started:
            raise ReleaseGateError("provider source timestamp order is invalid")
        executable_path = Path(record["executable"])
        try:
            current_version = executable_version(str(executable_path))
        except ProviderEvidenceError as exc:
            raise ReleaseGateError("provider executable version cannot be verified") from exc
        if (
            not executable_path.is_absolute()
            or not executable_path.is_file()
            or _sha256(executable_path) != record["executableDigest"]
            or current_version != record["executableVersion"]
        ):
            raise ReleaseGateError("provider executable identity is missing or stale")
        adapters = {
            "codex": REPO_ROOT / "scripts" / "providers" / "codex_runner.py",
            "claude-code": REPO_ROOT / "scripts" / "providers" / "claude_code_runner.py",
            "antigravity": REPO_ROOT / "scripts" / "providers" / "antigravity_runner.py",
        }
        if adapter_source_digest(adapters[record["provider"]]) != record["adapterDigest"]:
            raise ReleaseGateError("provider adapter digest is stale")
        invocation_name = Path(record["invocation"][0]).stem.lower()
        expected_name = "claude" if record["provider"] == "claude-code" else record["provider"]
        if (
            invocation_name != expected_name
            or record["installMethod"] != "public-provider-cli"
            or not {"canonical-conformance", "recorded-raw-output"}.issubset(record["capabilities"])
        ):
            raise ReleaseGateError("provider invocation/capability provenance is invalid")
        identity = (str(record["fixtureId"]), str(record["provider"]))
        identities.add(identity)
        run_ids.add(str(record["runId"]))
        provenance = str(record["provenanceId"])
        provenances.add(provenance)
        unsigned = dict(record)
        unsigned.pop("provenanceId")
        if provenance != canonical_digest(unsigned):
            raise ReleaseGateError("provider source provenance does not bind the complete run")
        raw_ref = str(record["rawOutputRef"])
        raw_refs.add(raw_ref)
        raw_text = raw_outputs.get(raw_ref)
        if not isinstance(raw_text, str):
            raise ReleaseGateError(f"provider raw output is missing: {raw_ref}")
        raw_digest = "sha256:" + hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        if raw_digest != record["rawOutputDigest"]:
            raise ReleaseGateError(f"provider raw output digest mismatch: {raw_ref}")
        fixture = _load(
            REPO_ROOT / "contracts" / "fixtures" / "release" / record["fixtureId"] / "canonical.json"
        )
        if record["normalizedProjection"] != canonical_projection(fixture):
            raise ReleaseGateError("provider normalized projection changed canonical semantics")
        approved_tuple = record["approvedTuple"]
        payload_digest = canonical_digest(fixture)
        approval_digest = approved_tuple["approvalEnvelopeDigest"]
        approval = approval_envelopes.get(approval_digest)
        if approved_tuple["payloadDigest"] != payload_digest:
            raise ReleaseGateError("provider run payload digest does not bind its canonical fixture")
        if not isinstance(approval, dict) or canonical_digest(approval) != approval_digest:
            raise ReleaseGateError("provider run approval envelope is missing or changed")
        approval_errors = list(approval_validator.iter_errors(approval))
        if approval_errors:
            raise ReleaseGateError("provider approval envelope fails schema: " + approval_errors[0].message)
        if (
            approval.get("payloadDigest") != payload_digest
            or approval.get("rendererMode") != fixture["rendererMode"]
            or approval.get("selectedOutputs") != fixture["outputs"]
            or approval.get("cycleId") != fixture["cycle"]["cycleId"]
            or approval.get("approvalRevision") != fixture["cycle"]["currentRevision"]
            or approval.get("visibleTextManifestDigest") != approved_tuple["visibleTextManifestDigest"]
        ):
            raise ReleaseGateError("provider approval envelope disagrees with canonical execution choices")
        visible_digest = approved_tuple["visibleTextManifestDigest"]
        if visible_digest:
            visible_manifest = visible_manifests.get(visible_digest)
            if not isinstance(visible_manifest, dict) or canonical_digest(visible_manifest) != visible_digest:
                raise ReleaseGateError("provider visible-text manifest is missing or changed")
            visible_errors = list(visible_validator.iter_errors(visible_manifest))
            if visible_errors:
                raise ReleaseGateError("provider visible-text manifest fails schema: " + visible_errors[0].message)
        elif fixture["rendererMode"] == "image-first":
            raise ReleaseGateError("image-first provider run lacks visible-text approval")
    if (
        identities != expected
        or len(run_ids) != 30
        or len(provenances) != 30
        or len(raw_refs) != 30
    ):
        raise ReleaseGateError("provider source does not contain the exact 30-run matrix")
    _compare_aggregate(summary, {"runCount": 30, "runIdCount": 30, "provenanceCount": 30}, ("runCount", "runIdCount", "provenanceCount"))


def _validate_visual_source(
    source: dict[str, Any],
    summary: dict[str, Any],
    evidence_dir: Path,
) -> None:
    cases = source.get("cases")
    if not isinstance(cases, list) or len(cases) != 10:
        raise ReleaseGateError("visual source requires ten case records")
    matrix = _load(REPO_ROOT / "contracts" / "fixtures" / "release" / "matrix.json")
    expected = {case["id"]: case for case in matrix["cases"]}
    case_ids = [str(case.get("caseId")) for case in cases]
    if len(set(case_ids)) != 10 or set(case_ids) != set(expected):
        raise ReleaseGateError("visual source case matrix mismatch")
    for case in cases:
        fixture = expected[str(case["caseId"])]
        if (
            case.get("rendererMode") != fixture["rendererMode"]
            or case.get("expectedVisual") != fixture["visual"]
        ):
            raise ReleaseGateError(f"visual source fixture choices changed: {case['caseId']}")
        validators = case.get("validators")
        if not isinstance(validators, dict) or set(validators) != {"fact", "structure", "contract"}:
            raise ReleaseGateError(f"visual source validator axes are incomplete: {case['caseId']}")
        if case.get("modeAutomationStatus") != "PASS" or any(
            validators[role] != "PASS" for role in ("fact", "structure", "contract")
        ):
            raise ReleaseGateError(f"visual source automation/validator result failed: {case['caseId']}")
        expected_external = "PASS" if fixture["visual"] else "NOT_APPLICABLE"
        if case.get("externalVisualStatus") != expected_external:
            raise ReleaseGateError(f"visual source external result is invalid: {case['caseId']}")
        evidence_records = case.get("evidence")
        if not isinstance(evidence_records, list):
            raise ReleaseGateError(f"visual source evidence list is missing: {case['caseId']}")
        kinds = [str(item.get("kind")) for item in evidence_records]
        if len(kinds) != len(set(kinds)):
            raise ReleaseGateError(f"visual source evidence kinds are duplicated: {case['caseId']}")
        required_kinds = {
            "approval-envelope",
            "mode-automation",
            "fact-validator",
            "structure-validator",
            "contract-validator",
        }
        required_kinds.update(f"artifact-{kind.lower()}" for kind in fixture["visual"])
        if fixture["visual"]:
            required_kinds.add("external-visual")
        if fixture["rendererMode"] == "scene-deck":
            required_kinds.update(
                {
                    "scene-receipt",
                    "scene-output-bundle",
                    "deck-output-receipt",
                    "deck-output-bundle",
                }
            )
        if fixture.get("ocrSuite"):
            required_kinds.update(
                {
                    "visible-text-manifest",
                    "ocr-pptx",
                    "ocr-pdf",
                    "render-receipt",
                    "rendered-png-bundle",
                }
            )
        if set(kinds) != required_kinds:
            raise ReleaseGateError(f"visual source evidence kinds do not exactly match: {case['caseId']}")
        paths: dict[str, Path] = {}
        digests: dict[str, str] = {}
        for item in evidence_records:
            kind = str(item["kind"])
            reference = str(item.get("ref", ""))
            path = (evidence_dir / reference).resolve()
            try:
                path.relative_to(evidence_dir.resolve())
            except ValueError as exc:
                raise ReleaseGateError("visual evidence reference escapes its directory") from exc
            if not path.is_file() or not _is_digest(item.get("digest")):
                raise ReleaseGateError(f"visual evidence artifact is missing: {reference}")
            if _sha256(path) != item["digest"]:
                raise ReleaseGateError(f"visual evidence artifact digest mismatch: {reference}")
            paths[kind] = path
            digests[kind] = item["digest"]
        artifact_digests = {
            kind.removeprefix("artifact-").upper(): digest
            for kind, digest in digests.items()
            if kind.startswith("artifact-")
        }
        for artifact_kind, artifact_digest in artifact_digests.items():
            path = paths[f"artifact-{artifact_kind.lower()}"]
            if artifact_kind in {"HWPX", "PPTX"}:
                if not zipfile.is_zipfile(path):
                    raise ReleaseGateError(f"visual artifact is not a valid {artifact_kind}: {path.name}")
                with zipfile.ZipFile(path) as package:
                    members = package.namelist()
                    if artifact_kind == "HWPX":
                        if (
                            not members
                            or members[0] != "mimetype"
                            or package.read("mimetype") != b"application/hwp+zip"
                            or package.getinfo("mimetype").compress_type != zipfile.ZIP_STORED
                            or not any(name.startswith("Contents/section") and name.endswith(".xml") for name in members)
                        ):
                            raise ReleaseGateError(f"visual artifact is not a valid HWPX: {path.name}")
                    elif {
                        "[Content_Types].xml",
                        "ppt/presentation.xml",
                    } - set(members):
                        raise ReleaseGateError(f"visual artifact is not a valid PPTX: {path.name}")
            if artifact_kind == "PDF" and not path.read_bytes().startswith(b"%PDF"):
                raise ReleaseGateError(f"visual artifact is not a valid PDF: {path.name}")
            if artifact_digest != _sha256(path):
                raise ReleaseGateError("visual artifact digest changed during validation")
        approval = _load(paths["approval-envelope"])
        approval_errors = list(
            Draft202012Validator(
                _load(REPO_ROOT / "contracts" / "schemas" / "approval-envelope.schema.json"),
                format_checker=FormatChecker(),
            ).iter_errors(approval)
        )
        if approval_errors:
            raise ReleaseGateError("visual approval envelope fails schema: " + approval_errors[0].message)
        canonical_fixture = _load(
            REPO_ROOT / "contracts" / "fixtures" / "release" / case["caseId"] / "canonical.json"
        )
        if (
            approval.get("payloadDigest") != canonical_digest(canonical_fixture)
            or approval.get("cycleId") != canonical_fixture["cycle"]["cycleId"]
            or approval.get("approvalRevision") != canonical_fixture["cycle"]["currentRevision"]
            or approval.get("rendererMode") != fixture["rendererMode"]
            or approval.get("selectedOutputs") != fixture["outputs"]
        ):
            raise ReleaseGateError(f"visual approval choices changed: {case['caseId']}")
        approval_digest = canonical_digest(approval)
        if approval_digest != digests["approval-envelope"]:
            raise ReleaseGateError("visual approval envelope is not stored canonically")
        report_kinds = {
            "mode-automation",
            "fact-validator",
            "structure-validator",
            "contract-validator",
        }
        if fixture["visual"]:
            report_kinds.add("external-visual")
        lock_digest = _sha256(REPO_ROOT / "release" / "toolchains.lock.json")
        for kind in report_kinds:
            report = _load(paths[kind])
            if (
                report.get("schemaVersion") != "1.0.0"
                or report.get("caseId") != case["caseId"]
                or report.get("kind") != kind
                or report.get("status") != "PASS"
                or report.get("rendererMode") != fixture["rendererMode"]
                or report.get("approvalEnvelopeDigest") != approval_digest
                or report.get("artifactDigests") != artifact_digests
                or report.get("toolchainLockDigest") != lock_digest
            ):
                raise ReleaseGateError(f"visual report binding is invalid: {case['caseId']}:{kind}")
        receipt_schemas = {
            "scene-receipt": "scene-receipt.schema.json",
            "deck-output-receipt": "deck-output-receipt.schema.json",
            "render-receipt": "render-receipt.schema.json",
        }
        receipts: dict[str, dict[str, Any]] = {}
        for kind, schema_name in receipt_schemas.items():
            if kind not in paths:
                continue
            receipt = _load(paths[kind])
            receipts[kind] = receipt
            errors = list(
                Draft202012Validator(
                    _load(REPO_ROOT / "contracts" / "schemas" / schema_name)
                ).iter_errors(receipt)
            )
            if (
                errors
                or receipt.get("approvalEnvelopeDigest") != approval_digest
                or receipt.get("rendererVersion") != approval.get("rendererVersion")
            ):
                raise ReleaseGateError(f"visual render receipt binding is invalid: {case['caseId']}:{kind}")
        bundle_specs = {
            "render-receipt": ("rendered-png-bundle", "slides", "fileName", "sha256"),
            "deck-output-receipt": ("deck-output-bundle", "slides", "fileName", "sha256"),
            "scene-receipt": ("scene-output-bundle", "scenes", "sceneId", "outputDigest"),
        }
        for receipt_kind, (bundle_kind, rows_key, name_key, digest_key) in bundle_specs.items():
            if receipt_kind not in receipts:
                continue
            bundle_path = paths[bundle_kind]
            if not zipfile.is_zipfile(bundle_path):
                raise ReleaseGateError(f"visual receipt output bundle is not ZIP: {bundle_kind}")
            with zipfile.ZipFile(bundle_path) as bundle:
                members = bundle.namelist()
                rows = receipts[receipt_kind][rows_key]
                expected_names = [
                    str(row[name_key]) + ".png"
                    if name_key == "sceneId"
                    else str(row[name_key])
                    for row in rows
                ]
                row_digests = [str(row[digest_key]) for row in rows]
                basenames = [PurePosixPath(name).name for name in members]
                if (
                    len(members) != len(set(members))
                    or len(basenames) != len(set(basenames))
                    or len(expected_names) != len(set(expected_names))
                    or len({name.casefold() for name in members}) != len(members)
                    or len({name.casefold() for name in expected_names}) != len(expected_names)
                    or len(row_digests) != len(set(row_digests))
                    or members != basenames
                    or set(members) != set(expected_names)
                    or any(
                        "/" in name
                        or "\\" in name
                        or ":" in name
                        or name in {".", ".."}
                        or name.endswith((" ", "."))
                        for name in members + expected_names
                    )
                    or any(_is_windows_reserved_filename(name) for name in members + expected_names)
                ):
                    raise ReleaseGateError(f"visual receipt output set mismatch: {bundle_kind}")
                by_name = {PurePosixPath(name).name: bundle.read(name) for name in members}
                for row, expected_name in zip(rows, expected_names, strict=True):
                    data = by_name[expected_name]
                    if "sha256:" + hashlib.sha256(data).hexdigest() != row[digest_key]:
                        raise ReleaseGateError(f"visual receipt output digest mismatch: {bundle_kind}:{expected_name}")
        if fixture.get("ocrSuite"):
            visible_manifest = _load(paths["visible-text-manifest"])
            visible_errors = list(
                Draft202012Validator(
                    _load(REPO_ROOT / "contracts" / "schemas" / "visible-text-manifest.schema.json")
                ).iter_errors(visible_manifest)
            )
            visible_digest = canonical_digest(visible_manifest)
            if (
                visible_errors
                or visible_digest != digests["visible-text-manifest"]
                or visible_digest != approval.get("visibleTextManifestDigest")
                or len(visible_manifest.get("entries", []))
                != len({entry.get("textId") for entry in visible_manifest.get("entries", [])})
            ):
                raise ReleaseGateError(f"visual manifest binding is invalid: {case['caseId']}")
            expected_text_ids = {entry["textId"] for entry in visible_manifest["entries"]}
            entry_by_text = {
                entry["textId"]: entry
                for entry in visible_manifest["entries"]
            }
            relation_rows = visible_manifest.get("relations", [])
            relation_ids = [relation.get("relationId") for relation in relation_rows]
            if (
                len(relation_ids) != len(set(relation_ids))
                or not all(relation_ids)
                or any(
                    relation.get("fromTextId") not in expected_text_ids
                    or relation.get("toTextId") not in expected_text_ids
                    or entry_by_text.get(relation.get("fromTextId"), {}).get("slide")
                    != entry_by_text.get(relation.get("toTextId"), {}).get("slide")
                    for relation in relation_rows
                )
            ):
                raise ReleaseGateError(f"visible manifest relations are invalid: {case['caseId']}")
            expected_pages = sorted({entry["slide"] for entry in visible_manifest["entries"]})
            expected_slide_pairs = sorted(
                {(entry["briefIndex"], entry["slide"]) for entry in visible_manifest["entries"]},
                key=lambda item: item[1],
            )
            expected_slide_ids = [f"{brief_index}:{slide}" for brief_index, slide in expected_slide_pairs]
            render_rows = receipts["render-receipt"]["slides"]
            received_slide_ids = [str(row["slideIdentity"]) for row in render_rows]
            if received_slide_ids != expected_slide_ids:
                raise ReleaseGateError(f"image render receipt slide order mismatch: {case['caseId']}")
            if (
                len(expected_slide_pairs) != len(expected_pages)
                or expected_pages != list(range(1, len(expected_pages) + 1))
            ):
                raise ReleaseGateError(f"visible manifest slide identity is ambiguous: {case['caseId']}")
            try:
                with zipfile.ZipFile(paths["artifact-pptx"]) as pptx_package:
                    package_names = set(pptx_package.namelist())
                    presentation = ET.fromstring(
                        pptx_package.read("ppt/presentation.xml")
                    )
                    relationships = ET.fromstring(
                        pptx_package.read("ppt/_rels/presentation.xml.rels")
                    )
                    slide_ids = presentation.findall(
                        "./{http://schemas.openxmlformats.org/presentationml/2006/main}sldIdLst/"
                        "{http://schemas.openxmlformats.org/presentationml/2006/main}sldId"
                    )
                    relationship_rows = list(relationships)
                    relationship_namespace = (
                        "http://schemas.openxmlformats.org/package/2006/relationships"
                    )
                    if (
                        relationships.tag != f"{{{relationship_namespace}}}Relationships"
                        or any(
                            relation.tag != f"{{{relationship_namespace}}}Relationship"
                            for relation in relationship_rows
                        )
                    ):
                        raise ReleaseGateError("visual PPTX relationship XML has invalid QNames")
                    relationship_id_values = [
                        relation.attrib.get("Id")
                        for relation in relationship_rows
                    ]
                    slide_relationship_types = {
                        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                        "http://purl.oclc.org/ooxml/officeDocument/relationships/slide",
                    }
                    slide_relationship_rows = [
                        relation
                        for relation in relationship_rows
                        if relation.attrib.get("Type") in slide_relationship_types
                    ]
                    relationship_map = {
                        relation.attrib["Id"]: relation.attrib["Target"]
                        for relation in slide_relationship_rows
                        if relation.attrib.get("TargetMode") in (None, "Internal")
                    }
                    relationship_ids = [
                        slide.attrib[
                            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                        ]
                        for slide in slide_ids
                    ]
                    slide_numeric_id_values = [
                        slide.attrib.get("id")
                        for slide in slide_ids
                    ]
                    slide_numeric_ids_valid = all(
                        isinstance(value, str)
                        and re.fullmatch(r"[1-9][0-9]*", value) is not None
                        and 256 <= int(value) <= 2147483647
                        for value in slide_numeric_id_values
                    )
                    normalized_slide_numeric_ids = (
                        [int(value) for value in slide_numeric_id_values]
                        if slide_numeric_ids_valid
                        else []
                    )
                    if (
                        not all(relationship_id_values)
                        or len(relationship_id_values) != len(set(relationship_id_values))
                        or len(slide_relationship_rows) != len(relationship_ids)
                        or set(relationship_map) != set(relationship_ids)
                        or not slide_numeric_ids_valid
                        or len(normalized_slide_numeric_ids)
                        != len(set(normalized_slide_numeric_ids))
                        or any(
                            relation.attrib.get("TargetMode") not in (None, "Internal")
                            for relation in slide_relationship_rows
                        )
                        or any(relationship_id not in relationship_map for relationship_id in relationship_ids)
                    ):
                        raise ReleaseGateError("visual PPTX slide relationships are ambiguous or external")
                    slide_targets = [
                        (PurePosixPath("ppt") / relationship_map[relationship_id]).as_posix()
                        for relationship_id in relationship_ids
                    ]
                    if (
                        len(relationship_ids) != len(set(relationship_ids))
                        or len(slide_targets) != len(set(slide_targets))
                        or any(".." in PurePosixPath(target).parts for target in slide_targets)
                        or any(
                            not re.fullmatch(r"ppt/slides/slide[1-9][0-9]*\.xml", target)
                            or target not in package_names
                            for target in slide_targets
                        )
                    ):
                        raise ReleaseGateError("visual PPTX slide relationships are invalid")
                    pptx_pages = len(slide_ids)
            except (KeyError, ET.ParseError, zipfile.BadZipFile) as exc:
                raise ReleaseGateError("visual PPTX cannot be parsed for page verification") from exc
            try:
                with fitz.open(paths["artifact-pdf"]) as pdf_document:
                    pdf_pages = pdf_document.page_count
            except Exception as exc:
                raise ReleaseGateError("visual PDF cannot be opened for page verification") from exc
            if pptx_pages != len(expected_pages) or pdf_pages != len(expected_pages):
                raise ReleaseGateError(f"delivered PPTX/PDF page count mismatch: {case['caseId']}")
            ocr_schema = Draft202012Validator(
                _load(REPO_ROOT / "contracts" / "schemas" / "ocr-evidence.schema.json")
            )
            toolchain_lock = _load(REPO_ROOT / "release" / "toolchains.lock.json")
            locked_components = {
                "rasterizer": (toolchain_lock.get("rasterizer", {}), "exactBuild"),
                "ocrExecutable": (toolchain_lock.get("ocr", {}).get("executable", {}), "exactBuild"),
                "ocrModel": (toolchain_lock.get("ocr", {}).get("model", {}), "exactBuild"),
                "languagePack": (toolchain_lock.get("ocr", {}).get("languagePack", {}), "exactBuild"),
                "normalizer": (toolchain_lock.get("normalizer", {}), "version"),
                "mapper": (toolchain_lock.get("mapper", {}), "version"),
            }
            expected_ocr_toolchain: dict[str, dict[str, str]] = {}
            for component_name, (component, version_key) in locked_components.items():
                version = component.get(version_key)
                digest = component.get("digest")
                if (
                    component.get("verified") is not True
                    or not isinstance(version, str)
                    or not version
                    or not _is_digest(digest)
                ):
                    raise ReleaseGateError(f"locked OCR toolchain is incomplete: {component_name}")
                expected_ocr_toolchain[component_name] = {
                    "version": version,
                    "digest": digest,
                }
            mapping_projections: dict[str, list[tuple[str, str, str, str]]] = {}
            for surface in ("pptx", "pdf"):
                report = _load(paths[f"ocr-{surface}"])
                errors = list(ocr_schema.iter_errors(report))
                mapping_rows = report.get("mapping", [])
                detection_rows = report.get("detections", [])
                mapped_id_list = [row.get("textId") for row in mapping_rows]
                detection_id_list = [row.get("detectionId") for row in detection_rows]
                referenced_id_list = [
                    detection_id
                    for row in mapping_rows
                    for detection_id in row.get("detectionIds", [])
                ]
                detection_by_id = {
                    row.get("detectionId"): row
                    for row in detection_rows
                }
                mapping_semantics_invalid = any(
                    not isinstance(row.get("normalizedText"), str)
                    or not row.get("normalizedText")
                    or row.get("normalizedText") != row.get("expectedText")
                    or row.get("expectedText")
                    != _normalize_ocr_text(
                        str(entry_by_text.get(row.get("textId"), {}).get("text", ""))
                    )
                    or _normalize_ocr_text(
                        "\n".join(
                            str(detection_by_id.get(detection_id, {}).get("text", ""))
                            for detection_id in row.get("detectionIds", [])
                        )
                    )
                    != row.get("normalizedText")
                    or any(
                        not _inside_approved_region(
                            detection_by_id.get(detection_id, {}).get("region"),
                            entry_by_text.get(row.get("textId"), {}).get("region"),
                        )
                        for detection_id in row.get("detectionIds", [])
                    )
                    or any(
                        detection_by_id.get(detection_id, {}).get("slide")
                        != entry_by_text.get(row.get("textId"), {}).get("slide")
                        for detection_id in row.get("detectionIds", [])
                    )
                    for row in mapping_rows
                )
                detection_semantics_invalid = any(
                    isinstance(row.get("confidence"), bool)
                    or not isinstance(row.get("confidence"), (int, float))
                    or not math.isfinite(float(row.get("confidence", float("nan"))))
                    or float(row.get("confidence", 0)) < 0.99
                    or row.get("alternatives") != []
                    or row.get("clipped") is not False
                    or row.get("tofu") is not False
                    or row.get("slide") not in expected_pages
                    for row in detection_rows
                )
                mapped_by_id = {
                    str(row.get("textId")): row
                    for row in mapping_rows
                }
                relation_geometry_invalid = any(
                    not _relation_geometry_valid(
                        relation,
                        mapped_by_id,
                        detection_by_id,
                    )
                    for relation in relation_rows
                )
                if (
                    errors
                    or report.get("approvalEnvelopeDigest") != approval_digest
                    or report.get("artifactDigest") != artifact_digests[surface.upper()]
                    or report.get("surface") != surface.upper()
                    or report.get("visibleTextManifestDigest") != visible_digest
                    or report.get("toolchain") != expected_ocr_toolchain
                    or report.get("status") != "PASS"
                    or report.get("blockers") != []
                    or report.get("pageCount") != len(expected_pages)
                    or report.get("pageCount") != len(report.get("pageRasterDigests", []))
                    or expected_pages != list(range(1, len(expected_pages) + 1))
                    or len(mapped_id_list) != len(set(mapped_id_list))
                    or set(mapped_id_list) != expected_text_ids
                    or len(detection_id_list) != len(set(detection_id_list))
                    or len(referenced_id_list) != len(set(referenced_id_list))
                    or set(referenced_id_list) != set(detection_id_list)
                    or mapping_semantics_invalid
                    or detection_semantics_invalid
                    or relation_geometry_invalid
                    or any(row.get("status") != "PASS" for row in mapping_rows)
                ):
                    raise ReleaseGateError(f"visual OCR binding is invalid: {case['caseId']}:{surface}")
                mapping_projections[surface] = sorted(
                    (
                        str(row["textId"]),
                        str(row["normalizedText"]),
                        str(row["expectedText"]),
                        str(row["status"]),
                    )
                    for row in report["mapping"]
                )
            if mapping_projections["pptx"] != mapping_projections["pdf"]:
                raise ReleaseGateError(f"PPTX/PDF OCR mapping disagreement: {case['caseId']}")
    defects = source.get("criticalDefects")
    if not isinstance(defects, list) or defects:
        raise ReleaseGateError("visual source has missing or non-empty critical-defect ledger")
    if summary.get("externalVisualPass") is not True or summary.get("criticalDefects") != 0:
        raise ReleaseGateError("visual summary disagrees with source")


def _validate_named_evidence_refs(value: Any, evidence_dir: Path) -> None:
    if isinstance(value, dict):
        if "evidenceRef" in value or "evidenceDigest" in value:
            reference = value.get("evidenceRef")
            digest = value.get("evidenceDigest")
            if not isinstance(reference, str) or not _is_digest(digest):
                raise ReleaseGateError("raw evidence reference/digest pair is incomplete")
            path = (evidence_dir / reference).resolve()
            try:
                path.relative_to(evidence_dir.resolve())
            except ValueError as exc:
                raise ReleaseGateError("raw evidence reference escapes its directory") from exc
            if not path.is_file() or _sha256(path) != digest:
                raise ReleaseGateError(f"raw evidence artifact is missing or stale: {reference}")
        for nested in value.values():
            _validate_named_evidence_refs(nested, evidence_dir)
    elif isinstance(value, list):
        for nested in value:
            _validate_named_evidence_refs(nested, evidence_dir)

def _validate_source_evidence(
    evidence_dir: Path,
    name: str,
    summary: dict[str, Any],
) -> None:
    source_path = (evidence_dir / str(summary["sourceEvidenceRef"])).resolve()
    try:
        source_path.relative_to(evidence_dir.resolve())
    except ValueError as exc:
        raise ReleaseGateError(f"{name} source evidence escapes its directory") from exc
    if not source_path.is_file() or _sha256(source_path) != summary["sourceEvidenceDigest"]:
        raise ReleaseGateError(f"{name} source evidence digest mismatch")
    source = _load(source_path)
    _validate_named_evidence_refs(source, evidence_dir)
    if name == "course-summary.json":
        derived = aggregate_course(source)
        _compare_aggregate(
            summary,
            derived,
            ("status", "validStarters", "requiredComplete", "complete", "requiredImproved", "improved", "blockers"),
        )
    elif name == "beta-summary.json":
        derived = aggregate_beta(source)
        _compare_aggregate(
            summary,
            derived,
            ("status", "participants", "providerAllocation", "scopeAllocation", "complete", "completedByProvider", "blockers"),
        )
    elif name == "documents-summary.json":
        derived = aggregate_documents(source)
        _compare_aggregate(
            summary,
            derived,
            ("status", "rendererStatus", "browserVisualStatus", "criticalDefects", "blockers"),
        )
    elif name == "provider-summary.json":
        _validate_provider_source(source, summary)
    elif name == "visual-summary.json":
        _validate_visual_source(source, summary, evidence_dir)


def _validate_artifact(
    archive_path: Path,
    manifest_path: Path,
    access_path: Path,
    *,
    target: str,
    closure: dict[str, Any],
) -> dict[str, Any]:
    manifest = _load(manifest_path)
    access = _load(access_path)
    if manifest.get("target") != target or access.get("target") != target:
        raise ReleaseGateError("artifact or access record belongs to another target")
    expected_name = closure["artifactPattern"].format(version=manifest.get("version"))
    if manifest.get("artifact") != archive_path.name or archive_path.name != expected_name:
        raise ReleaseGateError("artifact name/version does not match selected target closure")
    closure_digest = canonical_digest(closure)
    if manifest.get("closureDigest") != closure_digest or access.get("closureDigest") != closure_digest:
        raise ReleaseGateError("artifact is not bound to the selected closure")
    source_reads = manifest.get("sourceReads")
    if source_reads != access.get("sourceReads") or not isinstance(source_reads, list):
        raise ReleaseGateError("build source access record is missing or inconsistent")
    source_records = manifest.get("sourceRecords")
    if not isinstance(source_records, list) or len(source_records) != len(source_reads):
        raise ReleaseGateError("source digest records are missing")
    if {record.get("source") for record in source_records} != set(source_reads):
        raise ReleaseGateError("source digest records disagree with source access")
    archive_paths: set[str] = set()
    for record in source_records:
        source_path = (REPO_ROOT / str(record.get("source", ""))).resolve()
        try:
            source_path.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ReleaseGateError("source digest record escapes repository") from exc
        member_path = str(record.get("archivePath", ""))
        if not member_path or member_path in archive_paths:
            raise ReleaseGateError("source digest archive path is empty or duplicated")
        archive_paths.add(member_path)
        if not source_path.is_file() or _sha256(source_path) != record.get("sha256"):
            raise ReleaseGateError(f"release artifact source is stale: {record.get('source')}")
    for rule in closure.get("sourceRoots", []):
        if not any(_rule_matches(path, rule) for path in source_reads):
            raise ReleaseGateError(f"required source root was not read: {rule}")
    for rule in closure.get("forbiddenSourceRoots", []):
        if any(_rule_matches(path, rule) for path in source_reads):
            raise ReleaseGateError(f"forbidden source root was read: {rule}")
    if manifest.get("artifactSha256") != _sha256(archive_path):
        raise ReleaseGateError("archive digest does not match member manifest")
    member_records = manifest.get("members")
    if not isinstance(member_records, list):
        raise ReleaseGateError("member manifest is missing members")
    records = {item["path"]: item["sha256"] for item in member_records}
    if archive_paths != set(records):
        raise ReleaseGateError("source-to-archive mapping does not cover every member")
    for source_record in source_records:
        if records[source_record["archivePath"]] != source_record["sha256"]:
            raise ReleaseGateError("source digest does not match archived member digest")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or set(names) != set(records):
                raise ReleaseGateError("archive members do not match the member manifest")
            for info in archive.infolist():
                if info.compress_type != zipfile.ZIP_STORED:
                    raise ReleaseGateError("release archive must use reproducible stored members")
                actual = "sha256:" + hashlib.sha256(archive.read(info.filename)).hexdigest()
                if actual != records[info.filename]:
                    raise ReleaseGateError(f"archive member digest mismatch: {info.filename}")
    except zipfile.BadZipFile as exc:
        raise ReleaseGateError(f"release archive is invalid: {exc}") from exc
    return manifest


def _validate_toolchain_lock(lock: dict[str, Any]) -> None:
    if lock.get("status") != "LOCKED":
        raise ReleaseGateError("exact visual/OCR toolchain is not LOCKED")
    required_components = (
        lock.get("platform"),
        lock.get("applications", {}).get("hancomHangeul"),
        lock.get("applications", {}).get("powerPoint"),
        lock.get("applications", {}).get("edge"),
        lock.get("rasterizer"),
        lock.get("ocr", {}).get("executable"),
        lock.get("ocr", {}).get("model"),
        lock.get("ocr", {}).get("languagePack"),
        lock.get("normalizer"),
        lock.get("mapper"),
        lock.get("manifestBuilder"),
    )
    for component in required_components:
        if not isinstance(component, dict) or component.get("verified") is not True:
            raise ReleaseGateError("toolchain component is missing or unverified")
        if not _is_digest(component.get("digest")):
            raise ReleaseGateError("toolchain component digest is missing")
        identity = component.get("exactBuild") or component.get("name") or component.get("version")
        if not isinstance(identity, str) or not identity:
            raise ReleaseGateError("toolchain component exact identity is missing")
    file_components = required_components[1:8]
    for component in file_components:
        component_path = Path(str(component.get("path", "")))
        if not component_path.is_absolute() or not component_path.is_file():
            raise ReleaseGateError("toolchain binary/model path is missing")
        if _sha256(component_path) != component["digest"]:
            raise ReleaseGateError(f"installed toolchain digest mismatch: {component_path}")
    fonts = lock.get("fonts")
    if not isinstance(fonts, list) or not fonts:
        raise ReleaseGateError("toolchain font lock is missing")
    for font in fonts:
        font_path = Path(str(font.get("path", "")))
        if (
            font.get("verified") is not True
            or not font.get("name")
            or not _is_digest(font.get("digest"))
            or not font_path.is_absolute()
            or not font_path.is_file()
            or _sha256(font_path) != font["digest"]
        ):
            raise ReleaseGateError("toolchain font identity is incomplete or stale")
    source_digests = lock.get("sourceDigests")
    if not isinstance(source_digests, dict) or not source_digests or not all(_is_digest(value) for value in source_digests.values()):
        raise ReleaseGateError("toolchain source digests are incomplete")
    source_paths = {
        "build_visible_text_manifest.py": REPO_ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts" / "build_visible_text_manifest.py",
        "map_ocr_regions.py": REPO_ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts" / "ocr" / "map_ocr_regions.py",
        "validate_visible_text.py": REPO_ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts" / "ocr" / "validate_visible_text.py",
    }
    for name, path in source_paths.items():
        if source_digests.get(name) != _sha256(path):
            raise ReleaseGateError(f"toolchain source digest is stale: {name}")
    if lock["manifestBuilder"]["digest"] != source_digests["build_visible_text_manifest.py"]:
        raise ReleaseGateError("manifest builder component digest disagrees with source lock")
    if lock["mapper"]["digest"] != source_digests["map_ocr_regions.py"]:
        raise ReleaseGateError("mapper component digest disagrees with source lock")
    if lock["normalizer"]["digest"] != source_digests["validate_visible_text.py"]:
        raise ReleaseGateError("normalizer component digest disagrees with source lock")


def validate_release(
    *,
    target: str,
    closure_path: Path,
    artifacts: Path,
    evidence: Path | None,
    strict: bool,
) -> dict[str, object]:
    if target not in TARGETS:
        raise ReleaseGateError(f"unsupported target: {target}")
    closure = _load(closure_path)
    if closure.get("target") != target:
        raise ReleaseGateError("selected target does not match closure manifest")
    archives = list(artifacts.glob("*.zip"))
    manifests = list(artifacts.glob("*.members.json"))
    access_logs = list(artifacts.glob("*.access.json"))
    if len(archives) != 1 or len(manifests) != 1 or len(access_logs) != 1:
        raise ReleaseGateError("selected target requires one archive, member manifest, and access record")
    manifest = _validate_artifact(
        archives[0],
        manifests[0],
        access_logs[0],
        target=target,
        closure=closure,
    )
    required_evidence: list[str] = []
    if target == "business-plan-writer":
        required_evidence = ["provider-summary.json", "course-summary.json", "beta-summary.json", "visual-summary.json"]
    elif target == "course-kit":
        required_evidence = ["course-summary.json"]
    elif target == "business-documents":
        required_evidence = ["documents-summary.json"]
    if required_evidence and (not strict or evidence is None):
        raise ReleaseGateError("a qualifying release requires strict raw-bound evidence")
    checked: list[str] = []
    for name in required_evidence:
        summary = _load(evidence / name)
        _validate_evidence_shape(name, summary)
        _validate_source_evidence(evidence, name, summary)
        checked.append(name)
    if target == "business-plan-writer":
        lock_path = REPO_ROOT / "release" / "toolchains.lock.json"
        lock = _load(lock_path)
        _validate_toolchain_lock(lock)
        visual = _load(evidence / "visual-summary.json")
        if visual.get("toolchainLockDigest") != _sha256(lock_path):
            raise ReleaseGateError("visual evidence is not bound to the exact toolchain lock")
    return {
        "status": "PASS",
        "target": target,
        "version": manifest["version"],
        "required": closure.get("required", []),
        "accessLog": manifest["sourceReads"],
        "forbiddenReads": closure.get("forbiddenReads", []),
        "evidence": checked,
        "publishAttempted": False,
        "tagAttempted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed target release qualification without publishing")
    parser.add_argument("--target", choices=sorted(TARGETS), required=True)
    parser.add_argument("--closure", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--no-publish", action="store_true")
    parser.add_argument("--assert-no-tag", action="store_true")
    parser.add_argument("--strict-evidence", action="store_true")
    parser.add_argument("--audit-access-log", action="store_true")
    args = parser.parse_args()
    if not args.no_publish or not args.assert_no_tag or not args.audit_access_log:
        print("BLOCK: dry-run must forbid publish/tag and audit actual source access", file=sys.stderr)
        return 2
    try:
        result = validate_release(
            target=args.target,
            closure_path=args.closure,
            artifacts=args.artifacts,
            evidence=args.evidence,
            strict=args.strict_evidence,
        )
    except ReleaseGateError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

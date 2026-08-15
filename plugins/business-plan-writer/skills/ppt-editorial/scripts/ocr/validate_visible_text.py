from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from approved_inputs import (
    ApprovalError,
    IMAGE_RENDERER_VERSION,
    resolve_approved_bundle,
    resolve_value,
)

from map_ocr_regions import MappingError, map_detections

NORMALIZER_VERSION = "dayoun-visible-text-v1"
MIN_CONFIDENCE = 0.99
_HORIZONTAL_SPACE = re.compile(r"[\t\f\v \u00a0]+")


class VisibleTextError(ValueError):
    pass


def normalize_exact(text: str) -> str:
    value = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [_HORIZONTAL_SPACE.sub(" ", line).strip() for line in value.split("\n")]
    return "\n".join(lines).strip()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _detection_health(detection: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    detection_id = str(detection.get("detectionId", "<missing>"))
    raw_confidence = detection.get("confidence")
    if (
        isinstance(raw_confidence, bool)
        or not isinstance(raw_confidence, (int, float))
        or not math.isfinite(raw_confidence)
        or not 0 <= raw_confidence <= 1
    ):
        blockers.append(f"invalid-confidence:{detection_id}")
    elif raw_confidence < MIN_CONFIDENCE:
        blockers.append(f"low-confidence:{detection_id}:{raw_confidence}")
    if detection.get("alternatives"):
        blockers.append(f"ambiguous-alternatives:{detection_id}")
    if detection.get("clipped"):
        blockers.append(f"clipped:{detection_id}")
    if detection.get("tofu") or "\ufffd" in str(detection.get("text", "")):
        blockers.append(f"tofu:{detection_id}")
    return blockers


def validate_surface(
    manifest: dict[str, Any],
    ocr: dict[str, Any],
    *,
    surface: str,
    approval_envelope_digest: str,
    visible_manifest_digest: str,
    artifact_digest: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    if ocr.get("artifactDigest") != artifact_digest:
        blockers.append("ocr-artifact-digest-mismatch")
    page_count = ocr.get("pageCount")
    page_raster_digests = ocr.get("pageRasterDigests")
    if (
        isinstance(page_count, bool)
        or not isinstance(page_count, int)
        or page_count < 1
        or not isinstance(page_raster_digests, list)
        or len(page_raster_digests) != page_count
        or any(
            not isinstance(value, str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", value)
            for value in page_raster_digests
        )
    ):
        blockers.append("invalid-page-raster-provenance")
        page_count = 0
        page_raster_digests = []
    if surface not in {"PPTX", "PDF"}:
        blockers.append(f"unsupported-surface:{surface}")
    required_provenance = (
        "rasterizer",
        "ocrExecutable",
        "ocrModel",
        "languagePack",
        "normalizer",
        "mapper",
    )
    toolchain = ocr.get("toolchain")
    if not isinstance(toolchain, dict):
        blockers.append("missing-toolchain")
        toolchain = {}
    for key in required_provenance:
        value = toolchain.get(key)
        if (
            not isinstance(value, dict)
            or not value.get("version")
            or not isinstance(value.get("digest"), str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", value["digest"])
        ):
            blockers.append(f"missing-toolchain-provenance:{key}")
    detections = ocr.get("detections")
    if not isinstance(detections, list):
        blockers.append("missing-detections")
        detections = []
    for detection in detections:
        blockers.extend(_detection_health(detection))
        slide = detection.get("slide")
        if isinstance(slide, bool) or not isinstance(slide, int) or not 1 <= slide <= page_count:
            blockers.append(f"detection-page-out-of-range:{detection.get('detectionId', '<missing>')}")
    try:
        mapped = map_detections(manifest, detections)
    except (MappingError, KeyError, TypeError, ValueError) as exc:
        blockers.append(f"mapping-error:{exc}")
        mapped = {"mapping": [], "blockers": []}
    blockers.extend(mapped.get("blockers", []))
    if mapped.get("status") != "PASS":
        blockers.append("mapper-status-auto-block")
    entries = {str(item["textId"]): item for item in manifest.get("entries", [])}
    mapped_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in mapped.get("mapping", []):
        text_id = str(row["textId"])
        if text_id in seen:
            blockers.append(f"duplicate-mapping:{text_id}")
            continue
        seen.add(text_id)
        if row.get("status") != "MAPPED":
            blockers.append(f"mapper-row-auto-block:{text_id}")
        expected = normalize_exact(str(entries[text_id]["text"]))
        if not expected:
            blockers.append(f"empty-approved-text:{text_id}")
        actual = normalize_exact("\n".join(str(part) for part in row["textParts"]))
        status = "PASS" if actual == expected else "AUTO_BLOCK"
        if status != "PASS":
            blockers.append(f"text-mismatch:{text_id}")
        mapped_rows.append(
            {
                "textId": text_id,
                "detectionIds": row["detectionIds"],
                "normalizedText": actual,
                "expectedText": expected,
                "status": status,
            }
        )
    missing_ids = sorted(set(entries) - seen)
    blockers.extend(f"missing-mapping:{text_id}" for text_id in missing_ids)
    relation_ids: set[str] = set()
    detection_by_id = {
        str(detection.get("detectionId")): detection for detection in detections
    }
    mapped_by_id = {row["textId"]: row for row in mapped_rows}
    for relation in manifest.get("relations", []):
        relation_id = str(relation.get("relationId", ""))
        if not relation_id or relation_id in relation_ids:
            blockers.append(f"duplicate-or-empty-relation:{relation_id}")
        relation_ids.add(relation_id)
        if relation.get("fromTextId") not in seen or relation.get("toTextId") not in seen:
            blockers.append(f"unresolved-relation:{relation_id}")
        else:
            from_row = mapped_by_id[str(relation["fromTextId"])]
            to_row = mapped_by_id[str(relation["toTextId"])]
            from_boxes = [
                detection_by_id[item]["region"] for item in from_row["detectionIds"]
            ]
            to_boxes = [
                detection_by_id[item]["region"] for item in to_row["detectionIds"]
            ]
            from_center = (
                sum((box[0] + box[2]) / 2 for box in from_boxes) / len(from_boxes),
                sum((box[1] + box[3]) / 2 for box in from_boxes) / len(from_boxes),
            )
            to_center = (
                sum((box[0] + box[2]) / 2 for box in to_boxes) / len(to_boxes),
                sum((box[1] + box[3]) / 2 for box in to_boxes) / len(to_boxes),
            )
            geometry = relation.get("geometry")
            if geometry == "same-row-left-to-right":
                valid_geometry = (
                    abs(from_center[1] - to_center[1]) <= 0.05
                    and from_center[0] < to_center[0]
                )
            elif geometry == "top-to-bottom":
                valid_geometry = from_center[1] < to_center[1]
            elif geometry == "adjacent":
                valid_geometry = math.dist(from_center, to_center) <= 0.5
            else:
                valid_geometry = False
            if not valid_geometry:
                blockers.append(f"relation-geometry:{relation_id}")
    return {
        "schemaVersion": "1.0.0",
        "approvalEnvelopeDigest": approval_envelope_digest,
        "visibleTextManifestDigest": visible_manifest_digest,
        "artifactDigest": artifact_digest,
        "surface": surface,
        "pageCount": page_count,
        "pageRasterDigests": page_raster_digests,
        "toolchain": toolchain,
        "detections": detections,
        "mapping": mapped_rows,
        "status": "AUTO_BLOCK" if blockers else "PASS",
        "blockers": sorted(set(blockers)),
    }


def validate_pair(pptx: dict[str, Any], pdf: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pptx.get("status") != "PASS" or pdf.get("status") != "PASS":
        blockers.append("surface-not-pass")
    if pptx.get("pageCount") != pdf.get("pageCount"):
        blockers.append("pptx-pdf-page-count-disagreement")
    pptx_rows = {row["textId"]: row["normalizedText"] for row in pptx.get("mapping", [])}
    pdf_rows = {row["textId"]: row["normalizedText"] for row in pdf.get("mapping", [])}
    if pptx_rows != pdf_rows:
        blockers.append("pptx-pdf-disagreement")
    return blockers


def _reject_constant(value: str) -> None:
    raise VisibleTextError(f"non-finite JSON number: {value}")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise VisibleTextError(f"cannot load {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed visible-text validation for image-first PPT")
    parser.add_argument("--approval-digest", required=True)
    parser.add_argument("--approval-store", type=Path, required=True)
    parser.add_argument("--pptx-ocr", type=Path, required=True)
    parser.add_argument("--pdf-ocr", type=Path, required=True)
    parser.add_argument("--pptx", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        envelope = resolve_value(args.approval_store.resolve(), args.approval_digest)
        if envelope.get("rendererMode") != "image-first":
            raise VisibleTextError("approval envelope is not image-first")
        _payload, _briefs, manifest = resolve_approved_bundle(
            args.approval_store.resolve(),
            envelope,
            expected_mode="image-first",
            expected_renderer_version=IMAGE_RENDERER_VERSION,
        )
        if manifest is None:
            raise VisibleTextError("approved visible-text manifest is missing")
        manifest_digest = envelope["visibleTextManifestDigest"]
        pptx = validate_surface(
            manifest,
            _load(args.pptx_ocr),
            surface="PPTX",
            approval_envelope_digest=args.approval_digest,
            visible_manifest_digest=manifest_digest,
            artifact_digest=sha256_file(args.pptx),
        )
        pdf = validate_surface(
            manifest,
            _load(args.pdf_ocr),
            surface="PDF",
            approval_envelope_digest=args.approval_digest,
            visible_manifest_digest=manifest_digest,
            artifact_digest=sha256_file(args.pdf),
        )
        pair_blockers = validate_pair(pptx, pdf)
        result = {
            "normalizerVersion": NORMALIZER_VERSION,
            "status": "AUTO_BLOCK" if pair_blockers else "PASS",
            "pairBlockers": pair_blockers,
            "pptx": pptx,
            "pdf": pdf,
        }
    except (ApprovalError, VisibleTextError, KeyError, TypeError, ValueError) as exc:
        print(f"AUTO_BLOCK: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

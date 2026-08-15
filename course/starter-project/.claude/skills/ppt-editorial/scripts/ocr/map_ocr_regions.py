from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MAPPER_VERSION = "dayoun-region-map-v1"
MIN_DETECTION_OVERLAP = 0.50


class MappingError(ValueError):
    pass


def _region(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, list) or len(value) != 4:
        raise MappingError(f"invalid region: {value}")
    x0, y0, x1, y1 = (float(part) for part in value)
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise MappingError(f"region outside normalized raster: {value}")
    return x0, y0, x1, y1


def _center(region: tuple[float, float, float, float]) -> tuple[float, float]:
    x0, y0, x1, y1 = region
    return (x0 + x1) / 2, (y0 + y1) / 2


def _overlap_of_detection(
    detection: tuple[float, float, float, float], target: tuple[float, float, float, float]
) -> float:
    dx0, dy0, dx1, dy1 = detection
    tx0, ty0, tx1, ty1 = target
    width = max(0.0, min(dx1, tx1) - max(dx0, tx0))
    height = max(0.0, min(dy1, ty1) - max(dy0, ty0))
    area = (dx1 - dx0) * (dy1 - dy0)
    return 0.0 if area <= 0 else (width * height) / area


def _matches(
    detection: tuple[float, float, float, float], target: tuple[float, float, float, float]
) -> bool:
    cx, cy = _center(detection)
    tx0, ty0, tx1, ty1 = target
    return tx0 <= cx <= tx1 and ty0 <= cy <= ty1 and _overlap_of_detection(detection, target) >= MIN_DETECTION_OVERLAP


def map_detections(manifest: dict[str, Any], detections: list[dict[str, Any]]) -> dict[str, Any]:
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise MappingError("visible-text manifest has no entries")
    targets: dict[str, tuple[int, tuple[float, float, float, float]]] = {}
    for entry in entries:
        text_id = str(entry["textId"])
        if text_id in targets:
            raise MappingError(f"duplicate textId: {text_id}")
        targets[text_id] = (int(entry["slide"]), _region(entry["region"]))
    assignments: dict[str, list[dict[str, Any]]] = {text_id: [] for text_id in targets}
    blockers: list[str] = []
    seen_detection_ids: set[str] = set()
    for detection in detections:
        detection_id = str(detection.get("detectionId", ""))
        if not detection_id or detection_id in seen_detection_ids:
            blockers.append(f"duplicate-or-empty-detection-id:{detection_id}")
            continue
        seen_detection_ids.add(detection_id)
        slide = int(detection.get("slide", 0))
        box = _region(detection.get("region"))
        candidates = [
            text_id
            for text_id, (target_slide, target_region) in targets.items()
            if slide == target_slide and _matches(box, target_region)
        ]
        if len(candidates) != 1:
            blockers.append(
                f"ambiguous-detection:{detection_id}:{','.join(sorted(candidates)) or 'no-region'}"
            )
            continue
        assignments[candidates[0]].append(detection)
    mapping: list[dict[str, Any]] = []
    for entry in entries:
        text_id = str(entry["textId"])
        assigned = assignments[text_id]
        if not assigned:
            blockers.append(f"missing-text-region:{text_id}")
            continue
        ordered = sorted(
            assigned,
            key=lambda item: (
                round(float(item["region"][1]), 9),
                round(float(item["region"][0]), 9),
                str(item["detectionId"]),
            ),
        )
        mapping.append(
            {
                "textId": text_id,
                "detectionIds": [str(item["detectionId"]) for item in ordered],
                "textParts": [str(item.get("text", "")) for item in ordered],
                "status": "AUTO_BLOCK" if any(not part for part in [item.get("text") for item in ordered]) else "MAPPED",
            }
        )
    return {
        "mapperVersion": MAPPER_VERSION,
        "status": "AUTO_BLOCK" if blockers else "PASS",
        "mapping": mapping,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Map locked OCR detections to approved text regions")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ocr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        ocr = json.loads(args.ocr.read_text(encoding="utf-8"))
        result = map_detections(manifest, ocr["detections"])
    except (OSError, json.JSONDecodeError, KeyError, MappingError, TypeError, ValueError) as exc:
        print(f"AUTO_BLOCK: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result["status"])
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

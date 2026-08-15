from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

from approved_inputs import ApprovalError, digest_value, load_json

TOKEN_KINDS = {
    "heading",
    "body",
    "label",
    "value",
    "number",
    "date",
    "proper-noun",
    "evidence",
}
RELATION_KINDS = {"label-value", "evidence-claim", "date-event", "proper-noun-claim"}
RELATION_GEOMETRIES = {"same-row-left-to-right", "top-to-bottom", "adjacent"}


class ManifestError(ValueError):
    pass


def _validate_region(region: Any) -> list[float]:
    if not isinstance(region, list) or len(region) != 4:
        raise ManifestError("every visible text occurrence requires [x0,y0,x1,y1]")
    values = [float(value) for value in region]
    x0, y0, x1, y1 = values
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise ManifestError(f"invalid normalized region: {region}")
    return values


def build_manifest(payload: dict[str, Any], briefs: list[dict[str, Any]]) -> dict[str, Any]:
    if not payload.get("projectId"):
        raise ManifestError("canonical payload requires projectId")
    entries: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_relation_ids: set[str] = set()
    seen_slides: set[int] = set()
    for brief_index, brief in enumerate(briefs, start=1):
        slides = brief.get("slides")
        if not isinstance(slides, list):
            raise ManifestError(f"deck brief {brief_index} requires slides[]")
        for slide_position, slide in enumerate(slides, start=1):
            slide_number = int(slide.get("slide", slide_position))
            if slide_number in seen_slides:
                raise ManifestError(f"duplicate global slide number: {slide_number}")
            seen_slides.add(slide_number)
            visible = slide.get("visibleText")
            if not isinstance(visible, list) or not visible:
                raise ManifestError(f"slide {slide_number} requires non-empty visibleText[]")
            for occurrence, item in enumerate(visible, start=1):
                text_id = str(item.get("textId") or f"b{brief_index}.s{slide_number}.t{occurrence}")
                if text_id in seen_ids:
                    raise ManifestError(f"duplicate textId: {text_id}")
                seen_ids.add(text_id)
                text = unicodedata.normalize("NFC", str(item.get("text", ""))).strip()
                if not text:
                    raise ManifestError(f"empty visible text: {text_id}")
                token_kind = item.get("tokenKind", "body")
                if token_kind not in TOKEN_KINDS:
                    raise ManifestError(f"unsupported tokenKind {token_kind}: {text_id}")
                entry = {
                    "textId": text_id,
                    "briefIndex": brief_index,
                    "slide": slide_number,
                    "occurrence": int(item.get("occurrence", occurrence)),
                    "text": text,
                    "tokenKind": token_kind,
                    "region": _validate_region(item.get("region")),
                }
                if item.get("sourceRef"):
                    entry["sourceRef"] = str(item["sourceRef"])
                entries.append(entry)
            for relation_position, relation in enumerate(slide.get("relations", []), start=1):
                kind = relation.get("kind")
                if kind not in RELATION_KINDS:
                    raise ManifestError(f"unsupported relation kind: {kind}")
                geometry = relation.get("geometry")
                if geometry not in RELATION_GEOMETRIES:
                    raise ManifestError(f"unsupported relation geometry: {geometry}")
                relation_id = str(
                    relation.get("relationId")
                    or f"b{brief_index}.s{slide_number}.r{relation_position}"
                )
                if not relation_id or relation_id in seen_relation_ids:
                    raise ManifestError(f"duplicate or empty relationId: {relation_id}")
                seen_relation_ids.add(relation_id)
                relations.append(
                    {
                        "relationId": relation_id,
                        "kind": kind,
                        "geometry": geometry,
                        "fromTextId": str(relation["fromTextId"]),
                        "toTextId": str(relation["toTextId"]),
                    }
                )
    if not seen_slides or seen_slides != set(range(1, len(seen_slides) + 1)):
        raise ManifestError("deck brief slide numbers must be contiguous from 1")
    entry_slide_by_id = {
        entry["textId"]: entry["slide"]
        for entry in entries
    }
    for relation in relations:
        if relation["fromTextId"] not in seen_ids or relation["toTextId"] not in seen_ids:
            raise ManifestError(f"relation references unknown text: {relation['relationId']}")
        if entry_slide_by_id[relation["fromTextId"]] != entry_slide_by_id[relation["toTextId"]]:
            raise ManifestError(f"relation crosses slides: {relation['relationId']}")
    return {
        "schemaVersion": "1.0.0",
        "projectId": payload["projectId"],
        "normalizerVersion": "dayoun-visible-text-v1",
        "mapperVersion": "dayoun-region-map-v1",
        "entries": sorted(entries, key=lambda item: (item["slide"], item["occurrence"], item["textId"])),
        "relations": sorted(relations, key=lambda item: item["relationId"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the pre-render visible-text approval oracle")
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--brief", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = load_json(args.payload)
        briefs = [load_json(path) for path in args.brief]
        manifest = build_manifest(payload, briefs)
    except (ApprovalError, ManifestError, KeyError, TypeError, ValueError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(digest_value(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

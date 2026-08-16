#!/usr/bin/env python3
"""Lock and validate a user-edited HWPX as the next canonical source."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any
import zipfile
from xml.etree import ElementTree as ET

from hwpx_visuals import canonical_element, inspect_hwpx
from hwpx_style_integrity import validate as validate_style_integrity


MIMETYPE = b"application/hwp+zip"
SECTION_MEMBER = re.compile(r"^Contents/section\d+\.xml$")
STYLE_CONTAINERS = {
    "paraProperties": "paraPr",
    "charProperties": "charPr",
    "borderFills": "borderFill",
}
VISUAL_KEYS = (
    "caption",
    "beforeParagraph",
    "afterParagraph",
    "hierarchy",
    "rowCount",
    "columnCount",
    "tableWidth",
    "imageWidth",
    "imageCellMargin",
    "captionCellMargin",
    "imageCellBorderFillID",
    "captionCellBorderFillID",
    "imageCellBorderDigest",
    "captionCellBorderDigest",
    "captionRowHeight",
    "captionPointSize",
    "captionBold",
    "captionAlign",
    "captionBackground",
)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def snapshot(path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            errors.extend(
                f"duplicate ZIP member: {name}"
                for name, count in Counter(names).items()
                if count > 1
            )
            if not infos or infos[0].filename != "mimetype":
                errors.append("mimetype must be the first ZIP member")
            elif infos[0].compress_type != zipfile.ZIP_STORED:
                errors.append("mimetype must be stored without compression")
            if "mimetype" not in names or archive.read("mimetype") != MIMETYPE:
                errors.append("invalid HWPX mimetype")
            try:
                header = ET.fromstring(archive.read("Contents/header.xml"))
            except (KeyError, ET.ParseError) as error:
                return {}, [*errors, f"cannot parse Contents/header.xml: {error}"]
            section_names = sorted(
                name for name in names if SECTION_MEMBER.fullmatch(name)
            )
            if not section_names:
                errors.append("HWPX has no Contents/sectionN.xml members")
            visible_parts = []
            for name in section_names:
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError as error:
                    errors.append(f"cannot parse {name}: {error}")
                    continue
                visible_parts.extend(
                    node.text or ""
                    for node in root.iter()
                    if local_name(node.tag) == "t"
                )
    except (FileNotFoundError, zipfile.BadZipFile) as error:
        return {}, [f"cannot read HWPX: {error}"]

    styles: dict[str, Any] = {}
    for container_name, item_name in STYLE_CONTAINERS.items():
        containers = [
            node for node in header.iter() if local_name(node.tag) == container_name
        ]
        if len(containers) != 1:
            errors.append(f"header must contain exactly one {container_name}")
            continue
        container = containers[0]
        definitions = [
            node for node in list(container) if local_name(node.tag) == item_name
        ]
        styles[container_name] = {
            "itemCnt": container.get("itemCnt", ""),
            "definitions": [
                {
                    "index": index,
                    "id": node.get("id", ""),
                    "sha256": "sha256:"
                    + hashlib.sha256(canonical_element(node)).hexdigest(),
                }
                for index, node in enumerate(definitions)
            ],
        }

    visual_report = inspect_hwpx(path)
    errors.extend(visual_report.get("integrityErrors", []))
    visuals = [
        {key: visual.get(key) for key in VISUAL_KEYS}
        for visual in visual_report.get("visuals", [])
    ]
    style_report = validate_style_integrity(path)
    errors.extend(
        f"style integrity: {error}" for error in style_report.get("errors", [])
    )
    return {
        "sha256": sha256(path),
        "visibleText": "\n".join(visible_parts),
        "styles": styles,
        "visuals": visuals,
    }, errors


def load_removed_blocks(
    path: Path | None,
    canonical_text: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if path is None:
        return [], []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return [], [f"cannot read removed-blocks file: {error}"]
    records = payload.get("removedBlocks") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return [], ["removedBlocks must be an array"]
    errors = []
    result = []
    seen = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "anchor",
            "scope",
            "restoreWithoutApproval",
        }:
            errors.append(
                "removed block must contain only anchor, scope, restoreWithoutApproval"
            )
            continue
        anchor = record.get("anchor")
        scope = record.get("scope")
        if not isinstance(anchor, str) or not anchor.strip():
            errors.append("removed block anchor must be non-empty")
            continue
        if not isinstance(scope, str) or not scope.strip():
            errors.append(f"removed block scope is required: {anchor}")
            continue
        if record.get("restoreWithoutApproval") is not False:
            errors.append(f"restoreWithoutApproval must be false: {anchor}")
            continue
        key = (anchor, scope)
        if key in seen:
            errors.append(f"duplicate removed block: {anchor} / {scope}")
        seen.add(key)
        if anchor in canonical_text:
            errors.append(f"removed block still exists in canonical source: {anchor}")
        result.append(
            {
                "anchor": anchor,
                "scope": scope,
                "restoreWithoutApproval": False,
            }
        )
    return result, errors


def lock(
    user_edited: Path,
    canonical_output: Path,
    receipt_path: Path,
    previous: Path | None,
    removed_blocks_path: Path | None,
    overwrite: bool,
) -> dict[str, Any]:
    errors = []
    if user_edited.resolve() == canonical_output.resolve():
        errors.append("user-edited input and canonical output must differ")
    if canonical_output.exists() and not overwrite:
        errors.append(f"canonical output already exists: {canonical_output}")
    if receipt_path.exists() and not overwrite:
        errors.append(f"receipt already exists: {receipt_path}")
    current, current_errors = snapshot(user_edited)
    errors.extend(current_errors)
    removed, removed_errors = load_removed_blocks(
        removed_blocks_path, current.get("visibleText", "")
    )
    errors.extend(removed_errors)
    previous_snapshot = None
    previous_errors: list[str] = []
    if previous is not None:
        previous_snapshot, previous_errors = snapshot(previous)
        errors.extend(
            f"previous source: {error}"
            for error in previous_errors
            if not error.startswith("style integrity:")
        )
    if errors:
        return {"status": "BLOCK", "errors": errors}

    canonical_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(user_edited, canonical_output)
    if sha256(canonical_output) != current["sha256"]:
        canonical_output.unlink(missing_ok=True)
        return {"status": "BLOCK", "errors": ["canonical copy digest mismatch"]}
    receipt = {
        "schemaVersion": "1.0.0",
        "status": "PASS",
        "role": "user-edited-canonical",
        "canonicalSource": str(canonical_output),
        "canonicalSha256": current["sha256"],
        "styles": current["styles"],
        "visuals": current["visuals"],
        "removedBlocks": removed,
        "previous": (
            {
                "path": str(previous),
                "sha256": previous_snapshot["sha256"],
                "stylesChanged": previous_snapshot["styles"] != current["styles"],
                "visualProfileChanged": (
                    previous_snapshot["visuals"] != current["visuals"]
                ),
                "validationErrors": previous_errors,
            }
            if previous_snapshot is not None
            else None
        ),
        "errors": [],
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def style_prefix_preserved(
    expected: dict[str, Any],
    actual: dict[str, Any],
) -> bool:
    expected_defs = expected.get("definitions", [])
    actual_defs = actual.get("definitions", [])
    return actual_defs[: len(expected_defs)] == expected_defs


def validate(
    canonical: Path,
    receipt_path: Path,
    candidate: Path | None,
) -> dict[str, Any]:
    errors = []
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as error:
        return {"status": "BLOCK", "errors": [f"cannot read receipt: {error}"]}
    if (
        receipt.get("schemaVersion") != "1.0.0"
        or receipt.get("role") != "user-edited-canonical"
    ):
        errors.append("invalid canonical receipt schema or role")
    canonical_snapshot, canonical_errors = snapshot(canonical)
    errors.extend(canonical_errors)
    if receipt.get("canonicalSha256") != canonical_snapshot.get("sha256"):
        errors.append("canonical source digest is missing or stale")
    if receipt.get("styles") != canonical_snapshot.get("styles"):
        errors.append("canonical style profile is missing or stale")
    if receipt.get("visuals") != canonical_snapshot.get("visuals"):
        errors.append("canonical visual profile is missing or stale")

    if candidate is not None:
        candidate_snapshot, candidate_errors = snapshot(candidate)
        errors.extend(f"candidate: {error}" for error in candidate_errors)
        for record in receipt.get("removedBlocks", []):
            anchor = record.get("anchor", "")
            if anchor and anchor in candidate_snapshot.get("visibleText", ""):
                errors.append(
                    f"candidate restored removed block without approval: {anchor}"
                )
        for name in STYLE_CONTAINERS:
            if not style_prefix_preserved(
                receipt.get("styles", {}).get(name, {}),
                candidate_snapshot.get("styles", {}).get(name, {}),
            ):
                errors.append(f"candidate changed user-edited {name} definitions")
        expected_visuals = {
            item.get("caption"): item for item in receipt.get("visuals", [])
        }
        candidate_visuals = {
            item.get("caption"): item
            for item in candidate_snapshot.get("visuals", [])
        }
        for caption, profile in expected_visuals.items():
            if candidate_visuals.get(caption) != profile:
                errors.append(
                    f"candidate changed or removed user-edited visual profile: {caption}"
                )
    return {
        "status": "PASS" if not errors else "BLOCK",
        "canonical": str(canonical),
        "candidate": str(candidate) if candidate else None,
        "receipt": str(receipt_path),
        "errors": errors,
    }


def write_report(report: dict[str, Any], path: Path | None) -> None:
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lock user-edited HWPX revisions.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    lock_parser = subparsers.add_parser("lock")
    lock_parser.add_argument("user_edited", type=Path)
    lock_parser.add_argument("--canonical-output", type=Path, required=True)
    lock_parser.add_argument("--receipt", type=Path, required=True)
    lock_parser.add_argument("--previous", type=Path)
    lock_parser.add_argument("--removed-blocks", type=Path)
    lock_parser.add_argument("--overwrite", action="store_true")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("canonical", type=Path)
    validate_parser.add_argument("--receipt", type=Path, required=True)
    validate_parser.add_argument("--candidate", type=Path)
    validate_parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    if args.command == "lock":
        report = lock(
            args.user_edited.expanduser().resolve(),
            args.canonical_output.expanduser().resolve(),
            args.receipt.expanduser().resolve(),
            args.previous.expanduser().resolve() if args.previous else None,
            args.removed_blocks.expanduser().resolve()
            if args.removed_blocks
            else None,
            args.overwrite,
        )
        output = None
    else:
        report = validate(
            args.canonical.expanduser().resolve(),
            args.receipt.expanduser().resolve(),
            args.candidate.expanduser().resolve() if args.candidate else None,
        )
        output = args.output
    write_report(report, output)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate HWPX style array order, references, and semantic alignment."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any
import zipfile
from xml.etree import ElementTree as ET


SECTION_MEMBER = re.compile(r"^Contents/section(\d+)\.xml$")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def attributes(node: ET.Element) -> dict[str, str]:
    return {local_name(key): value for key, value in node.attrib.items()}


def descendants(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if local_name(child.tag) == name]


def text_of(node: ET.Element) -> str:
    return "".join(
        child.text or ""
        for child in node.iter()
        if local_name(child.tag) == "t"
    ).strip()


def parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def definition_report(
    header: ET.Element,
    container_name: str,
    item_name: str,
    errors: list[str],
) -> tuple[dict[str, ET.Element], dict[str, Any]]:
    containers = descendants(header, container_name)
    if len(containers) != 1:
        errors.append(f"header must contain exactly one {container_name}")
        return {}, {
            "container": container_name,
            "ids": [],
            "itemCnt": None,
            "ordered": False,
        }
    container = containers[0]
    definitions = [
        child for child in list(container) if local_name(child.tag) == item_name
    ]
    ids = [attributes(node).get("id", "") for node in definitions]
    numeric_ids: list[int] = []
    for value in ids:
        try:
            numeric_ids.append(int(value))
        except ValueError:
            errors.append(f"{item_name} id must be numeric: {value!r}")
    if len(ids) != len(set(ids)):
        errors.append(f"{item_name} ids must be unique")
    ordered = bool(numeric_ids) and len(numeric_ids) == len(ids)
    if ordered:
        expected = list(range(numeric_ids[0], numeric_ids[0] + len(numeric_ids)))
        ordered = numeric_ids == expected
        if not ordered:
            errors.append(
                f"{container_name} array order must be consecutive from "
                f"{numeric_ids[0]}: {numeric_ids}"
            )
    elif not definitions:
        errors.append(f"{container_name} must contain at least one {item_name}")
    item_count = attributes(container).get("itemCnt")
    if item_count != str(len(definitions)):
        errors.append(
            f"{container_name} itemCnt {item_count!r} != {len(definitions)}"
        )
    return {
        value: node for value, node in zip(ids, definitions) if value
    }, {
        "container": container_name,
        "ids": ids,
        "itemCnt": item_count,
        "ordered": ordered,
    }


def paragraph_alignment(definition: ET.Element | None) -> str:
    if definition is None:
        return ""
    aligns = descendants(definition, "align")
    return attributes(aligns[0]).get("horizontal", "") if aligns else ""


def validate(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            duplicates = [
                name for name, count in Counter(names).items() if count > 1
            ]
            errors.extend(f"duplicate ZIP member: {name}" for name in duplicates)
            try:
                header = ET.fromstring(archive.read("Contents/header.xml"))
            except (KeyError, ET.ParseError) as error:
                return {
                    "status": "BLOCK",
                    "input": str(path),
                    "definitions": [],
                    "sections": [],
                    "errors": [*errors, f"cannot parse Contents/header.xml: {error}"],
                }
            definitions = []
            para_defs, para_report = definition_report(
                header, "paraProperties", "paraPr", errors
            )
            char_defs, char_report = definition_report(
                header, "charProperties", "charPr", errors
            )
            _border_defs, border_report = definition_report(
                header, "borderFills", "borderFill", errors
            )
            definitions.extend((para_report, char_report, border_report))
            matched_sections = []
            for name in names:
                match = SECTION_MEMBER.fullmatch(name)
                if match:
                    matched_sections.append((int(match.group(1)), name))
            matched_sections.sort()
            if not matched_sections:
                errors.append("HWPX has no Contents/sectionN.xml members")
            section_reports = []
            for _index, name in matched_sections:
                try:
                    root = ET.fromstring(archive.read(name))
                except ET.ParseError as error:
                    errors.append(f"cannot parse {name}: {error}")
                    continue
                parents = parent_map(root)
                image_paragraphs: set[ET.Element] = set()
                for image in descendants(root, "img"):
                    current = image
                    while current in parents:
                        current = parents[current]
                        if local_name(current.tag) == "p":
                            image_paragraphs.add(current)
                            break
                paragraph_count = 0
                run_count = 0
                for paragraph in descendants(root, "p"):
                    paragraph_count += 1
                    values = attributes(paragraph)
                    para_ref = values.get("paraPrIDRef", "")
                    definition = para_defs.get(para_ref)
                    if definition is None:
                        errors.append(
                            f"{name} paragraph references missing paraPrIDRef {para_ref!r}"
                        )
                    alignment = paragraph_alignment(definition)
                    visible = text_of(paragraph)
                    if visible.startswith("· ") and alignment != "LEFT":
                        errors.append(
                            f"{name} subdetail paragraph must resolve to LEFT, got "
                            f"{alignment!r} via paraPrIDRef {para_ref!r}"
                        )
                    if paragraph in image_paragraphs and alignment != "CENTER":
                        errors.append(
                            f"{name} image paragraph must resolve to CENTER, got "
                            f"{alignment!r} via paraPrIDRef {para_ref!r}"
                        )
                for run in descendants(root, "run"):
                    run_count += 1
                    char_ref = attributes(run).get("charPrIDRef", "")
                    if char_ref not in char_defs:
                        errors.append(
                            f"{name} run references missing charPrIDRef {char_ref!r}"
                        )
                section_reports.append(
                    {
                        "member": name,
                        "paragraphCount": paragraph_count,
                        "runCount": run_count,
                        "imageParagraphCount": len(image_paragraphs),
                    }
                )
    except (FileNotFoundError, zipfile.BadZipFile) as error:
        errors.append(f"cannot read HWPX: {error}")
        definitions = []
        section_reports = []
    return {
        "status": "PASS" if not errors else "BLOCK",
        "input": str(path),
        "definitions": definitions,
        "sections": section_reports,
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate HWPX style array order and semantic references."
    )
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    report = validate(args.input.expanduser().resolve())
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

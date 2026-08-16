from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET


CAPTION_PATTERN = re.compile(r"^그림 [1-9][0-9]*\. [^\n]+$")
FORBIDDEN_CAPTION_TEXT = ("자체 구성", "검증계획(", " — ")
MAX_CAPTION_CHARS = 50


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def attributes(element: ET.Element) -> dict[str, str]:
    return {local_name(key): value for key, value in element.attrib.items()}


def text_of(element: ET.Element) -> str:
    return "".join(
        node.text or "" for node in element.iter() if local_name(node.tag) == "t"
    ).strip()


def descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in element.iter() if local_name(node.tag) == name]


def direct_children(element: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in element if local_name(node.tag) == name]


def first_descendant(element: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in element.iter() if local_name(node.tag) == name), None)


def parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: node for node in root.iter() for child in node}


def ancestor(element: ET.Element, parents: dict[ET.Element, ET.Element], name: str) -> ET.Element | None:
    current = element
    while current in parents:
        current = parents[current]
        if local_name(current.tag) == name:
            return current
    return None


def canonical_element(element: ET.Element) -> bytes:
    source = ET.tostring(element, encoding="unicode")
    canonical = ET.canonicalize(source, strip_text=True, with_comments=False)
    return canonical.encode("utf-8")


def element_digest(element: ET.Element) -> str:
    return hashlib.sha256(canonical_element(element)).hexdigest()


def read_xml(archive: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(name))
    except KeyError as error:
        raise ValueError(f"missing HWPX member: {name}") from error
    except ET.ParseError as error:
        raise ValueError(f"invalid XML member: {name}: {error}") from error


def section_names(archive: zipfile.ZipFile) -> list[str]:
    return sorted(
        name
        for name in archive.namelist()
        if name.startswith("Contents/section") and name.endswith(".xml")
    )


def section_roots(archive: zipfile.ZipFile) -> list[tuple[str, ET.Element]]:
    names = section_names(archive)
    if not names:
        raise ValueError("missing HWPX section XML")
    return [(name, read_xml(archive, name)) for name in names]


def secpr_receipt(path: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(path) as archive:
        receipt: list[dict[str, str]] = []
        for name, root in section_roots(archive):
            sections = descendants(root, "secPr")
            if not sections:
                raise ValueError(f"missing secPr: {name}")
            for index, section in enumerate(sections):
                receipt.append(
                    {
                        "member": name,
                        "index": str(index),
                        "sha256": element_digest(section),
                    }
                )
        return receipt


def normalize_manifest_href(href: str) -> str:
    if not href:
        raise ValueError("manifest href must not be empty")
    if "\\" in href:
        raise ValueError(f"manifest href must use POSIX separators: {href}")
    if href.startswith("/") or re.match(r"^[A-Za-z]:", href) or "://" in href:
        raise ValueError(f"manifest href must be relative: {href}")
    parts = PurePosixPath(href).parts
    if not parts or any(part in {"", ".", ".."} for part in href.split("/")):
        raise ValueError(f"manifest href contains an unsafe path segment: {href}")
    return href


def manifest_items(archive: zipfile.ZipFile) -> tuple[dict[str, str], list[str]]:
    root = read_xml(archive, "Contents/content.hpf")
    result: dict[str, str] = {}
    errors: list[str] = []
    for item in descendants(root, "item"):
        values = attributes(item)
        item_id = values.get("id", "")
        href = values.get("href", "")
        if not item_id:
            errors.append("content.hpf item is missing id")
            continue
        if item_id in result:
            errors.append(f"duplicate content.hpf item id: {item_id}")
            continue
        try:
            result[item_id] = normalize_manifest_href(href)
        except ValueError as error:
            errors.append(str(error))
    return result, errors


def visual_tables(root: ET.Element) -> list[ET.Element]:
    parents = parent_map(root)
    candidates: list[ET.Element] = []
    seen: set[int] = set()
    for image in descendants(root, "img"):
        table = ancestor(image, parents, "tbl")
        if table is not None and id(table) not in seen:
            candidates.append(table)
            seen.add(id(table))
    return candidates


def nearest_paragraphs(
    table: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, str]:
    containing = ancestor(table, parents, "p")
    if containing is None or containing not in parents:
        return "", ""
    container = parents[containing]
    if local_name(container.tag) != "subList":
        return "", ""
    paragraphs = direct_children(container, "p")
    position = paragraphs.index(containing)
    before = next(
        (text_of(node) for node in reversed(paragraphs[:position]) if text_of(node)),
        "",
    )
    after = next(
        (text_of(node) for node in paragraphs[position + 1 :] if text_of(node)),
        "",
    )
    return before, after


def find_header_definition(
    header: ET.Element,
    name: str,
    identifier: str,
) -> ET.Element | None:
    return next(
        (
            node
            for node in descendants(header, name)
            if attributes(node).get("id") == identifier
        ),
        None,
    )


def direct_size(element: ET.Element) -> ET.Element | None:
    return next((node for node in element if local_name(node.tag) == "sz"), None)


def visual_receipt(
    table: ET.Element,
    root: ET.Element,
    header: ET.Element,
    manifest: dict[str, str],
    archive_names: set[str],
) -> dict[str, Any]:
    parents = parent_map(root)
    table_values = attributes(table)
    rows = direct_children(table, "tr")
    cells = [direct_children(row, "tc") for row in rows]
    flat_cells = [cell for row in cells for cell in row]
    caption = ""
    before, after = nearest_paragraphs(table, parents)
    errors: list[str] = []

    expected_chain = ["run", "p", "subList", "tc"]
    chain: list[str] = []
    current = table
    for _ in expected_chain:
        if current not in parents:
            break
        current = parents[current]
        chain.append(local_name(current.tag))
    if chain != expected_chain:
        errors.append(
            "visual table must use tc → subList → p → run → tbl hierarchy"
        )

    if table_values.get("rowCnt") != "2" or table_values.get("colCnt") != "1":
        errors.append("visual table must be exactly 1 column × 2 rows")
    if len(rows) != 2 or any(len(row) != 1 for row in cells):
        errors.append("visual table XML must contain two rows with one cell each")

    image = first_descendant(rows[0], "img") if rows else None
    image_ref = attributes(image).get("binaryItemIDRef", "") if image is not None else ""
    image_href = manifest.get(image_ref, "")
    if not image_ref:
        errors.append("visual table image is missing binaryItemIDRef")
    elif not image_href:
        errors.append(f"missing content.hpf manifest item for {image_ref}")
    elif not image_href.startswith("BinData/"):
        errors.append(f"visual image manifest href must be inside BinData: {image_href}")
    elif image_href not in archive_names:
        errors.append(f"missing BinData member for {image_ref}: {image_href}")

    table_size = direct_size(table)
    table_width = attributes(table_size).get("width", "") if table_size is not None else ""
    picture = ancestor(image, parents, "pic") if image is not None else None
    image_size = direct_size(picture) if picture is not None else None
    image_width = attributes(image_size).get("width", "") if image_size is not None else ""

    image_cell = flat_cells[0] if len(flat_cells) >= 1 else None
    caption_cell = flat_cells[1] if len(flat_cells) >= 2 else None
    caption = text_of(caption_cell) if caption_cell is not None else ""
    image_margin = first_descendant(image_cell, "cellMargin") if image_cell is not None else None
    caption_margin = first_descendant(caption_cell, "cellMargin") if caption_cell is not None else None
    caption_size = first_descendant(caption_cell, "cellSz") if caption_cell is not None else None

    caption_paragraph = first_descendant(caption_cell, "p") if caption_cell is not None else None
    caption_run = first_descendant(caption_cell, "run") if caption_cell is not None else None
    para_ref = attributes(caption_paragraph).get("paraPrIDRef", "") if caption_paragraph is not None else ""
    char_ref = attributes(caption_run).get("charPrIDRef", "") if caption_run is not None else ""
    para_definition = find_header_definition(header, "paraPr", para_ref)
    char_definition = find_header_definition(header, "charPr", char_ref)
    border_ref = attributes(caption_cell).get("borderFillIDRef", "") if caption_cell is not None else ""
    border_definition = find_header_definition(header, "borderFill", border_ref)

    align = first_descendant(para_definition, "align") if para_definition is not None else None
    caption_align = attributes(align).get("horizontal", "") if align is not None else ""
    caption_height = attributes(char_definition).get("height", "") if char_definition is not None else ""
    caption_bold = bool(descendants(char_definition, "bold")) if char_definition is not None else False
    brush = first_descendant(border_definition, "winBrush") if border_definition is not None else None
    caption_background = attributes(brush).get("faceColor", "") if brush is not None else ""

    if not CAPTION_PATTERN.fullmatch(caption):
        errors.append("caption must use '그림 N. 핵심 그림명' format")
    if len(caption) > MAX_CAPTION_CHARS:
        errors.append(
            f"caption must be at most {MAX_CAPTION_CHARS} characters, got {len(caption)}"
        )
    if any(term in caption for term in FORBIDDEN_CAPTION_TEXT):
        errors.append("caption contains a forbidden long explanation")
    if not before or not after:
        errors.append("visual table must be between explicit before/after paragraphs")

    return {
        "caption": caption,
        "beforeParagraph": before,
        "afterParagraph": after,
        "hierarchy": list(reversed(chain)) + ["tbl"],
        "rowCount": table_values.get("rowCnt", ""),
        "columnCount": table_values.get("colCnt", ""),
        "tableWidth": table_width,
        "imageWidth": image_width,
        "imageRef": image_ref,
        "imageHref": image_href,
        "imageCellMargin": attributes(image_margin) if image_margin is not None else {},
        "captionCellMargin": attributes(caption_margin) if caption_margin is not None else {},
        "captionRowHeight": attributes(caption_size).get("height", "") if caption_size is not None else "",
        "captionPointSize": str(int(caption_height) // 100) if caption_height.isdigit() else "",
        "captionBold": caption_bold,
        "captionAlign": caption_align,
        "captionBackground": caption_background,
        "errors": errors,
    }


def inspect_hwpx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        member_counts = Counter(archive.namelist())
        names = set(member_counts)
        header = read_xml(archive, "Contents/header.xml")
        manifest, manifest_errors = manifest_items(archive)
        integrity_errors = list(manifest_errors)
        integrity_errors.extend(
            f"duplicate ZIP member: {name}"
            for name, count in sorted(member_counts.items())
            if count > 1
        )
        visuals: list[dict[str, Any]] = []
        referenced_images: set[str] = set()
        for _, root in section_roots(archive):
            referenced_images.update(
                attributes(image).get("binaryItemIDRef", "")
                for image in descendants(root, "img")
                if attributes(image).get("binaryItemIDRef")
            )
            visuals.extend(
                visual_receipt(table, root, header, manifest, names)
                for table in visual_tables(root)
            )


        for image_ref in sorted(referenced_images):
            href = manifest.get(image_ref, "")
            if not href:
                integrity_errors.append(f"missing manifest item: {image_ref}")
            elif not href.startswith("BinData/"):
                integrity_errors.append(
                    f"image manifest href must be inside BinData: {image_ref} → {href}"
                )
            elif href not in names:
                integrity_errors.append(f"missing BinData member: {image_ref} → {href}")

        return {
            "schemaVersion": "1.0.0",
            "file": path.name,
            "secPr": secpr_receipt(path),
            "visuals": visuals,
            "referencedImages": sorted(referenced_images),
            "integrityErrors": integrity_errors,
        }


def compare_value(
    errors: list[str],
    caption: str,
    actual: Any,
    expected: Any,
    label: str,
) -> None:
    if str(actual) != str(expected):
        errors.append(f"{caption}: {label} expected {expected}, got {actual}")


def validate_against_spec(
    result: Path,
    spec_path: Path,
    source: Path | None,
) -> dict[str, Any]:
    report = inspect_hwpx(result)
    errors = list(report["integrityErrors"])
    for visual in report["visuals"]:
        errors.extend(f"{visual['caption']}: {error}" for error in visual["errors"])

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    expected_visuals = spec.get("visuals")
    if not isinstance(expected_visuals, list) or not expected_visuals:
        errors.append("visual spec must contain a non-empty visuals array")
        expected_visuals = []
    by_caption: dict[str, list[dict[str, Any]]] = {}
    for visual in report["visuals"]:
        by_caption.setdefault(str(visual["caption"]), []).append(visual)
    expected_captions = [
        str(item.get("caption", ""))
        for item in expected_visuals
        if isinstance(item, dict)
    ]
    duplicate_expected = [
        caption for caption, count in Counter(expected_captions).items() if count > 1
    ]
    if duplicate_expected:
        errors.append(f"duplicate visual captions in spec: {', '.join(sorted(duplicate_expected))}")

    required_fields = ("caption", "beforeParagraphContains", "afterParagraphContains")
    for expected in expected_visuals:
        if not isinstance(expected, dict):
            errors.append("visual spec entries must be objects")
            continue
        missing = [field for field in required_fields if not expected.get(field)]
        if missing:
            errors.append(f"visual spec missing fields: {', '.join(missing)}")
            continue
        caption = str(expected["caption"])
        matches = by_caption.get(caption, [])
        if not matches:
            errors.append(f"missing visual: {caption}")
            continue
        if len(matches) > 1:
            errors.append(f"duplicate visual: {caption} appears {len(matches)} times")
            continue
        actual = matches[0]
        if str(expected["beforeParagraphContains"]) not in actual["beforeParagraph"]:
            errors.append(f"{caption}: before paragraph anchor mismatch")
        if str(expected["afterParagraphContains"]) not in actual["afterParagraph"]:
            errors.append(f"{caption}: after paragraph anchor mismatch")

        scalar_checks = {
            "tableWidth": "tableWidth",
            "imageWidth": "imageWidth",
            "captionRowHeight": "captionRowHeight",
            "captionPointSize": "captionPointSize",
            "captionBold": "captionBold",
            "captionAlign": "captionAlign",
            "captionBackground": "captionBackground",
        }
        for spec_key, report_key in scalar_checks.items():
            if spec_key in expected:
                compare_value(errors, caption, actual[report_key], expected[spec_key], spec_key)
        if "cellMargin" in expected:
            for side, value in expected["cellMargin"].items():
                compare_value(
                    errors,
                    caption,
                    actual["imageCellMargin"].get(side, ""),
                    value,
                    f"image cell margin {side}",
                )
                compare_value(
                    errors,
                    caption,
                    actual["captionCellMargin"].get(side, ""),
                    value,
                    f"caption cell margin {side}",
                )

    expected_caption_set = set(expected_captions)
    unexpected = sorted(set(by_caption) - expected_caption_set)
    if unexpected:
        errors.append(f"unexpected visuals: {', '.join(unexpected)}")
    if len(report["visuals"]) != len(expected_visuals):
        errors.append(
            "visual cardinality mismatch: "
            f"expected {len(expected_visuals)}, got {len(report['visuals'])}"
        )

    source_secpr = None
    if source is None:
        errors.append("source HWPX is required for secPr preservation validation")
    else:
        source_secpr = secpr_receipt(source)
        if source_secpr != report["secPr"]:
            errors.append("secPr changed from the source HWPX")

    return {
        "status": "PASS" if not errors else "BLOCK",
        "result": str(result),
        "source": str(source) if source is not None else None,
        "spec": str(spec_path),
        "secPrPreserved": source_secpr == report["secPr"] if source_secpr is not None else False,
        "visualCount": len(report["visuals"]),
        "visuals": report["visuals"],
        "errors": errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and validate semantic HWPX visuals")
    commands = parser.add_subparsers(dest="command", required=True)

    inspect_parser = commands.add_parser("inspect", help="print semantic visual settings")
    inspect_parser.add_argument("hwpx", type=Path)

    validate_parser = commands.add_parser("validate", help="validate result against source and visual spec")
    validate_parser.add_argument("hwpx", type=Path)
    validate_parser.add_argument("--source", type=Path, required=True)
    validate_parser.add_argument("--spec", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "inspect":
            report = inspect_hwpx(args.hwpx)
        else:
            report = validate_against_spec(args.hwpx, args.spec, args.source)
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        print(json.dumps({"status": "BLOCK", "errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status", "PASS") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


PLACEHOLDER = re.compile(r"\{[^{}]+\}")
SECTION_MEMBER = re.compile(r"^Contents/section(\d+)\.xml$")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def attributes(node: ET.Element) -> dict[str, str]:
    return {local_name(key): value for key, value in node.attrib.items()}


def descendants(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node.iter() if local_name(child.tag) == name]


def direct_children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(node) if local_name(child.tag) == name]


def text_of(node: ET.Element) -> str:
    return "".join(
        text.text or ""
        for text in node.iter()
        if local_name(text.tag) == "t"
    ).strip()


def parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def has_table_ancestor(
    table: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> bool:
    current = parents.get(table)
    while current is not None:
        if local_name(current.tag) == "tbl":
            return True
        current = parents.get(current)
    return False


def paragraph_text(node: ET.Element) -> str:
    values: list[str] = []

    def visit(current: ET.Element) -> None:
        for child in list(current):
            if local_name(child.tag) == "tbl":
                continue
            if local_name(child.tag) == "t":
                values.append(child.text or "")
            visit(child)

    visit(node)
    return "".join(values).strip()


def canonical_xml(node: ET.Element) -> str:
    name = local_name(node.tag)
    attrs = ";".join(
        f"{local_name(key)}={value}" for key, value in sorted(node.attrib.items())
    )
    children = "".join(canonical_xml(child) for child in list(node))
    return f"<{name} {attrs}>{children}</{name}>"


def section_members(names: list[str]) -> list[str]:
    matched = []
    for name in names:
        found = SECTION_MEMBER.fullmatch(name)
        if found:
            matched.append((int(found.group(1)), name))
    return [name for _index, name in sorted(matched)]


def load_sections(path: Path) -> tuple[list[str], dict[str, ET.Element], list[str]]:
    errors: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            errors.append("duplicate ZIP member: " + ", ".join(duplicates))
        members = section_members(names)
        roots: dict[str, ET.Element] = {}
        for member in members:
            try:
                roots[member] = ET.fromstring(archive.read(member))
            except (ET.ParseError, KeyError) as error:
                errors.append(f"cannot parse {member}: {error}")
    if not roots:
        errors.append("HWPX has no Contents/sectionN.xml members")
    return members, roots, errors


def paragraph_pattern(text: str) -> str:
    cursor = 0
    parts = ["^"]
    for match in PLACEHOLDER.finditer(text):
        parts.append(re.escape(text[cursor:match.start()]))
        parts.append(".+?")
        cursor = match.end()
    parts.append(re.escape(text[cursor:]))
    parts.append("$")
    return "".join(parts)


def fixed_paragraph_patterns(
    root: ET.Element,
    editable_exact: set[str],
) -> list[str]:
    result = []
    for paragraph in descendants(root, "p"):
        text = paragraph_text(paragraph)
        if not text or text in editable_exact:
            continue
        result.append(paragraph_pattern(text))
    return result


def top_level_table_topology(root: ET.Element) -> list[dict[str, Any]]:
    parents = parent_map(root)
    result = []
    for table in descendants(root, "tbl"):
        if has_table_ancestor(table, parents):
            continue
        rows = direct_children(table, "tr")
        cells = [direct_children(row, "tc") for row in rows]
        values = attributes(table)
        result.append(
            {
                "declaredRows": values.get("rowCnt", ""),
                "declaredColumns": values.get("colCnt", ""),
                "actualRows": len(rows),
                "actualColumnsByRow": [len(row) for row in cells],
            }
        )
    return result


def secpr_digest(root: ET.Element) -> str:
    nodes = descendants(root, "secPr")
    payload = "\n".join(canonical_xml(node) for node in nodes).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def is_subsequence(expected_patterns: list[str], actual: list[str]) -> bool:
    cursor = 0
    for value in actual:
        if (
            cursor < len(expected_patterns)
            and re.fullmatch(expected_patterns[cursor], value) is not None
        ):
            cursor += 1
    return cursor == len(expected_patterns)


def load_editable_exact(path: Path | None) -> list[str]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("editableParagraphExact", [])
    if (
        not isinstance(values, list)
        or not all(isinstance(value, str) and value for value in values)
        or len(values) != len(set(values))
    ):
        raise ValueError(
            "editableParagraphExact must be an array of unique non-empty strings"
        )
    return values


def validate(
    source: Path,
    result: Path,
    editable_spec: Path | None = None,
) -> dict[str, Any]:
    requested_editable = load_editable_exact(editable_spec)
    source_members, source_roots, source_errors = load_sections(source)
    result_members, result_roots, result_errors = load_sections(result)
    errors = [*source_errors, *result_errors]

    source_paragraphs = [
        paragraph_text(paragraph)
        for member in source_members
        if member in source_roots
        for paragraph in descendants(source_roots[member], "p")
        if paragraph_text(paragraph)
    ]
    editable_exact: set[str] = set()
    for value in requested_editable:
        matches = source_paragraphs.count(value)
        if matches != 1:
            errors.append(
                f"editable paragraph anchor must match exactly once, got {matches}: {value}"
            )
        else:
            editable_exact.add(value)

    if source_members != result_members:
        errors.append("source section member order changed")

    section_reports = []
    for member in source_members:
        if member not in source_roots or member not in result_roots:
            continue
        source_root = source_roots[member]
        result_root = result_roots[member]
        source_fixed = fixed_paragraph_patterns(source_root, editable_exact)
        result_text = [
            paragraph_text(node)
            for node in descendants(result_root, "p")
            if paragraph_text(node)
        ]
        fixed_preserved = is_subsequence(source_fixed, result_text)
        source_topology = top_level_table_topology(source_root)
        result_topology = top_level_table_topology(result_root)
        topology_preserved = source_topology == result_topology
        section_secpr_preserved = secpr_digest(source_root) == secpr_digest(result_root)
        if not fixed_preserved:
            errors.append(f"fixed source paragraphs changed or reordered: {member}")
        if not topology_preserved:
            errors.append(f"top-level table topology changed: {member}")
        if not section_secpr_preserved:
            errors.append(f"secPr changed from source: {member}")
        section_reports.append(
            {
                "member": member,
                "fixedParagraphCount": len(source_fixed),
                "fixedParagraphsPreserved": fixed_preserved,
                "topLevelTableTopologyPreserved": topology_preserved,
                "secPrPreserved": section_secpr_preserved,
            }
        )

    return {
        "status": "PASS" if not errors else "BLOCK",
        "source": str(source),
        "sourceSha256": sha256(source),
        "result": str(result),
        "resultSha256": sha256(result),
        "editableSpec": str(editable_spec) if editable_spec else None,
        "sourceSectionOrderPreserved": source_members == result_members,
        "sections": section_reports,
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-closed validation for fixed source HWPX content and topology."
    )
    parser.add_argument("result", type=Path)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--editable-spec", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate(args.source, args.result, args.editable_spec)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Scan, fill, and validate exact {placeholders} in HWPX files."""

from __future__ import annotations

import argparse
from copy import deepcopy
import csv
import html
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable, Iterable
from xml.sax.saxutils import escape
from zipfile import BadZipFile, ZIP_STORED, ZipFile

EXPECTED_MIMETYPE = "application/hwp+zip"
REQUIRED_FILES = (
    "mimetype",
    "Contents/content.hpf",
    "Contents/header.xml",
    "Contents/section0.xml",
)
PLACEHOLDER_RE = re.compile(r"\{[^{}\r\n]{1,100}\}")
PARAGRAPH_OPEN_RE = re.compile(r"<hp:p\b")
LINES_RE = re.compile(
    r"<hp:linesegarray\b[^>]*>.*?</hp:linesegarray>|<hp:linesegarray\b[^>]*/>",
    flags=re.DOTALL,
)
P_ID_RE = re.compile(r'(<hp:p\b[^>]*\bid=")([^"]+)(")')
PARA_REF_RE = re.compile(r'(<hp:p\b[^>]*\bparaPrIDRef=")([^"]+)(")')
RUN_CHAR_REF_RE = re.compile(r'(<hp:run\b[^>]*\bcharPrIDRef=")([^"]+)(")')
RUN_BLOCK_RE = re.compile(r"<hp:run\b[^>]*>.*?</hp:run>", flags=re.DOTALL)
OUTLINE_HEADING_PREFIXES = ("o ", "○ ", "□ ")
OUTLINE_DETAIL_PREFIXES = ("- ", "• ", "▪ ")
OUTLINE_SUBDETAIL_PREFIXES = ("· ",)
SOURCE_CITATION_RE = re.compile(r"^(.+), ((?:19|20)\d{2})$")
CLAIM_MARKER_START_RE = re.compile(r"\[[EUHP]\d{3}")
CLAIM_MARKER_RE = re.compile(
    r"\[([EUHP]\d{3}) \| ([^\[\]\|]{2,100})\]"
)
EVIDENCE_TYPE_BY_PREFIX = {
    "E": "external",
    "U": "user",
    "H": "hypothesis",
    "P": "plan",
}
HEAD_NS = "http://www.hancom.co.kr/hwpml/2011/head"
PARAGRAPH_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
CORE_NS = "http://www.hancom.co.kr/hwpml/2011/core"
REQUIRED_APPROVAL_FIELDS = ("approved_by", "approved_at", "source_draft")
BLOCK_LOG_STATUSES = {"BLOCK", "NOT_FOUND", "SKIPPED_EMPTY"}


def require_hwpx(path: Path) -> None:
    if path.suffix.lower() == ".hwp":
        raise ValueError(
            ".hwp는 직접 처리하지 않습니다. 한글에서 '다른 이름으로 저장'하여 .hwpx로 준비하세요."
        )
    if path.suffix.lower() != ".hwpx":
        raise ValueError("입력 파일 확장자는 .hwpx여야 합니다.")
    if not path.is_file():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")


def validate_hwpx(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        require_hwpx(path)
    except (ValueError, FileNotFoundError) as exc:
        return [str(exc)]

    try:
        with ZipFile(path, "r") as archive:
            names = archive.namelist()
            for required in REQUIRED_FILES:
                if required not in names:
                    errors.append(f"필수 항목 누락: {required}")

            if "mimetype" in names:
                mime = archive.read("mimetype").decode("utf-8").strip()
                if mime != EXPECTED_MIMETYPE:
                    errors.append(f"mimetype 오류: {mime}")
                if names[0] != "mimetype":
                    errors.append("mimetype이 ZIP의 첫 항목이 아닙니다.")
                if archive.getinfo("mimetype").compress_type != ZIP_STORED:
                    errors.append("mimetype은 압축하지 않은 ZIP_STORED여야 합니다.")

            for name in names:
                if name.endswith((".xml", ".hpf")):
                    try:
                        ET.fromstring(archive.read(name))
                    except ET.ParseError as exc:
                        errors.append(f"XML 오류 {name}: {exc}")
    except BadZipFile:
        errors.append("유효한 ZIP/HWPX 파일이 아닙니다.")

    return errors


def xml_entries(path: Path) -> Iterable[tuple[str, str]]:
    with ZipFile(path, "r") as archive:
        for name in archive.namelist():
            if name.endswith((".xml", ".hpf")):
                try:
                    yield name, archive.read(name).decode("utf-8")
                except UnicodeDecodeError:
                    continue


def scan_placeholders(path: Path) -> list[str]:
    errors = validate_hwpx(path)
    if errors:
        raise ValueError("\n".join(errors))
    found: set[str] = set()
    for name, text in xml_entries(path):
        if not re.fullmatch(r"Contents/section\d+\.xml", name):
            continue
        root = ET.fromstring(text.encode("utf-8"))
        for element in root.iter():
            if element.text:
                found.update(PLACEHOLDER_RE.findall(element.text))
    return sorted(found)


def visible_text(xml_fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", xml_fragment)).strip()


def reset_paragraph_id(block: str, new_id: str) -> str:
    return P_ID_RE.sub(
        lambda match: match.group(1) + new_id + match.group(3),
        block,
        count=1,
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def outline_role(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith(OUTLINE_HEADING_PREFIXES):
        return "heading"
    if stripped.startswith(OUTLINE_DETAIL_PREFIXES):
        return "detail"
    if stripped.startswith(OUTLINE_SUBDETAIL_PREFIXES):
        return "subdetail"
    return None


def claim_markers_at_end(text: str) -> list[tuple[str, str]]:
    stripped = text.strip()
    start = CLAIM_MARKER_START_RE.search(stripped)
    if start is None:
        return []
    suffix = stripped[start.start():]
    parsed = []
    cursor = 0
    for match in CLAIM_MARKER_RE.finditer(suffix):
        if match.start() != cursor:
            raise ValueError(
                "첫 주장 표지부터 문단 끝까지 올바른 표지만 연속으로 와야 합니다."
            )
        evidence_id = match.group(1)
        label = match.group(2)
        if (
            label != label.strip()
            or len(label) < 2
            or any(unicodedata.category(char).startswith("C") for char in label)
        ):
            raise ValueError(
                "주장 표지의 짧은 출처·상태는 공백·제어문자 없는 2자 이상이어야 합니다."
            )
        parsed.append((evidence_id, label))
        cursor = match.end()
    if not parsed or cursor != len(suffix):
        raise ValueError(
            "첫 주장 표지부터 문단 끝까지 올바른 표지만 연속으로 와야 합니다."
        )
    return parsed


def render_claim_citations(text: str) -> str:
    stripped = text.strip()
    markers = claim_markers_at_end(stripped)
    if not markers:
        return stripped
    start = CLAIM_MARKER_START_RE.search(stripped)
    if start is None:
        return stripped
    body = stripped[:start.start()].rstrip()
    labels = "; ".join(label for _, label in markers)
    return f"{body} ({labels})"


def source_citation_year(row: dict[str, str]) -> str | None:
    for field in ("published_or_recorded_date", "base_date", "checked_on"):
        match = re.search(r"(?:19|20)\d{2}", row.get(field) or "")
        if match:
            return match.group(0)
    return None


def parse_outline_value(value: str) -> list[str] | None:
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    roles = [outline_role(line) for line in lines]
    if not any(roles):
        return None
    if any(role is None for role in roles):
        raise ValueError("개조식 값의 모든 일반 문단에는 허용된 항목 기호가 필요합니다.")
    if roles[0] != "heading":
        raise ValueError("개조식 값은 `o`, `○`, `□` 대항목으로 시작해야 합니다.")
    if "detail" not in roles:
        raise ValueError("각 개조식 값에는 `-`, `•`, `▪` 핵심항목이 필요합니다.")
    has_detail = False
    previous_role = None
    for role in roles:
        if role == "heading":
            if previous_role is not None and not has_detail:
                raise ValueError("각 대항목 뒤에는 다음 대항목 전에 핵심항목이 필요합니다.")
            has_detail = False
        elif role == "detail":
            has_detail = True
        elif role == "subdetail" and previous_role not in {"detail", "subdetail"}:
            raise ValueError("`·` 세부내용은 `-`, `•`, `▪` 핵심항목 뒤에 와야 합니다.")
        previous_role = role
    if not has_detail:
        raise ValueError("마지막 대항목에도 핵심항목이 필요합니다.")
    untraced_details = [
        line
        for line, role in zip(lines, roles)
        if role in {"detail", "subdetail"} and not claim_markers_at_end(line)
    ]
    if untraced_details:
        raise ValueError(
            "각 핵심항목·세부내용 주장은 끝에 "
            "[E001 | 기관명, {발표연도}]·[U001 | 사용자 제공자료, {기록연도}]·"
            "[H001 | 검증가설]·[P001 | 실행계획] 형식의 "
            "근거 또는 상태 표지가 필요합니다."
        )
    return lines


def normalize_prose_as_outline(value: str) -> list[str]:
    paragraphs = [line.strip() for line in value.splitlines() if line.strip()]
    if not paragraphs:
        return []
    for paragraph in paragraphs:
        if not claim_markers_at_end(paragraph):
            raise ValueError(
                "산문 입력을 개조식으로 바꾸려면 각 문장 끝에 "
                "[E001 | 기관명, {발표연도}]·[U001 | 사용자 제공자료, {기록연도}]·"
                "[H001 | 검증가설]·[P001 | 실행계획] 표지가 필요합니다."
            )
    return ["o 핵심내용", *(f"- {paragraph}" for paragraph in paragraphs)]


def marker_block_style_refs(
    block: str,
    marker: str,
) -> tuple[str, str] | None:
    para_match = PARA_REF_RE.search(block)
    marker_runs = [
        match.group(0)
        for match in RUN_BLOCK_RE.finditer(block)
        if marker in match.group(0)
    ]
    if para_match is None or len(marker_runs) != 1:
        return None
    marker_run = marker_runs[0]
    if visible_text(marker_run) != marker:
        return None
    char_match = RUN_CHAR_REF_RE.search(marker_run)
    if char_match is None:
        return None
    return para_match.group(2), char_match.group(2)


def find_marker_style_refs(
    text: str,
    marker: str,
) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = set()
    search_from = 0
    while True:
        marker_at = text.find(marker, search_from)
        if marker_at < 0:
            break
        p_start = text.rfind("<hp:p", 0, marker_at)
        p_end_at = text.find("</hp:p>", marker_at)
        if p_start >= 0 and p_end_at >= 0:
            block = text[p_start:p_end_at + len("</hp:p>")]
            if visible_text(block) == marker:
                pair = marker_block_style_refs(block, marker)
                if pair is not None:
                    refs.add(pair)
        search_from = marker_at + len(marker)
    return refs


def _numeric_id(node: ET.Element) -> int:
    try:
        return int(node.attrib.get("id", "-1"))
    except ValueError:
        return -1


def _has_child(node: ET.Element, child_name: str) -> bool:
    return any(local_name(child.tag) == child_name for child in list(node))




def _set_outline_margin(para_pr: ET.Element, *, left: int, intent: int) -> None:
    found_left = False
    found_intent = False
    for node in para_pr.iter():
        name = local_name(node.tag)
        if name == "left":
            node.set("value", str(left))
            node.set("unit", "HWPUNIT")
            found_left = True
        elif name == "intent":
            node.set("value", str(intent))
            node.set("unit", "HWPUNIT")
            found_intent = True
        elif name == "align":
            node.set("horizontal", "LEFT")
    if not found_left or not found_intent:
        raise ValueError("기준 문단 스타일에서 내어쓰기 margin을 찾지 못했습니다.")


def _clone_char_style(
    char_properties: ET.Element,
    base: ET.Element,
    *,
    new_id: int,
    bold: bool,
) -> str:
    clone = deepcopy(base)
    clone.set("id", str(new_id))
    for child in list(clone):
        if local_name(child.tag) == "bold" and not bold:
            clone.remove(child)
    if bold and not _has_child(clone, "bold"):
        bold_node = ET.Element(f"{{{HEAD_NS}}}bold")
        children = list(clone)
        insert_at = next(
            (
                index
                for index, child in enumerate(children)
                if local_name(child.tag) in {"underline", "strikeout"}
            ),
            len(children),
        )
        clone.insert(insert_at, bold_node)
    char_properties.append(clone)
    return str(new_id)


def _sort_numeric_definitions(
    container: ET.Element,
    item_name: str,
) -> None:
    children = list(container)
    definitions = [
        child for child in children if local_name(child.tag) == item_name
    ]
    if not definitions:
        raise ValueError(f"{item_name} 스타일 목록이 비어 있습니다.")
    ids = [_numeric_id(node) for node in definitions]
    if any(value < 0 for value in ids) or len(ids) != len(set(ids)):
        raise ValueError(f"{item_name} 스타일 ID는 고유한 숫자여야 합니다.")
    first_index = min(
        index
        for index, child in enumerate(children)
        if local_name(child.tag) == item_name
    )
    prefix = [
        child
        for child in children[:first_index]
        if local_name(child.tag) != item_name
    ]
    suffix = [
        child
        for child in children[first_index:]
        if local_name(child.tag) != item_name
    ]
    ordered = sorted(definitions, key=_numeric_id)
    container[:] = [*prefix, *ordered, *suffix]


def ensure_outline_styles(
    header_text: str,
    base_pairs: set[tuple[str, str]],
) -> tuple[str, dict[tuple[str, str], dict[str, str]]]:
    ET.register_namespace("hh", HEAD_NS)
    ET.register_namespace("hp", PARAGRAPH_NS)
    ET.register_namespace("hc", CORE_NS)
    root = ET.fromstring(header_text.encode("utf-8"))
    para_properties = next(
        (node for node in root.iter() if local_name(node.tag) == "paraProperties"),
        None,
    )
    char_properties = next(
        (node for node in root.iter() if local_name(node.tag) == "charProperties"),
        None,
    )
    if para_properties is None or char_properties is None:
        raise ValueError("header.xml에서 문단·글자 스타일 목록을 찾지 못했습니다.")

    para_defs = {
        node.attrib.get("id"): node
        for node in list(para_properties)
        if local_name(node.tag) == "paraPr"
    }
    char_defs = {
        node.attrib.get("id"): node
        for node in list(char_properties)
        if local_name(node.tag) == "charPr"
    }
    next_para_id = max(
        (_numeric_id(node) for node in list(para_properties)),
        default=-1,
    ) + 1
    next_char_id = max(
        (_numeric_id(node) for node in list(char_properties)),
        default=-1,
    ) + 1
    styles_by_base: dict[tuple[str, str], dict[str, str]] = {}

    def stable_pair(pair: tuple[str, str]) -> tuple[int, int, str, str]:
        para_id, char_id = pair
        try:
            para_number = int(para_id)
        except ValueError:
            para_number = -1
        try:
            char_number = int(char_id)
        except ValueError:
            char_number = -1
        return para_number, char_number, para_id, char_id

    for base_para_id, base_char_id in sorted(base_pairs, key=stable_pair):
        base_para = para_defs.get(base_para_id)
        base_char = char_defs.get(base_char_id)
        if base_para is None or base_char is None:
            raise ValueError("플레이스홀더의 기준 문단·글자 스타일을 찾지 못했습니다.")

        heading_para_id = str(next_para_id)
        next_para_id += 1
        heading_para = deepcopy(base_para)
        heading_para.set("id", heading_para_id)
        _set_outline_margin(heading_para, left=1200, intent=-1200)
        para_properties.append(heading_para)

        detail_para_id = str(next_para_id)
        next_para_id += 1
        detail_para = deepcopy(base_para)
        detail_para.set("id", detail_para_id)
        _set_outline_margin(detail_para, left=2400, intent=-1200)
        para_properties.append(detail_para)

        subdetail_para_id = str(next_para_id)
        next_para_id += 1
        subdetail_para = deepcopy(base_para)
        subdetail_para.set("id", subdetail_para_id)
        _set_outline_margin(subdetail_para, left=3600, intent=-800)
        para_properties.append(subdetail_para)

        heading_char_id = _clone_char_style(
            char_properties,
            base_char,
            new_id=next_char_id,
            bold=True,
        )
        next_char_id += 1
        detail_char_id = _clone_char_style(
            char_properties,
            base_char,
            new_id=next_char_id,
            bold=False,
        )
        next_char_id += 1
        styles_by_base[(base_para_id, base_char_id)] = {
            "headingParaPrIDRef": heading_para_id,
            "detailParaPrIDRef": detail_para_id,
            "subdetailParaPrIDRef": subdetail_para_id,
            "headingCharPrIDRef": heading_char_id,
            "detailCharPrIDRef": detail_char_id,
            "subdetailCharPrIDRef": detail_char_id,
        }

    _sort_numeric_definitions(para_properties, "paraPr")
    _sort_numeric_definitions(char_properties, "charPr")
    para_properties.set(
        "itemCnt",
        str(sum(local_name(node.tag) == "paraPr" for node in list(para_properties))),
    )
    char_properties.set(
        "itemCnt",
        str(sum(local_name(node.tag) == "charPr" for node in list(char_properties))),
    )
    serialized = ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    ).decode("utf-8")
    return serialized, styles_by_base


def apply_outline_style(
    block: str,
    marker: str,
    role: str,
    styles_by_base: dict[tuple[str, str], dict[str, str]],
) -> str:
    base_refs = marker_block_style_refs(block, marker)
    if base_refs is None:
        raise ValueError(
            "개조식 플레이스홀더는 한 개의 텍스트 run에 단독으로 있어야 합니다."
        )
    styles = styles_by_base.get(base_refs)
    if styles is None:
        raise ValueError("플레이스홀더 기준 스타일의 개조식 매핑을 찾지 못했습니다.")

    prefix = {
        "heading": "heading",
        "detail": "detail",
        "subdetail": "subdetail",
    }[role]
    para_id = styles[f"{prefix}ParaPrIDRef"]
    char_id = styles[f"{prefix}CharPrIDRef"]
    block = PARA_REF_RE.sub(
        lambda match: match.group(1) + para_id + match.group(3),
        block,
        count=1,
    )
    marker_run_match = next(
        (
            match
            for match in RUN_BLOCK_RE.finditer(block)
            if marker in match.group(0)
        ),
        None,
    )
    if marker_run_match is None:
        raise ValueError("플레이스홀더 텍스트 run을 찾지 못했습니다.")
    marker_run = RUN_CHAR_REF_RE.sub(
        lambda match: match.group(1) + char_id + match.group(3),
        marker_run_match.group(0),
        count=1,
    )
    return (
        block[:marker_run_match.start()]
        + marker_run
        + block[marker_run_match.end():]
    )


def replace_multiline(
    text: str,
    marker: str,
    value: str,
    outline_styles: dict[tuple[str, str], dict[str, str]] | None = None,
    outline_lines: list[str] | None = None,
    next_paragraph_id: Callable[[], str] | None = None,
) -> tuple[str, int, str | None]:
    count = 0
    while marker in text:
        marker_at = text.find(marker)
        p_start = text.rfind("<hp:p", 0, marker_at)
        p_end_at = text.find("</hp:p>", marker_at)
        if p_start < 0 or p_end_at < 0 or not PARAGRAPH_OPEN_RE.match(text, p_start):
            return text, count, "플레이스홀더가 hp:p 문단 안에 있지 않습니다."
        p_end = p_end_at + len("</hp:p>")
        block = text[p_start:p_end]
        if visible_text(block) != marker:
            return text, count, "여러 줄 값의 플레이스홀더는 문단에 단독으로 있어야 합니다."
        if next_paragraph_id is None:
            return text, count, "결정적 문단 ID allocator가 없습니다."

        lines = outline_lines if outline_lines is not None else (value.splitlines() or [""])
        clones = []
        for line in lines:
            clone = block
            if outline_lines is not None:
                role = outline_role(line)
                if role is None or outline_styles is None:
                    return text, count, "개조식 문단 역할 또는 스타일 매핑이 없습니다."
                try:
                    clone = apply_outline_style(
                        clone,
                        marker,
                        role,
                        outline_styles,
                    )
                except ValueError as exc:
                    return text, count, str(exc)
            clone = clone.replace(marker, escape(line), 1)
            clone = reset_paragraph_id(clone, next_paragraph_id())
            clones.append(clone)
        text = text[:p_start] + "".join(clones) + text[p_end:]
        count += 1
    return text, count, None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def validate_canonical_receipt(source: Path, receipt_path: Path) -> None:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"canonical receipt를 읽을 수 없습니다: {exc}") from exc
    if receipt.get("status") != "PASS":
        raise ValueError("canonical receipt status는 PASS여야 합니다.")
    if receipt.get("role") != "user-edited-canonical":
        raise ValueError("canonical receipt role은 user-edited-canonical이어야 합니다.")
    actual_digest = sha256(source)
    if receipt.get("canonicalSha256") != actual_digest:
        raise ValueError(
            "canonical receipt digest가 입력 HWPX와 일치하지 않습니다. "
            f"expected={receipt.get('canonicalSha256')} actual={actual_digest}"
        )


def load_values(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("치환값 JSON의 최상위는 객체여야 합니다.")

    approval = raw.get("_approval")
    raw_values = raw.get("values") if "values" in raw else raw
    if not isinstance(raw_values, dict):
        raise ValueError("치환값 JSON의 values는 객체여야 합니다.")

    if not isinstance(approval, dict) or approval.get("status") != "APPROVED":
        raise ValueError(
            "승인된 치환값만 사용할 수 있습니다. "
            "_approval.status가 APPROVED인 승인 문서를 사용하세요."
        )
    missing = [field for field in REQUIRED_APPROVAL_FIELDS if not approval.get(field)]
    if missing:
        raise ValueError("승인 메타데이터 누락: " + ", ".join(missing))

    values: dict[str, str] = {}
    for marker, value in raw_values.items():
        if not isinstance(marker, str) or not PLACEHOLDER_RE.fullmatch(marker):
            raise ValueError(f"잘못된 플레이스홀더 키: {marker!r}")
        if isinstance(value, (dict, list)):
            raise ValueError(f"치환값은 문자열 또는 단순 값이어야 합니다: {marker}")
        values[marker] = "" if value is None else str(value)
    return values


def load_claim_free(path: Path, values: dict[str, str]) -> set[str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    claim_free = raw.get("_claim_free", {})
    if not isinstance(claim_free, dict):
        raise ValueError("_claim_free는 플레이스홀더와 비주장 사유의 객체여야 합니다.")
    result = set()
    for marker, reason in claim_free.items():
        if marker not in values:
            raise ValueError(f"_claim_free에 values에 없는 키가 있습니다: {marker}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"_claim_free 사유가 필요합니다: {marker}")
        result.add(marker)
    return result


def validate_evidence_registry(
    values: dict[str, str],
    registry_path: Path | None,
) -> set[str]:
    claimed_labels: dict[str, set[str]] = {}
    for value in values.values():
        for paragraph in value.splitlines() or [value]:
            for evidence_id, label in claim_markers_at_end(paragraph):
                claimed_labels.setdefault(evidence_id, set()).add(label)
    claimed_ids = set(claimed_labels)
    if not claimed_ids:
        return set()
    if registry_path is None:
        raise ValueError(
            "주장 ID가 있는 값에는 --evidence-registry 근거목록.csv가 필요합니다."
        )
    if not registry_path.is_file():
        raise FileNotFoundError(f"근거목록.csv를 찾을 수 없습니다: {registry_path}")

    with registry_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "evidence_id",
            "evidence_type",
            "inline_citation",
            "statement",
            "source_name",
            "source_path_or_url",
            "checked_on",
            "status",
        }
        missing_columns = required.difference(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "근거목록.csv 필수 열 누락: " + ", ".join(sorted(missing_columns))
            )
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            evidence_id = (row.get("evidence_id") or "").strip()
            if not evidence_id:
                continue
            if not re.fullmatch(r"[EUHP]\d{3}", evidence_id):
                raise ValueError(f"잘못된 evidence_id: {evidence_id}")
            if evidence_id in rows:
                raise ValueError(f"중복 evidence_id: {evidence_id}")
            rows[evidence_id] = row

    missing_ids = sorted(claimed_ids.difference(rows))
    if missing_ids:
        raise ValueError(
            "근거목록.csv에 없는 주장 ID: " + ", ".join(missing_ids)
        )
    for evidence_id in sorted(claimed_ids):
        row = rows[evidence_id]
        expected_type = EVIDENCE_TYPE_BY_PREFIX[evidence_id[0]]
        actual_type = (row.get("evidence_type") or "").strip().lower()
        if actual_type != expected_type:
            raise ValueError(
                f"{evidence_id} evidence_type은 {expected_type}이어야 합니다."
            )
        inline_citation = row.get("inline_citation") or ""
        if (
            not inline_citation
            or inline_citation != inline_citation.strip()
            or any(
                unicodedata.category(char).startswith("C")
                for char in inline_citation
            )
        ):
            raise ValueError(
                f"{evidence_id} inline_citation은 앞뒤 공백·제어문자 없이 필요합니다."
            )
        if evidence_id[0] in {"E", "U"}:
            citation_match = SOURCE_CITATION_RE.fullmatch(inline_citation)
            if citation_match is None:
                raise ValueError(
                    f"{evidence_id} inline_citation은 `출처명, YYYY` 형식이어야 합니다."
                )
            expected_year = source_citation_year(row)
            if expected_year is None:
                raise ValueError(
                    f"{evidence_id} 출처 연도를 확인할 날짜가 필요합니다."
                )
            if citation_match.group(2) != expected_year:
                raise ValueError(
                    f"{evidence_id} inline_citation 연도는 근거목록 날짜의 "
                    f"{expected_year}와 같아야 합니다."
                )
        elif evidence_id[0] == "H" and inline_citation != "검증가설":
            raise ValueError("H 계열 inline_citation은 `검증가설`이어야 합니다.")
        elif evidence_id[0] == "P" and inline_citation != "실행계획":
            raise ValueError("P 계열 inline_citation은 `실행계획`이어야 합니다.")
        if claimed_labels[evidence_id] != {inline_citation}:
            raise ValueError(
                f"{evidence_id} 보고서 표지는 근거목록.csv inline_citation "
                f"{inline_citation!r}와 정확히 일치해야 합니다."
            )
        for field in ("statement", "status"):
            if not (row.get(field) or "").strip():
                raise ValueError(f"{evidence_id} {field} 값이 필요합니다.")
        if evidence_id[0] in {"E", "U"}:
            for field in ("source_name", "source_path_or_url", "checked_on"):
                if not (row.get(field) or "").strip():
                    raise ValueError(f"{evidence_id} {field} 값이 필요합니다.")
    return claimed_ids


def write_log(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("placeholder", "file", "replacements", "status", "message"),
        )
        writer.writeheader()
        writer.writerows(rows)


def fill_hwpx(
    source: Path,
    values_path: Path,
    output: Path,
    log_path: Path,
    overwrite: bool,
    allow_empty: bool = False,
    evidence_registry_path: Path | None = None,
    canonical_receipt_path: Path | None = None,
) -> tuple[list[str], list[dict[str, str]]]:
    input_errors = validate_hwpx(source)
    if input_errors:
        raise ValueError("\n".join(input_errors))
    if source.resolve() == output.resolve():
        raise ValueError("원본과 출력 경로는 달라야 합니다.")
    if canonical_receipt_path is not None:
        validate_canonical_receipt(source, canonical_receipt_path)
    if output.exists() and not overwrite:
        raise FileExistsError(f"출력 파일이 이미 있습니다: {output}")
    if not values_path.is_file():
        raise FileNotFoundError(f"치환값 파일을 찾을 수 없습니다: {values_path}")

    values = load_values(values_path)
    claim_free_markers = load_claim_free(values_path, values)
    if not values and not allow_empty:
        raise ValueError(
            "치환값이 0개입니다. 자동 치환을 중단합니다. "
            "빈 치환이 의도라면 --allow-empty를 명시하세요."
        )
    outline_lines_by_marker: dict[str, list[str]] = {}
    auto_outlined_markers: set[str] = set()
    for marker, value in values.items():
        if not value or marker in claim_free_markers:
            continue
        try:
            outline_lines = parse_outline_value(value)
        except ValueError as exc:
            raise ValueError(f"{marker}: {exc}") from exc
        if outline_lines is None:
            try:
                outline_lines = normalize_prose_as_outline(value)
            except ValueError as exc:
                raise ValueError(f"{marker}: {exc}") from exc
            auto_outlined_markers.add(marker)
        outline_lines_by_marker[marker] = outline_lines
    validate_evidence_registry(values, evidence_registry_path)
    outline_lines_by_marker = {
        marker: [render_claim_citations(line) for line in lines]
        for marker, lines in outline_lines_by_marker.items()
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    modified: dict[str, bytes] = {}
    totals = {marker: 0 for marker in values}

    with ZipFile(source, "r") as archive:
        section_texts = {
            name: archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if re.fullmatch(r"Contents/section\d+\.xml", name)
        }
        existing_paragraph_ids = []
        for section_text in section_texts.values():
            for match in P_ID_RE.finditer(section_text):
                try:
                    existing_paragraph_ids.append(int(match.group(2)))
                except (IndexError, ValueError):
                    continue
        next_paragraph_number = max(existing_paragraph_ids, default=0) + 1

        def allocate_paragraph_id() -> str:
            nonlocal next_paragraph_number
            allocated = str(next_paragraph_number)
            next_paragraph_number += 1
            return allocated

        outline_styles: (
            dict[tuple[str, str], dict[str, str]] | None
        ) = None
        if outline_lines_by_marker:
            base_pairs: set[tuple[str, str]] = set()
            for section_text in section_texts.values():
                for marker in sorted(outline_lines_by_marker):
                    base_pairs.update(find_marker_style_refs(section_text, marker))
            if base_pairs:
                header_text = archive.read("Contents/header.xml").decode("utf-8")
                updated_header, outline_styles = ensure_outline_styles(
                    header_text,
                    base_pairs,
                )
                modified["Contents/header.xml"] = updated_header.encode("utf-8")
        for name in archive.namelist():
            data = archive.read(name)
            if not name.endswith((".xml", ".hpf")):
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue

            file_changed = False
            for marker, value in values.items():
                if not value:
                    if marker in text:
                        rows.append(
                            {
                                "placeholder": marker,
                                "file": name,
                                "replacements": "0",
                                "status": "SKIPPED_EMPTY",
                                "message": "값이 비어 있어 원문을 유지했습니다.",
                            }
                        )
                    continue

                outline_lines = outline_lines_by_marker.get(marker)
                if (
                    "\n" in value
                    or "\r" in value
                    or outline_lines is not None
                    or marker not in claim_free_markers
                ):
                    text, replacements, error = replace_multiline(
                        text,
                        marker,
                        value,
                        outline_styles,
                        outline_lines,
                        allocate_paragraph_id,
                    )
                    if error:
                        rows.append(
                            {
                                "placeholder": marker,
                                "file": name,
                                "replacements": str(replacements),
                                "status": "BLOCK",
                                "message": error,
                            }
                        )
                    elif replacements:
                        rows.append(
                            {
                                "placeholder": marker,
                                "file": name,
                                "replacements": str(replacements),
                                "status": (
                                    "AUTO_OUTLINED"
                                    if marker in auto_outlined_markers
                                    else "REPLACED"
                                ),
                                "message": (
                                    "산문 입력을 `o 핵심내용 → - 주장` 개조식으로 자동 정규화했습니다."
                                    if marker in auto_outlined_markers
                                    else "주장·여러 줄·개조식 문단 치환"
                                ),
                            }
                        )
                    totals[marker] += replacements
                    file_changed = file_changed or replacements > 0
                else:
                    replacements = text.count(marker)
                    if replacements:
                        text = text.replace(marker, escape(value))
                        rows.append(
                            {
                                "placeholder": marker,
                                "file": name,
                                "replacements": str(replacements),
                                "status": "REPLACED",
                                "message": "정확한 플레이스홀더 치환",
                            }
                        )
                        totals[marker] += replacements
                        file_changed = True

            if file_changed and name.startswith("Contents/section"):
                text = LINES_RE.sub("", text)
            if file_changed:
                try:
                    ET.fromstring(text.encode("utf-8"))
                except ET.ParseError as exc:
                    raise ValueError(f"치환 후 XML 오류 {name}: {exc}") from exc
                modified[name] = text.encode("utf-8")

        for marker, total in totals.items():
            if total == 0 and not any(row["placeholder"] == marker for row in rows):
                rows.append(
                    {
                        "placeholder": marker,
                        "file": "",
                        "replacements": "0",
                        "status": "NOT_FOUND",
                        "message": "HWPX에서 플레이스홀더를 찾지 못했습니다.",
                    }
                )

        temp_file = tempfile.NamedTemporaryFile(
            prefix=output.stem + "-",
            suffix=".hwpx",
            dir=output.parent,
            delete=False,
        )
        temp_path = Path(temp_file.name)
        temp_file.close()
        try:
            with ZipFile(temp_path, "w") as target:
                ordered = ["mimetype"] + [
                    name for name in archive.namelist() if name != "mimetype"
                ]
                for name in ordered:
                    info = archive.getinfo(name)
                    target.writestr(info, modified.get(name, archive.read(name)))

            output_errors = validate_hwpx(temp_path)
            if output_errors:
                raise ValueError("\n".join(output_errors))
            os.replace(temp_path, output)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    unresolved = scan_placeholders(output)
    write_log(log_path, rows)
    return unresolved, rows


def command_scan(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser().resolve()
    placeholders = scan_placeholders(source)
    mapping = {marker: "" for marker in placeholders}
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
    if args.map_out:
        target = Path(args.map_out).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "_approval": {
                "status": "DRAFT",
                "approved_by": "",
                "approved_at": "",
                "source_draft": "",
            },
            "_claim_free": {},
            "values": mapping,
        }
        target.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"MAP: {target}")
    print(f"PLACEHOLDERS: {len(placeholders)}")
    if not placeholders:
        if args.manual_mapping:
            print("MODE: MANUAL_MAPPING")
            return 0
        if args.allow_empty:
            print("WARNING: 빈 플레이스홀더 스캔을 명시적으로 허용했습니다.")
            return 0
        print(
            "BLOCK: 플레이스홀더가 0개입니다. 교육용 주석 HWPX인지 확인하거나 "
            "--manual-mapping 또는 --allow-empty를 명시하세요."
        )
        return 2
    return 0


def command_fill(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    values = Path(args.values).expanduser().resolve()
    log_path = (
        Path(args.log).expanduser().resolve()
        if args.log
        else output.with_name(output.stem + "-replacement-log.csv")
    )
    unresolved, rows = fill_hwpx(
        source,
        values,
        output,
        log_path,
        args.overwrite,
        allow_empty=args.allow_empty,
        evidence_registry_path=(
            Path(args.evidence_registry).expanduser().resolve()
            if args.evidence_registry
            else None
        ),
        canonical_receipt_path=(
            Path(args.canonical_receipt).expanduser().resolve()
            if args.canonical_receipt
            else None
        ),
    )
    blocks = [row for row in rows if row["status"] in BLOCK_LOG_STATUSES]
    print(f"OUTPUT: {output}")
    print(f"LOG: {log_path}")
    print(f"BLOCKS: {len(blocks)}")
    print(f"UNRESOLVED: {len(unresolved)}")
    for marker in unresolved:
        print(f"  - {marker}")
    auto_outlined = sorted(
        {
            row["placeholder"]
            for row in rows
            if row["status"] == "AUTO_OUTLINED"
        }
    )
    print(f"AUTO_OUTLINED: {len(auto_outlined)}")
    for marker in auto_outlined:
        print(f"  - {marker}")
    return 2 if blocks or unresolved else 0


def command_validate(args: argparse.Namespace) -> int:
    source = Path(args.input).expanduser().resolve()
    errors = validate_hwpx(source)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"VALID: {source}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HWPX 플레이스홀더 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="중괄호 플레이스홀더 스캔")
    scan.add_argument("input")
    scan.add_argument("--map-out")
    scan.add_argument(
        "--allow-empty",
        action="store_true",
        help="플레이스홀더 0개를 명시적으로 허용",
    )
    scan.add_argument(
        "--manual-mapping",
        action="store_true",
        help="플레이스홀더가 없을 때 수동 매핑 모드로 종료",
    )
    scan.set_defaults(func=command_scan)

    fill = subparsers.add_parser("fill", help="JSON 값으로 새 HWPX 생성")
    fill.add_argument("input")
    fill.add_argument("--values", required=True)
    fill.add_argument("--output", required=True)
    fill.add_argument("--log")
    fill.add_argument("--overwrite", action="store_true")
    fill.add_argument(
        "--allow-empty",
        action="store_true",
        help="0개 치환값으로 변경 없는 결과 생성을 명시적으로 허용",
    )
    fill.add_argument(
        "--evidence-registry",
        help="주장 ID와 실제 출처·가설·계획을 대조할 근거목록.csv",
    )
    fill.add_argument(
        "--canonical-receipt",
        help="user-edited canonical 입력의 digest-bound receipt JSON",
    )
    fill.set_defaults(func=command_fill)

    validate = subparsers.add_parser("validate", help="HWPX 구조 검증")
    validate.add_argument("input")
    validate.set_defaults(func=command_validate)
    return parser


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (BadZipFile, FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

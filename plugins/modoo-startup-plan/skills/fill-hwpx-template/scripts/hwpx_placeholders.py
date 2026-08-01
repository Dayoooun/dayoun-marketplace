#!/usr/bin/env python3
"""Scan, fill, and validate exact {placeholders} in HWPX files."""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import random
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable
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
P_ID_RE = re.compile(r'(<hp:p\b[^>]*\bid=")[^"]+(")')


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


def reset_paragraph_id(block: str) -> str:
    new_id = str(random.randint(100_000_000, 2_000_000_000))
    return P_ID_RE.sub(rf"\g<1>{new_id}\2", block, count=1)


def replace_multiline(text: str, marker: str, value: str) -> tuple[str, int, str | None]:
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

        lines = value.splitlines() or [""]
        clones = []
        for line in lines:
            clone = block.replace(marker, escape(line), 1)
            clones.append(reset_paragraph_id(clone))
        text = text[:p_start] + "".join(clones) + text[p_end:]
        count += 1
    return text, count, None


def load_values(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("치환값 JSON의 최상위는 객체여야 합니다.")

    values: dict[str, str] = {}
    for marker, value in raw.items():
        if not isinstance(marker, str) or not PLACEHOLDER_RE.fullmatch(marker):
            raise ValueError(f"잘못된 플레이스홀더 키: {marker!r}")
        if isinstance(value, (dict, list)):
            raise ValueError(f"치환값은 문자열 또는 단순 값이어야 합니다: {marker}")
        values[marker] = "" if value is None else str(value)
    return values


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
) -> tuple[list[str], list[dict[str, str]]]:
    input_errors = validate_hwpx(source)
    if input_errors:
        raise ValueError("\n".join(input_errors))
    if source.resolve() == output.resolve():
        raise ValueError("원본과 출력 경로는 달라야 합니다.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"출력 파일이 이미 있습니다: {output}")
    if not values_path.is_file():
        raise FileNotFoundError(f"치환값 파일을 찾을 수 없습니다: {values_path}")

    values = load_values(values_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    modified: dict[str, bytes] = {}
    totals = {marker: 0 for marker in values}

    with ZipFile(source, "r") as archive:
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

                if "\n" in value or "\r" in value:
                    text, replacements, error = replace_multiline(text, marker, value)
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
                                "status": "REPLACED",
                                "message": "여러 줄 문단 치환",
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
        target.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"MAP: {target}")
    print(f"PLACEHOLDERS: {len(placeholders)}")
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
    unresolved, rows = fill_hwpx(source, values, output, log_path, args.overwrite)
    blocks = [row for row in rows if row["status"] == "BLOCK"]
    print(f"OUTPUT: {output}")
    print(f"LOG: {log_path}")
    print(f"BLOCKS: {len(blocks)}")
    print(f"UNRESOLVED: {len(unresolved)}")
    for marker in unresolved:
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
    scan.set_defaults(func=command_scan)

    fill = subparsers.add_parser("fill", help="JSON 값으로 새 HWPX 생성")
    fill.add_argument("input")
    fill.add_argument("--values", required=True)
    fill.add_argument("--output", required=True)
    fill.add_argument("--log")
    fill.add_argument("--overwrite", action="store_true")
    fill.set_defaults(func=command_fill)

    validate = subparsers.add_parser("validate", help="HWPX 구조 검증")
    validate.add_argument("input")
    validate.set_defaults(func=command_validate)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (BadZipFile, FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Synchronize and validate HWPX Preview/PrvText.txt from final section text."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET


MIMETYPE = "application/hwp+zip"
PREVIEW_MEMBER = "Preview/PrvText.txt"
SECTION_MEMBER = re.compile(r"^Contents/section(\d+)\.xml$")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


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


def normalize_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip() + "\n"


def body_preview(archive: zipfile.ZipFile) -> tuple[str, list[str]]:
    errors: list[str] = []
    members = []
    for name in archive.namelist():
        match = SECTION_MEMBER.fullmatch(name)
        if match:
            members.append((int(match.group(1)), name))
    members.sort()
    if not members:
        return "", ["HWPX has no Contents/sectionN.xml members"]
    paragraphs = []
    for _index, name in members:
        try:
            root = ET.fromstring(archive.read(name))
        except ET.ParseError as error:
            errors.append(f"cannot parse {name}: {error}")
            continue
        for node in root.iter():
            if local_name(node.tag) != "p":
                continue
            text = paragraph_text(node)
            if text:
                paragraphs.append(text)
    if not paragraphs:
        errors.append("HWPX sections contain no visible paragraph text")
    return normalize_text("\n".join(paragraphs)), errors


def inspect(path: Path) -> dict[str, object]:
    errors: list[str] = []
    body = ""
    preview = ""
    try:
        with zipfile.ZipFile(path) as archive:
            counts = Counter(archive.namelist())
            errors.extend(
                f"duplicate ZIP member: {name}"
                for name, count in counts.items()
                if count > 1
            )
            body, body_errors = body_preview(archive)
            errors.extend(body_errors)
            try:
                preview = normalize_text(
                    archive.read(PREVIEW_MEMBER).decode("utf-8-sig")
                )
            except KeyError:
                errors.append(f"missing {PREVIEW_MEMBER}")
            except UnicodeDecodeError as error:
                errors.append(f"preview text is not UTF-8: {error}")
    except (FileNotFoundError, zipfile.BadZipFile) as error:
        errors.append(f"cannot read HWPX: {error}")
    if body and preview and body != preview:
        errors.append("Preview/PrvText.txt does not match normalized section text")
    return {
        "status": "PASS" if not errors else "BLOCK",
        "input": str(path),
        "bodyCharacters": len(body),
        "previewCharacters": len(preview),
        "previewMatchesBody": bool(body) and body == preview,
        "errors": errors,
    }


def preview_zipinfo(existing: zipfile.ZipInfo | None) -> zipfile.ZipInfo:
    if existing is not None:
        return existing
    info = zipfile.ZipInfo(PREVIEW_MEMBER, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    return info


def sync(source: Path, output: Path, overwrite: bool = False) -> dict[str, object]:
    errors: list[str] = []
    if source.resolve() == output.resolve():
        return {"status": "BLOCK", "errors": ["input and output must differ"]}
    if output.exists() and not overwrite:
        return {"status": "BLOCK", "errors": [f"output already exists: {output}"]}
    try:
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            duplicates = [
                name for name, count in Counter(names).items() if count > 1
            ]
            if duplicates:
                return {
                    "status": "BLOCK",
                    "errors": [f"duplicate ZIP member: {name}" for name in duplicates],
                }
            body, body_errors = body_preview(archive)
            if body_errors:
                return {"status": "BLOCK", "errors": body_errors}
            infos = {info.filename: info for info in archive.infolist()}
            payloads = {name: archive.read(name) for name in names}
    except (FileNotFoundError, zipfile.BadZipFile) as error:
        return {"status": "BLOCK", "errors": [f"cannot read HWPX: {error}"]}
    if payloads.get("mimetype") != MIMETYPE.encode("ascii"):
        errors.append("invalid or missing HWPX mimetype")
    if errors:
        return {"status": "BLOCK", "errors": errors}
    payloads[PREVIEW_MEMBER] = body.encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=output.stem + "-",
        suffix=".hwpx",
        dir=output.parent,
        delete=False,
    )
    temp_path = Path(handle.name)
    handle.close()
    try:
        with zipfile.ZipFile(temp_path, "w") as target:
            mimetype_info = infos.get("mimetype") or zipfile.ZipInfo("mimetype")
            mimetype_info.compress_type = zipfile.ZIP_STORED
            target.writestr(mimetype_info, payloads["mimetype"])
            ordered_names = [name for name in names if name != "mimetype"]
            if PREVIEW_MEMBER not in ordered_names:
                ordered_names.append(PREVIEW_MEMBER)
            for name in ordered_names:
                info = (
                    preview_zipinfo(infos.get(name))
                    if name == PREVIEW_MEMBER
                    else infos[name]
                )
                target.writestr(info, payloads[name])
        temp_path.replace(output)
    finally:
        if temp_path.exists():
            temp_path.unlink()
    report = inspect(output)
    report["source"] = str(source)
    report["output"] = str(output)
    return report


def write_report(report: dict[str, object], output: Path | None) -> None:
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize HWPX preview text.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("input", type=Path)
    validate.add_argument("--output", type=Path, dest="report")
    synchronize = subparsers.add_parser("sync")
    synchronize.add_argument("input", type=Path)
    synchronize.add_argument("--output", type=Path, required=True)
    synchronize.add_argument("--overwrite", action="store_true")
    synchronize.add_argument("--report", type=Path)
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = parse_args()
    if args.command == "validate":
        report = inspect(args.input.expanduser().resolve())
        report_path = args.report
    else:
        report = sync(
            args.input.expanduser().resolve(),
            args.output.expanduser().resolve(),
            overwrite=args.overwrite,
        )
        report_path = args.report
    write_report(report, report_path)
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

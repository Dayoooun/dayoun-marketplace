from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import fitz
from PIL import Image


REQUIRED_CHECKS = {
    "clipping",
    "overlap",
    "blankPage",
    "lowContrast",
    "orphanParagraph",
    "captionSplit",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def resolve_file(root: Path, value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} path is required")
        return None
    candidate = Path(value)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label} path escapes receipt directory: {value}")
        return None
    if not resolved.is_file():
        errors.append(f"{label} file is missing: {value}")
        return None
    return resolved


def validate(hwpx: Path, receipt_path: Path) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    root = receipt_path.parent
    errors: list[str] = []

    if receipt.get("schemaVersion") != "1.0.0":
        errors.append("render receipt schemaVersion must be 1.0.0")
    if receipt.get("status") != "PASS":
        errors.append("render receipt status must be PASS")
    renderer = receipt.get("renderer")
    if not isinstance(renderer, dict) or not renderer.get("name") or not renderer.get("version"):
        errors.append("renderer name and version are required")

    actual_hwpx_digest = sha256(hwpx)
    if receipt.get("hwpxSha256") != actual_hwpx_digest:
        errors.append("render receipt HWPX digest is missing or stale")

    pdf_record = receipt.get("pdf")
    pdf_path = None
    if not isinstance(pdf_record, dict):
        errors.append("pdf record is required")
    else:
        pdf_path = resolve_file(root, pdf_record.get("path"), "PDF", errors)
        if pdf_path is not None and pdf_record.get("sha256") != sha256(pdf_path):
            errors.append("PDF digest is missing or stale")

    pdf_pages = 0
    pdf_opened = False
    if pdf_path is not None:
        try:
            document = fitz.open(pdf_path)
            pdf_opened = True
            pdf_pages = document.page_count
            document.close()
        except Exception as error:
            errors.append(f"cannot open rendered PDF: {error}")

    page_records = receipt.get("pages")
    if not isinstance(page_records, list) or not page_records:
        errors.append("at least one rendered page PNG is required")
        page_records = []

    seen_indexes: set[int] = set()
    pages = []
    for record in page_records:
        if not isinstance(record, dict):
            errors.append("page record must be an object")
            continue
        index = record.get("index")
        if not isinstance(index, int) or index < 1 or index in seen_indexes:
            errors.append(f"page index must be unique positive integer: {index}")
            continue
        seen_indexes.add(index)
        png_path = resolve_file(root, record.get("png"), f"page {index} PNG", errors)
        width = height = 0
        if png_path is not None:
            if record.get("sha256") != sha256(png_path):
                errors.append(f"page {index} PNG digest is missing or stale")
            try:
                with Image.open(png_path) as image:
                    width, height = image.size
            except Exception as error:
                errors.append(f"cannot open page {index} PNG: {error}")
            if record.get("width") != width or record.get("height") != height:
                errors.append(f"page {index} PNG dimensions are missing or stale")

        checks = record.get("checks")
        if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS:
            errors.append(
                f"page {index} checks must contain exactly: "
                + ", ".join(sorted(REQUIRED_CHECKS))
            )
        elif any(checks[name] is not False for name in REQUIRED_CHECKS):
            errors.append(f"page {index} visual QA has a reported defect")
        if record.get("zoomReviewed") is not True:
            errors.append(f"page {index} requires 100-percent and zoom review")
        pages.append(
            {
                "index": index,
                "png": str(png_path) if png_path else None,
                "width": width,
                "height": height,
            }
        )

    expected_indexes = list(range(1, len(page_records) + 1))
    if sorted(seen_indexes) != expected_indexes:
        errors.append("rendered page PNG indexes must be consecutive from 1")
    if pdf_opened and pdf_pages < 1:
        errors.append("rendered PDF must contain at least one page")
    if pdf_opened and pdf_pages != len(page_records):
        errors.append("PDF page count and page PNG count differ")

    return {
        "status": "PASS" if not errors else "BLOCK",
        "hwpx": str(hwpx),
        "hwpxSha256": actual_hwpx_digest,
        "receipt": str(receipt_path),
        "renderer": renderer,
        "pdfPageCount": pdf_pages,
        "pages": pages,
        "errors": errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify digest-bound PDF/page-PNG HWPX render QA evidence."
    )
    parser.add_argument("hwpx", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = validate(args.hwpx, args.receipt)
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    print(serialized, end="")
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

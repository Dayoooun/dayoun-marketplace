#!/usr/bin/env python3
"""Render a Hanword-exported PDF to page PNGs and draft a fail-closed QA receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import fitz
from PIL import Image


CHECKS = (
    "clipping",
    "overlap",
    "blankPage",
    "lowContrast",
    "orphanParagraph",
    "captionSplit",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def relative_to_receipt(path: Path, receipt: Path) -> str:
    return path.resolve().relative_to(receipt.parent.resolve()).as_posix()


def build_receipt(
    hwpx: Path,
    pdf: Path,
    output_dir: Path,
    receipt: Path,
    renderer_name: str,
    renderer_version: str,
    dpi: int,
    overwrite: bool,
) -> dict[str, object]:
    for source in (hwpx, pdf):
        if not source.is_file():
            raise FileNotFoundError(source)
    if receipt.exists() and not overwrite:
        raise FileExistsError(receipt)
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"output directory is not empty: {output_dir}")

    receipt.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    local_pdf = output_dir / pdf.name
    if pdf.resolve() != local_pdf.resolve():
        shutil.copyfile(pdf, local_pdf)

    pages: list[dict[str, object]] = []
    document = fitz.open(local_pdf)
    try:
        for index, page in enumerate(document, 1):
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            png = output_dir / f"page-{index:03d}.png"
            pixmap.save(png)
            with Image.open(png) as image:
                width, height = image.size
            pages.append(
                {
                    "index": index,
                    "png": relative_to_receipt(png, receipt),
                    "sha256": sha256(png),
                    "width": width,
                    "height": height,
                    "checks": {name: None for name in CHECKS},
                    "zoomReviewed": False,
                }
            )
    finally:
        document.close()

    payload: dict[str, object] = {
        "schemaVersion": "1.0.0",
        "status": "NEEDS_REVIEW",
        "renderer": {"name": renderer_name, "version": renderer_version},
        "hwpxSha256": sha256(hwpx),
        "pdf": {
            "path": relative_to_receipt(local_pdf, receipt),
            "sha256": sha256(local_pdf),
        },
        "pages": pages,
    }
    receipt.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an exported PDF to PNGs and create a review-required receipt."
    )
    parser.add_argument("hwpx", type=Path)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--renderer-name", required=True)
    parser.add_argument("--renderer-version", required=True)
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_receipt(
        args.hwpx.resolve(),
        args.pdf.resolve(),
        args.output_dir.resolve(),
        args.receipt.resolve(),
        args.renderer_name,
        args.renderer_version,
        args.dpi,
        args.overwrite,
    )
    print(f"PAGES: {len(payload['pages'])}")
    print(f"RECEIPT: {args.receipt.resolve()}")
    print("REVIEW_REQUIRED: checks를 모두 false, zoomReviewed를 true로 확인한 뒤 status를 PASS로 바꾸세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

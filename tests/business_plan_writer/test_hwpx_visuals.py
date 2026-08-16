from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
import warnings
from pathlib import Path
from xml.etree import ElementTree as ET

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "fill-hwpx-template"
    / "scripts"
    / "hwpx_visuals.py"
)
INTEGRITY_SCRIPT = SCRIPT.with_name("hwpx_source_integrity.py")
RENDER_SCRIPT = SCRIPT.with_name("verify_hwpx_render.py")


def load_module():
    spec = importlib.util.spec_from_file_location("hwpx_visuals", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


def load_integrity_module():
    spec = importlib.util.spec_from_file_location(
        "hwpx_source_integrity",
        INTEGRITY_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {INTEGRITY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INTEGRITY = load_integrity_module()


def load_render_module():
    spec = importlib.util.spec_from_file_location(
        "verify_hwpx_render",
        RENDER_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {RENDER_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RENDER = load_render_module()


def element(name: str, attributes: dict[str, str] | None = None, text: str | None = None) -> ET.Element:
    node = ET.Element(name, attributes or {})
    if text is not None:
        node.text = text
    return node


def paragraph(text: str, para_ref: str = "0", char_ref: str = "0") -> ET.Element:
    node = element("p", {"paraPrIDRef": para_ref})
    run = element("run", {"charPrIDRef": char_ref})
    run.append(element("t", text=text))
    node.append(run)
    return node


def visual_table(
    caption: str,
    *,
    row_count: int = 2,
    column_count: int = 1,
) -> ET.Element:
    table = element("tbl", {"rowCnt": str(row_count), "colCnt": str(column_count)})
    table.append(element("sz", {"width": "45900", "height": "26000"}))

    image_row = element("tr")
    image_cell = element("tc", {"borderFillIDRef": "15"})
    image_list = element("subList")
    image_p = element("p", {"paraPrIDRef": "0"})
    image_run = element("run", {"charPrIDRef": "0"})
    picture = element("pic")
    picture.append(element("sz", {"width": "39982", "height": "24000"}))
    picture.append(element("img", {"binaryItemIDRef": "image3"}))
    image_run.append(picture)
    image_p.append(image_run)
    image_list.append(image_p)
    image_cell.extend(
        [
            image_list,
            element("cellSz", {"width": "45900", "height": "24500"}),
            element(
                "cellMargin",
                {"left": "510", "right": "510", "top": "220", "bottom": "220"},
            ),
        ]
    )
    image_row.append(image_cell)
    if column_count > 1:
        image_row.append(element("tc"))
    table.append(image_row)

    caption_row = element("tr")
    caption_cell = element("tc", {"borderFillIDRef": "16"})
    caption_list = element("subList")
    caption_list.append(paragraph(caption, para_ref="19", char_ref="31"))
    caption_cell.extend(
        [
            caption_list,
            element("cellSz", {"width": "45900", "height": "1200"}),
            element(
                "cellMargin",
                {"left": "510", "right": "510", "top": "220", "bottom": "220"},
            ),
        ]
    )
    caption_row.append(caption_cell)
    if column_count > 1:
        caption_row.append(element("tc"))
    table.append(caption_row)
    if row_count > 2:
        extra_row = element("tr")
        extra_row.append(element("tc"))
        table.append(extra_row)
    return table


def header_xml() -> bytes:
    root = element("head")

    def bordered(border_id: str, background: str) -> ET.Element:
        border = element("borderFill", {"id": border_id})
        for side in ("leftBorder", "rightBorder", "topBorder", "bottomBorder"):
            border.append(
                element(
                    side,
                    {"type": "SOLID", "width": "0.1 mm", "color": "#000000"},
                )
            )
        brush = element("fillBrush")
        brush.append(element("winBrush", {"faceColor": background}))
        border.append(brush)
        return border

    root.extend([bordered("15", "#FFFFFF"), bordered("16", "#F2F2F2")])

    char = element("charPr", {"id": "31", "height": "1000"})
    char.append(element("bold"))
    root.append(char)

    para = element("paraPr", {"id": "19"})
    para.append(element("align", {"horizontal": "CENTER"}))
    root.append(para)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def section_xml(
    *,
    hierarchy_ok: bool = True,
    semantic_position_ok: bool = True,
    left_margin: str = "5669",
    caption: str = "그림 1. 지역순환 사업모델",
    duplicate_visual: bool = False,
    extra_malformed_visual: str | None = None,
    before_text: str = "시각자료가 설명하는 문단",
    after_text: str = "o 다음 핵심항목",
    outer_row_count: str = "1",
    include_visual: bool = True,
) -> bytes:
    root = element("section")
    secpr = element("secPr")
    page = element("pagePr", {"width": "59528", "height": "84186"})
    page.append(
        element(
            "margin",
            {
                "left": left_margin,
                "right": "5669",
                "top": "4251",
                "bottom": "4252",
                "header": "2834",
                "footer": "2834",
                "gutter": "0",
            },
        )
    )
    secpr.append(page)
    root.append(secpr)

    outer = element("tbl", {"rowCnt": outer_row_count, "colCnt": "1"})
    row = element("tr")
    cell = element("tc")
    sublist = element("subList")
    before = paragraph(before_text)
    after = paragraph(after_text)
    def wrapped_visual(visual: ET.Element | None = None) -> ET.Element:
        visual = visual if visual is not None else visual_table(caption)
        if not hierarchy_ok:
            return visual
        visual_p = element("p", {"paraPrIDRef": "0"})
        visual_run = element("run", {"charPrIDRef": "0"})
        visual_run.append(visual)
        visual_p.append(visual_run)
        return visual_p

    visual_nodes = [wrapped_visual()] if include_visual else []
    if duplicate_visual:
        visual_nodes.append(wrapped_visual())
    if extra_malformed_visual == "rows":
        visual_nodes.append(wrapped_visual(visual_table("", row_count=3)))
    elif extra_malformed_visual == "columns":
        visual_nodes.append(wrapped_visual(visual_table("", column_count=2)))
    elif extra_malformed_visual == "caption":
        visual_nodes.append(wrapped_visual(visual_table("")))

    if semantic_position_ok:
        sublist.extend([before, *visual_nodes, after])
    else:
        sublist.extend([before, after, *visual_nodes])
    cell.append(sublist)
    row.append(cell)
    outer.append(row)
    root.append(outer)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def manifest_xml(
    include_image: bool = True,
    *,
    image_href: str = "BinData/image3.PNG",
    duplicate_image_id: bool = False,
) -> bytes:
    root = element("package")
    manifest = element("manifest")
    if include_image:
        manifest.append(
            element(
                "item",
                {"id": "image3", "href": image_href, "media-type": "image/png"},
            )
        )
        if duplicate_image_id:
            manifest.append(
                element(
                    "item",
                    {
                        "id": "image3",
                        "href": "BinData/duplicate.PNG",
                        "media-type": "image/png",
                    },
                )
            )
    manifest.append(
        element(
            "item",
            {"id": "section0", "href": "Contents/section0.xml", "media-type": "application/xml"},
        )
    )
    root.append(manifest)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def make_hwpx(
    path: Path,
    *,
    hierarchy_ok: bool = True,
    semantic_position_ok: bool = True,
    left_margin: str = "5669",
    include_manifest_image: bool = True,
    include_bindata: bool = True,
    caption: str = "그림 1. 지역순환 사업모델",
    image_href: str = "BinData/image3.PNG",
    duplicate_manifest_id: bool = False,
    duplicate_zip_member: bool = False,
    duplicate_visual: bool = False,
    extra_malformed_visual: str | None = None,
    before_text: str = "시각자료가 설명하는 문단",
    after_text: str = "o 다음 핵심항목",
    outer_row_count: str = "1",
    include_visual: bool = True,
) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("mimetype"),
            "application/hwp+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("Contents/header.xml", header_xml())
        archive.writestr(
            "Contents/section0.xml",
            section_xml(
                hierarchy_ok=hierarchy_ok,
                semantic_position_ok=semantic_position_ok,
                left_margin=left_margin,
                caption=caption,
                duplicate_visual=duplicate_visual,
                extra_malformed_visual=extra_malformed_visual,
                before_text=before_text,
                after_text=after_text,
                outer_row_count=outer_row_count,
                include_visual=include_visual,
            ),
        )
        archive.writestr(
            "Contents/content.hpf",
            manifest_xml(
                include_manifest_image,
                image_href=image_href,
                duplicate_image_id=duplicate_manifest_id,
            ),
        )
        if include_bindata:
            archive.writestr("BinData/image3.PNG", b"synthetic-image")
        if duplicate_zip_member:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr("BinData/image3.PNG", b"duplicate-member")


def write_spec(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "visuals": [
                    {
                        "caption": "그림 1. 지역순환 사업모델",
                        "beforeParagraphContains": "설명하는 문단",
                        "afterParagraphContains": "o 다음 핵심항목",
                        "tableWidth": 45900,
                        "imageWidth": 39982,
                        "imageCellBorderFillID": "15",
                        "captionCellBorderFillID": "16",
                        "cellMargin": {"left": 510, "right": 510, "top": 220, "bottom": 220},
                        "captionRowHeight": 1200,
                        "captionPointSize": 10,
                        "captionBold": True,
                        "captionAlign": "CENTER",
                        "captionBackground": "#F2F2F2",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class HwpxVisualRegressionTests(unittest.TestCase):
    def test_valid_visual_receipt_matches_verified_1r_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.hwpx"
            make_hwpx(path)
            report = MODULE.inspect_hwpx(path)
            self.assertEqual(report["integrityErrors"], [])
            visual = report["visuals"][0]
            self.assertEqual(visual["hierarchy"], ["tc", "subList", "p", "run", "tbl"])
            self.assertEqual(visual["tableWidth"], "45900")
            self.assertEqual(visual["imageWidth"], "39982")
            self.assertEqual(visual["captionRowHeight"], "1200")
            self.assertEqual(visual["captionPointSize"], "10")
            self.assertTrue(visual["captionBold"])
            self.assertEqual(visual["captionAlign"], "CENTER")
            self.assertEqual(visual["imageCellBorderFillID"], "15")
            self.assertEqual(visual["captionCellBorderFillID"], "16")
            self.assertTrue(visual["imageCellBorderDigest"])
            self.assertTrue(visual["captionCellBorderDigest"])
            self.assertNotEqual(
                visual["imageCellBorderDigest"],
                visual["captionCellBorderDigest"],
            )
            self.assertEqual(visual["captionBackground"], "#F2F2F2")

    def test_validate_passes_semantic_placement_and_secpr_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hwpx"
            result = root / "result.hwpx"
            spec = root / "visuals.json"
            make_hwpx(source)
            make_hwpx(result)
            write_spec(spec)
            report = MODULE.validate_against_spec(result, spec, source)
            self.assertEqual(report["status"], "PASS", report["errors"])
            self.assertTrue(report["secPrPreserved"])

    def test_regressions_block_without_override(self) -> None:
        cases = {
            "wrong hierarchy": ({"hierarchy_ok": False}, "tc → subList → p → run → tbl"),
            "cell tail placement": ({"semantic_position_ok": False}, "after paragraph anchor mismatch"),
            "manifest mismatch": ({"include_manifest_image": False}, "missing manifest item"),
            "missing bindata": ({"include_bindata": False}, "missing BinData member"),
            "long caption": (
                {"caption": "그림 1. 지역순환 사업모델 — 자체 구성"},
                "forbidden long explanation",
            ),
            "long caption without forbidden text": (
                {"caption": "그림 1. " + "매우 긴 핵심 그림명" * 8},
                "caption must be at most",
            ),
            "unsafe manifest href": (
                {"image_href": "../BinData/image3.PNG"},
                "unsafe path segment",
            ),
            "image outside bindata": (
                {"image_href": "Pictures/image3.PNG"},
                "must be inside BinData",
            ),
            "duplicate manifest id": (
                {"duplicate_manifest_id": True},
                "duplicate content.hpf item id",
            ),
            "duplicate ZIP member": (
                {"duplicate_zip_member": True},
                "duplicate ZIP member",
            ),
            "duplicate visual caption": (
                {"duplicate_visual": True},
                "duplicate visual",
            ),
            "extra three-row visual": (
                {"extra_malformed_visual": "rows"},
                "visual table must be exactly 1 column × 2 rows",
            ),
            "extra two-column visual": (
                {"extra_malformed_visual": "columns"},
                "visual table must be exactly 1 column × 2 rows",
            ),
            "extra empty-caption visual": (
                {"extra_malformed_visual": "caption"},
                "caption must use",
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hwpx"
            spec = root / "visuals.json"
            make_hwpx(source)
            write_spec(spec)
            for name, (kwargs, expected) in cases.items():
                with self.subTest(name=name):
                    result = root / f"{name}.hwpx"
                    make_hwpx(result, **kwargs)
                    report = MODULE.validate_against_spec(result, spec, source)
                    self.assertEqual(report["status"], "BLOCK")
                    self.assertIn(expected, "\n".join(report["errors"]))

    def test_secpr_mutation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hwpx"
            result = root / "result.hwpx"
            spec = root / "visuals.json"
            make_hwpx(source)
            make_hwpx(result, left_margin="5000")
            write_spec(spec)
            report = MODULE.validate_against_spec(result, spec, source)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn("secPr changed from the source HWPX", report["errors"])

    def test_source_is_required_for_fail_closed_secpr_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = root / "result.hwpx"
            spec = root / "visuals.json"
            make_hwpx(result)
            write_spec(spec)
            report = MODULE.validate_against_spec(result, spec, None)
            self.assertEqual(report["status"], "BLOCK")
            self.assertFalse(report["secPrPreserved"])
            self.assertIn(
                "source HWPX is required for secPr preservation validation",
                report["errors"],
            )

    def test_source_integrity_allows_placeholder_fill_and_nested_visual(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hwpx"
            result = root / "result.hwpx"
            make_hwpx(source, before_text="{답변}", include_visual=False)
            make_hwpx(result, before_text="승인된 답변", include_visual=True)

            report = INTEGRITY.validate(source, result)

            self.assertEqual(report["status"], "PASS", report["errors"])
            self.assertTrue(report["sourceSectionOrderPreserved"])
            self.assertTrue(report["sections"][0]["fixedParagraphsPreserved"])
            self.assertTrue(
                report["sections"][0]["topLevelTableTopologyPreserved"]
            )
            self.assertTrue(report["sections"][0]["secPrPreserved"])

    def test_source_integrity_blocks_fixed_text_and_topology_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.hwpx"
            make_hwpx(source, include_visual=False)

            changed_text = root / "changed-text.hwpx"
            make_hwpx(
                changed_text,
                before_text="공식 질문을 바꾼 문장",
                include_visual=False,
            )
            report = INTEGRITY.validate(source, changed_text)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "fixed source paragraphs changed or reordered",
                "\n".join(report["errors"]),
            )

            changed_topology = root / "changed-topology.hwpx"
            make_hwpx(
                changed_topology,
                outer_row_count="2",
                include_visual=False,
            )
            report = INTEGRITY.validate(source, changed_topology)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "top-level table topology changed",
                "\n".join(report["errors"]),
            )

    def test_source_integrity_uses_exact_editable_anchors_and_fixed_literals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            source = root / "placeholder-source.hwpx"
            result = root / "placeholder-result.hwpx"
            make_hwpx(
                source,
                before_text="사업명: {사업명}",
                include_visual=False,
            )
            make_hwpx(
                result,
                before_text="고객명: 김다윤",
                include_visual=False,
            )
            report = INTEGRITY.validate(source, result)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "fixed source paragraphs changed or reordered",
                "\n".join(report["errors"]),
            )

            suffix_source = root / "suffix-source.hwpx"
            suffix_result = root / "suffix-result.hwpx"
            make_hwpx(
                suffix_source,
                before_text="사업명: {사업명} (필수)",
                include_visual=False,
            )
            make_hwpx(
                suffix_result,
                before_text="사업명: 김다윤 (선택)",
                include_visual=False,
            )
            report = INTEGRITY.validate(suffix_source, suffix_result)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "fixed source paragraphs changed or reordered",
                "\n".join(report["errors"]),
            )

            exact_source = root / "exact-source.hwpx"
            exact_result = root / "exact-result.hwpx"
            exact_spec = root / "editable.json"
            make_hwpx(
                exact_source,
                before_text="그림 1. 긴 승인 전 캡션",
                include_visual=False,
            )
            make_hwpx(
                exact_result,
                before_text="그림 1. 짧은 캡션",
                include_visual=False,
            )
            exact_spec.write_text(
                json.dumps(
                    {
                        "editableParagraphExact": [
                            "그림 1. 긴 승인 전 캡션"
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = INTEGRITY.validate(exact_source, exact_result, exact_spec)
            self.assertEqual(report["status"], "PASS", report["errors"])

            ambiguous_source = root / "ambiguous-source.hwpx"
            ambiguous_result = root / "ambiguous-result.hwpx"
            ambiguous_spec = root / "ambiguous.json"
            make_hwpx(
                ambiguous_source,
                caption="중복 캡션",
                duplicate_visual=True,
            )
            make_hwpx(
                ambiguous_result,
                caption="중복 캡션",
                duplicate_visual=True,
            )
            ambiguous_spec.write_text(
                json.dumps(
                    {"editableParagraphExact": ["중복 캡션"]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = INTEGRITY.validate(
                ambiguous_source,
                ambiguous_result,
                ambiguous_spec,
            )
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "editable paragraph anchor must match exactly once",
                "\n".join(report["errors"]),
            )

            missing_spec = root / "missing.json"
            missing_spec.write_text(
                json.dumps(
                    {"editableParagraphExact": ["원본에 없는 문단"]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            report = INTEGRITY.validate(
                exact_source,
                exact_result,
                missing_spec,
            )
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "editable paragraph anchor must match exactly once, got 0",
                "\n".join(report["errors"]),
            )

            reordered = root / "reordered.hwpx"
            make_hwpx(
                source,
                before_text="첫 번째 고정 문단",
                after_text="두 번째 고정 문단",
                include_visual=False,
            )
            make_hwpx(
                reordered,
                before_text="두 번째 고정 문단",
                after_text="첫 번째 고정 문단",
                include_visual=False,
            )
            report = INTEGRITY.validate(source, reordered)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "fixed source paragraphs changed or reordered",
                "\n".join(report["errors"]),
            )

            changed_secpr = root / "changed-secpr.hwpx"
            make_hwpx(
                changed_secpr,
                before_text="첫 번째 고정 문단",
                after_text="두 번째 고정 문단",
                left_margin="5000",
                include_visual=False,
            )
            report = INTEGRITY.validate(source, changed_secpr)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "secPr changed from source",
                "\n".join(report["errors"]),
            )

    def test_render_receipt_requires_bound_pdf_png_and_zoom_qa(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hwpx = root / "result.hwpx"
            pdf = root / "result.pdf"
            png = root / "page-01.png"
            receipt_path = root / "render-qa.json"
            make_hwpx(hwpx)

            document = fitz.open()
            document.new_page(width=595, height=842)
            document.save(pdf)
            document.close()
            Image.new("RGB", (595, 842), "white").save(png)

            receipt = {
                "schemaVersion": "1.0.0",
                "status": "PASS",
                "hwpxSha256": RENDER.sha256(hwpx),
                "renderer": {"name": "test-renderer", "version": "1.0"},
                "pdf": {
                    "path": pdf.name,
                    "sha256": RENDER.sha256(pdf),
                },
                "pages": [
                    {
                        "index": 1,
                        "png": png.name,
                        "sha256": RENDER.sha256(png),
                        "width": 595,
                        "height": 842,
                        "zoomReviewed": True,
                        "checks": {
                            "clipping": False,
                            "overlap": False,
                            "blankPage": False,
                            "lowContrast": False,
                            "orphanParagraph": False,
                            "captionSplit": False,
                        },
                    }
                ],
            }
            receipt_path.write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            report = RENDER.validate(hwpx, receipt_path)
            self.assertEqual(report["status"], "PASS", report["errors"])
            self.assertEqual(report["pdfPageCount"], 1)

            def assert_block(mutator, expected: str) -> None:
                changed = json.loads(json.dumps(receipt))
                mutator(changed)
                receipt_path.write_text(
                    json.dumps(changed, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                report = RENDER.validate(hwpx, receipt_path)
                self.assertEqual(report["status"], "BLOCK")
                self.assertIn(expected, "\n".join(report["errors"]))

            cases = [
                (
                    lambda payload: payload.__setitem__(
                        "hwpxSha256",
                        "sha256:" + "0" * 64,
                    ),
                    "HWPX digest is missing or stale",
                ),
                (
                    lambda payload: payload["pdf"].__setitem__(
                        "sha256",
                        "sha256:" + "0" * 64,
                    ),
                    "PDF digest is missing or stale",
                ),
                (
                    lambda payload: payload["pages"][0].__setitem__(
                        "sha256",
                        "sha256:" + "0" * 64,
                    ),
                    "PNG digest is missing or stale",
                ),
                (
                    lambda payload: payload["renderer"].pop("version"),
                    "renderer name and version are required",
                ),
                (
                    lambda payload: payload["pages"][0].__setitem__("width", 1),
                    "PNG dimensions are missing or stale",
                ),
                (
                    lambda payload: payload["pages"][0].__setitem__(
                        "zoomReviewed",
                        False,
                    ),
                    "requires 100-percent and zoom review",
                ),
                (
                    lambda payload: payload["pages"][0]["checks"].pop(
                        "captionSplit"
                    ),
                    "checks must contain exactly",
                ),
                (
                    lambda payload: payload["pages"][0].__setitem__("index", 2),
                    "indexes must be consecutive from 1",
                ),
                (
                    lambda payload: payload["pages"][0]["checks"].__setitem__(
                        "clipping",
                        True,
                    ),
                    "visual QA has a reported defect",
                ),
                (
                    lambda payload: payload["pages"].append(
                        {
                            **payload["pages"][0],
                            "index": 2,
                        }
                    ),
                    "PDF page count and page PNG count differ",
                ),
            ]
            for mutator, expected in cases:
                with self.subTest(expected=expected):
                    assert_block(mutator, expected)

            zero_pdf = root / "zero-page.pdf"
            payload = bytearray(b"%PDF-1.4\n")
            offsets = []
            for number, body in (
                (1, b"<< /Type /Catalog /Pages 2 0 R >>"),
                (2, b"<< /Type /Pages /Count 0 /Kids [] >>"),
            ):
                offsets.append(len(payload))
                payload.extend(
                    f"{number} 0 obj\n".encode("ascii")
                    + body
                    + b"\nendobj\n"
                )
            xref_offset = len(payload)
            payload.extend(b"xref\n0 3\n0000000000 65535 f \n")
            for offset in offsets:
                payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
            payload.extend(
                b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n"
                + str(xref_offset).encode("ascii")
                + b"\n%%EOF\n"
            )
            zero_pdf.write_bytes(payload)
            zero_receipt = json.loads(json.dumps(receipt))
            zero_receipt["pdf"] = {
                "path": zero_pdf.name,
                "sha256": RENDER.sha256(zero_pdf),
            }
            receipt_path.write_text(
                json.dumps(zero_receipt, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            report = RENDER.validate(hwpx, receipt_path)
            self.assertEqual(report["status"], "BLOCK")
            self.assertIn(
                "rendered PDF must contain at least one page",
                "\n".join(report["errors"]),
            )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
import warnings
from pathlib import Path
from xml.etree import ElementTree as ET


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


def load_module():
    spec = importlib.util.spec_from_file_location("hwpx_visuals", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = load_module()


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


def visual_table(caption: str) -> ET.Element:
    table = element("tbl", {"rowCnt": "2", "colCnt": "1"})
    table.append(element("sz", {"width": "45900", "height": "26000"}))

    image_row = element("tr")
    image_cell = element("tc", {"borderFillIDRef": "4"})
    image_list = element("subList")
    image_p = element("p", {"paraPrIDRef": "0"})
    image_run = element("run", {"charPrIDRef": "0"})
    picture = element("pic")
    picture.append(element("sz", {"width": "43900", "height": "24000"}))
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
    table.append(image_row)

    caption_row = element("tr")
    caption_cell = element("tc", {"borderFillIDRef": "15"})
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
    table.append(caption_row)
    return table


def header_xml() -> bytes:
    root = element("head")
    border = element("borderFill", {"id": "15"})
    brush = element("fillBrush")
    brush.append(element("winBrush", {"faceColor": "#F2F2F2"}))
    border.append(brush)
    root.append(border)

    char = element("charPr", {"id": "31", "height": "1200"})
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

    outer = element("tbl", {"rowCnt": "1", "colCnt": "1"})
    row = element("tr")
    cell = element("tc")
    sublist = element("subList")
    before = paragraph("시각자료가 설명하는 문단")
    after = paragraph("o 다음 핵심항목")
    def wrapped_visual() -> ET.Element:
        visual = visual_table(caption)
        if not hierarchy_ok:
            return visual
        visual_p = element("p", {"paraPrIDRef": "0"})
        visual_run = element("run", {"charPrIDRef": "0"})
        visual_run.append(visual)
        visual_p.append(visual_run)
        return visual_p

    visual_nodes = [wrapped_visual()]
    if duplicate_visual:
        visual_nodes.append(wrapped_visual())

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
                        "imageWidth": 43900,
                        "cellMargin": {"left": 510, "right": 510, "top": 220, "bottom": 220},
                        "captionRowHeight": 1200,
                        "captionPointSize": 12,
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
            self.assertEqual(visual["imageWidth"], "43900")
            self.assertEqual(visual["captionRowHeight"], "1200")
            self.assertEqual(visual["captionPointSize"], "12")
            self.assertTrue(visual["captionBold"])
            self.assertEqual(visual["captionAlign"], "CENTER")
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


if __name__ == "__main__":
    unittest.main()

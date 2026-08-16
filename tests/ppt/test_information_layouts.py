from __future__ import annotations

import os
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts"
SCENE = SCRIPTS / "scene-deck"
for path in (str(SCRIPTS), str(SCENE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import info_layouts as IL  # noqa: E402
import codex_parallel_gen as CG  # noqa: E402
import layout_engine as LE  # noqa: E402
from deck import Deck, _prepare_slide_outputs, _safe_receipt_valid  # noqa: E402


class InformationLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        IL.register()
        LE.FOOT = "regression"

    def test_seven_information_layouts_are_registered(self) -> None:
        for layout in ("TABLE", "EXAMPLE", "MATRIX", "BAR", "FLOW", "GENEALOGY", "PROMPT"):
            self.assertIn(layout, LE.LAY)

    def test_deck_exposes_flow_genealogy_and_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deck = Deck(out_dir=directory)
            deck.flow("FLOW", ["순서"], ["설명"], [("01", "입력", "근거"), ("02", "검증", "PASS")])
            deck.genealogy(
                "GENEALOGY",
                ["계보"],
                ["설명"],
                [("Prompt", "요청문", "지시"), ("Harness", "실행틀", "검증")],
            )
            deck.prompt("PROMPT", ["복사"], ["설명"], ["저장소를 확인해줘"], checks=["PASS"])
            deck.table(
                "TABLE",
                ["투사용 표"],
                ["본문 하한"],
                ["skill", "기능"],
                [["complete-business-plan", "전체 순서 총괄"]],
                font_sizes=[38, 36],
            )
            self.assertEqual(
                [slide["lay"] for slide in deck.slides],
                ["FLOW", "GENEALOGY", "PROMPT", "TABLE"],
            )

    def test_scene_prompt_enforces_four_direction_eighteen_percent_safety(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deck = Deck(out_dir=directory)
            deck.slide("A", "SCENE", ["제목"], ["설명"], scene="seven connected modules")
            prompt = deck.jobs()[0]["prompt"]
            self.assertIn("TOP, BOTTOM, LEFT, and RIGHT 18%", prompt)
            self.assertIn("central 64%", prompt)
            self.assertIn("no touching, cropping, or edge exits", prompt)
            job = deck.jobs()[0]
            self.assertEqual(job["safe_zone"], 0.18)
            self.assertTrue(job["safe_frame"])

    def test_new_layouts_render_and_genealogy_gutter_does_not_touch_cards(self) -> None:
        samples = [
            (
                "FLOW",
                {
                    "head": ["10단계"],
                    "sub": ["전문 workflow"],
                    "modules": [(f"{index:02d}", f"단계 {index}", "통과 조건") for index in range(1, 11)],
                    "cols": 5,
                },
            ),
            (
                "GENEALOGY",
                {
                    "head": ["실행 계보"],
                    "sub": ["번호와 카드 분리"],
                    "modules": [
                        ("Prompt Engineering", "요청문 설계", "지시"),
                        ("Context Engineering", "정보 설계", "정보"),
                        ("Harness Engineering", "실행 설계", "실행"),
                        ("Loop Engineering", "반복 설계", "반복"),
                        ("Graph Engineering", "관계 설계", "관계"),
                    ],
                    "highlight": 2,
                },
            ),
            (
                "PROMPT",
                {
                    "head": ["복사용 프롬프트"],
                    "sub": ["정확한 명령"],
                    "prompt": ["저장소를 확인해줘", "기존 설정은 덮어쓰지 마"],
                    "checks": ["버전", "enabled", "테스트"],
                },
            ),
            (
                "TABLE",
                {
                    "head": ["투사용 표"],
                    "sub": ["큰 본문"],
                    "columns": ["skill", "기능"],
                    "rows": [["complete-business-plan", "공고부터 발표까지 총괄"]],
                    "widths": [2, 4],
                    "font_sizes": [38],
                },
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for layout, data in samples:
                with self.subTest(layout=layout):
                    image = Image.new("RGB", (LE.W, LE.H), LE.WHITE)
                    draw = ImageDraw.Draw(image)
                    slide = {"eyebrow": layout, **data}
                    LE.LAY[layout](image, draw, slide)
                    output = Path(directory) / f"{layout}.png"
                    image.save(output)
                    self.assertGreater(output.stat().st_size, 10_000)

                    if layout == "GENEALOGY":
                        ytop = IL._body_top(draw, slide, gap=32, floor=.31)
                        row_h = min(
                            134,
                            (int(LE.H * IL.BODY_BOT) - ytop - 14 * 4) // 5,
                        )
                        sample_y = ytop + row_h // 2
                        gap_pixel = image.getpixel((LE.M + 86, sample_y))
                        self.assertEqual(gap_pixel, LE.WHITE)

    def test_information_layouts_fail_closed_on_projection_overflow(self) -> None:
        cases = [
            (
                "TABLE",
                {
                    "head": ["긴 표"],
                    "sub": ["분할 필요"],
                    "columns": ["구분", "내용"],
                    "rows": [[str(index), "설명 " * 30] for index in range(12)],
                    "font_sizes": [24],
                },
            ),
            (
                "FLOW",
                {
                    "head": ["긴 흐름"],
                    "sub": ["분할 필요"],
                    "modules": [("01", "끊김없는매우긴단계명" * 12, "검증")],
                    "cols": 1,
                },
            ),
            (
                "GENEALOGY",
                {
                    "head": ["긴 계보"],
                    "sub": ["분할 필요"],
                    "modules": [("Prompt", "끊김없는매우긴설명" * 30, "지시")],
                },
            ),
            (
                "TABLE",
                {
                    "head": ["긴 표 헤더"],
                    "sub": ["분할 필요"],
                    "columns": ["끊김없는매우긴헤더" * 40, "내용"],
                    "rows": [["구분", "검증"]],
                    "font_sizes": [24],
                },
            ),
            (
                "FLOW",
                {
                    "head": ["긴 흐름 주석"],
                    "sub": ["분할 필요"],
                    "modules": [("01", "입력", "근거")],
                    "cols": 1,
                    "footer_note": "투사용 하단 주석 " * 100,
                },
            ),
            (
                "GENEALOGY",
                {
                    "head": ["긴 계보 주석"],
                    "sub": ["분할 필요"],
                    "modules": [("Prompt", "요청", "지시")],
                    "note": "투사용 하단 주석 " * 100,
                },
            ),
            (
                "FLOW",
                {
                    "head": ["주석과 출처"],
                    "sub": ["세로 충돌 차단"],
                    "modules": [("01", "입력", "근거")],
                    "footer_note": "짧은 주석",
                    "source": "공식 출처",
                },
            ),
            (
                "GENEALOGY",
                {
                    "head": ["주석과 출처"],
                    "sub": ["세로 충돌 차단"],
                    "modules": [("Prompt", "요청", "지시")],
                    "note": "짧은 주석",
                    "source": "공식 출처",
                },
            ),
            (
                "PROMPT",
                {
                    "head": ["긴 프롬프트"],
                    "sub": ["분할 필요"],
                    "prompt": ["복사할 요청문 " * 300],
                    "checks": ["PASS"],
                },
            ),
        ]
        for layout, data in cases:
            with self.subTest(layout=layout):
                image = Image.new("RGB", (LE.W, LE.H), LE.WHITE)
                draw = ImageDraw.Draw(image)
                with self.assertRaises(ValueError):
                    LE.LAY[layout](image, draw, {"eyebrow": layout, **data})

    def test_scene_safe_zone_postprocessor_blocks_edges_and_emits_pass_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scene.png"
            image = Image.new("RGB", (1000, 1000), LE.WHITE)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 350, 240, 650), fill=LE.BLUE)
            image.save(path)

            before = CG.scene_safe_zone_receipt(path, 0.18)
            self.assertEqual(before["status"], "BLOCK")

            after = CG.frame_scene_safe_zone(path, 0.18)
            self.assertEqual(after["status"], "PASS")
            self.assertTrue(all(value >= 0.175 for value in after["margins"].values()))
            self.assertRegex(after["sha256"], r"^sha256:[0-9a-f]{64}$")
            CG.write_scene_safe_receipt(path, after)
            sidecar = Path(str(path) + ".safe.json")
            tampered = json.loads(sidecar.read_text(encoding="utf-8"))
            tampered["margins"] = {
                "left": 0.18,
                "top": 0.18,
                "right": 0.18,
                "bottom": 0.18,
            }
            tampered["foregroundBox"] = [180, 180, 820, 820]
            sidecar.write_text(json.dumps(tampered), encoding="utf-8")
            self.assertFalse(_safe_receipt_valid(path, 0.18))

    def test_shorter_rebuild_removes_only_stale_slide_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(1, 5):
                (root / f"slide_{index:02d}.png").write_bytes(b"slide")
            unrelated = root / "contact-sheet.png"
            unrelated.write_bytes(b"keep")
            slide_reference = root / "slide_reference.png"
            slide_reference.write_bytes(b"keep")

            _prepare_slide_outputs(root, 3)

            self.assertEqual(
                sorted(path.name for path in root.glob("slide_*.png")),
                ["slide_01.png", "slide_02.png", "slide_03.png", "slide_reference.png"],
            )
            self.assertTrue(unrelated.is_file())
            self.assertTrue(slide_reference.is_file())


if __name__ == "__main__":
    unittest.main()

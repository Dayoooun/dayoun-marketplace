from __future__ import annotations

import json
import sys
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
PPT_SCRIPTS = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
    / "scripts"
)
SCENE_DECK = PPT_SCRIPTS / "scene-deck"
for path in (PPT_SCRIPTS, SCENE_DECK):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import deck_qc  # noqa: E402
import layout_engine as layout  # noqa: E402
from deck import Deck  # noqa: E402


def object_scene(path: Path, box: tuple[int, int, int, int]) -> None:
    image = Image.new("RGB", (800, 600), (246, 240, 230))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(box, radius=36, fill=(52, 92, 112), outline=(22, 42, 54), width=6)
    image.save(path)


def slide(scene: str, layout_name: str, minimum=0.68, maximum=0.88) -> dict:
    return {
        "_sid": 1,
        "scene": scene,
        "sceneMode": "cutout",
        "sceneTarget": {
            "slot": "test",
            "minOccupancy": minimum,
            "maxOccupancy": maximum,
        },
        "sceneTransparent": False,
        "lay": layout_name,
    }


class SceneOccupancyTests(unittest.TestCase):
    def setUp(self) -> None:
        layout.clear_placement_receipts()

    def test_deck_spec_records_explicit_scene_modes_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            deck = Deck(out_dir=directory)
            deck.slide(
                "L",
                "OBJECT",
                ["큰 전경"],
                ["배경 사각형 없음"],
                scene="isolated object",
            )
            deck.slide(
                "W",
                "ENVIRONMENT",
                ["전체 장면"],
                ["배경 포함"],
                scene="wide environment",
            )
            cutout_slide, canvas_slide = deck.slides
            self.assertEqual(cutout_slide["sceneMode"], "cutout")
            self.assertEqual(
                cutout_slide["sceneTarget"]["minOccupancy"],
                0.68,
            )
            self.assertTrue(
                cutout_slide["sceneTarget"]["allowAspectAdjusted"]
            )
            self.assertEqual(canvas_slide["sceneMode"], "canvas")
            jobs = deck.jobs(only_missing=False)
            self.assertEqual(jobs[0]["scene_mode"], "cutout")
            self.assertEqual(jobs[1]["scene_mode"], "canvas")
            self.assertIn(
                "isolated foreground object group",
                jobs[0]["prompt"],
            )
            with self.assertRaisesRegex(ValueError, "requires"):
                deck.slide(
                    "L",
                    "BAD",
                    ["잘못된 조합"],
                    [],
                    scene="environment",
                    scene_mode="canvas",
                    scene_transparent=True,
                )

    def test_cutout_fills_cover_slot_without_exceeding_maximum(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            object_scene(root / "cover.png", (180, 120, 620, 500))
            previous = layout.SCN
            layout.SCN = str(root)
            canvas = Image.new("RGB", (layout.W, layout.H), "white")
            try:
                layout.place_scene_in_slot(
                    canvas,
                    slide("cover", "COVER", 0.70, 0.88),
                    "COVER",
                    (
                        int(layout.W * 0.51),
                        int(layout.H * 0.14),
                        int(layout.W * 0.46),
                        int(layout.H * 0.72),
                    ),
                    horizontal="right",
                )
            finally:
                layout.SCN = previous
            receipt = layout.placement_receipts()[0]
            self.assertGreaterEqual(receipt["areaOccupancy"], 0.70)
            self.assertLessEqual(receipt["areaOccupancy"], 0.882)
            self.assertEqual(receipt["collisions"], [])
            self.assertEqual(receipt["sceneMode"], "cutout")

    def test_extreme_aspect_ratio_below_target_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            object_scene(root / "tiny.png", (80, 270, 720, 315))
            previous = layout.SCN
            layout.SCN = str(root)
            try:
                with self.assertRaisesRegex(ValueError, "occupancy"):
                    layout.place_scene_in_slot(
                        Image.new("RGB", (layout.W, layout.H), "white"),
                        slide("tiny", "COVER", 0.70, 0.88),
                        "COVER",
                        (700, 250, 1100, 850),
                    )
            finally:
                layout.SCN = previous

    def test_text_and_footer_collision_slots_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            object_scene(root / "object.png", (170, 110, 630, 505))
            previous = layout.SCN
            layout.SCN = str(root)
            try:
                with self.assertRaisesRegex(ValueError, "text"):
                    layout.place_scene_in_slot(
                        Image.new("RGB", (layout.W, layout.H), "white"),
                        slide("object", "L"),
                        "L",
                        (int(layout.W * 0.30), 300, 900, 800),
                    )
                with self.assertRaisesRegex(ValueError, "footer-rule"):
                    layout.place_scene_in_slot(
                        Image.new("RGB", (layout.W, layout.H), "white"),
                        slide("object", "A", 0.20, 0.90),
                        "A",
                        (int(layout.W * 0.50), layout.BODY_BOT - 100, 900, 300),
                    )
            finally:
                layout.SCN = previous

    def test_canvas_mode_records_full_asset_without_cutout_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            object_scene(root / "environment.png", (100, 100, 700, 500))
            previous = layout.SCN
            layout.SCN = str(root)
            canvas = Image.new("RGB", (layout.W, layout.H), "white")
            canvas_slide = {
                "_sid": 2,
                "scene": "environment",
                "sceneMode": "canvas",
                "sceneTarget": {"slot": "bottom"},
                "lay": "W",
            }
            try:
                layout.place_scene_in_slot(
                    canvas,
                    canvas_slide,
                    "W",
                    (layout.M, 350, layout.W - layout.M * 2, 750),
                )
            finally:
                layout.SCN = previous
            receipt = layout.placement_receipts()[0]
            self.assertEqual(receipt["sceneMode"], "canvas")
            self.assertEqual(receipt["contentBBox"], [0, 0, 800, 600])

            strict_slide = dict(canvas_slide)
            strict_slide["sceneTarget"] = {
                "slot": "bottom",
                "minOccupancy": 0.72,
                "maxOccupancy": 0.92,
                "allowAspectAdjusted": False,
            }
            previous = layout.SCN
            layout.SCN = str(root)
            try:
                with self.assertRaisesRegex(ValueError, "occupancy"):
                    layout.place_scene_in_slot(
                        Image.new("RGB", (layout.W, layout.H), "white"),
                        strict_slide,
                        "W",
                        (layout.M, 350, layout.W - layout.M * 2, 750),
                    )
            finally:
                layout.SCN = previous

    def test_deck_qc_rejects_bad_placement_receipt(self) -> None:
        valid = {
            "placements": [
                {
                    "scene": "s01",
                    "sceneMode": "cutout",
                    "slot": [100, 100, 900, 800],
                    "placedBBox": [150, 120, 850, 760],
                    "areaOccupancy": 0.80,
                    "minOccupancy": 0.70,
                    "maxOccupancy": 0.88,
                    "aspectAdjusted": False,
                    "collisions": [],
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "placement.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            self.assertEqual(deck_qc.validate_placement_receipt(path), [])
            invalid = valid.copy()
            invalid["placements"] = [dict(valid["placements"][0])]
            invalid["placements"][0]["areaOccupancy"] = 0.30
            invalid["placements"][0]["collisions"] = ["footer-rule"]
            path.write_text(json.dumps(invalid), encoding="utf-8")
            errors = deck_qc.validate_placement_receipt(path)
            self.assertTrue(any("occupancy" in error for error in errors))
            self.assertTrue(any("collision" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

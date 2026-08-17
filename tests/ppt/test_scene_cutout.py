from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SCENE_DECK = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
    / "scripts"
    / "scene-deck"
)
PPT_SCRIPTS = SCENE_DECK.parent
if str(PPT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PPT_SCRIPTS))
if str(SCENE_DECK) not in sys.path:
    sys.path.insert(0, str(SCENE_DECK))

import cutout  # noqa: E402
import layout_engine as layout  # noqa: E402
from codex_parallel_gen import (  # noqa: E402
    frame_scene_safe_zone,
    scene_safe_zone_receipt,
    verify as verify_generated_scenes,
    write_scene_safe_receipt,
)
from deck import _safe_receipt_valid  # noqa: E402


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def opaque_object(path: Path, background=(246, 240, 230)) -> None:
    image = Image.new("RGB", (640, 480), background)
    draw = ImageDraw.Draw(image)
    draw.ellipse((205, 130, 455, 390), fill=(250, 250, 248), outline=(31, 50, 68), width=8)
    draw.ellipse((230, 330, 430, 405), fill=(112, 96, 72))
    draw.rounded_rectangle((250, 185, 410, 330), radius=28, fill=(235, 239, 232))
    image.save(path)


def checkerboard(path: Path) -> None:
    image = Image.new("RGB", (480, 360), "white")
    draw = ImageDraw.Draw(image)
    size = 24
    colors = ((224, 224, 224), (248, 248, 248))
    for y in range(0, image.height, size):
        for x in range(0, image.width, size):
            draw.rectangle(
                (x, y, x + size - 1, y + size - 1),
                fill=colors[(x // size + y // size) % 2],
            )
    draw.ellipse((150, 90, 330, 285), fill=(33, 72, 104))
    image.save(path)


class SceneCutoutTests(unittest.TestCase):
    def test_safe_sidecar_does_not_disable_opaque_ivory_crop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scene.png"
            opaque_object(source)
            report = cutout.analyze_scene(source)
            self.assertEqual(report["status"], "PASS", report)
            Path(str(source) + ".safe.json").write_text(
                json.dumps(
                    {
                        "status": "PASS",
                        "sha256": digest(source),
                        "contentBBox": report["contentBBox"],
                    }
                ),
                encoding="utf-8",
            )
            previous = layout.SCN
            layout.SCN = str(root)
            try:
                prepared, loaded_report = layout.scene("scene", mode="cutout")
            finally:
                layout.SCN = previous
            self.assertIsNotNone(prepared)
            self.assertEqual(prepared.mode, "RGBA")
            self.assertLess(prepared.width, 400)
            self.assertLess(prepared.height, 400)
            self.assertEqual(loaded_report["backgroundMode"], "opaque-uniform")
            alpha = np.asarray(prepared.getchannel("A"))
            self.assertEqual(int(alpha.min()), 0)
            self.assertEqual(int(alpha.max()), 255)

    def test_canvas_mode_preserves_entire_generated_background(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "scene.png"
            opaque_object(source)
            previous = layout.SCN
            layout.SCN = str(root)
            try:
                prepared, report = layout.scene("scene", mode="canvas")
            finally:
                layout.SCN = previous
            self.assertEqual(prepared.size, (640, 480))
            self.assertEqual(prepared.mode, "RGB")
            self.assertEqual(report["contentBBox"], [0, 0, 640, 480])

    def test_safe_receipt_binds_unframed_source_artifact_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rendered = root / "scene.png"
            source = root / "scene.png.source.png"
            opaque_object(source)
            opaque_object(rendered)
            report = scene_safe_zone_receipt(rendered, 0.18)
            source_report = cutout.analyze_scene(source)
            report.update(
                {
                    "sceneMode": "cutout",
                    "transparencyRequested": False,
                    "contentErrors": [],
                    "preFrameContentBBox": source_report["contentBBox"],
                    "preFrameBackgroundMode": source_report["backgroundMode"],
                    "sourceArtifact": source.name,
                    "sourceSha256": digest(source),
                }
            )
            write_scene_safe_receipt(rendered, report)
            self.assertTrue(_safe_receipt_valid(rendered, 0.18))
            receipt = json.loads(
                Path(str(rendered) + ".safe.json").read_text(encoding="utf-8")
            )
            receipt["sourceArtifact"] = rendered.name
            write_scene_safe_receipt(rendered, receipt)
            self.assertFalse(_safe_receipt_valid(rendered, 0.18))
            receipt["sourceArtifact"] = source.name
            write_scene_safe_receipt(rendered, receipt)
            source.write_bytes(source.read_bytes() + b"tampered")
            self.assertFalse(_safe_receipt_valid(rendered, 0.18))

    def test_safe_framing_preserves_semitransparent_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alpha.png"
            image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.rectangle((40, 40, 160, 160), fill=(70, 170, 180, 160))
            image.save(path)
            receipt = frame_scene_safe_zone(path, 0.18)
            self.assertEqual(receipt["status"], "PASS")
            framed = np.asarray(Image.open(path).convert("RGBA"))
            self.assertIn(160, set(np.unique(framed[:, :, 3]).tolist()))

    def test_fake_alpha_and_alpha_padded_checkerboard_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_alpha = Image.new("RGBA", (480, 360), (246, 246, 246, 254))
            draw = ImageDraw.Draw(fake_alpha)
            draw.ellipse((150, 90, 330, 285), fill=(33, 72, 104, 254))
            fake_alpha_path = root / "alpha-254.png"
            fake_alpha.save(fake_alpha_path)
            fake_report = cutout.analyze_scene(fake_alpha_path)
            self.assertEqual(fake_report["status"], "BLOCK")
            self.assertTrue(
                any("span 0 through 255" in error for error in fake_report["errors"])
            )

            padded = Image.new("RGBA", (480, 360), (0, 0, 0, 0))
            padded_draw = ImageDraw.Draw(padded)
            tile = 24
            colors = ((224, 224, 224, 255), (248, 248, 248, 255))
            for y in range(48, 312, tile):
                for x in range(72, 408, tile):
                    padded_draw.rectangle(
                        (x, y, x + tile - 1, y + tile - 1),
                        fill=colors[(x // tile + y // tile) % 2],
                    )
            padded_draw.ellipse((160, 95, 320, 285), fill=(33, 72, 104, 255))
            padded_path = root / "alpha-checker.png"
            padded.save(padded_path)
            padded_report = cutout.analyze_scene(padded_path)
            self.assertEqual(padded_report["status"], "BLOCK")
            self.assertTrue(padded_report["checkerboardDetected"])

    def test_uniform_rim_with_textured_interior_background_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "uniform-rim.png"
            image = Image.new("RGB", (500, 400), "white")
            draw = ImageDraw.Draw(image)
            for y in range(18, 382):
                shade = 205 + (y % 40)
                draw.line((18, y, 482, y), fill=(shade, 225, 238))
            draw.rounded_rectangle(
                (180, 110, 320, 310),
                radius=35,
                fill=(40, 85, 110),
            )
            image.save(path)
            report = cutout.analyze_scene(path)
            self.assertEqual(report["status"], "BLOCK")
            self.assertTrue(
                any("excessive interior" in error for error in report["errors"])
            )
    def test_verify_blocks_preexisting_transparency_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "scene.png"
            image = Image.new("RGB", (600, 600), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((180, 180, 420, 420), fill=(20, 60, 90))
            image.save(output, compress_level=0)
            bad = verify_generated_scenes(
                [
                    {
                        "label": "s01",
                        "out": output.name,
                        "prompt": "transparent isolated object",
                        "safe_zone": 0.18,
                        "scene_mode": "cutout",
                        "requested_transparent": True,
                    }
                ],
                root,
            )
            self.assertIn("s01", bad)
            self.assertIn("cutout-validation", bad["s01"])
    def test_transparency_request_requires_real_alpha_range_and_border(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rgb_path = root / "rgb.png"
            opaque_object(rgb_path)
            rgb = cutout.analyze_scene(rgb_path, requested_transparent=True)
            self.assertEqual(rgb["status"], "BLOCK")
            self.assertTrue(
                any("alpha channel" in error for error in rgb["errors"])
            )

            opaque_rgba = Image.open(rgb_path).convert("RGBA")
            opaque_rgba_path = root / "opaque-rgba.png"
            opaque_rgba.save(opaque_rgba_path)
            all_opaque = cutout.analyze_scene(
                opaque_rgba_path,
                requested_transparent=True,
            )
            self.assertEqual(all_opaque["status"], "BLOCK")
            self.assertTrue(any("span 0 through 255" in error for error in all_opaque["errors"]))

            transparent = Image.new("RGBA", (480, 360), (0, 0, 0, 0))
            draw = ImageDraw.Draw(transparent)
            draw.ellipse((135, 95, 345, 315), fill=(46, 88, 112, 255))
            valid_path = root / "valid.png"
            transparent.save(valid_path)
            valid = cutout.analyze_scene(valid_path, requested_transparent=True)
            self.assertEqual(valid["status"], "PASS", valid)
            self.assertGreaterEqual(valid["alpha"]["transparentBorderRatio"], 0.95)

    def test_painted_checkerboard_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "checker.png"
            checkerboard(source)
            report = cutout.analyze_scene(source)
            self.assertEqual(report["status"], "BLOCK")
            self.assertTrue(report["checkerboardDetected"])
            with self.assertRaisesRegex(ValueError, "checkerboard"):
                cutout.cutout_scene(source)

    def test_white_ceramic_interior_and_translucent_shadow_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ceramic_path = root / "ceramic.png"
            image = Image.new("RGB", (500, 400), (255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.ellipse((115, 90, 385, 345), fill=(255, 255, 255), outline=(30, 45, 58), width=10)
            image.save(ceramic_path)
            ceramic, _report = cutout.cutout_scene(ceramic_path)
            alpha = np.asarray(ceramic.getchannel("A"))
            self.assertEqual(int(alpha[alpha.shape[0] // 2, alpha.shape[1] // 2]), 255)

            gel_path = root / "gel.png"
            gel = Image.new("RGBA", (500, 400), (0, 0, 0, 0))
            gel_draw = ImageDraw.Draw(gel)
            gel_draw.ellipse((105, 275, 395, 355), fill=(45, 62, 73, 80))
            gel_draw.rounded_rectangle((155, 95, 345, 310), radius=48, fill=(74, 174, 185, 160))
            gel_draw.rectangle((205, 125, 295, 170), fill=(230, 246, 245, 255))
            gel.save(gel_path)
            prepared, report = cutout.cutout_scene(
                gel_path,
                requested_transparent=True,
            )
            values = set(np.unique(np.asarray(prepared.getchannel("A"))).tolist())
            self.assertEqual(report["status"], "PASS")
            self.assertIn(80, values)
            self.assertIn(160, values)
            self.assertIn(255, values)


if __name__ == "__main__":
    unittest.main()

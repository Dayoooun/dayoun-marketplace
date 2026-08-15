from __future__ import annotations

import copy
import inspect
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "ocr"))

from approved_inputs import (  # noqa: E402
    ApprovalError,
    IMAGE_RENDERER_VERSION,
    build_approval_envelope,
    build_image_render_receipt,
    store_value,
    verify_approval_bundle,
    verify_image_render_receipt,
)
from build_visible_text_manifest import ManifestError, build_manifest  # noqa: E402
from validate_visible_text import validate_pair, validate_surface  # noqa: E402

DIGEST = "sha256:" + "1" * 64


class OcrContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = {
            "schemaVersion": "1.0.0",
            "projectId": "demo",
            "normalizerVersion": "dayoun-visible-text-v1",
            "mapperVersion": "dayoun-region-map-v1",
            "entries": [
                {"textId": "label", "briefIndex": 1, "slide": 1, "occurrence": 1, "text": "매출", "tokenKind": "label", "region": [0.1, 0.1, 0.4, 0.3]},
                {"textId": "value", "briefIndex": 1, "slide": 1, "occurrence": 1, "text": "910만원", "tokenKind": "value", "region": [0.5, 0.1, 0.9, 0.3]},
            ],
            "relations": [{"relationId": "r1", "kind": "label-value", "geometry": "same-row-left-to-right", "fromTextId": "label", "toTextId": "value"}],
        }
        self.toolchain = {
            name: {"version": "locked", "digest": DIGEST}
            for name in ("rasterizer", "ocrExecutable", "ocrModel", "languagePack", "normalizer", "mapper")
        }
        self.ocr = {
            "artifactDigest": DIGEST,
            "pageCount": 1,
            "pageRasterDigests": [DIGEST],
            "toolchain": self.toolchain,
            "detections": [
                {"detectionId": "d1", "slide": 1, "text": "매출", "confidence": 0.999, "region": [0.12, 0.12, 0.3, 0.2], "alternatives": [], "clipped": False, "tofu": False},
                {"detectionId": "d2", "slide": 1, "text": "910만원", "confidence": 0.999, "region": [0.55, 0.12, 0.8, 0.2], "alternatives": [], "clipped": False, "tofu": False},
            ],
        }

    def validate(self, ocr: dict) -> dict:
        return validate_surface(
            self.manifest,
            ocr,
            surface="PPTX",
            approval_envelope_digest=DIGEST,
            visible_manifest_digest=DIGEST,
            artifact_digest=DIGEST,
        )
    def image_brief(self) -> dict:
        return {
            "slides": [
                {
                    "slide": 1,
                    "visibleText": copy.deepcopy(self.manifest["entries"]),
                    "relations": copy.deepcopy(self.manifest["relations"]),
                }
            ]
        }


    def test_exact_visible_text_and_relation_pass(self) -> None:
        result = self.validate(self.ocr)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(validate_pair(result, copy.deepcopy(result)), [])

    def test_one_glyph_and_swapped_value_block(self) -> None:
        glyph = copy.deepcopy(self.ocr)
        glyph["detections"][0]["text"] = "매츨"
        self.assertEqual(self.validate(glyph)["status"], "AUTO_BLOCK")
        swapped = copy.deepcopy(self.ocr)
        swapped["detections"][0]["text"] = "910만원"
        swapped["detections"][1]["text"] = "매출"
        blockers = self.validate(swapped)["blockers"]
        self.assertIn("text-mismatch:label", blockers)
        self.assertIn("text-mismatch:value", blockers)

    def test_uncertain_missing_and_clipped_detection_block(self) -> None:
        for mutation in ("confidence", "alternatives", "clipped", "tofu"):
            ocr = copy.deepcopy(self.ocr)
            if mutation == "confidence":
                ocr["detections"][0][mutation] = 0.989
            elif mutation == "alternatives":
                ocr["detections"][0][mutation] = ["매츨"]
            else:
                ocr["detections"][0][mutation] = True
            self.assertEqual(self.validate(ocr)["status"], "AUTO_BLOCK")
        missing = copy.deepcopy(self.ocr)
        missing["detections"].pop()
        self.assertEqual(self.validate(missing)["status"], "AUTO_BLOCK")

    def test_stale_ocr_and_non_finite_confidence_block(self) -> None:
        stale = copy.deepcopy(self.ocr)
        stale["artifactDigest"] = "sha256:" + "b" * 64
        self.assertIn(
            "ocr-artifact-digest-mismatch",
            self.validate(stale)["blockers"],
        )
        non_finite = copy.deepcopy(self.ocr)
        non_finite["detections"][0]["confidence"] = float("nan")
        self.assertTrue(
            any(
                blocker.startswith("invalid-confidence:")
                for blocker in self.validate(non_finite)["blockers"]
            )
        )

    def test_render_receipt_blocks_same_count_png_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            png_dir = root / "png"
            png_dir.mkdir()
            image = png_dir / "slide_01.png"
            image.write_bytes(b"approved-pixels")
            payload = {"projectId": "demo", "outputs": {"hwpx": False, "ppt": True}}
            briefs = [self.image_brief()]
            envelope = build_approval_envelope(
                payload=payload,
                deck_briefs=briefs,
                visible_manifest=self.manifest,
                renderer_mode="image-first",
                approved_by="owner",
                approval_revision=1,
                cycle_id="cycle-render",
                renderer_version=IMAGE_RENDERER_VERSION,
            )
            for value in (payload, briefs[0], self.manifest):
                store_value(store, value)
            approval_digest = store_value(store, envelope)
            receipt = build_image_render_receipt(
                store=store,
                approval_digest=approval_digest,
                png_dir=png_dir,
            )
            verify_image_render_receipt(
                receipt,
                approval_digest=approval_digest,
                png_dir=png_dir,
                expected_slide_ids=["1:1"],
            )
            image.write_bytes(b"substituted-pixels")
            with self.assertRaises(ApprovalError):
                verify_image_render_receipt(
                    receipt,
                    approval_digest=approval_digest,
                    png_dir=png_dir,
                    expected_slide_ids=["1:1"],
                )
    def test_post_approval_manifest_or_brief_mutation_is_stale(self) -> None:
        payload = {"projectId": "demo", "outputs": {"hwpx": False, "ppt": True}}
        briefs = [self.image_brief()]
        envelope = build_approval_envelope(
            payload=payload,
            deck_briefs=briefs,
            visible_manifest=self.manifest,
            renderer_mode="image-first",
            approved_by="owner",
            approval_revision=1,
            cycle_id="cycle-1",
            renderer_version="1",
        )
        verify_approval_bundle(
            envelope,
            payload=payload,
            deck_briefs=briefs,
            visible_manifest=self.manifest,
            expected_mode="image-first",
        )
        changed = copy.deepcopy(self.manifest)
        changed["entries"][1]["text"] = "911만원"
        with self.assertRaises(ApprovalError):
            verify_approval_bundle(
                envelope,
                payload=payload,
                deck_briefs=briefs,
                visible_manifest=changed,
                expected_mode="image-first",
            )


    def test_visible_text_oracle_requires_normalized_regions(self) -> None:
        briefs = [{"slides": [{"slide": 1, "visibleText": [{"text": "매출"}]}]}]
        with self.assertRaises(ManifestError):
            build_manifest({"projectId": "demo"}, briefs)

    def test_manifest_rejects_empty_duplicate_or_noncontiguous_slides(self) -> None:
        item = {
            "textId": "title",
            "text": "제목",
            "tokenKind": "label",
            "region": [0.1, 0.1, 0.9, 0.2],
        }
        invalid_briefs = [
            [{"slides": [{"slide": 1, "visibleText": []}]}],
            [
                {"slides": [{"slide": 1, "visibleText": [item]}]},
                {"slides": [{"slide": 1, "visibleText": [{**item, "textId": "other"}]}]},
            ],
            [{"slides": [{"slide": 2, "visibleText": [item]}]}],
        ]
        for briefs in invalid_briefs:
            with self.subTest(briefs=briefs), self.assertRaises(ManifestError):
                build_manifest({"projectId": "demo"}, briefs)

    def test_renderer_mode_must_match_selected_ppt_output(self) -> None:
        payload = {"projectId": "demo", "outputs": {"hwpx": False, "ppt": False}}
        with self.assertRaises(ApprovalError):
            build_approval_envelope(
                payload=payload,
                deck_briefs=[self.image_brief()],
                visible_manifest=self.manifest,
                renderer_mode="image-first",
                approved_by="owner",
                approval_revision=1,
                cycle_id="C1",
                renderer_version=IMAGE_RENDERER_VERSION,
            )
    def test_ppt_approval_api_has_no_hwpx_prerequisite(self) -> None:
        parameters = inspect.signature(build_approval_envelope).parameters
        self.assertNotIn("hwpx", parameters)
        source = (SCRIPTS / "approved_inputs.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("hwpx", source)

if __name__ == "__main__":
    unittest.main()

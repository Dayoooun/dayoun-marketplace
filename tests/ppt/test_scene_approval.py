from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from jsonschema import Draft202012Validator
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "scene-deck"))

from approved_inputs import (  # noqa: E402
    ApprovalError,
    SCENE_RENDERER_VERSION,
    build_approval_envelope,
    digest_value,
    store_value,
    sha256_file,
)
from deck import Deck  # noqa: E402
from codex_parallel_gen import scene_safe_zone_receipt, write_scene_safe_receipt  # noqa: E402
from cutout import analyze_scene  # noqa: E402


class SceneApprovalTests(unittest.TestCase):
    def test_scene_render_spec_is_bound_to_approval_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = root / "store"
            deck = Deck(domain="it", title="approved", out_dir=root / "deck")
            deck.slide("L", "FACT", ["승인 문구"], ["근거 E1"], scene="approved-scene")
            payload = {"projectId": "demo", "outputs": {"hwpx": False, "ppt": True}}
            brief = {
                "sceneDeckSlides": copy.deepcopy(deck.slides),
                "sceneDeckConfig": copy.deepcopy(deck.approval_config()),
            }
            envelope = build_approval_envelope(
                payload=payload,
                deck_briefs=[brief],
                visible_manifest=None,
                renderer_mode="scene-deck",
                approved_by="owner",
                approval_revision=1,
                cycle_id="cycle-scene",
                renderer_version=SCENE_RENDERER_VERSION,
            )
            store_value(store, payload)
            store_value(store, brief)
            digest = store_value(store, envelope)
            deck._require_approved(digest, store)
            deck.slides[0]["head"][0] = "승인 뒤 변조"
            with self.assertRaises(ApprovalError):
                deck._require_approved(digest, store)

    def test_scene_v3_receipt_schemas_accept_bound_placement(self) -> None:
        schemas = ROOT / "contracts" / "schemas"
        digest = "sha256:" + "a" * 64
        placement = {
            "slideId": 1,
            "scene": "s01",
            "layout": "COVER",
            "sceneMode": "cutout",
            "slot": [100, 100, 900, 800],
            "placedBBox": [120, 110, 880, 780],
            "contentBBox": [200, 150, 700, 550],
            "sourceSha256": digest,
            "areaOccupancy": 0.80,
            "widthOccupancy": 0.95,
            "heightOccupancy": 0.84,
            "minOccupancy": 0.70,
            "maxOccupancy": 0.88,
            "aspectAdjusted": False,
            "allowAspectAdjusted": True,
            "collisions": [],
        }
        placement_receipt = {
            "schemaVersion": "1.0.0",
            "approvalEnvelopeDigest": digest,
            "rendererVersion": SCENE_RENDERER_VERSION,
            "slideSpecDigest": digest,
            "sceneReceiptSha256": digest,
            "placements": [placement],
        }
        output_receipt = {
            "schemaVersion": "1.0.0",
            "approvalEnvelopeDigest": digest,
            "rendererVersion": SCENE_RENDERER_VERSION,
            "slides": [{"fileName": "slide_01.png", "sha256": digest}],
            "scenePlacementReceiptSha256": digest,
            "sceneReceiptSha256": digest,
            "scenePlacements": [placement],
        }
        for name, value in (
            ("scene-placement-receipt.schema.json", placement_receipt),
            ("deck-output-receipt.schema.json", output_receipt),
        ):
            schema = json.loads((schemas / name).read_text(encoding="utf-8"))
            errors = list(Draft202012Validator(schema).iter_errors(value))
            self.assertEqual(errors, [], [error.message for error in errors])

    def test_scene_job_receipt_requires_unframed_source_binding(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = Deck(out_dir=root)
            deck.slide(
                "L",
                "OBJECT",
                ["전경"],
                [],
                scene="isolated object",
            )
            scene_root = root / "scenes"
            scene_root.mkdir()
            output = scene_root / "s01.png"
            image = Image.new("RGB", (600, 600), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((180, 180, 420, 420), fill=(20, 60, 90))
            image.save(output)
            receipt = scene_safe_zone_receipt(output, 0.18)
            receipt.update(
                {
                    "sceneMode": "cutout",
                    "transparencyRequested": False,
                    "contentErrors": [],
                }
            )
            receipt["jobPromptDigest"] = digest_value(
                deck.jobs(only_missing=False)[0]["prompt"]
            )
            write_scene_safe_receipt(output, receipt)
            with self.assertRaisesRegex(ApprovalError, "unframed-source"):
                deck._scene_job_record(deck.jobs(only_missing=False)[0])


    def test_assembled_slide_receipt_blocks_pixel_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = Deck(domain="it", title="receipt", out_dir=root)
            output = root / "out"
            output.mkdir()
            slide = output / "slide_01.png"
            slide.write_bytes(b"approved-slide")
            approval_digest = "sha256:" + "a" * 64
            placement_receipt = {
                "schemaVersion": "1.0.0",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "slideSpecDigest": digest_value(deck.slides),
                "sceneReceiptSha256": None,
                "placements": [],
            }
            Path(deck._placement_receipt_path()).write_text(
                json.dumps(placement_receipt),
                encoding="utf-8",
            )
            receipt = {
                "schemaVersion": "1.0.0",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "slides": deck._output_records(),
                "scenePlacementReceiptSha256": (
                    "sha256:"
                    + hashlib.sha256(
                        Path(deck._placement_receipt_path()).read_bytes()
                    ).hexdigest()
                ),
                "scenePlacements": [],
                "sceneReceiptSha256": None,
            }
            Path(deck._output_receipt_path()).write_text(
                json.dumps(receipt),
                encoding="utf-8",
            )
            deck._verify_output_receipt(approval_digest)
            slide.write_bytes(b"substituted-slide")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)

    def test_output_verification_rejects_every_scene_chain_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = Deck(out_dir=root)
            deck.slide(
                "L",
                "OBJECT",
                ["전경"],
                [],
                scene="isolated object",
            )
            job = deck.jobs(only_missing=False)[0]
            scenes = root / "scenes"
            scenes.mkdir(exist_ok=True)
            framed = scenes / "s01.png"
            source = scenes / "s01.png.source.png"
            image = Image.new("RGB", (600, 600), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((180, 180, 420, 420), fill=(20, 60, 90))
            image.save(framed, compress_level=0)
            image.save(source, compress_level=0)
            safe = scene_safe_zone_receipt(framed, 0.18)
            source_report = analyze_scene(source)
            safe.update(
                {
                    "sceneMode": "cutout",
                    "transparencyRequested": False,
                    "contentErrors": [],
                    "sourceArtifact": source.name,
                    "sourceSha256": sha256_file(source),
                    "preFrameContentBBox": source_report["contentBBox"],
                    "preFrameBackgroundMode": source_report["backgroundMode"],
                    "jobPromptDigest": digest_value(job["prompt"]),
                }
            )
            write_scene_safe_receipt(framed, safe)
            approval_digest = "sha256:" + "a" * 64
            scene_receipt = {
                "schemaVersion": "1.0.0",
                "receiptVersion": "dayoun-scene-render-receipt-v3",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "scenes": [deck._scene_job_record(job)],
            }
            scene_path = Path(deck._scene_receipt_path())
            scene_path.write_text(json.dumps(scene_receipt), encoding="utf-8")
            placement = {
                "slideId": 1,
                "scene": "s01",
                "layout": "L",
                "sceneMode": "cutout",
                "slot": [100, 100, 900, 800],
                "placedBBox": [120, 120, 880, 780],
                "contentBBox": source_report["contentBBox"],
                "sourceSha256": sha256_file(framed),
                "areaOccupancy": 0.80,
                "widthOccupancy": 0.95,
                "heightOccupancy": 0.84,
                "minOccupancy": 0.68,
                "maxOccupancy": 0.88,
                "allowAspectAdjusted": True,
                "aspectAdjusted": False,
                "collisions": [],
            }
            placement_receipt = {
                "schemaVersion": "1.0.0",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "slideSpecDigest": digest_value(deck.slides),
                "sceneReceiptSha256": sha256_file(scene_path),
                "placements": [placement],
            }
            placement_path = Path(deck._placement_receipt_path())
            placement_path.write_text(
                json.dumps(placement_receipt),
                encoding="utf-8",
            )
            output_root = root / "out"
            output_root.mkdir()
            slide = output_root / "slide_01.png"
            slide.write_bytes(b"approved-slide")
            output_receipt = {
                "schemaVersion": "1.0.0",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "slides": deck._output_records(),
                "scenePlacementReceiptSha256": sha256_file(placement_path),
                "scenePlacements": [placement],
                "sceneReceiptSha256": sha256_file(scene_path),
            }
            output_path = Path(deck._output_receipt_path())
            output_path.write_text(json.dumps(output_receipt), encoding="utf-8")
            deck._verify_output_receipt(approval_digest)

            source_bytes = source.read_bytes()
            source.write_bytes(source_bytes + b"tampered")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            source.write_bytes(source_bytes)

            sidecar = Path(str(framed) + ".safe.json")
            sidecar_bytes = sidecar.read_bytes()
            sidecar.write_bytes(sidecar_bytes + b" ")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            sidecar.write_bytes(sidecar_bytes)

            scene_bytes = scene_path.read_bytes()
            scene_path.write_bytes(scene_bytes + b" ")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            scene_path.write_bytes(scene_bytes)

            placement_bytes = placement_path.read_bytes()
            placement_path.write_bytes(placement_bytes + b" ")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            placement_path.write_bytes(placement_bytes)

            slide_bytes = slide.read_bytes()
            slide.write_bytes(slide_bytes + b"tampered")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            slide.write_bytes(slide_bytes)

            output_bytes = output_path.read_bytes()
            changed_output = dict(output_receipt)
            changed_output["rendererVersion"] = "stale"
            output_path.write_text(json.dumps(changed_output), encoding="utf-8")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
            output_path.write_bytes(output_bytes)
if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "scene-deck"))

from approved_inputs import (  # noqa: E402
    ApprovalError,
    SCENE_RENDERER_VERSION,
    build_approval_envelope,
    store_value,
)
from deck import Deck  # noqa: E402


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


    def test_assembled_slide_receipt_blocks_pixel_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            deck = Deck(domain="it", title="receipt", out_dir=root)
            output = root / "out"
            output.mkdir()
            slide = output / "slide_01.png"
            slide.write_bytes(b"approved-slide")
            approval_digest = "sha256:" + "a" * 64
            receipt = {
                "schemaVersion": "1.0.0",
                "approvalEnvelopeDigest": approval_digest,
                "rendererVersion": SCENE_RENDERER_VERSION,
                "slides": deck._output_records(),
            }
            Path(deck._output_receipt_path()).write_text(
                json.dumps(receipt),
                encoding="utf-8",
            )
            deck._verify_output_receipt(approval_digest)
            slide.write_bytes(b"substituted-slide")
            with self.assertRaises(ApprovalError):
                deck._verify_output_receipt(approval_digest)
if __name__ == "__main__":
    unittest.main()

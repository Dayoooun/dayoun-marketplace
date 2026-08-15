# -*- coding: utf-8 -*-
"""ppt-editorial 요구사항 인터뷰와 운영체제 호환성 회귀 테스트."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = str(REPO_ROOT / "plugins" / "business-plan-writer" / "skills" / "ppt-editorial" / "scripts")
SCENE = os.path.join(HERE, "scene-deck")
for path in (HERE, SCENE):
    if path not in sys.path:
        sys.path.insert(0, path)


class IntakeTests(unittest.TestCase):
    def test_sparse_request_asks_at_most_three_core_questions(self) -> None:
        from intake import assess

        result = assess({"title": "신제품 발표"})
        self.assertEqual(result["phase"], "intake")
        self.assertFalse(result["ready"])
        self.assertGreater(len(result["questions"]), 0)
        self.assertLessEqual(len(result["questions"]), 3)
        question_ids = {q["id"] for q in result["questions"]}
        self.assertNotIn("brightness", question_ids)
        self.assertNotIn("style_route", question_ids)

    def test_complete_request_stops_at_confirmation_gate(self) -> None:
        from intake import assess

        result = assess({
            "title": "사업계획 발표",
            "purpose": "pitch",
            "audience": "지원사업 심사위원",
            "delivery_context": "10분 발표 후 질의응답",
            "duration_minutes": 10,
            "source_materials": [],
            "identity_anchors": ["회사명", "제품명"],
        })
        self.assertEqual(result["phase"], "confirmation")
        self.assertFalse(result["ready"])
        self.assertTrue(result["baseline"]["recommended_mode"])
        self.assertIn("확인", result["confirmation_prompt"])

    def test_confirmed_request_is_ready_and_keeps_corrections(self) -> None:
        from intake import apply_answers, assess, require_confirmed

        brief = {
            "title": "사업계획 발표",
            "purpose": "pitch",
            "audience": "지원사업 심사위원",
            "delivery_context": "10분 발표",
            "duration_minutes": 10,
            "source_materials": [],
            "identity_anchors": [],
        }
        corrected = apply_answers(
            brief,
            {"audience": "투자심사역", "must_avoid": ["근거 없는 시장수치"]},
            confirm=True,
        )
        result = assess(corrected)
        self.assertTrue(result["ready"])
        self.assertEqual(result["phase"], "ready")
        normalized = require_confirmed(corrected)
        self.assertEqual(normalized["audience"], "투자심사역")
        self.assertEqual(normalized["language"], "ko")

    def test_markdown_brief_round_trip_uses_json_fence(self) -> None:
        from intake import load_brief, save_brief

        brief = {
            "title": "강의 덱",
            "purpose": "lecture",
            "audience": "수강생",
            "delivery_context": "20분 강의",
            "duration_minutes": 20,
            "source_materials": [],
            "identity_anchors": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "deck_brief.md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("# deck_brief.md\n\n```json\n")
                json.dump(brief, handle, ensure_ascii=False, indent=2)
                handle.write("\n```\n")
            self.assertEqual(load_brief(path)["title"], "강의 덱")
            brief["requirements_confirmed"] = True
            save_brief(path, brief)
            self.assertTrue(load_brief(path)["requirements_confirmed"])

    def test_editable_text_requirement_requires_output_caveat_acceptance(self) -> None:
        from intake import assess

        brief = {
            "title": "편집 요구 덱",
            "purpose": "report",
            "audience": "고객",
            "delivery_context": "파일 제출",
            "slide_count": 8,
            "source_materials": [],
            "identity_anchors": [],
            "editable_text_required": True,
        }
        result = assess(brief)
        self.assertIn("output_editability", result["missing"])
        brief["flattened_pptx_accepted"] = True
        self.assertEqual(assess(brief)["phase"], "confirmation")
    def test_deck_from_brief_rejects_unconfirmed_requirements(self) -> None:
        from deck import Deck
        from intake import IntakeBlocked

        brief = {
            "title": "확인 전 덱",
            "purpose": "lecture",
            "audience": "수강생",
            "delivery_context": "30분 강의",
            "duration_minutes": 30,
            "source_materials": [],
            "identity_anchors": [],
        }
        with self.assertRaises(IntakeBlocked):
            Deck.from_brief(brief)

        brief["requirements_confirmed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            deck = Deck.from_brief(brief, out_dir=tmp)
            self.assertEqual(deck.title, "확인 전 덱")
            with open(deck.save(), encoding="utf-8") as handle:
                spec = json.load(handle)
            self.assertTrue(spec["brief"]["requirements_confirmed"])


class PlatformTests(unittest.TestCase):
    def test_macos_font_directories_and_process_group(self) -> None:
        from platform_support import font_dirs, process_group_kwargs

        dirs = font_dirs(system="Darwin", home="/Users/test", existing_only=False)
        self.assertIn("/Users/test/Library/Fonts", dirs)
        self.assertIn("/System/Library/Fonts", dirs)
        self.assertEqual(process_group_kwargs(system="Darwin"), {"start_new_session": True})

    def test_current_platform_can_resolve_and_load_korean_font(self) -> None:
        from PIL import ImageFont
        from platform_support import default_font

        path = default_font(bold=True)
        self.assertTrue(os.path.isfile(path), path)
        ImageFont.truetype(path, 24)

    def test_render_modules_do_not_hardcode_windows_font_directory(self) -> None:
        modules = [
            os.path.join(SCENE, "fonts.py"),
            os.path.join(HERE, "chrome.py"),
            os.path.join(HERE, "index_chrome.py"),
            os.path.join(HERE, "screenshot_frame.py"),
        ]
        for path in modules:
            source = Path(path).read_text(encoding="utf-8")
            self.assertNotIn("C:\\Windows\\Fonts", source, path)
            self.assertNotIn("C:/Windows/Fonts", source, path)

    def test_generator_uses_portable_process_tree_helpers(self) -> None:
        source = Path(HERE, "codex_parallel_gen.py").read_text(encoding="utf-8")
        self.assertIn("process_group_kwargs", source)
        self.assertIn("terminate_process_tree", source)
        self.assertNotIn('subprocess.run(["taskkill"', source)

    def test_skill_documents_macos_commands_and_confirmation_gate(self) -> None:
        doc_path = Path(HERE, "..", "SKILL.md")
        if not doc_path.exists():
            doc_path = Path(HERE, "README.md")
        skill = doc_path.read_text(encoding="utf-8")
        self.assertIn("macOS", skill)
        self.assertIn("요구사항", skill)
        self.assertIn("확인 게이트", skill)
        self.assertIn("python3", skill)


if __name__ == "__main__":
    unittest.main(verbosity=2)

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


class RenderIntegrityTests(unittest.TestCase):
    """실제 덱 제작에서 백지·미반영 슬라이드를 납품한 결함들의 회귀 테스트."""

    def test_empty_graph_is_rejected_instead_of_rendering_a_blank_slide(self) -> None:
        # 빈 그래프는 검증 루프를 전부 건너뛰어 errors 가 비고, network 슬라이드가
        # 백지인 채로 "렌더 성공"으로 납품됐다.
        from html_slide_renderer import validate_graph

        self.assertNotEqual(validate_graph({}), [])
        self.assertNotEqual(validate_graph({"nodes": [], "edges": []}), [])
        self.assertEqual(
            validate_graph(
                {
                    "nodes": [
                        {"id": "a", "label": "입력", "entityType": "source"},
                        {"id": "b", "label": "출력", "entityType": "outcome"},
                    ],
                    "edges": [
                        {"source": "a", "target": "b", "direction": "forward", "label": "전달"}
                    ],
                }
            ),
            [],
        )

    def test_spec_digest_ignores_asset_bytes_but_tracks_the_asset_path(self) -> None:
        # digest 가 base64 자산 바이트를 포함하면 판정 측이 같은 값을 만들 수 없어
        # 이미지 슬라이드가 영구 stale 이 된다.
        from html_slide_renderer import spec_digest

        base = {"layout": "image", "imagePath": "assets/a.png"}
        with_bytes = dict(
            base, imageData="data:image/png;base64,AAAA", _resolvedImagePath="/tmp/a.png"
        )
        self.assertEqual(spec_digest(base), spec_digest(with_bytes))
        self.assertNotEqual(
            spec_digest(base),
            spec_digest({"layout": "image", "imagePath": "assets/b.png"}),
        )

    def test_job_spec_matches_what_the_renderer_actually_digests(self) -> None:
        # accent·designPreset·compositionPreset 은 잡 수준에서 주입된 뒤 digest 에
        # 들어간다. 판정이 이 주입을 건너뛰면 방금 렌더한 슬라이드도 stale 로 오판한다.
        from html_slide_renderer import job_spec

        spec = job_spec(
            {
                "styleProfile": "technical-blueprint",
                "accentColor": "#0B5FFF",
                "htmlSpec": {"layout": "table"},
            }
        )
        self.assertEqual(spec["accent"], "#0B5FFF")
        self.assertEqual(spec["designPreset"], "technical-blueprint")
        self.assertIn("compositionPreset", spec)

    def test_isolated_codex_home_follows_the_codex_home_environment(self) -> None:
        # 계정 관리 런처는 ~/.codex 가 아닌 경로를 CODEX_HOME 으로 주입한다.
        # 하드코딩하면 격리홈에 auth.json 이 복사되지 않아 전 잡이 401 로 죽는다.
        import importlib

        import codex_parallel_gen

        original = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = os.path.join(tempfile.gettempdir(), "managed-codex")
        try:
            reloaded = importlib.reload(codex_parallel_gen)
            self.assertEqual(
                reloaded.USER_CODEX_HOME,
                os.path.join(tempfile.gettempdir(), "managed-codex"),
            )
        finally:
            if original is None:
                os.environ.pop("CODEX_HOME", None)
            else:
                os.environ["CODEX_HOME"] = original
            importlib.reload(codex_parallel_gen)


class QualityGateTests(unittest.TestCase):
    """렌더러가 이미 측정하던 신호를 실제 제작 경로가 강제하는지 검사한다."""

    def test_receipt_violations_reads_the_render_contract_gate(self) -> None:
        from html_slide_renderer import receipt_violations

        clean = {
            "layout": "process",
            "pixelSize": [1920, 1080],
            "overflow": [],
            "koreanMidWordBreaks": [],
        }
        self.assertEqual(receipt_violations(clean), [])

        overflowing = dict(
            clean,
            overflow=[{"className": "content", "clientHeight": 311, "scrollHeight": 326}],
        )
        self.assertTrue(any("overflow" in item for item in receipt_violations(overflowing)))
        self.assertTrue(receipt_violations(dict(clean, koreanMidWordBreaks=["실패를 읽는"])))
        self.assertTrue(receipt_violations(dict(clean, pixelSize=[1280, 720])))

    def test_network_receipt_without_nodes_is_a_violation(self) -> None:
        from html_slide_renderer import receipt_violations

        blank = {
            "layout": "network",
            "pixelSize": [1920, 1080],
            "overflow": [],
            "graph": {"nodes": 0, "edges": 0, "visibility": []},
        }
        self.assertIn("empty-graph", receipt_violations(blank))

    def test_occluded_edge_labels_are_a_contract_violation(self) -> None:
        # 노드 박스에 깔려 잘린 엣지 라벨을 endpoint 검사만으로는 못 잡는다.
        from html_slide_renderer import receipt_violations

        receipt = {
            "layout": "network",
            "pixelSize": [1920, 1080],
            "overflow": [],
            "graph": {
                "nodes": 3,
                "edges": 2,
                "visibility": [
                    {"source": "a", "target": "b", "labelOccluded": True},
                    {"source": "b", "target": "c", "pathOccluded": True},
                ],
            },
        }
        violations = receipt_violations(receipt)
        self.assertTrue(any("labelOccluded" in item for item in violations))
        self.assertTrue(any("pathOccluded" in item for item in violations))

    def test_verify_rejects_a_slide_whose_receipt_breaks_the_contract(self) -> None:
        # 게이트 함수가 있어도 verify 가 호출하지 않으면 아무것도 막지 못한다.
        import codex_parallel_gen
        from html_slide_renderer import OUTPUT_HEIGHT, OUTPUT_WIDTH

        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            out = os.path.join(temp_dir, "s01.png")
            Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), "white").save(out)
            with open(out, "ab") as handle:
                handle.write(b"\0" * 200 * 1024)

            receipt = {
                "layout": "process",
                "pixelSize": [OUTPUT_WIDTH, OUTPUT_HEIGHT],
                "overflow": [
                    {"className": "content", "clientHeight": 311, "scrollHeight": 326}
                ],
                "koreanMidWordBreaks": [],
            }
            with open(os.path.join(temp_dir, "s01.layout.json"), "w", encoding="utf-8") as handle:
                json.dump(receipt, handle)

            job = {
                "label": "S01",
                "renderer": "html",
                "out": out,
                "htmlSpec": {"layout": "process"},
            }
            bad = codex_parallel_gen.verify([job], temp_dir)

        self.assertIn("S01", bad)
        self.assertIn("overflow", bad["S01"])

    def test_process_rail_offset_does_not_overflow_its_parent(self) -> None:
        # transform 으로 15px 내리면 레이아웃 높이에 반영되지 않아 부모 밖으로 나간다.
        source = (
            REPO_ROOT
            / "plugins"
            / "business-plan-writer"
            / "skills"
            / "ppt-editorial"
            / "scripts"
            / "html_slide_renderer.py"
        ).read_text(encoding="utf-8")
        rule = next(
            line for line in source.splitlines() if line.startswith(".process {{")
        )
        self.assertNotIn("translateY", rule)

    def test_large_numerals_leave_room_for_korean_glyphs(self) -> None:
        # line-height:1 은 한글 글리프가 em 박스를 넘어 8~9px overflow 를 만들었다.
        source = (
            REPO_ROOT
            / "plugins"
            / "business-plan-writer"
            / "skills"
            / "ppt-editorial"
            / "scripts"
            / "html_slide_renderer.py"
        ).read_text(encoding="utf-8")
        for selector in (".kpi-value {{", ".break-duration {{"):
            rule = next(line for line in source.splitlines() if line.startswith(selector))
            self.assertNotIn("line-height: 1;", rule, selector)
            self.assertIn("line-height: 1.12", rule, selector)


class SpecContractTests(unittest.TestCase):
    """레이아웃이 읽지 않는 키가 조용히 백지를 만드는 것을 막는다."""

    def test_layout_specific_keys_are_rejected_in_other_layouts(self) -> None:
        from html_slide_renderer import validate_spec_keys

        wrong = {
            "layout": "image",
            "imagePath": "a.png",
            "statement": "cover 전용 키",
            "metadata": [{"label": "x", "value": "y"}],
        }
        problems = validate_spec_keys(wrong)
        self.assertTrue(problems)
        self.assertIn("statement", problems[0])
        self.assertIn("callout", problems[0])

        right = {
            "layout": "image",
            "imagePath": "a.png",
            "callout": "제목",
            "caption": "설명",
            "facts": ["항목"],
        }
        self.assertEqual(validate_spec_keys(right), [])

    def test_build_html_refuses_a_spec_with_ignored_keys(self) -> None:
        # 검증 함수가 있어도 build_html 이 호출하지 않으면 백지가 그대로 렌더된다.
        from html_slide_renderer import build_html

        with self.assertRaises(ValueError) as caught:
            build_html(
                {
                    "layout": "image",
                    "imageData": "data:image/png;base64,AAAA",
                    "statement": "cover 전용 키",
                }
            )
        self.assertIn("statement", str(caught.exception))

    def test_common_spec_keys_cover_what_build_html_reads(self) -> None:
        # build_html 이 새 공통 키를 읽는데 화이트리스트에 없으면 정상 스펙이 BLOCK 된다.
        import re

        import html_slide_renderer

        source = Path(html_slide_renderer.__file__).read_text(encoding="utf-8")
        body = re.search(
            r"def build_html\(spec: dict\) -> str:(.*?)(?=\n\ndef |\Z)", source, re.S
        )
        read_keys = set(re.findall(r'spec\.get\("([a-zA-Z_]+)"', body.group(1)))
        missing = read_keys - html_slide_renderer._COMMON_SPEC_KEYS
        self.assertEqual(
            missing, set(), f"build_html 이 읽지만 _COMMON_SPEC_KEYS 에 없는 키: {sorted(missing)}"
        )

    def test_every_catalog_scenario_passes_its_own_spec_contract(self) -> None:
        # 번들 카탈로그가 자기 계약을 어기면 그 레이아웃을 쓰는 사용자가 바로 막힌다.
        from html_slide_renderer import validate_spec_keys

        catalog_path = (
            REPO_ROOT
            / "plugins"
            / "business-plan-writer"
            / "skills"
            / "ppt-editorial"
            / "references"
            / "scenario_catalog.json"
        )
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        scenarios = catalog if isinstance(catalog, list) else catalog.get("scenarios", [])
        for scenario in scenarios:
            spec = scenario.get("spec") or {}
            if not spec.get("layout"):
                continue
            self.assertEqual(
                validate_spec_keys(spec), [], f"catalog scenario {spec.get('layout')}"
            )


class GraphLayoutTests(unittest.TestCase):
    """엣지 방향이 노드 배치를 왜곡하지 않는지 검사한다."""

    def test_bidirectional_edges_do_not_compress_the_layer_spread(self) -> None:
        # bidirectional 을 역간선으로 넣으면 위상 레이어가 밀려 노드가 한쪽에 뭉친다
        # (실측: 5개 중 4개가 우측 절반). 방향과 무관하게 같은 간격으로 퍼져야 한다.
        from html_slide_renderer import _graph_positions

        nodes = [
            {"id": "a", "label": "입력", "entityType": "source"},
            {"id": "b", "label": "1층", "entityType": "process"},
            {"id": "c", "label": "2층", "entityType": "process"},
            {"id": "d", "label": "출력", "entityType": "process"},
        ]
        chain = [("a", "b"), ("b", "c"), ("c", "d")]

        def spread(direction: str) -> list[int]:
            graph = {
                "nodes": nodes,
                "edges": [
                    {"source": s, "target": t, "direction": direction, "label": "x"}
                    for s, t in chain
                ],
            }
            positions = _graph_positions(graph)
            return sorted(round(positions[node["id"]][0]) for node in nodes)

        self.assertEqual(spread("forward"), spread("bidirectional"))

        xs = spread("bidirectional")
        gaps = [b - a for a, b in zip(xs, xs[1:])]
        # 반올림으로 1px 차이는 난다. 쏠림은 그보다 훨씬 크게 벌어진다.
        self.assertLessEqual(max(gaps) - min(gaps), 2, f"레이어 간격이 균일하지 않다: {xs}")


class SkillDocumentationTests(unittest.TestCase):
    """SKILL.md 가 실제 코드 계약과 어긋나지 않는지 검사한다."""

    def _skill_text(self) -> str:
        return (
            REPO_ROOT
            / "plugins"
            / "business-plan-writer"
            / "skills"
            / "ppt-editorial"
            / "SKILL.md"
        ).read_text(encoding="utf-8")

    def test_layout_key_table_matches_the_renderer(self) -> None:
        # 문서가 실제 키와 어긋나면 그 표를 믿고 쓴 스펙이 BLOCK 되거나 백지가 된다.
        from html_slide_renderer import LAYOUT_CONTENT_KEYS

        skill = self._skill_text()
        for layout, keys in LAYOUT_CONTENT_KEYS.items():
            self.assertIn(f"|`{layout}`|", skill, f"{layout} 행이 SKILL.md 에 없다")
            for key in (key for key in keys if not key.startswith("image")):
                self.assertIn(f"`{key}`", skill, f"{layout} 의 {key} 가 SKILL.md 에 없다")

    def test_field_lessons_record_the_gates_that_shipped_defects(self) -> None:
        skill = self._skill_text()
        for marker in (
            "receipt_violations",
            "validate_spec_keys",
            "html-spec-stale",
            "record-render",
            "CODEX_HOME",
        ):
            self.assertIn(marker, skill, f"SKILL.md 에 {marker} 기록이 없다")


if __name__ == "__main__":
    unittest.main(verbosity=2)

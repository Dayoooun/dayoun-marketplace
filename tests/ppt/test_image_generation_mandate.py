"""PPT 슬라이드가 코드드로잉이 아니라 이미지 생성으로 만들어지는지 강제한다.

배경 (SKILL.md "3대 철칙"):
- 철칙 A: codex 는 같은 프롬프트에도 이미지생성과 코드드로잉을 확률적으로 고른다.
  코드드로잉으로 빠지면 PIL 기본 폰트에 CJK 글리프가 없어 한글이 전부 "?" 가 되고,
  SVG/matplotlib 결과물은 에디토리얼 품질이 나오지 않는다.
- 철칙 B: 스타일 앵커(`-i`) 없이 프롬프트만 주면 매번 다른 룩이 나온다.
  "토스 느낌" 같은 지시는 문장으로 재현되지 않는다.

두 철칙 모두 SKILL.md 에만 적혀 있으면 잡 작성자가 빠뜨린다.
이 테스트는 실행 경로가 강제하는지 검사한다.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PPT_SCRIPTS = (
    ROOT
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
    / "scripts"
)
sys.path.insert(0, str(PPT_SCRIPTS))
sys.path.insert(0, str(PPT_SCRIPTS / "scene-deck"))

import codex_parallel_gen as gen  # noqa: E402


class ImageGenerationMandateTests(unittest.TestCase):
    def test_mandate_forbids_every_code_drawing_renderer(self) -> None:
        mandate = gen.IMAGE_GEN_MANDATE

        for banned in (
            "Python",
            "PIL",
            "matplotlib",
            "SVG",
            "HTML/CSS",
            "canvas",
            "ImageDraw",
        ):
            with self.subTest(renderer=banned):
                self.assertIn(banned, mandate)

        self.assertIn("image-generation capability", mandate)
        # 앞선 지시와 충돌하므로 우선순위를 명시해야 먹는다.
        self.assertIn("OVERRIDES", mandate)

    def test_mandate_is_appended_to_every_prompt(self) -> None:
        source = (PPT_SCRIPTS / "codex_parallel_gen.py").read_text(encoding="utf-8")

        # 프롬프트 조립 지점에서 상수를 붙여야 한다. 문서에만 적으면 누락된다.
        self.assertIn("+ IMAGE_GEN_MANDATE", source)

    def test_default_profile_supplies_validated_style_anchors(self) -> None:
        variant = gen.resolve_style_variant(None, "토스 느낌의 표지")
        refs = gen.resolve_style_refs(None, variant)

        self.assertEqual("toss-3d", variant)
        self.assertEqual(3, len(refs))
        self.assertTrue(all(Path(path).is_file() for path in refs))

    def test_declared_style_anchor_must_exist_on_disk(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            job = {
                "label": "bad-ref",
                "out": "out/s01.png",
                "prompt": "표지",
                "refs": ["refs/does-not-exist.png"],
            }
            with self.assertRaises(FileNotFoundError):
                gen._run_one(job, temp, retry=0)

    def test_drawing_threshold_catches_measured_fallback_sizes(self) -> None:
        # SKILL.md 실측: 코드드로잉 18~50KB, 이미지생성 700KB~1MB.
        # 임계값이 50 이하이면 50KB 짜리 드로잉이 통과한다.
        self.assertGreater(gen.DRAWING_FALLBACK_KB, 50)

    def test_verify_rejects_code_drawing_sized_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            drawn = base / "drawn.png"
            drawn.write_bytes(b"x" * (40 * 1024))
            generated = base / "generated.png"
            generated.write_bytes(b"x" * (800 * 1024))

            bad = gen.verify(
                [
                    {"label": "drawn", "out": "drawn.png"},
                    {"label": "generated", "out": "generated.png"},
                ],
                str(base),
            )

        self.assertIn("drawn", bad)
        self.assertIn("code-drawing-fallback", bad["drawn"])
        self.assertNotIn("generated", bad)


class StyleProfileDefaultTests(unittest.TestCase):
    """전역 통합 프로파일이 슬라이드 역할별 변형을 일관되게 고르는지."""

    def test_unspecified_job_gets_unified_toss_default(self) -> None:
        variant = gen.resolve_style_variant(None, "서비스 구조를 보여주는 표지")
        block = gen.resolve_style_prompt(None, None, variant)

        self.assertEqual("toss-3d", variant)
        for token in (
            "TOSS 3D + ICON + DATA EDITORIAL UNIFIED",
            "SELECTED STYLE VARIANT: toss-3d",
            "Pretendard",
            "premium 3D isometric or clay object group",
            "NO generic decorative icons",
        ):
            with self.subTest(token=token):
                self.assertIn(token, block)

    def test_visual_role_router_selects_icons_and_charts(self) -> None:
        icon_variant = gen.resolve_style_variant(
            None,
            "핵심 기능 4가지와 단계별 체크리스트",
        )
        data_variant = gen.resolve_style_variant(
            None,
            "응답자 설문 KPI 58.4% 분포 차트",
        )

        self.assertEqual("icon-editorial", icon_variant)
        self.assertEqual("data-editorial", data_variant)
        self.assertEqual(3, len(gen.resolve_style_refs(None, icon_variant)))
        self.assertEqual(3, len(gen.resolve_style_refs(None, data_variant)))
        negative_variant = gen.resolve_style_variant(
            None,
            "로드맵 단계와 아이콘. No chart, no 3D hero.",
        )
        self.assertEqual("icon-editorial", negative_variant)
        icon_block = gen.resolve_style_prompt(None, None, icon_variant)
        self.assertIn("SEMANTIC ICON EDITORIAL", icon_block)
        self.assertIn("6% of slide height", icon_block)
        self.assertIn("NO equal repeated cards", icon_block)
        self.assertIn("NEVER use a straight timeline", icon_block)
        self.assertIn("four staggered editorial steps", icon_block)
        self.assertIn("last meaningful body edge", icon_block)
        self.assertIn(
            "DATA REPORT EDITORIAL",
            gen.resolve_style_prompt(None, None, data_variant),
        )
        data_block = gen.resolve_style_prompt(None, None, data_variant)
        self.assertIn("solid accent-blue header", data_block)
        self.assertIn("28% / 52% / 20%", data_block)
        self.assertIn("last meaningful edge lands between 78% and 84%", data_block)
        table_refs = gen.resolve_style_refs(
            None,
            data_variant,
            "세 열 데이터 테이블",
        )
        self.assertEqual(1, len(table_refs))
        self.assertTrue(table_refs[0].endswith("toss-data-table.png"))

    def test_illustration_must_be_semantically_bound_and_small(self) -> None:
        variant = gen.resolve_style_variant(None, "제품 개념을 보여주는 3D scene")
        block = gen.resolve_style_prompt(None, None, variant)

        self.assertIn("semantically bound", block)
        self.assertIn("Tuck it into a corner", block)
        self.assertIn("NO generic decorative icons", block)

    def test_missing_accent_does_not_fall_back_to_generic_blue(self) -> None:
        variant = gen.resolve_style_variant(None, "표지")
        block = gen.resolve_style_prompt(None, None, variant)

        self.assertIn("NOT SUPPLIED", block)
        self.assertIn("generic tech blue", block)

    def test_supplied_accent_overrides_reference_colour(self) -> None:
        variant = gen.resolve_style_variant(None, "표지")
        block = gen.resolve_style_prompt(None, "#0B5FFF", variant)

        self.assertIn("#0B5FFF", block)
        self.assertIn("Do NOT substitute a generic blue", block)

    def test_unknown_profile_is_rejected_not_silently_ignored(self) -> None:
        with self.assertRaises(Exception) as caught:
            gen.resolve_style_prompt("toss-super-style", None)

        self.assertIn("알 수 없는 스타일 프로파일", str(caught.exception))

    def test_style_block_is_wired_into_prompt_assembly(self) -> None:
        source = (PPT_SCRIPTS / "codex_parallel_gen.py").read_text(encoding="utf-8")

        self.assertIn("+ style_block", source)


class ParallelGenerationTests(unittest.TestCase):
    """이미지 생성이 항상 병렬로 돌아가는지.

    슬라이드 1장 생성에 수 분이 걸린다. 순차로 떨어지면 23장 덱이 70분 넘게
    걸려 수업·납품 일정에서 그대로 실패한다. 격리 CODEX_HOME 을 쓰므로
    고병렬이 안전하고, 순차로 내려가는 건 언제나 실수다.
    """

    def _observed_cap(self, job_count, extra_argv):
        observed = []

        def fake_run_round(jobs, base_dir, cap, retry, effort, model, timeout=590):
            observed.append(cap)

        original = gen.run_round
        gen.run_round = fake_run_round
        try:
            with tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                (base / "anchor.png").write_bytes(b"x" * 1024)
                jobs = [
                    {
                        "label": f"s{index:02d}",
                        "out": f"out/s{index:02d}.png",
                        "prompt": "슬라이드",
                        "refs": ["anchor.png"],
                    }
                    for index in range(1, job_count + 1)
                ]
                jobs_path = base / "jobs.json"
                jobs_path.write_text(
                    json.dumps(jobs, ensure_ascii=False), encoding="utf-8"
                )

                argv = sys.argv
                sys.argv = [
                    "codex_parallel_gen.py",
                    str(jobs_path),
                    "--loop",
                    "1",
                ] + extra_argv
                # main() 은 한글 진행로그를 쏟는다. 테스트 출력이 묻히고,
                # cp1252 콘솔에서는 UnicodeEncodeError 로 죽는다.
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        gen.main()
                except SystemExit:
                    pass
                finally:
                    sys.argv = argv
        finally:
            gen.run_round = original

        self.assertTrue(observed, "run_round 가 호출되지 않았습니다")
        return observed[0]

    def test_sequential_cap_is_overridden_for_multi_slide_decks(self) -> None:
        # 사용자가 --cap 1 로 순차를 요청해도 덱 생성은 병렬로 올린다.
        self.assertEqual(self._observed_cap(8, ["--cap", "1"]), gen.MIN_PARALLEL_CAP)
        self.assertEqual(self._observed_cap(8, ["--cap", "2"]), gen.MIN_PARALLEL_CAP)

    def test_cap_above_minimum_is_respected(self) -> None:
        self.assertEqual(self._observed_cap(8, ["--cap", "6"]), 6)

    def test_forced_cap_never_exceeds_job_count(self) -> None:
        # 잡보다 많은 워커는 낭비다.
        self.assertEqual(self._observed_cap(3, ["--cap", "1"]), 3)

    def test_single_slide_stays_sequential(self) -> None:
        self.assertEqual(self._observed_cap(1, ["--cap", "1"]), 1)

    def test_auto_cap_is_parallel_for_multi_slide_decks(self) -> None:
        self.assertGreater(self._observed_cap(8, []), 1)


if __name__ == "__main__":
    unittest.main()

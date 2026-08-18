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

    def test_missing_style_anchor_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            job = {
                "label": "no-anchor",
                "out": "out/s01.png",
                "prompt": "토스 느낌의 표지",
            }
            with self.assertRaises(ValueError) as caught:
                gen._run_one(job, temp, retry=0)

        message = str(caught.exception)
        self.assertIn("스타일 앵커가 없습니다", message)
        # 막기만 하고 대안을 안 주면 사용자가 우회한다.
        self.assertIn("allowNoStyleAnchor", message)

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
    """스타일 프로파일이 매 실행 흔들리지 않고 기본값으로 고정되는지.

    SKILL.md 에 "모던 플랫 (Toss/Naver flat)" 설명이 있어도 산문이라 실행 경로가
    읽지 못했다. 그래서 사용자가 매번 토스 룩을 원해도 슬라이드마다 룩이 달랐다.
    """

    def test_unspecified_job_gets_modern_flat_default(self) -> None:
        block = gen.resolve_style_prompt(None, None)

        for token in (
            "MODERN FLAT",
            "Pretendard",
            "NEVER serif",
            "3D isometric",
            "clay illustration",
            "One message per slide",
        ):
            with self.subTest(token=token):
                self.assertIn(token, block)

    def test_illustration_must_be_semantically_bound_and_small(self) -> None:
        block = gen.resolve_style_prompt(None, None)

        self.assertIn("NO generic decorative icons", block)
        self.assertIn("meaningless geometric filler", block)
        # 크게 그리면 토스 룩이 아니라 흔한 AI 슬롭이 된다.
        self.assertIn("tucked", block)

    def test_missing_accent_does_not_fall_back_to_generic_blue(self) -> None:
        block = gen.resolve_style_prompt(None, None)

        self.assertIn("NOT SUPPLIED", block)
        self.assertIn("generic tech blue", block)

    def test_supplied_accent_overrides_reference_colour(self) -> None:
        block = gen.resolve_style_prompt(None, "#0B5FFF")

        self.assertIn("#0B5FFF", block)
        self.assertIn("Do NOT substitute a generic blue", block)

    def test_unknown_profile_is_rejected_not_silently_ignored(self) -> None:
        with self.assertRaises(Exception) as caught:
            gen.resolve_style_prompt("toss-super-style", None)

        self.assertIn("알 수 없는 스타일 프로파일", str(caught.exception))

    def test_style_block_is_wired_into_prompt_assembly(self) -> None:
        source = (PPT_SCRIPTS / "codex_parallel_gen.py").read_text(encoding="utf-8")

        self.assertIn("+ style_block", source)


if __name__ == "__main__":
    unittest.main()

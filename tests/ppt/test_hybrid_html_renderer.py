from __future__ import annotations

import json

import sys
from pathlib import Path

from PIL import Image


SKILL = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "business-plan-writer"
    / "skills"
    / "ppt-editorial"
)
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import codex_parallel_gen as generator  # noqa: E402
import html_slide_renderer as html_renderer  # noqa: E402


def test_hybrid_router_keeps_3d_in_codex() -> None:
    table = {"renderer": "html", "layout": "table", "out": "table.png"}
    scene = {"renderer": "codex", "prompt": "3D product scene", "out": "scene.png"}

    assert generator.is_html_job(table)
    assert not generator.is_html_job(scene)
    assert html_renderer.supports(
        {"renderer": "html", "layout": "overview", "out": "overview.png"}
    )
    assert html_renderer.supports(
        {"renderer": "html", "layout": "network", "out": "network.png"}
    )
    assert html_renderer.supports(
        {"renderer": "html", "layout": "image", "out": "image.png"}
    )
    assert html_renderer.supports(
        {"renderer": "html", "layout": "break", "out": "break.png"}
    )
    assert html_renderer.supports(
        {"renderer": "html", "layout": "cover", "out": "cover.png"}
    )


def test_bar_widths_are_normalized_to_the_largest_value() -> None:
    markup = html_renderer.build_html(
        {
            "layout": "bars",
            "items": [
                {"label": "A", "value": 31, "display": "31%", "highlight": True},
                {"label": "B", "value": 5, "display": "5%"},
            ],
        }
    )

    assert "width:100.0%" in markup
    assert "width:16.129" in markup
    assert "grid-template-columns: 68% 28%" in markup
    assert "min-height: 510px" in markup
    assert "background: var(--accent)" in markup
    assert "linear-gradient(90deg" not in markup
    assert "word-break: keep-all" in html_renderer.build_html(
        {
            "layout": "table",
            "columns": [{"label": "항목", "width": "100%"}],
            "rows": [["운영 기준으로 연결합니다"]],
        }
    )
    assert "word-break: keep-all" in html_renderer.build_html(
        {
            "layout": "image",
            "imageData": "data:image/png;base64,AA==",
            "callout": "생성 자산과 정보 구조를 분리합니다",
        }
    )
    style_prompt = __import__("style_profile").prompt_block(
        "toss-data-unified",
        "#246BFD",
        "toss-3d",
    )
    assert "EDITORIAL SURFACE RULE" in style_prompt
    assert "HEADLINE LANGUAGE RULE" in style_prompt
    assert "large pale-grey or pale-accent rectangular card" in style_prompt
    assert "다시 시작합니다" in style_prompt
    legacy_prompt = __import__("style_profile").prompt_block(
        "modern-flat",
        "#D45745",
    )
    assert "EDITORIAL SURFACE RULE" in legacy_prompt
    assert "HEADLINE LANGUAGE RULE" in legacy_prompt
    profiles = __import__("style_profile").load_profiles()
    assert {
        "swiss-grid",
        "warm-editorial",
        "technical-blueprint",
        "photo-documentary",
    } <= set(profiles["profiles"])
    assert len(profiles["profiles"]) >= 8
    assert len(profiles["palettePresets"]) >= 10
    for preset in (
        "swiss-grid",
        "warm-editorial",
        "technical-blueprint",
        "photo-documentary",
    ):
        markup = html_renderer.build_html(
            {
                "layout": "bars",
                "designPreset": preset,
                "items": [{"label": "검수", "value": 1}],
                "summaries": [{"value": "1", "label": "결과"}],
            }
        )
        assert f"preset-{preset}" in markup
    for module_preset in ("feature-left", "feature-right", "feature-top", "ledger"):
        module_markup = html_renderer.build_html(
            {
                "layout": "modules",
                "compositionPreset": module_preset,
                "featured": 0,
                "items": [
                    {"label": f"모듈 {index}", "detail": "검수 기준", "icon": "check"}
                    for index in range(4)
                ],
            }
        )
        assert f"modules-{module_preset}" in module_markup
    contract = json.loads(
        (SKILL / "references" / "render_contract.json").read_text(encoding="utf-8")
    )
    contract_presets = contract["compositionPresets"]
    assert set(contract_presets) == set(html_renderer.COMPOSITION_PRESETS)
    assert sum(len(value["allowed"]) for value in contract_presets.values()) == 34
    for layout, allowed in html_renderer.COMPOSITION_PRESETS.items():
        assert tuple(contract_presets[layout]["allowed"]) == allowed
    cover_markup = html_renderer.build_html(
        {
            "layout": "cover",
            "imageData": "data:image/png;base64,AA==",
            "statement": "포지셔닝",
            "metadata": [{"label": "대상", "value": "책임자"}],
        }
    )
    cover_copy_rule = cover_markup.split(".cover-copy {", 1)[1].split("}", 1)[0]
    assert "background:" not in cover_copy_rule
    assert "border-top:" not in cover_copy_rule
    assert "word-break: keep-all" in html_renderer.build_html(
        {
            "layout": "process",
            "items": [
                {
                    "label": "검수 요청",
                    "detail": "왜 이 필드가 필요한가",
                    "icon": "check",
                }
            ],
        }
    )
    image_markup = html_renderer.build_html(
        {
            "layout": "image",
            "imageData": "data:image/png;base64,AA==",
            "callout": "운영 원칙",
            "facts": ["HTML", "Codex"],
        }
    )
    image_copy_rule = image_markup.split(".image-copy {", 1)[1].split("}", 1)[0]
    assert "background:" not in image_copy_rule


def test_generator_accepts_full_hd_html_output(tmp_path: Path) -> None:
    output = tmp_path / "full-hd.png"
    Image.effect_noise((1920, 1080), 12).convert("RGB").save(output)

    bad = generator.verify(
        [{"label": "S01", "renderer": "html", "layout": "table", "out": str(output)}],
        tmp_path,
    )

    assert bad == {}


def test_table_renders_with_real_chromium(tmp_path: Path) -> None:
    job = {
        "renderer": "html",
        "layout": "table",
        "out": "table.png",
        "accent": "#536FE8",
        "eyebrow": "FUNCTION MAP",
        "title": [
            {"text": "신청서 작성은", "weight": "light"},
            {"text": "두 단계로 완성됩니다", "weight": "bold"},
        ],
        "subtitle": "브라우저 한글 렌더 검증",
        "columns": [
            {"label": "기능", "width": "28%"},
            {"label": "무엇을 해주나", "width": "52%"},
            {"label": "산출물", "width": "20%"},
        ],
        "rows": [
            ["1. 분석", "제출요건을 정리", "분석표"],
            ["2. 작성", "평가기준에 맞춰 작성", "초안"],
        ],
    }

    out = html_renderer.render_job(job, tmp_path)

    assert out.is_file()
    assert out.stat().st_size > 10 * 1024
    with Image.open(out) as image:
        assert image.size == (
            html_renderer.OUTPUT_WIDTH,
            html_renderer.OUTPUT_HEIGHT,
        )
        assert image.format == "PNG"
    receipt = out.with_suffix(".layout.json")
    assert receipt.is_file()
    assert '"renderer": "html-playwright"' in receipt.read_text(encoding="utf-8")
    assert '"pixelSize": [\n    1920,\n    1080\n  ]' in receipt.read_text(encoding="utf-8")

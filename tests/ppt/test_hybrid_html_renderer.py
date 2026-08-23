from __future__ import annotations

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

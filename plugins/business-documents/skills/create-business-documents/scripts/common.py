from __future__ import annotations

import base64
import html
import io
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any


FONT_STACK = '"Malgun Gothic", "AppleSDGothicNeo-Regular", "Apple SD Gothic Neo", "Noto Sans KR", "NanumGothic", sans-serif'


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def fmt_date(value: Any) -> str:
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return "[날짜 입력]"
        parsed = date.fromisoformat(text[:10])
    return f"{parsed.year}. {parsed.month}. {parsed.day}."


def safe_color(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip()
    return candidate if re.fullmatch(r"#[0-9A-Fa-f]{6}", candidate) else fallback


def get_image_backend():
    try:
        from PIL import Image
    except (ImportError, OSError):
        return None
    return Image


def image_data_uri(path_value: Any) -> str | None:
    source = str(path_value or "").strip()
    backend = get_image_backend()
    if not source or backend is None:
        return None
    path = Path(source).expanduser()
    if not path.is_file():
        return None
    try:
        with backend.open(path) as image:
            converted = image.convert("RGBA")
            buffer = io.BytesIO()
            converted.save(buffer, format="PNG")
    except (OSError, ValueError):
        return None
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def base_css(accent: str, extra: str = "") -> str:
    return f"""
:root {{ --accent: {accent}; --ink: #172033; --muted: #667085; --line: #d8dee9; }}
* {{ box-sizing: border-box; }}
@page {{ size: A4; margin: 12mm; }}
body {{ margin: 0; color: var(--ink); background: #eef1f5; font-family: {FONT_STACK}; }}
.print-bar {{ position: sticky; top: 0; z-index: 10; display: flex; justify-content: center; padding: 12px; background: #172033; }}
.print-bar button {{ border: 0; border-radius: 8px; padding: 10px 18px; color: white; background: var(--accent); font: inherit; font-weight: 700; cursor: pointer; }}
.sheet {{ width: 210mm; min-height: 297mm; margin: 20px auto; padding: 18mm; background: white; box-shadow: 0 10px 32px rgba(23, 32, 51, .12); }}
h1, h2, h3, p {{ margin-top: 0; }}
.muted {{ color: var(--muted); }}
.placeholder {{ color: #8b94a5; }}
@media print {{
  body {{ background: white; }}
  .print-bar {{ display: none !important; }}
  .sheet {{ width: auto; min-height: 0; margin: 0; padding: 0; box-shadow: none; }}
}}
{extra}
""".strip()


def document(title: Any, body: str, accent: str, extra_css: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{base_css(accent, extra_css)}</style>
</head>
<body>
<div class="print-bar"><button type="button" onclick="window.print()">PDF로 저장 / 인쇄</button></div>
<main class="sheet">{body}</main>
</body>
</html>
"""


def save_html(html_text: str, name: str, output_dir: str | Path) -> Path:
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(name).name
    if not safe_name.lower().endswith(".html"):
        safe_name += ".html"
    target = target_dir / safe_name
    target.write_text(html_text, encoding="utf-8")
    return target

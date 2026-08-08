from __future__ import annotations

from typing import Any

from common import document, esc, fmt_date, image_data_uri, safe_color


STYLES = {
    "official": ("#1e3a5f", ".notice-head { border-bottom: 3px double var(--ink); text-align: center; }"),
    "notice": ("#0369a1", ".notice-head { border-left: 8px solid var(--accent); padding-left: 8mm; }"),
    "poster": ("#7c3aed", ".notice-head { padding: 12mm; color: white; background: var(--accent); border-radius: 16px; text-align: center; } .notice-head h1 { font-size: 32px; }"),
}
KOREAN = "가나다라마바사아자차카타파하"
CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"
CIRCLED_KOREAN = "㉮㉯㉰㉱㉲㉳㉴㉵㉶㉷㉸㉹㉺㉻"


def _label(level: int, index: int) -> str:
    number = index + 1
    korean = KOREAN[index % len(KOREAN)]
    if level == 0:
        return f"{number}."
    if level == 1:
        return f"{korean}."
    if level == 2:
        return f"{number})"
    if level == 3:
        return f"{korean})"
    if level == 4:
        return f"({number})"
    if level == 5:
        return f"({korean})"
    if level == 6:
        return CIRCLED[index % len(CIRCLED)]
    return CIRCLED_KOREAN[index % len(CIRCLED_KOREAN)]


def _render_nodes(nodes: Any, level: int = 0) -> str:
    if not isinstance(nodes, list):
        return ""
    rendered: list[str] = []
    for index, node in enumerate(nodes):
        if isinstance(node, dict):
            text = node.get("text") or "[내용 입력]"
            children = node.get("children")
        else:
            text = node
            children = None
        rendered.append(
            f'<div class="body-row level-{level}">{_label(level, index)} {esc(text)}</div>'
        )
        if children:
            rendered.append(_render_nodes(children, level + 1))
    return "".join(rendered)


def render(data: dict[str, Any], kind: str = "official") -> str:
    if kind not in STYLES:
        raise ValueError(f"unsupported notice kind: {kind}")
    base_accent, style_css = STYLES[kind]
    accent = safe_color(data.get("accent"), base_accent)
    seal_uri = image_data_uri(data.get("seal_path"))
    seal = (
        f'<img class="seal" src="{seal_uri}" alt="사용자 제공 직인">'
        if seal_uri
        else '<span class="seal-placeholder">(직인)</span>'
    )
    body_nodes = _render_nodes(data.get("body"))
    if not body_nodes:
        body_nodes = '<div class="body-row"><span>[내용 입력]</span></div>'
    attachments = data.get("attach") if isinstance(data.get("attach"), list) else []
    attach_html = ""
    if attachments:
        attach_html = '<section class="attachments"><b>붙임</b><ol>' + "".join(
            f"<li>{esc(item)}</li>" for item in attachments
        ) + "</ol></section>"
    recipient = esc(data.get("to") or "[수신 입력]")
    via = str(data.get("via") or "").strip()
    date_text = fmt_date(data.get("date"))
    end_marker = '<p class="end-marker">끝.</p>' if kind == "official" else ""

    body = f"""
<header class="notice-head">
  <p class="org">{esc(data.get("org") or "[기관명 입력]")}</p>
  <h1>{esc(data.get("title") or "[제목 입력]")}</h1>
  <p>{esc(data.get("subtitle") or "")}</p>
</header>
<section class="routing">
  <p><b>수신</b> {recipient}</p>
  {f'<p><b>경유</b> {esc(via)}</p>' if via else ''}
</section>
<section class="body-copy">{body_nodes}</section>
{attach_html}
{end_marker}
<footer><p>{date_text}</p><p class="signature">{esc(data.get("org") or "[기관명 입력]")} {seal}</p></footer>
"""
    css = f"""
{style_css}
.notice-head {{ margin-bottom: 12mm; padding-bottom: 8mm; }}
.notice-head .org {{ color: var(--accent); font-weight: 800; letter-spacing: .08em; }}
.notice-head h1 {{ margin-bottom: 3mm; font-size: 27px; line-height: 1.35; }}
.routing {{ padding: 5mm 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }}
.routing p {{ margin: 2mm 0; }}
.body-copy {{ margin: 10mm 0; font-size: 14px; line-height: 1.8; }}
.body-row {{ margin: 3mm 0; }}
.level-1 {{ margin-left: 9mm; }}
.level-2 {{ margin-left: 18mm; }}
.level-3 {{ margin-left: 27mm; }}
.level-4, .level-5, .level-6, .level-7 {{ margin-left: 32mm; }}
.attachments {{ margin-top: 10mm; padding: 5mm; background: #f6f8fb; border-radius: 8px; }}
.attachments ol {{ margin-bottom: 0; }}
.end-marker {{ margin-top: 8mm; font-weight: 800; }}
footer {{ margin-top: 20mm; text-align: center; }}
footer > p:first-child {{ font-size: 14px; }}
.signature {{ font-size: 20px; font-weight: 800; }}
.seal {{ width: 18mm; height: 18mm; object-fit: contain; vertical-align: middle; }}
.seal-placeholder {{ color: var(--accent); }}
"""
    return document(data.get("title") or "공문·안내문", body, accent, css)

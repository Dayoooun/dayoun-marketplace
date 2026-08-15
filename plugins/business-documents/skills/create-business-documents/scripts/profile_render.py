from __future__ import annotations

from typing import Any

from common import document, esc, image_data_uri


STYLES = {
    "clean": ("#2563eb", ""),
    "sidebar": ("#0f766e", ".profile { grid-template-columns: 58mm 1fr; } .identity { background: #ecfdf5; padding: 8mm; border-radius: 12px; align-self: start; }"),
    "editorial": ("#c2410c", ".identity h1 { font-family: Georgia, serif; font-size: 34px; } .section h2 { border-bottom: 3px solid var(--accent); padding-bottom: 4px; }"),
}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _entry(item: Any) -> str:
    if isinstance(item, dict):
        title = item.get("org") or item.get("title") or item.get("name") or "[항목 입력]"
        role = item.get("role") or item.get("detail") or item.get("course") or ""
        period = item.get("period") or ""
        description = item.get("description") or ""
        meta = " · ".join(esc(value) for value in (role, period) if str(value).strip())
        meta_html = f'<p class="meta">{meta}</p>' if meta else ""
        description_html = f"<p>{esc(description)}</p>" if str(description).strip() else ""
        return f"<article><h3>{esc(title)}</h3>{meta_html}{description_html}</article>"
    return f"<article><p>{esc(item)}</p></article>"


def _section(label: str, content: str) -> str:
    return f'<section class="section"><h2>{label}</h2>{content}</section>'


def render(data: dict[str, Any], style: str = "clean") -> str:
    if style not in STYLES:
        raise ValueError(f"unsupported profile style: {style}")
    accent, style_css = STYLES[style]
    photo_uri = image_data_uri(data.get("photo_path"))
    photo = (
        f'<img class="photo" src="{photo_uri}" alt="사용자 제공 프로필 사진">'
        if photo_uri
        else '<div class="photo-placeholder" aria-label="사진 미제공">PHOTO</div>'
    )
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    contact_rows = "".join(
        f"<p><b>{label}</b> {esc(contact.get(key) or placeholder)}</p>"
        for key, label, placeholder in (
            ("phone", "연락처", "[연락처 입력]"),
            ("email", "이메일", "[이메일 입력]"),
            ("location", "지역", "[지역 입력]"),
        )
    )

    sections: list[str] = []
    summary = str(data.get("summary") or "").strip()
    if summary:
        sections.append(_section("요약", f"<p>{esc(summary)}</p>"))
    for key, label in (("career", "경력"), ("edu", "교육"), ("cert", "자격"), ("skills", "역량")):
        values = _list(data.get(key))
        if values:
            sections.append(_section(label, "".join(_entry(item) for item in values)))

    body = f"""
<div class="profile">
  <aside class="identity">
    {photo}
    <p class="eyebrow">PROFILE</p>
    <h1>{esc(data.get("name") or "[이름 입력]")}</h1>
    <p class="headline">{esc(data.get("headline") or "[전문 분야 입력]")}</p>
    <div class="contact">{contact_rows}</div>
  </aside>
  <div class="content">{''.join(sections)}</div>
</div>
"""
    css = f"""
{style_css}
.profile {{ display: grid; grid-template-columns: 62mm 1fr; gap: 13mm; }}
.identity {{ min-height: 230mm; }}
.photo, .photo-placeholder {{ width: 48mm; height: 58mm; border-radius: 10px; object-fit: cover; }}
.photo-placeholder {{ display: grid; place-items: center; color: #9aa4b5; background: #edf1f6; font-weight: 800; letter-spacing: .16em; }}
.eyebrow {{ margin: 10mm 0 3mm; color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: .14em; }}
.identity h1 {{ margin-bottom: 3mm; font-size: 28px; }}
.headline {{ color: var(--muted); }}
.contact {{ margin-top: 10mm; font-size: 12px; }}
.contact p {{ overflow-wrap: anywhere; }}
.section {{ margin-bottom: 10mm; }}
.section h2 {{ color: var(--accent); font-size: 17px; }}
.section article {{ padding: 0 0 6mm 5mm; border-left: 2px solid var(--line); }}
.section article h3 {{ margin-bottom: 2mm; font-size: 15px; }}
.section article p {{ margin-bottom: 2mm; font-size: 13px; line-height: 1.65; }}
.meta {{ color: var(--muted); }}
"""
    return document(f"{data.get('name') or '프로필'} 프로필", body, accent, css)

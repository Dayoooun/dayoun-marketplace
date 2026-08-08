from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from common import document, esc, image_data_uri


STYLES = {
    "clean": ("#2563eb", ""),
    "office": ("#1f4b7a", ".quote-head { border-top: 8px solid var(--accent); padding-top: 18px; }"),
    "brand": ("#6d28d9", ".quote-head { background: #f5f3ff; margin: -8mm -8mm 12mm; padding: 12mm 8mm; }"),
}


def _money(value: int) -> str:
    return f"{value:,}원"


def _rounded(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calculate_totals(items: list[dict[str, Any]], vat_mode: str) -> tuple[int, int, int]:
    if vat_mode not in {"exclusive", "inclusive"}:
        raise ValueError("vat_mode must be 'exclusive' or 'inclusive'")
    item_sum = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{index}] must be an object")
        qty = int(item.get("qty", 0))
        unit_price = int(item.get("unit_price", 0))
        if qty < 0 or unit_price < 0:
            raise ValueError(f"items[{index}] qty and unit_price must be zero or greater")
        item_sum += qty * unit_price
    if vat_mode == "exclusive":
        supply = item_sum
        vat = _rounded(Decimal(supply) * Decimal("0.1"))
        return supply, vat, supply + vat
    total = item_sum
    supply = _rounded(Decimal(total) / Decimal("1.1"))
    return supply, total - supply, total


def _under_ten_thousand(value: int) -> str:
    digits = "영일이삼사오육칠팔구"
    units = ("천", "백", "십", "")
    places = (1000, 100, 10, 1)
    parts: list[str] = []
    for place, unit in zip(places, units):
        digit = value // place
        value %= place
        if digit:
            parts.append(digits[digit] + unit)
    return "".join(parts)


def kor_amount(value: int) -> str:
    amount = int(value)
    if amount < 0:
        raise ValueError("amount must be zero or greater")
    if amount == 0:
        return "영원정"
    groups = ("", "만", "억", "조", "경")
    parts: list[str] = []
    index = 0
    while amount:
        group = amount % 10_000
        if group:
            parts.append(_under_ten_thousand(group) + groups[index])
        amount //= 10_000
        index += 1
        if index >= len(groups) and amount:
            raise ValueError("amount is too large")
    return "".join(reversed(parts)) + "원정"


def _field(data: dict[str, Any], key: str, placeholder: str) -> str:
    value = data.get(key)
    return esc(value if str(value or "").strip() else placeholder)


def render(data: dict[str, Any], style: str = "clean") -> str:
    if style not in STYLES:
        raise ValueError(f"unsupported quote style: {style}")
    supplier = data.get("supplier") if isinstance(data.get("supplier"), dict) else {}
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    items = data.get("items") if isinstance(data.get("items"), list) else []
    vat_mode = str(data.get("vat_mode") or "exclusive")
    supply, vat, total = calculate_totals(items, vat_mode)
    accent, extra_style = STYLES[style]

    logo_uri = image_data_uri(supplier.get("logo_path"))
    logo = (
        f'<img class="logo" src="{logo_uri}" alt="사용자 제공 로고">'
        if logo_uri
        else f'<div class="logo-fallback">{_field(supplier, "company", "[상호 입력]")}</div>'
    )
    seal_uri = image_data_uri(supplier.get("seal_path"))
    seal = (
        f'<img class="seal" src="{seal_uri}" alt="사용자 제공 인장">'
        if seal_uri
        else '<span class="seal-fallback">(인)</span>'
    )

    rows: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        qty = int(item.get("qty", 0))
        unit_price = int(item.get("unit_price", 0))
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{_field(item, 'name', '[품목 입력]')}</td>"
            f"<td>{_field(item, 'spec', '-')}</td>"
            f"<td class=\"num\">{qty:,}</td>"
            f"<td class=\"num\">{unit_price:,}</td>"
            f"<td class=\"num\">{qty * unit_price:,}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td>1</td><td>[품목 입력]</td><td>-</td><td class="num">0</td><td class="num">0</td><td class="num">0</td></tr>')

    notes = data.get("notes") if isinstance(data.get("notes"), list) else []
    note_items = [f"<li>{esc(note)}</li>" for note in notes if str(note).strip()]
    if vat_mode == "inclusive":
        note_items.append("<li>부가세 포함 금액에서 공급가액을 역산했습니다.</li>")
    notes_html = "".join(note_items) or "<li>[특기사항 입력]</li>"

    body = f"""
<header class="quote-head">
  <div>{logo}</div>
  <div><p class="eyebrow">QUOTATION</p><h1>{_field(data, "title", "견적서")}</h1></div>
</header>
<section class="meta-grid">
  <div><b>공급받는 자</b><p>{_field(customer, "company", "[수신처 입력]")}</p><p>{_field(customer, "contact", "[담당자 입력]")}</p></div>
  <div><b>공급자</b><p>{_field(supplier, "company", "[상호 입력]")} {seal}</p><p>대표: {_field(supplier, "representative", "[대표자 입력]")}</p><p>사업자등록번호: {_field(supplier, "business_number", "[사업자등록번호 입력]")}</p><p>주소: {_field(supplier, "address", "[주소 입력]")}</p><p>연락처: {_field(supplier, "phone", "[연락처 입력]")}</p></div>
</section>
<div class="total-callout"><span>견적 합계</span><strong>{_money(total)}</strong><small>{kor_amount(total)}</small></div>
<table><thead><tr><th>No.</th><th>품목</th><th>규격</th><th>수량</th><th>단가</th><th>금액</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<section class="summary"><p>공급가액 <b>{_money(supply)}</b></p><p>부가세 <b>{_money(vat)}</b></p><p>합계 <b>{_money(total)}</b></p></section>
<section class="notes"><h2>특기사항</h2><ul>{notes_html}</ul></section>
"""
    css = f"""
{extra_style}
.quote-head {{ display: flex; justify-content: space-between; align-items: center; gap: 24px; margin-bottom: 12mm; }}
.quote-head h1 {{ margin: 0; font-size: 30px; }}
.eyebrow {{ color: var(--accent); font-weight: 800; letter-spacing: .14em; }}
.logo {{ max-width: 52mm; max-height: 22mm; object-fit: contain; }}
.logo-fallback {{ max-width: 70mm; font-size: 20px; font-weight: 800; color: var(--accent); }}
.seal {{ width: 16mm; height: 16mm; object-fit: contain; vertical-align: middle; }}
.seal-fallback {{ color: var(--accent); font-weight: 800; }}
.meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10mm; padding: 7mm; background: #f7f9fc; border-radius: 10px; }}
.meta-grid p {{ margin: 4px 0 0; font-size: 13px; }}
.total-callout {{ display: grid; grid-template-columns: 1fr auto; gap: 2px 20px; align-items: end; margin: 10mm 0 6mm; padding: 7mm; color: white; background: var(--accent); border-radius: 10px; }}
.total-callout strong {{ font-size: 25px; }}
.total-callout small {{ grid-column: 1 / -1; opacity: .85; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ padding: 9px 7px; border: 1px solid var(--line); text-align: left; }}
th {{ background: #f2f5f9; }}
.num {{ text-align: right; }}
.summary {{ display: flex; justify-content: flex-end; gap: 20px; margin-top: 6mm; }}
.summary p {{ margin: 0; }}
.notes {{ margin-top: 10mm; }}
.notes h2 {{ font-size: 16px; }}
.notes li {{ margin: 5px 0; }}
"""
    return document(data.get("title") or "견적서", body, accent, css)

# -*- coding: utf-8 -*-
"""정보 구도 — 표 · 대비 · 매트릭스 · 막대 (2026-08-07)

## 왜 필요한가
씬 덱은 발표 중 집중에는 유리하지만, 청중이 자료만 다시 볼 때 내용이 남지 않는다.
실측한 교육 덱에서 씬 중심 16장만으로는 개념 정의·비교·판정 기준을
전달할 수 없어 학습자가 혼자 복습하지 못했다. 표·예시·기준을 넣어 22장으로 바꿨다.

교육·매뉴얼·심사자료처럼 **읽는 사람이 혼자 판단해야 하는 덱**에서 쓴다.
씬을 만들지 않으므로 생성 비용이 0이고, 텍스트만 고치면 즉시 반영된다.

## 사용법
```python
from deck import Deck
import info_layouts as IL
IL.register()                    # LAY 에 4개 구도 등록 — build() 전에 한 번

d = Deck(domain="교육", foot="㈜바이론", title="슬라이드")
IL.table(d, "CONCEPT 01", ["불편과 문제는", "다르다"], ["섞어 쓰면 해결책이 좁아진다"],
         ["구분", "의미", "사례"],
         [["불편", "겉으로 드러난 현상", "엘리베이터가 느리다"],
          ["문제", "불편이 생기는 이유", "기다리는 시간이 지루하다"]],
         widths=[1, 2.3, 2.7], source="서비스디자인 문제 재정의 원리")
IL.example(d, "WORKED EXAMPLE", ["문제 정의문", "넓은 문장을 좁힌다"], [],
           [("수정 전", "대학생은 혼밥 때문에 외롭다.", "대상·상황이 넓다."),
            ("수정 후", "타지역 신입생은 평일 저녁 동행을 찾기 어렵다.", "관찰 가능하다.")])
IL.matrix(d, "CONVERGENCE", ["두 기준으로", "1개를 고른다"], [],
          [("우선 실험", "쉽고 효과 큼"), ("후보", "어렵지만 효과 큼"),
           ("보류", "쉽지만 효과 작음"), ("제외", "어렵고 효과 작음")],
          "실행 어려움 →", "효과 ↑")
IL.bar(d, "RESULT", ["집계", "이렇게 해석한다"], [],
       [("A팀 근거", 31), ("A팀 아이디어", 12)], source="예시 데이터")
```

## 표 정렬 규칙
열 단위로 위에서부터 판정해 **처음 걸리는 것**을 적용한다.

  1  일련번호      모든 셀이 숫자 또는 숫자범위(1, 6–8)          → 가운데
  2  1열           행 라벨이므로 눈이 따라갈 축을 왼쪽에 둔다     → 왼쪽
  3  줄바꿈 발생   두 줄 이상 되는 셀이 있는 열                  → 왼쪽
  4  폭 편차 큼    최대·최소 셀 폭 차이 > 폰트크기 × 3.5         → 왼쪽
  5  짧은 값       셀 폭 ≤ 폰트×8 이면서 열 내부폭 × 0.55        → 가운데
  6  그 외                                                      → 왼쪽

세로는 예외 없이 항상 중앙. 헤더 행은 본문 열 정렬을 그대로 따른다.
`table(align=["left", "center", ...])` 로 열별 수동 지정 가능 — 규칙보다 우선한다.

글자 수가 아니라 `textlength()` 실측 폭으로 판정하므로 `widths` 를 바꿔도 따라온다.
(실측: 글자 수 기준이던 초판은 같은 역할의 1열이 2~8자 차이로 갈려 12개 표가 제각각이었다)

## 철칙
- **씬을 만들지 않는다.** `s["scene"] = None` 이라 `jobs()` 가 건너뛴다.
- **고정 y 좌표 금지.** `_body_top()` 으로 헤더가 실제 끝난 위치를 받는다.
  (실측: 고정값을 쓰면 헤드라인이 2줄일 때 서브텍스트와 본문이 겹친다)
- 내용이 넘치면 폰트를 단계적으로 줄이고, 남으면 행 높이로 분배한다.
"""
import re

import layout_engine as LE

BODY_BOT = 0.815          # 본문이 침범하면 안 되는 하단 경계
SRC_Y = 0.838             # 출처 줄
FILL_RATIO = 0.55         # 규칙 5 — 열을 이 비율 이하로 채울 때만 가운데
SHORT_K = 8               # 규칙 5 — 가운데를 허용하는 셀 폭 절대 상한 (폰트 × N)
SPREAD_K = 3.5            # 규칙 4 — 폰트 크기의 몇 배까지 편차를 허용하나
RE_INDEX = re.compile(r"\d+\s*[–\-~]?\s*\d*")

BAD = (202, 72, 72)       # 대비 구도의 좌측(부정) 캡션


# ────────────────────────── 공통 헬퍼 ──────────────────────────
def _lines(d, text, width, fn):
    """폭에 맞춰 줄바꿈. \\n 은 강제 개행."""
    out = []
    for para in str(text).split("\n"):
        words = para.split()
        if not words:
            out.append("")
            continue
        cur = ""
        for w in words:
            cand = (cur + " " + w).strip()
            if d.textlength(cand, font=fn) <= width or not cur:
                cur = cand
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def _block(d, x, y, w, lines, fn, fill, lh, align="left"):
    """줄 목록을 그린다. align=center 면 폭 w 안에서 가운데."""
    for ln in lines:
        tx = x if align == "left" else x + (w - d.textlength(ln, font=fn)) / 2
        d.text((tx, y), ln, font=fn, fill=fill)
        y += lh
    return y


def _header(d, s):
    """헤드라인+서브를 그리고 실제로 끝난 y 를 돌려준다."""
    return LE.typo(d, LE.M, int(LE.H * .155), s["head"],
                   s.get("sub") or [], maxw=int(LE.W * .88))


def _body_top(d, s, gap=44, floor=.34):
    """헤더 아래 · 최소 기준선 중 낮은 쪽. 고정 y 대신 반드시 이것을 쓴다."""
    return max(_header(d, s) + gap, int(LE.H * floor))


def _source(d, s, y=None):
    src = s.get("source")
    if src:
        yy = min(y if y is not None else int(LE.H * SRC_Y), int(LE.H * SRC_Y))
        d.text((LE.M, yy), "출처  " + src, font=LE.f("chrome", size=25), fill=LE.GREY)


def _cols_x(cols, widths):
    """열 경계 x 좌표. widths 는 상대 비율."""
    x0, x1 = LE.M, LE.W - LE.M
    ws = widths or [1] * len(cols)
    tot = float(sum(ws))
    xs = [x0]
    for w in ws:
        xs.append(xs[-1] + int((x1 - x0) * w / tot))
    xs[-1] = x1
    return xs


def align_of(d, cols, rows, wrapped, xs, fn, cpad):
    """열별 정렬 판정. 모듈 docstring 의 6개 규칙을 순서대로 적용한다."""
    out = []
    for c in range(len(cols)):
        cells = [str(r[c]).strip() for r in rows]

        # 1 — 일련번호 열
        if all(RE_INDEX.fullmatch(x) for x in cells):
            out.append("center"); continue

        # 2 — 1열은 행 라벨
        if c == 0:
            out.append("left"); continue

        # 3 — 줄바꿈이 생기는 열
        if any(len(wrapped[r][c]) > 1 for r in range(len(rows))):
            out.append("left"); continue

        ws = [d.textlength(x, font=fn) for x in cells]

        # 4 — 셀 폭 편차가 크면 가운데 정렬이 들쭉날쭉해진다
        if max(ws) - min(ws) > fn.size * SPREAD_K:
            out.append("left"); continue

        # 5 — 짧은 값이면서 열이 헐렁할 때만 가운데, 6 — 아니면 왼쪽
        inner = xs[c + 1] - xs[c] - cpad * 2
        cap = min(inner * FILL_RATIO, fn.size * SHORT_K)
        out.append("center" if max(ws) <= cap else "left")
    return out


# ────────────────────────── TABLE ──────────────────────────
def lay_TABLE(im, d, s):
    """표 — 최대 5열 × 6행 권장. 넘치면 폰트가 32→22 로 줄어든다."""
    ytop = _body_top(d, s, gap=40)
    cols, rows = s["columns"], s["rows"]
    xs = _cols_x(cols, s.get("widths"))
    x0, x1 = xs[0], xs[-1]

    limit = int(LE.H * BODY_BOT)
    hh, pad, cpad = 78, 26, 22

    for size in (32, 30, 28, 26, 24, 22):
        fn = LE.f("sub", size=size)
        lh = int(size * 1.34)
        wrapped = [[_lines(d, cell, xs[c + 1] - xs[c] - cpad * 2, fn)
                    for c, cell in enumerate(row)] for row in rows]
        rh = pad * 2 + max(max(len(x) for x in row) for row in wrapped) * lh
        if ytop + hh + rh * len(rows) <= limit:
            break

    # 남는 세로 공간을 행 높이로 분배 — 표가 본문 영역을 채우게 한다
    rh = max(rh, min((limit - ytop - hh) // len(rows), int(LE.H * .108)))
    hh = max(hh, int(rh * .74))

    align = s.get("align") or align_of(d, cols, rows, wrapped, xs, fn, cpad)

    d.rounded_rectangle((x0, ytop, x1, ytop + hh), radius=14, fill=LE.BLUE)
    d.rectangle((x0, ytop + hh - 16, x1, ytop + hh), fill=LE.BLUE)
    fh = LE.f("label", size=min(31, fn.size + 2))
    for c, col in enumerate(cols):
        _block(d, xs[c] + cpad, ytop + (hh - int(fh.size * 1.1)) // 2,
               xs[c + 1] - xs[c] - cpad * 2, [str(col)], fh, LE.WHITE, lh, align[c])

    for r, row in enumerate(wrapped):
        yy = ytop + hh + r * rh
        d.rectangle((x0, yy, x1, yy + rh),
                    fill=(247, 249, 250) if r % 2 == 0 else LE.WHITE)
        d.line((x0, yy + rh, x1, yy + rh), fill=LE.LINE, width=2)
        for c, cell in enumerate(row):
            if c:
                d.line((xs[c], yy + 6, xs[c], yy + rh - 6), fill=LE.LINE, width=2)
            _block(d, xs[c] + cpad, yy + (rh - len(cell) * lh) // 2,
                   xs[c + 1] - xs[c] - cpad * 2, cell, fn, LE.INK, lh, align[c])

    _source(d, s, ytop + hh + rh * len(rows) + 26)


# ────────────────────────── EXAMPLE ──────────────────────────
def lay_EXAMPLE(im, d, s):
    """대비 — 좌측이 부정(붉은 캡션), 우측이 개선. blocks=[(캡션, 본문, 해설), ...]"""
    ytop = _body_top(d, s, gap=40)
    blocks = s["blocks"]
    gap = 40
    bw = int((LE.W - 2 * LE.M - gap * (len(blocks) - 1)) / len(blocks))
    limit = int(LE.H * BODY_BOT)
    cap, pad = 74, 30

    for size in (39, 36, 33, 30, 28):
        fq = LE.f("label", size=size)
        fd = LE.f("sub", size=max(25, size - 10))
        lq, ld = int(size * 1.34), int(max(25, size - 10) * 1.34)
        need = 0
        for b in blocks:
            q = _lines(d, b[1], bw - pad * 2, fq)
            n = _lines(d, b[2], bw - pad * 2, fd)
            need = max(need, cap + 34 + len(q) * lq + 34 + len(n) * ld + pad)
        if ytop + need <= limit:
            break
    bh = min(limit - ytop, max(need, int(LE.H * .30)))

    for i, b in enumerate(blocks):
        x = LE.M + i * (bw + gap)
        color = BAD if i == 0 and len(blocks) > 1 else LE.BLUE
        d.rounded_rectangle((x, ytop, x + bw, ytop + bh), radius=22,
                            fill=(248, 249, 250), outline=LE.LINE, width=2)
        d.rounded_rectangle((x, ytop, x + bw, ytop + cap), radius=22, fill=color)
        d.rectangle((x, ytop + cap - 18, x + bw, ytop + cap), fill=color)
        fc = LE.f("label", size=31)
        d.text((x + pad, ytop + (cap - int(fc.size * 1.1)) // 2), b[0], font=fc, fill=LE.WHITE)
        y = _block(d, x + pad, ytop + cap + 34, bw - pad * 2,
                   _lines(d, b[1], bw - pad * 2, fq), fq, LE.INK, lq)
        d.line((x + pad, y + 18, x + bw - pad, y + 18), fill=LE.LINE, width=2)
        _block(d, x + pad, y + 42, bw - pad * 2,
               _lines(d, b[2], bw - pad * 2, fd), fd, LE.GREY, ld)

    _source(d, s, ytop + bh + 26)


# ────────────────────────── MATRIX ──────────────────────────
def lay_MATRIX(im, d, s):
    """2×2 — quadrants 는 좌상·우상·좌하·우하 순. 본문에 \\n 으로 예시를 붙인다."""
    ytop = _body_top(d, s, gap=56, floor=.36)
    bot = max(int(LE.H * .795), ytop + int(LE.H * .26))
    left, right = int(LE.W * .135), int(LE.W * .865)
    mx, my = (left + right) // 2, (ytop + bot) // 2
    fills = [(232, 246, 242), (247, 249, 250), (247, 249, 250), (251, 242, 237)]
    boxes = [(left, ytop, mx, my), (mx, ytop, right, my),
             (left, my, mx, bot), (mx, my, right, bot)]

    ft, fd = LE.f("label", size=31), LE.f("sub", size=27)
    for box, fill, q in zip(boxes, fills, s["quadrants"]):
        d.rectangle(box, fill=fill, outline=LE.WHITE, width=8)
        cw = box[2] - box[0] - 48
        body = _lines(d, q[1], cw, fd)
        total = int(ft.size * 1.15) + 16 + len(body) * int(27 * 1.3)
        y = box[1] + ((box[3] - box[1]) - total) // 2
        d.text((box[0] + 24, y), q[0], font=ft, fill=LE.INK)
        _block(d, box[0] + 24, y + int(ft.size * 1.15) + 16, cw,
               body, fd, LE.GREY, int(27 * 1.3))

    d.line((left, bot, right, bot), fill=LE.INK, width=4)
    d.line((left, ytop, left, bot), fill=LE.INK, width=4)
    fa = LE.f("chrome", size=27)
    xl = s.get("x_label", "")
    d.text((right - d.textlength(xl, font=fa), bot + 20), xl, font=fa, fill=LE.GREY)
    d.text((left - 8, ytop - 46), s.get("y_label", ""), font=fa, fill=LE.GREY)
    _source(d, s, bot + 66)


# ────────────────────────── BAR ──────────────────────────
def lay_BAR(im, d, s):
    """가로 막대 — 최대 6개 권장. 실측인지 예시인지 source 에 반드시 밝힌다."""
    ytop = _body_top(d, s, gap=56, floor=.40)
    bars = s["bars"]
    fl = LE.f("label", size=32)
    x0 = int(LE.M + max(d.textlength(str(b[0]), font=fl) for b in bars) + 46)
    x1 = int(LE.W * .90)
    limit = int(LE.H * BODY_BOT)

    step = max(92, min(152, (limit - ytop) // max(1, len(bars))))
    bh = min(74, step - 34)
    maxv = max(v for _, v in bars) or 1
    fv = LE.f("label", size=34)

    for i, (label, val) in enumerate(bars):
        yy = ytop + i * step
        d.text((LE.M, yy + (bh - int(fl.size * 1.1)) // 2), str(label), font=fl, fill=LE.INK)
        d.rounded_rectangle((x0, yy, x1, yy + bh), radius=18, fill=(238, 241, 244))
        xe = x0 + max(int(bh * .8), int((x1 - x0) * val / maxv))
        d.rounded_rectangle((x0, yy, xe, yy + bh), radius=18, fill=LE.BLUE)
        vt = str(val)
        vw = d.textlength(vt, font=fv)
        inside = xe - x0 > vw + 60
        vx = xe - vw - 24 if inside else min(xe + 22, LE.W - LE.M - vw)
        d.text((vx, yy + (bh - int(fv.size * 1.1)) // 2), vt, font=fv,
               fill=LE.WHITE if inside else LE.INK)

    _source(d, s, ytop + step * len(bars) + 18)


# ────────────────────────── 등록 ──────────────────────────
def register():
    """LAY 에 4개 구도를 얹는다. build() 전에 한 번 호출한다."""
    LE.LAY.update({"TABLE": lay_TABLE, "EXAMPLE": lay_EXAMPLE,
                   "MATRIX": lay_MATRIX, "BAR": lay_BAR})
    return LE.LAY


def _add(d, lay, eyebrow, head, sub, **data):
    d.slide(lay, eyebrow, head, sub)
    s = d.slides[-1]
    s["scene"] = None            # 씬을 만들지 않는다 — jobs() 가 건너뛴다
    s.update(data)
    d.save()
    return d


def table(d, eyebrow, head, sub, columns, rows, widths=None, align=None, source=None):
    """표. widths 는 열 상대 비율, align 은 열별 수동 정렬(규칙보다 우선)."""
    return _add(d, "TABLE", eyebrow, head, sub, columns=columns, rows=rows,
                widths=widths, align=align, source=source)


def example(d, eyebrow, head, sub, blocks, source=None):
    """대비. blocks=[(캡션, 본문, 해설), ...] — 첫 블록이 붉은 캡션(부정)."""
    return _add(d, "EXAMPLE", eyebrow, head, sub, blocks=blocks, source=source)


def matrix(d, eyebrow, head, sub, quadrants, x_label, y_label, source=None):
    """2×2. quadrants 는 좌상·우상·좌하·우하 순 [(제목, 본문), ...]."""
    return _add(d, "MATRIX", eyebrow, head, sub, quadrants=quadrants,
                x_label=x_label, y_label=y_label, source=source)


def bar(d, eyebrow, head, sub, bars, source=None):
    """가로 막대. bars=[(라벨, 값), ...]."""
    return _add(d, "BAR", eyebrow, head, sub, bars=bars, source=source)

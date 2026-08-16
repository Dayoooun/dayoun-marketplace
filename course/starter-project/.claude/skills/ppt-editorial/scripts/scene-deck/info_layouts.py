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
IL.register()                    # LAY 에 7개 정보 구도 등록 — build() 전에 한 번

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
- 내용이 24px 이상 투사용 크기에서 본문·footer 경계에 맞지 않으면 ValueError로 BLOCK하고 슬라이드를 나눈다.
"""
import math
import re

import layout_engine as LE

BODY_BOT = 0.815          # 본문이 침범하면 안 되는 하단 경계
SRC_Y = 0.838             # 출처 줄
FILL_RATIO = 0.55         # 규칙 5 — 열을 이 비율 이하로 채울 때만 가운데
SHORT_K = 8               # 규칙 5 — 가운데를 허용하는 셀 폭 절대 상한 (폰트 × N)
SPREAD_K = 3.5            # 규칙 4 — 폰트 크기의 몇 배까지 편차를 허용하나
RE_INDEX = re.compile(r"\d+\s*[–\-~]?\s*\d*")
MIN_PROJECTED_FONT = 24

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


def _assert_lines_fit(d, lines, width, font, layout):
    overflowing = [line for line in lines if d.textlength(line, font=font) > width]
    if overflowing:
        raise ValueError(
            f"{layout} text exceeds its card width at {font.size}px; "
            "shorten content or split the slide"
        )


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
    """표 — 최대 5열 × 6행 권장. font_sizes로 투사용 본문 크기를 고정할 수 있다."""
    ytop = _body_top(d, s, gap=40)
    cols, rows = s["columns"], s["rows"]
    if not cols or not rows:
        raise ValueError("TABLE requires at least one column and one row")
    if any(len(row) != len(cols) for row in rows):
        raise ValueError("TABLE row width must match the column count")
    xs = _cols_x(cols, s.get("widths"))
    x0, x1 = xs[0], xs[-1]

    limit = int(LE.H * BODY_BOT)
    hh, pad, cpad = 78, 26, 22

    requested_sizes = s.get("font_sizes", (32, 30, 28, 26, 24, 22))
    sizes = [int(size) for size in requested_sizes if int(size) >= MIN_PROJECTED_FONT]
    if not sizes:
        raise ValueError(
            f"TABLE requires a projection font of at least {MIN_PROJECTED_FONT}px"
        )
    fits = False
    for size in sizes:
        fn = LE.f("sub", size=size)
        lh = int(size * 1.34)
        wrapped = [
            [
                _lines(d, cell, xs[c + 1] - xs[c] - cpad * 2, fn)
                for c, cell in enumerate(row)
            ]
            for row in rows
        ]
        for row in wrapped:
            for column, cell in enumerate(row):
                _assert_lines_fit(
                    d,
                    cell,
                    xs[column + 1] - xs[column] - cpad * 2,
                    fn,
                    "TABLE",
                )
        rh = pad * 2 + max(max(len(cell) for cell in row) for row in wrapped) * lh
        if ytop + hh + rh * len(rows) <= limit:
            fits = True
            break
    if not fits:
        raise ValueError(
            "TABLE exceeds the body/footer boundary at the minimum projection font; "
            "split the table across slides"
        )

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


# ────────────────────────── FLOW ──────────────────────────
def _arrow(d, start, end, color=LE.BLUE, width=5):
    x1, y1 = start
    x2, y2 = end
    d.line((x1, y1, x2, y2), fill=color, width=width)
    dx, dy = x2 - x1, y2 - y1
    length = max(1.0, math.hypot(dx, dy))
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    base_x, base_y = x2 - ux * 18, y2 - uy * 18
    d.polygon(
        [
            (x2, y2),
            (base_x + px * 10, base_y + py * 10),
            (base_x - px * 10, base_y - py * 10),
        ],
        fill=color,
    )


def lay_FLOW(im, d, s):
    """모듈 흐름 — cols 열의 뱀형 경로. step·title·detail 튜플을 순서대로 연결한다."""
    ytop = _body_top(d, s, gap=38, floor=.34)
    modules = s["modules"]
    cols = s.get("cols", 3)
    if not modules:
        raise ValueError("FLOW requires at least one module")
    if not isinstance(cols, int) or not 1 <= cols <= 5:
        raise ValueError("FLOW cols must be between 1 and 5")
    rows = math.ceil(len(modules) / cols)
    gap_x, gap_y = 34, 34
    limit = int(LE.H * BODY_BOT)
    total_w = LE.W - 2 * LE.M
    bw = (total_w - gap_x * (cols - 1)) // cols
    bh = min(226, (limit - ytop - gap_y * (rows - 1)) // rows)
    if bh < 150:
        raise ValueError(
            "FLOW cards are too short for projection text; reduce modules or split the slide"
        )
    positions = []

    for index in range(len(modules)):
        row, offset = divmod(index, cols)
        col = offset if row % 2 == 0 else cols - 1 - offset
        x = LE.M + col * (bw + gap_x)
        y = ytop + row * (bh + gap_y)
        positions.append((x, y, x + bw, y + bh))

    for index in range(len(positions) - 1):
        current = positions[index]
        following = positions[index + 1]
        current_cy = (current[1] + current[3]) // 2
        following_cy = (following[1] + following[3]) // 2
        if current[1] == following[1]:
            if following[0] > current[0]:
                start = (current[2] + 6, current_cy)
                end = (following[0] - 8, following_cy)
            else:
                start = (current[0] - 6, current_cy)
                end = (following[2] + 8, following_cy)
        else:
            start = ((current[0] + current[2]) // 2, current[3] + 5)
            end = ((following[0] + following[2]) // 2, following[1] - 8)
        _arrow(d, start, end, color=(170, 184, 199), width=4)

    chosen = None
    for title_size, detail_size in ((34, 28), (32, 27), (30, 26)):
        ft = LE.f("label", size=title_size)
        fd = LE.f("sub", size=detail_size)
        title_lh = int(ft.size * 1.24)
        detail_lh = int(fd.size * 1.28)
        fits = True
        for module, box in zip(modules, positions):
            title = str(module[1])
            detail = str(module[2]) if len(module) > 2 else ""
            maxw = box[2] - box[0] - 40
            title_lines = _lines(d, title, maxw, ft)
            detail_lines = _lines(d, detail, maxw, fd) if detail else []
            _assert_lines_fit(d, title_lines, maxw, ft, "FLOW")
            _assert_lines_fit(d, detail_lines, maxw, fd, "FLOW")
            content_bottom = 76 + len(title_lines) * title_lh
            if detail_lines:
                content_bottom += 24 + len(detail_lines) * detail_lh
            if content_bottom > bh - 16:
                fits = False
                break
        if fits:
            chosen = (ft, fd)
            break
    if chosen is None:
        raise ValueError(
            "FLOW content does not fit at the minimum projection font; "
            "shorten modules or split the slide"
        )
    ft, fd = chosen
    fs = LE.f("chrome", size=MIN_PROJECTED_FONT)
    highlights = set(str(value) for value in s.get("highlight_steps", []))

    for module, box in zip(modules, positions):
        step, title = str(module[0]), str(module[1])
        detail = str(module[2]) if len(module) > 2 else ""
        x0, y0, x1, y1 = box
        highlight = step in highlights
        fill = (235, 244, 255) if highlight else (248, 250, 252)
        outline = LE.BLUE if highlight else LE.LINE
        d.rounded_rectangle(box, radius=22, fill=fill, outline=outline, width=3)
        d.rounded_rectangle((x0 + 20, y0 + 18, x0 + 86, y0 + 58), radius=14, fill=LE.BLUE)
        sw = d.textlength(step, font=fs)
        d.text((x0 + 53 - sw / 2, y0 + 22), step, font=fs, fill=LE.WHITE)

        maxw = x1 - x0 - 40
        title_lines = _lines(d, title, maxw, ft)
        y = _block(d, x0 + 20, y0 + 76, maxw, title_lines, ft, LE.INK, int(ft.size * 1.24))
        if detail:
            d.line((x0 + 20, y + 10, x1 - 20, y + 10), fill=LE.LINE, width=2)
            _block(
                d,
                x0 + 20,
                y + 24,
                maxw,
                _lines(d, detail, maxw, fd),
                fd,
                LE.GREY,
                int(fd.size * 1.28),
            )

    note = s.get("footer_note")
    if note:
        fn = LE.f("chrome", size=24)
        d.text((LE.M, limit + 22), str(note), font=fn, fill=LE.GREY)
    _source(d, s, limit + 54)


# ────────────────────────── GENEALOGY ──────────────────────────
def lay_GENEALOGY(im, d, s):
    """엔지니어링 계보 — 번호 timeline과 분리된 동일 폭 카드로 설명한다."""
    ytop = _body_top(d, s, gap=32, floor=.31)
    modules = s["modules"]
    if not modules:
        raise ValueError("GENEALOGY requires at least one module")
    limit = int(LE.H * BODY_BOT)
    gap = 14
    row_h = min(134, (limit - ytop - gap * (len(modules) - 1)) // len(modules))
    if row_h < 96:
        raise ValueError(
            "GENEALOGY rows are too short for projection text; split the slide"
        )
    connector_x = LE.M + 42
    card_x0 = LE.M + 112
    card_x1 = LE.W - LE.M
    ft = LE.f("label", size=32)
    fd = LE.f("sub", size=27)
    fg = LE.f("chrome", size=MIN_PROJECTED_FONT)
    fn = LE.f("chrome", size=MIN_PROJECTED_FONT)
    highlight = int(s.get("highlight", 2))
    card_inner = card_x1 - card_x0 - 56
    for module in modules:
        name = str(module[0])
        description = str(module[1])
        group = str(module[2]) if len(module) > 2 else ""
        _assert_lines_fit(d, [description], card_inner, fd, "GENEALOGY")
        reserved_group = d.textlength(group, font=fg) + 32 if group else 0
        _assert_lines_fit(
            d,
            [name],
            card_inner - reserved_group,
            ft,
            "GENEALOGY",
        )

    d.line(
        (
            connector_x,
            ytop + row_h // 2,
            connector_x,
            ytop + (row_h + gap) * (len(modules) - 1) + row_h // 2,
        ),
        fill=(180, 190, 201),
        width=4,
    )

    for index, module in enumerate(modules):
        name, description = str(module[0]), str(module[1])
        group = str(module[2]) if len(module) > 2 else ""
        y0 = ytop + index * (row_h + gap)
        y1 = y0 + row_h
        is_highlight = index == highlight
        fill = (230, 241, 255) if is_highlight else (248, 249, 250)
        outline = LE.BLUE if is_highlight else LE.LINE

        d.ellipse(
            (
                connector_x - 25,
                y0 + row_h // 2 - 25,
                connector_x + 25,
                y0 + row_h // 2 + 25,
            ),
            fill=LE.BLUE,
        )
        step = f"{index + 1:02d}"
        step_w = d.textlength(step, font=fn)
        d.text(
            (connector_x - step_w / 2, y0 + row_h // 2 - 12),
            step,
            font=fn,
            fill=LE.WHITE,
        )

        d.rounded_rectangle(
            (card_x0, y0, card_x1, y1),
            radius=18,
            fill=fill,
            outline=outline,
            width=3,
        )
        d.text((card_x0 + 28, y0 + 18), name, font=ft, fill=LE.INK)
        d.text((card_x0 + 28, y0 + 54), description, font=fd, fill=(72, 82, 94))
        if group:
            group_w = d.textlength(group, font=fg)
            d.text(
                (card_x1 - 28 - group_w, y0 + 22),
                group,
                font=fg,
                fill=LE.BLUE if is_highlight else LE.GREY,
            )

    note = s.get("note")
    if note:
        note_font = LE.f("chrome", size=24)
        d.text((LE.M, limit + 22), str(note), font=note_font, fill=LE.GREY)
    _source(d, s, limit + 54)


# ────────────────────────── PROMPT ──────────────────────────
def lay_PROMPT(im, d, s):
    """복사용 프롬프트 — 코드 블록과 실행 후 확인값을 한 화면에 보여준다."""
    ytop = _body_top(d, s, gap=38, floor=.33)
    x0, x1 = LE.M, LE.W - LE.M
    prompt_lines = s["prompt"]
    checks = s.get("checks", [])
    if not prompt_lines:
        raise ValueError("PROMPT requires at least one prompt line")
    card_bottom = int(LE.H * .71)
    d.rounded_rectangle((x0, ytop, x1, card_bottom), radius=24, fill=(30, 36, 46))
    d.rounded_rectangle((x0, ytop, x1, ytop + 66), radius=24, fill=(41, 50, 63))
    d.rectangle((x0, ytop + 42, x1, ytop + 66), fill=(41, 50, 63))
    fl = LE.f("label", size=25)
    d.text((x0 + 28, ytop + 19), "PROMPT", font=fl, fill=(123, 181, 255))

    fp = LE.f("sub", size=31)
    line_h = int(fp.size * 1.34)
    y = ytop + 92
    maxw = x1 - x0 - 64
    for raw in prompt_lines:
        color = (123, 181, 255) if str(raw).startswith("https://") else LE.WHITE
        wrapped = _lines(d, raw, maxw, fp)
        _assert_lines_fit(d, wrapped, maxw, fp, "PROMPT")
        y = _block(d, x0 + 32, y, maxw, wrapped, fp, color, line_h)
        y += 8
    if y > card_bottom - 24:
        raise ValueError(
            "PROMPT text exceeds the code card; shorten it or split the slide"
        )

    if checks:
        if len(checks) > 4:
            raise ValueError("PROMPT supports at most four projection check cards")
        gap = 24
        box_w = (x1 - x0 - gap * (len(checks) - 1)) // len(checks)
        box_y0 = card_bottom + 30
        box_y1 = min(int(LE.H * BODY_BOT), box_y0 + 94)
        fc = LE.f("label", size=25)
        for index, check in enumerate(checks):
            bx0 = x0 + index * (box_w + gap)
            bx1 = bx0 + box_w
            d.rounded_rectangle((bx0, box_y0, bx1, box_y1), radius=18, fill=(237, 244, 255))
            text = str(check)
            if d.textlength(str(check), font=fc) > box_w - 32:
                raise ValueError(
                    "PROMPT check text exceeds its card; shorten it or split the slide"
                )
            tw = d.textlength(text, font=fc)
            d.text((bx0 + (box_w - tw) / 2, box_y0 + 29), text, font=fc, fill=LE.BLUE)
    _source(d, s, int(LE.H * BODY_BOT) + 30)

# ────────────────────────── 등록 ──────────────────────────
def register():
    """LAY 에 7개 정보 구도를 얹는다. build() 전에 한 번 호출한다."""
    LE.LAY.update(
        {
            "TABLE": lay_TABLE,
            "EXAMPLE": lay_EXAMPLE,
            "MATRIX": lay_MATRIX,
            "BAR": lay_BAR,
            "FLOW": lay_FLOW,
            "GENEALOGY": lay_GENEALOGY,
            "PROMPT": lay_PROMPT,
        }
    )
    return LE.LAY


def _add(d, lay, eyebrow, head, sub, **data):
    d.slide(lay, eyebrow, head, sub)
    s = d.slides[-1]
    s["scene"] = None            # 씬을 만들지 않는다 — jobs() 가 건너뛴다
    s.update(data)
    d.save()
    return d


def table(
    d,
    eyebrow,
    head,
    sub,
    columns,
    rows,
    widths=None,
    align=None,
    source=None,
    font_sizes=None,
):
    """표. widths·font_sizes를 조정할 수 있고 align 수동 지정은 규칙보다 우선한다."""
    data = {
        "columns": columns,
        "rows": rows,
        "widths": widths,
        "align": align,
        "source": source,
    }
    if font_sizes:
        data["font_sizes"] = font_sizes
    return _add(d, "TABLE", eyebrow, head, sub, **data)


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


def flow(
    d,
    eyebrow,
    head,
    sub,
    modules,
    cols=3,
    highlight_steps=None,
    footer_note=None,
    source=None,
):
    """순서형 모듈 그래프. modules=[(step, title, detail), ...]."""
    return _add(
        d,
        "FLOW",
        eyebrow,
        head,
        sub,
        modules=modules,
        cols=cols,
        highlight_steps=highlight_steps or [],
        footer_note=footer_note,
        source=source,
    )


def genealogy(d, eyebrow, head, sub, modules, highlight=2, note=None, source=None):
    """엔지니어링 계보. modules=[(name, description, group), ...]."""
    return _add(
        d,
        "GENEALOGY",
        eyebrow,
        head,
        sub,
        modules=modules,
        highlight=highlight,
        note=note,
        source=source,
    )


def prompt(d, eyebrow, head, sub, prompt_lines, checks=None, source=None):
    """복사용 프롬프트 코드 블록과 실행 후 확인값."""
    return _add(
        d,
        "PROMPT",
        eyebrow,
        head,
        sub,
        prompt=prompt_lines,
        checks=checks or [],
        source=source,
    )

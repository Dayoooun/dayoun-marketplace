# -*- coding: utf-8 -*-
"""v3 조립 — 내용에 최적화된 4가지 구도
   L: 좌텍스트/우씬   |   W: 상단텍스트/하단 와이드씬
   C: 중앙정렬 대형    |   S: 좌씬/우텍스트 (반전)
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
SCN = os.path.join(BASE, "scenes3")
OUT = os.path.join(BASE, "v3_out")
os.makedirs(OUT, exist_ok=True)

W, H = 2560, 1440
M = int(W * 0.030)

# SAFE ZONE — 본문이 침범하면 안 되는 상하 경계 (크롬이 차지하는 영역)
BODY_TOP = int(H * 0.150)
BODY_BOT = int(H * 0.855)

BLUE = (43, 110, 242)
INK = (22, 29, 43)
GREY = (122, 132, 148)
LINE = (228, 231, 236)
WHITE = (255, 255, 255)

# ── 타이포그래피는 fonts.py 표준을 쓴다 (맑은고딕 하드코딩 금지)
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fonts import font as TF, metrics as TM, draw_tracked   # noqa: E402

FAMILY = "pretendard"      # 프로젝트별로 덮어쓴다 (presets.py의 fonts.head)

FOOT = ""                  # 발신주체. Deck(foot=...) 로 넘긴다 — 하드코딩 금지


def f(role, size=None, weight=None):
    """역할 기반 폰트. f("headline") / f("sub", 28)"""
    return TF(role, family=FAMILY, size=size, weight=weight)


def _legacy_f(sz, p=None):
    return ImageFont.truetype(p, sz)


def trim(im, thr=248):
    a = np.array(im.convert("L"))
    ys, xs = np.nonzero(a < thr)
    if not len(xs):
        return im
    p = 8
    return im.crop((max(0, xs.min() - p), max(0, ys.min() - p),
                    min(im.width, xs.max() + p), min(im.height, ys.max() + p)))


def scene(name):
    path = os.path.join(SCN, "%s.png" % name)
    if not os.path.exists(path):
        return None
    image = Image.open(path).convert("RGB")
    if os.path.isfile(path + ".safe.json"):
        return image
    return trim(image)


def chrome(im, d, eyebrow, num, total):
    ey = int(H * 0.062)
    d.rounded_rectangle((M, ey + 12, M + 62, ey + 20), radius=4, fill=BLUE)
    d.text((M + 86, ey), eyebrow, font=f("eyebrow"), fill=BLUE)
    fn = f("chrome", 38)
    d.text((W - M - d.textlength(num, font=fn), ey - 4), num, font=fn, fill=(178, 186, 198))
    by = int(H * 0.889)
    d.line([(M, by), (W - M, by)], fill=LINE, width=2)
    ff = f("chrome")
    d.text((M, by + 30), FOOT, font=ff, fill=GREY)
    pg = "%s / %02d" % (num, total)
    d.text((W - M - d.textlength(pg, font=ff), by + 30), pg, font=ff, fill=GREY)


def _wrap(d, text, fnt, maxw, trk=0.0):
    """어절 단위 줄바꿈. 한 어절이 폭을 넘으면 그 어절만 글자 단위로 자른다."""
    def w(t):
        return d.textlength(t, font=fnt) + trk * max(0, len(t) - 1)
    if w(text) <= maxw:
        return [text]
    out, cur = [], ""
    for word in text.split(" "):
        cand = (cur + " " + word).strip()
        if w(cand) <= maxw or not cur:
            cur = cand
        else:
            out.append(cur); cur = word
        while w(cur) > maxw and len(cur) > 1:      # 초장문 어절
            cut = len(cur)
            while cut > 1 and w(cur[:cut]) > maxw:
                cut -= 1
            out.append(cur[:cut]); cur = cur[cut:]
    if cur:
        out.append(cur)
    return out


def _fit_role(d, lines, role, maxw, min_ratio=0.62):
    """폰트를 줄여 maxw 안에 들어오게 한다. 반환=(폰트, metrics, 줄목록)"""
    base = TM(role, FAMILY)
    size = base["size"]
    floor = max(28, int(size * min_ratio))
    while size >= floor:
        fnt = f(role, size=size)
        trk = base["tracking_px"] * size / base["size"]
        wrapped = []
        for ln in lines:
            wrapped.extend(_wrap(d, ln, fnt, maxw, trk))
        # 줄 수가 3을 넘으면 더 줄인다 (헤드라인은 2줄이 기본)
        if len(wrapped) <= 3:
            lead = int(round(size * (base["leading"] / base["size"])))
            return fnt, {"leading": lead, "tracking_px": trk}, wrapped
        size -= 6
    fnt = f(role, size=floor)
    trk = base["tracking_px"] * floor / base["size"]
    wrapped = []
    for ln in lines:
        wrapped.extend(_wrap(d, ln, fnt, maxw, trk))
    lead = int(round(floor * (base["leading"] / base["size"])))
    return fnt, {"leading": lead, "tracking_px": trk}, wrapped


def typo(d, x, y, head, sub, role="headline", align="left", center=False, maxw=None):
    """헤드라인 + 서브 렌더. 크기·행간·자간은 fonts.py 황금비 스케일을 따른다."""
    if center:
        align = "center"
    # 사용 가능한 폭: 좌측 정렬이면 x부터 우측 여백까지, 중앙이면 캔버스 폭의 84%
    avail = maxw or (int(W * 0.84) if align == "center" else (W - M - x))
    fh, mh, hlines = _fit_role(d, head, role, avail)
    for ln in hlines:
        w = d.textlength(ln, font=fh) + mh["tracking_px"] * max(0, len(ln) - 1)
        tx = x if align == "left" else x - w / 2
        draw_tracked(d, (tx, y), ln, fh, INK, mh["tracking_px"])
        y += mh["leading"]
    y += 34
    fs = f("sub")
    ms = TM("sub", FAMILY)
    slines = []
    for ln in sub:
        slines.extend(_wrap(d, ln, fs, avail, ms["tracking_px"]))
    for ln in slines:
        w = d.textlength(ln, font=fs) + ms["tracking_px"] * max(0, len(ln) - 1)
        tx = x if align == "left" else x - w / 2
        draw_tracked(d, (tx, y), ln, fs, GREY, ms["tracking_px"])
        y += ms["leading"]
    return y


def fit(sc, bw, bh):
    """씬 이미지를 박스(bw x bh)에 비율 유지로 맞춘다."""
    r = min(bw / sc.width, bh / sc.height)
    return sc.resize((max(1, int(sc.width * r)), max(1, int(sc.height * r))), Image.LANCZOS)


def place_right(im, sc, right_x, top):
    """씬을 우측 기준으로 붙이되 콘텐츠가 여백을 넘지 않게 보정.

    trim()으로 흰 여백을 걷어낸 씬은 콘텐츠가 가장자리에 딱 붙어 있다.
    그대로 우변에 맞추면 안티에일리어싱 픽셀이 여백선을 넘어 QC가 위반을 잡는다.
    (실측: A 구도에서 우측 0.990 — 씬이 캔버스 91%를 채운 경우)
    """
    pad = max(2, int(sc.width * 0.012))
    im.paste(sc, (right_x - sc.width - pad, top))


# ══════════ 구도별 빌더 ══════════
def _emphasis(im, d, s, x, y):
    """스펙에 강조 요소가 있으면 렌더. 없으면 no-op.
    spec 예: {"num": ["2,800", "회", "연간 커밋"], "chips": ["경영", "기술"]}"""
    hero, pale = BLUE, _pale()
    if s.get("num"):
        v = s["num"]
        y = accent_number(d, x, y, v[0], v[1] if len(v) > 1 else "",
                          v[2] if len(v) > 2 else "", hero)
    if s.get("chips"):
        y = keyword_chips(d, x, y + 8, s["chips"], hero, pale) + 24
    return y


def _pale():
    """hero에서 밝은 배경색 파생 (칩 배경용)"""
    r, g, b = BLUE
    return (min(255, r + (255 - r) * 87 // 100),
            min(255, g + (255 - g) * 87 // 100),
            min(255, b + (255 - b) * 87 // 100))


def lay_L(im, d, s):
    """좌 텍스트 / 우 씬 — 개념 설명용"""
    sc = scene(s["scene"])
    if sc:
        bw, bh = int(W * 0.42), int(H * 0.60)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        place_right(im, sc, W - M - int(W * 0.02),
                    int(H * 0.20) + (bh - sc.height) // 2)
    _y = typo(d, M, int(H * 0.245), s["head"], s["sub"], maxw=int(W * 0.50))
    _emphasis(im, d, s, M, _y + 18)


def lay_S(im, d, s):
    """좌 씬 / 우 텍스트 — 리듬 전환용(반전)"""
    sc = scene(s["scene"])
    if sc:
        bw, bh = int(W * 0.40), int(H * 0.60)
        r = min(bw / sc.width, bh / sc.height)
        sc = sc.resize((int(sc.width * r), int(sc.height * r)), Image.LANCZOS)
        im.paste(sc, (M + int(W * 0.02), int(H * 0.20) + (bh - sc.height) // 2))
    _y = typo(d, int(W * 0.52), int(H * 0.245), s["head"], s["sub"], maxw=int(W * 0.42))
    _emphasis(im, d, s, int(W * 0.52), _y + 18)


def lay_W(im, d, s):
    """상단 텍스트 / 하단 와이드 씬 — 프로세스 플로우용.
    씬 영역을 고정하지 않고 텍스트가 실제로 차지한 높이 아래 남은 공간을 모두 쓴다.
    (고정 H*0.40이면 텍스트가 짧을 때 상단이 비고 씬이 하단으로 쏠린다 — 실측)"""
    y = typo(d, M, int(H * 0.16), s["head"], s["sub"], role="title")
    y = _emphasis(im, d, s, M, y + 10)
    sc = scene(s["scene"])
    if sc:
        top = y + 28
        bw = W - M * 2 - int(W * 0.04)
        bh = max(int(H * 0.28), BODY_BOT - top)
        sc = fit(sc, bw, bh)
        im.paste(sc, ((W - sc.width) // 2, top + (bh - sc.height) // 2))


def lay_C(im, d, s):
    """중앙 정렬 — 비교/교집합 등 대칭 구도용.
    typo()를 그대로 쓴다(자체 렌더하면 줄바꿈·폰트축소 보호가 빠져 오버플로우 — 실측)."""
    y = typo(d, W // 2, int(H * 0.155), s["head"], s["sub"],
             role="title", center=True, maxw=int(W * 0.78))
    y = _emphasis(im, d, s, W // 2, y + 12)
    sc = scene(s["scene"])
    if sc:
        top = y + 24
        bh = max(int(H * 0.30), BODY_BOT - top)
        sc = fit(sc, int(W * 0.56), bh)
        im.paste(sc, ((W - sc.width) // 2, top + (bh - sc.height) // 2))




# ══════ 확장 구도 (2026-08-01 G003) ══════
def lay_A(im, d, s):
    """A — 비대칭 대형: 씬을 우측에 크게, 텍스트는 좌측 상단.
    임팩트가 필요한 장(오프닝·핵심 주장)에 쓴다.
    ★ 씬 우변은 반드시 M(=W*0.030) 안쪽에 둔다. 예전엔 W*0.01 오프셋이라
      여백을 침범해 deck_qc가 우측 위반을 잡았다(실측 0.979)."""
    sc = scene(s["scene"])
    if sc:
        sc = fit(sc, int(W * 0.58), int(H * 0.70))
        place_right(im, sc, W - M, int(H * 0.17))
    _y = typo(d, M, int(H * 0.22), s["head"], s["sub"], maxw=int(W * 0.36))
    _emphasis(im, d, s, M, _y + 18)


def lay_F(im, d, s):
    """F — 전면(full-bleed): 씬을 화면 폭 전체로 깔고 텍스트를 좌측 상단에 얹는다.
    분위기·규모를 보여줄 때. 씬 하단이 크롬과 겹치지 않게 상단 정렬."""
    sc = scene(s["scene"])
    if sc:
        sc = fit(sc, int(W * 0.98), int(H * 0.66))
        im.paste(sc, ((W - sc.width) // 2, int(H * 0.24)))
    typo(d, M, int(H * 0.165), s["head"], s["sub"], role="title")


def lay_T(im, d, s):
    """T — 3분할: 좌 텍스트 / 중앙 씬 / 우 보조 리스트.
    항목 나열이 있는 장. s["items"] = [(제목, 설명), ...] 최대 3개."""
    sc = scene(s["scene"])
    if sc:
        sc = fit(sc, int(W * 0.30), int(H * 0.52))
        im.paste(sc, (int(W * 0.355), int(H * 0.24) + (int(H * 0.52) - sc.height) // 2))
    y = typo(d, M, int(H * 0.245), s["head"], s["sub"], maxw=int(W * 0.30))
    _emphasis(im, d, s, M, y + 18)
    items = s.get("items") or []
    if items:
        x = int(W * 0.70)
        y = int(H * 0.27)
        for t, desc in items[:3]:
            d.rounded_rectangle((x, y, W - M, y + int(H * 0.13)), radius=20,
                                fill=(246, 248, 250))
            d.text((x + 28, y + 26), t, font=f("label"), fill=INK)
            d.text((x + 28, y + 72), desc, font=f("sub", 28), fill=GREY)
            y += int(H * 0.155)




# ══════ 강조 요소 (2026-08-01 G003) ══════
def accent_number(d, x, y, num, unit, caption, hero):
    """대형 수치 강조. 헤드라인 아래에 배치해 시선을 붙든다."""
    fn = f("num")
    fu = f("label", 40)
    fc = f("sub", 30)
    draw_tracked(d, (x, y), num, fn, hero, TM("num", FAMILY)["tracking_px"])
    nw = d.textlength(num, font=fn)
    if unit:
        d.text((x + nw + 12, y + fn.size - fu.size - 6), unit, font=fu, fill=hero)
    if caption:
        d.text((x, y + fn.size + 16), caption, font=fc, fill=GREY)
    return y + fn.size + 60


def keyword_chips(d, x, y, words, hero, pale):
    """핵심 키워드 칩. 서브 텍스트보다 강하고 헤드라인보다 약한 중간 위계."""
    fk = f("label", 32)
    cx = x
    for w in words:
        tw_ = d.textlength(w, font=fk)
        pad = 22
        d.rounded_rectangle((cx, y, cx + tw_ + pad * 2, y + 56), radius=28, fill=pale)
        d.text((cx + pad, y + 12), w, font=fk, fill=hero)
        cx += tw_ + pad * 2 + 14
    return y + 56


def connector(d, x0, y0, x1, y1, hero, dashed=True):
    """텍스트 축과 씬을 잇는 얇은 연결선. 시각적 연결 강화."""
    if dashed:
        step = 16
        dx, dy = x1 - x0, y1 - y0
        n = max(1, int((dx ** 2 + dy ** 2) ** 0.5 / step))
        for i in range(0, n, 2):
            a = i / n
            b = min(1.0, (i + 1) / n)
            d.line([(x0 + dx * a, y0 + dy * a), (x0 + dx * b, y0 + dy * b)],
                   fill=hero, width=3)
    else:
        d.line([(x0, y0), (x1, y1)], fill=hero, width=3)


def align_axis(d, x, top, bottom, hero):
    """좌측 정렬 축 — 헤드라인 왼쪽에 얇은 세로선. 텍스트 블록을 묶어준다."""
    d.rounded_rectangle((x - 22, top, x - 16, bottom), radius=3, fill=hero)




# ══════ 실무 필수 구도 (2026-08-01) — 표지·목차·클로징 ══════
def lay_COVER(im, d, s):
    """표지 — 좌 대형타이포 + 발신 정보 / 우 씬. 크롬은 최소화.
    기준 덱 실측: eyebrow(영문) → 초대형 헤드 2줄 → 서브 → 발신주체."""
    sc = scene(s["scene"])
    if sc:
        sc = fit(sc, int(W * 0.46), int(H * 0.72))
        place_right(im, sc, W - M, (H - sc.height) // 2)
    # 텍스트 블록 높이를 먼저 재서 세로 중앙에 놓는다.
    # 고정 y(0.26)면 짧은 표지에서 하단이 크게 비고 상단으로 쏠린다(실측).
    x = M
    fe_ = f("eyebrow")
    n_head = len(s["head"])
    n_sub = len(s.get("sub") or [])
    n_meta = len(s.get("meta") or [])
    est = (int(fe_.size * 2.0)
           + TM("display", FAMILY)["leading"] * n_head + 34
           + TM("sub", FAMILY)["leading"] * n_sub
           + 40 + (58 if s.get("issuer") else 0) + 44 * n_meta)
    y = max(int(H * 0.18), (H - est) // 2)
    # 영문 eyebrow
    me = TM("eyebrow", FAMILY)
    draw_tracked(d, (x, y), s.get("eyebrow", ""), fe_, BLUE, me["tracking_px"])
    y += int(fe_.size * 2.0)
    # 초대형 헤드라인
    y = typo(d, x, y, s["head"], s.get("sub") or [],
             role="display", maxw=int(W * 0.46))
    # 발신 주체 (조직명 + 부가정보)
    y += 40
    if s.get("issuer"):
        d.text((x, y), s["issuer"], font=f("label", 40), fill=INK)
        y += 58
    for ln in (s.get("meta") or []):
        d.text((x, y), ln, font=f("sub", 30), fill=GREY)
        y += 44


def lay_AGENDA(im, d, s):
    """목차 — 번호 + 제목 리스트. items=[(번호, 제목), ...] 최대 6."""
    # eyebrow는 크롬이 이미 그린다 — 여기서 또 그리면 중복(실측)
    x = M
    y = typo(d, x, int(H * 0.175), s["head"], s.get("sub") or [],
             role="title", maxw=int(W * 0.60))
    y += 30
    items = (s.get("items") or [])[:6]
    fn = f("num", 54)
    ft = f("label", 44)
    for i, it in enumerate(items, 1):
        num, title = it if isinstance(it, (list, tuple)) else ("%02d" % i, it)
        d.text((x + 8, y + 6), str(num), font=fn, fill=BLUE)
        d.text((x + 160, y + 12), title, font=ft, fill=INK)
        yy = y + 82
        if i < len(items):
            d.line([(x, yy), (W - M - int(W * 0.20), yy)], fill=LINE, width=2)
        y = yy + 18
    sc = scene(s["scene"])
    if sc:
        sc = fit(sc, int(W * 0.30), int(H * 0.50))
        place_right(im, sc, W - M, int(H * 0.30))


def lay_CLOSING(im, d, s):
    """클로징 — 중앙 엠블럼 씬 + 감사 문구 + 연락 정보(선택)."""
    y = typo(d, W // 2, int(H * 0.20), s["head"], s.get("sub") or [],
             role="title", center=True, maxw=int(W * 0.72))
    sc = scene(s["scene"])
    if sc:
        top = y + 30
        bh = max(int(H * 0.26), int(H * 0.80) - top)
        sc = fit(sc, int(W * 0.42), bh)
        im.paste(sc, ((W - sc.width) // 2, top + (bh - sc.height) // 2))
    if s.get("issuer"):
        fi = f("label", 38)
        tw_ = d.textlength(s["issuer"], font=fi)
        d.text(((W - tw_) / 2, int(H * 0.80)), s["issuer"], font=fi, fill=INK)


LAY = {"L": lay_L, "S": lay_S, "W": lay_W, "C": lay_C,
       "A": lay_A, "F": lay_F, "T": lay_T,
       "COVER": lay_COVER, "AGENDA": lay_AGENDA, "CLOSING": lay_CLOSING}

SLIDES = [
    {"lay": "L", "eyebrow": "THE PROBLEM", "scene": "s1_gap",
     "head": ["경영과 기술은", "만나지 않습니다"],
     "sub": ["컨설턴트는 기술을 모르고", "개발자는 경영을 모른다"]},

    {"lay": "W", "eyebrow": "THE SOLUTION", "scene": "s2_flow",
     "head": ["진단부터 실행까지 한 사람이"],
     "sub": ["경영 관점과 기술 관점을 결합한 실행형 컨설팅"]},

    {"lay": "S", "eyebrow": "TRACK RECORD", "scene": "s3_stack",
     "head": ["매일 만들고", "공공이 검증했습니다"],
     "sub": ["연 2,800회 커밋 · 저장소 90개", "공공기관 10곳 이상 위촉"]},

    {"lay": "C", "eyebrow": "DIFFERENTIATION", "scene": "s4_venn",
     "head": ["둘 다 하는 사람은 드뭅니다"],
     "sub": ["진단만 하거나, 개발만 하거나"]},

    {"lay": "L", "eyebrow": "PROOF", "scene": "s5_saas",
     "head": ["직접 만든 제품이", "증거입니다"],
     "sub": ["AI SaaS 딸깍 · 1인 개발 운영", "공공기관 계약 체결"]},
]

if __name__ == "__main__":
    n = len(SLIDES)
    for i, s in enumerate(SLIDES):
        im = Image.new("RGB", (W, H), WHITE)
        d = ImageDraw.Draw(im)
        LAY[s["lay"]](im, d, s)
        chrome(im, d, s["eyebrow"], "%02d" % (i + 1), n)
        im.save(os.path.join(OUT, "slide_%02d.png" % (i + 1)))
        print("  %02d [%s] %s" % (i + 1, s["lay"], s["head"][0]))

    import fitz
    doc = fitz.open()
    for i in range(n):
        pg = doc.new_page(width=1280, height=720)
        pg.insert_image(pg.rect, filename=os.path.join(OUT, "slide_%02d.png" % (i + 1)))
    p = os.path.join(BASE, "deck_컨설팅소개_v3.pdf")
    doc.save(p, deflate=True)
    print("→", p, "%.1f MB" % (os.path.getsize(p) / 1024 / 1024))

# -*- coding: utf-8 -*-
"""한글 슬라이드 타이포그래피 표준 (2026-08-01 확정)

## 설계 원칙
1. **기본값은 Pretendard다.** 사용자·브랜드·공식 양식이 다른 글꼴을 요구할 때만 변경한다.
2. **자간·행간은 황금비(1.618) 기반 스케일**로 계산한다. 눈대중 금지.
3. 맑은 고딕은 **사용 금지** — 시스템 기본 폰트 티가 나고 웨이트가 2종뿐이라 위계가 뭉갠다.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from platform_support import default_font, find_font, font_dirs

FONT_DIRS = font_dirs()
FONT_DIR = FONT_DIRS[0] if FONT_DIRS else ""   # 하위호환


def _find(fn):
    """파일명 → 실제 경로 (Windows/macOS/Linux 폰트 폴더 탐색)"""
    return find_font(fn)
PHI = 1.618  # 황금비

# ══════════════════════════════════════════════════════════
# 1. 폰트 풀 — 덱 성격별
# ══════════════════════════════════════════════════════════
POOL = {
    # ── 모던 산세리프 : IT·핀테크·스타트업·컨설팅 (기본값)
    "pretendard": {
        "label": "Pretendard — 기본값. Apple system-ui 대체용, 9웨이트",
        "use": "IT·핀테크·컨설팅·제안서. 중립적이고 어디에도 어울림",
        "files": {w: "Pretendard-%s.otf" % w for w in
                  ["Thin", "ExtraLight", "Light", "Regular", "Medium",
                   "SemiBold", "Bold", "ExtraBold", "Black"]},
        "tracking": -0.02,      # 자간 보정 (em) — 이미 조밀해 살짝만
    },
    "paperlogy": {
        "label": "Paperlogy — 9웨이트, 각지고 단단한 인상",
        "use": "제조·건설·기술 문서. 신뢰감·견고함",
        "files": {w: "Paperlogy-%d%s.ttf" % (i + 1, w) for i, w in enumerate(
            ["Thin", "ExtraLight", "Light", "Regular", "Medium",
             "SemiBold", "Bold", "ExtraBold", "Black"])},
        "tracking": -0.01,
    },
    "a2z": {
        "label": "A2Z — 9웨이트, 기하학적 그로테스크",
        "use": "디자인·브랜딩·크리에이티브 덱",
        "files": {w: "에이투지체-%d%s.ttf" % (i + 1, w) for i, w in enumerate(
            ["Thin", "ExtraLight", "Light", "Regular", "Medium",
             "SemiBold", "Bold", "ExtraBold", "Black"])},
        "tracking": -0.015,
    },
    "noto": {
        "label": "Noto Sans KR — 본고딕. 범용·무난",
        "use": "공공기관 제출물(폰트 설치 보장 안 될 때). 안전빵",
        "files": {w: "NotoSansKR-%s.ttf" % w for w in
                  ["Thin", "ExtraLight", "Light", "Regular", "Medium",
                   "SemiBold", "Bold", "ExtraBold", "Black"]},
        "tracking": -0.03,      # 본고딕은 자간이 넓어 더 조여야 함
    },

    # ── 명조 : 격식·전통·출판
    "serif_noto": {
        "label": "Noto Serif KR — 본명조",
        "use": "결과보고서·정책제안·전통/식음 브랜드. 차분하고 격식 있음",
        "files": {"Regular": "NotoSerifKR-VF.ttf"},
        "tracking": -0.01,
    },
    "serif_ridi": {
        "label": "RIDIBatang — 리디바탕, 읽기 최적화 명조",
        "use": "긴 문장·인용·에디토리얼 덱",
        "files": {"Regular": "RIDIBatang.otf"},
        "tracking": 0.0,
    },
    "serif_chosun": {
        "label": "조선굵은명조 — 묵직한 제목용 명조",
        "use": "표지 헤드라인. 전통·권위·역사 주제",
        "files": {"Regular": "ChosunKm.TTF"},
        "tracking": -0.02,
    },

    # ── 디스플레이 : 제목 전용 (본문 사용 금지)
    "gmarket": {
        "label": "Gmarket Sans — 임팩트 강한 제목",
        "use": "표지·섹션 구분. **본문 금지**(가독성 낮음)",
        "files": {"Light": "GmarketSansLight.otf",
                  "Medium": "GmarketSansMedium.otf",
                  "Bold": "GmarketSansBold.otf"},
        "tracking": -0.02,
    },
    "euljiro": {
        "label": "BM 을지로체 — 레트로 간판 느낌",
        "use": "로컬·전통시장·복고 브랜드 표지",
        "files": {"Regular": "BMEULJIROTTF.ttf"},
        "tracking": 0.0,
    },

    # ── 손글씨 : 감성·친근
    "hand_malang": {
        "label": "Hancom 말랑말랑 — 둥글고 친근한 손글씨",
        "use": "교육·아동·복지·커뮤니티 덱의 강조 문구",
        "files": {"Regular": "MalangmalangR.ttf", "Bold": "MalangmalangB.ttf"},
        "tracking": 0.0,
    },
    "hand_letter": {
        "label": "휴먼편지체 — 손편지 감성",
        "use": "감사 인사·클로징 한 줄. 남발 금지",
        "files": {"Regular": "HMFMPYUN.TTF"},
        "tracking": 0.0,
    },
    "hand_magic": {
        "label": "휴먼매직체 — 마커펜 느낌",
        "use": "메모·강조 주석 표현",
        "files": {"Regular": "HMFMMAGIC.TTF"},
        "tracking": 0.0,
    },
}

# 폴백 체인 (해당 웨이트가 없으면 순서대로 탐색)
FALLBACK = ["pretendard", "noto"]

# ══════════════════════════════════════════════════════════
# 2. 타입 스케일 — 황금비 기반
# ══════════════════════════════════════════════════════════
# 2560×1440 캔버스 기준. base=38px(서브 텍스트)에서 φ로 증감.
BASE = 38


def scale(step):
    """황금비 스케일. step=0 → base, +1 → ×φ, -1 → ÷φ"""
    return int(round(BASE * (PHI ** step)))


TYPE_SCALE = {
    "display":  scale(2.4),   # 표지 초대형     ≈ 121
    "headline": scale(2.3),   # 헤드라인        ≈ 112
    "title":    scale(1.9),   # W/C 구도 제목   ≈  96
    "num":      scale(2.2),   # 대형 수치       ≈ 104
    "label":    scale(-0.2),  # 카드 라벨       ≈  34
    "sub":      scale(0),     # 서브 텍스트     ≈  38
    "eyebrow":  scale(-0.5),  # 영문 라벨       ≈  30
    "chrome":   scale(-0.65), # 하단 크롬       ≈  28
    "caption":  scale(-0.9),  # 캡션           ≈  25
}

# ══════════════════════════════════════════════════════════
# 3. 행간·자간 — 황금비 파생
# ══════════════════════════════════════════════════════════
# 행간(line-height) 배수: 글자가 클수록 조이고, 작을수록 벌린다.
LEADING = {
    "display":  1.14,          # 초대형 — 아주 타이트
    "headline": 1.22,          # φ/√2 ≈ 1.14 ~ 1.22 구간
    "title":    1.26,
    "num":      1.10,
    "label":    1.35,
    "sub":      PHI * 0.94,    # ≈ 1.52  본문 가독 최적
    "eyebrow":  1.20,
    "chrome":   1.30,
    "caption":  PHI * 0.94,
}

# 자간(tracking, em 단위): 큰 글자는 조이고 작은 글자는 벌린다
TRACKING = {
    "display":  -0.030,
    "headline": -0.025,
    "title":    -0.020,
    "num":      -0.030,
    "label":    -0.005,
    "sub":       0.000,
    "eyebrow":   0.080,        # 영문 대문자 라벨은 크게 벌림
    "chrome":    0.010,
    "caption":   0.005,
}

# 역할 → 권장 웨이트
ROLE_WEIGHT = {
    "display":  "ExtraBold",
    "headline": "Bold",
    "title":    "Bold",
    "num":      "ExtraBold",
    "label":    "SemiBold",
    "sub":      "Regular",
    "eyebrow":  "SemiBold",
    "chrome":   "Regular",
    "caption":  "Regular",
}


# ══════════════════════════════════════════════════════════
# 4. API
# ══════════════════════════════════════════════════════════
def _path(family, weight):
    fam = POOL.get(family)
    if fam:
        fn = fam["files"].get(weight)
        if fn:
            p = _find(fn)
            if p:
                return p
        # 같은 패밀리 내 근접 웨이트
        for w in ["Bold", "SemiBold", "Medium", "Regular"]:
            fn = fam["files"].get(w)
            if fn:
                p = _find(fn)
                if p:
                    return p
    for fb in FALLBACK:
        fn = POOL[fb]["files"].get(weight) or POOL[fb]["files"].get("Regular")
        p = _find(fn)
        if p:
            return p
    return default_font(bold=weight in {"Bold", "SemiBold", "ExtraBold", "Black"})


def font(role, family="pretendard", size=None, weight=None):
    """역할 기반 폰트. font("headline") → Pretendard Bold 112"""
    from PIL import ImageFont
    w = weight or ROLE_WEIGHT.get(role, "Regular")
    s = size or TYPE_SCALE.get(role, BASE)
    return ImageFont.truetype(_path(family, w), s)


def metrics(role, family="pretendard"):
    """행간(px)·자간(px) 반환"""
    s = TYPE_SCALE.get(role, BASE)
    lead = int(round(s * LEADING.get(role, 1.4)))
    trk = TRACKING.get(role, 0.0) + POOL.get(family, {}).get("tracking", 0.0)
    return {"size": s, "leading": lead, "tracking_px": round(s * trk, 2)}


def draw_tracked(d, xy, text, fnt, fill, tracking_px=0.0):
    """자간을 적용해 글자 단위로 렌더. 반환=그린 폭"""
    if abs(tracking_px) < 0.01:
        d.text(xy, text, font=fnt, fill=fill)
        return d.textlength(text, font=fnt)
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + tracking_px
    return x - xy[0]


def recommend(topic):
    """주제 → 권장 폰트 조합"""
    t = topic.lower()
    if any(k in t for k in ["전통", "역사", "문화", "식음", "한식", "공예"]):
        return {"head": "serif_chosun", "body": "serif_ridi",
                "why": "전통·문화 주제는 명조가 격을 만든다"}
    if any(k in t for k in ["교육", "아동", "복지", "커뮤니티", "돌봄"]):
        return {"head": "pretendard", "body": "pretendard",
                "accent": "hand_malang", "why": "친근함은 손글씨를 강조 문구에만"}
    if any(k in t for k in ["제조", "건설", "기술", "설비", "공정"]):
        return {"head": "paperlogy", "body": "paperlogy",
                "why": "각진 글꼴이 견고함을 전달"}
    if any(k in t for k in ["디자인", "브랜드", "크리에이티브", "패션"]):
        return {"head": "a2z", "body": "pretendard",
                "why": "기하학적 그로테스크로 감각 표현"}
    if any(k in t for k in ["공공", "정책", "보고서", "제출"]):
        return {"head": "noto", "body": "noto",
                "why": "폰트 미설치 환경에서도 안전"}
    return {"head": "pretendard", "body": "pretendard",
            "why": "기본값 — 중립적이고 어디에도 어울림"}


def check():
    print("=== 폰트 풀 가용성 ===")
    for k, v in POOL.items():
        ok = sum(1 for fn in v["files"].values() if _find(fn))
        mark = "OK" if ok else "미설치"
        print("  %-14s %-6s %d/%d  %s" % (k, mark, ok, len(v["files"]), v["label"][:44]))
    print("\n=== 황금비 타입 스케일 (base=%d) ===" % BASE)
    for r in ["display", "headline", "title", "num", "sub", "eyebrow", "chrome"]:
        m = metrics(r)
        print("  %-9s %4dpx  행간 %4dpx  자간 %+.2fpx" %
              (r, m["size"], m["leading"], m["tracking_px"]))


if __name__ == "__main__":
    check()

# -*- coding: utf-8 -*-
"""도메인 프리셋 — 팔레트·폰트·씬 모티프·톤을 한 묶음으로 (2026-08-01)

`preset("식음료")` 한 줄로 그 도메인에 맞는 전체 스타일이 잡힌다.
프리셋 없이 매번 손으로 팔레트/폰트/모티프를 정하면 도메인마다 품질이 흔들린다.

## 프리셋이 묶는 4가지
1. **팔레트** — hero/mid/pale/ink/grey. hero는 그 산업이 신뢰하는 색.
2. **폰트 조합** — head/body/accent. fonts.py의 풀에서 고른다.
3. **씬 모티프** — 그 도메인에서 자연스러운 오브젝트·재질·조명.
4. **톤** — 격식(formal) / 중립(neutral) / 친근(warm). 카피 문체와 씬 분위기를 좌우.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ══════════════════════════════════════════════════════════
# 도메인 프리셋
# ══════════════════════════════════════════════════════════
PRESETS = {
    # ── IT · 핀테크 · 컨설팅 (기본값)
    "it": {
        "aliases": ["it", "핀테크", "fintech", "saas", "테크", "스타트업", "플랫폼"],
        "palette": {"hero": (43, 110, 242), "mid": (111, 160, 250), "pale": (220, 231, 253),
                    "ink": (22, 29, 43), "grey": (122, 132, 148), "line": (228, 231, 236)},
        "fonts": {"head": "pretendard", "body": "pretendard", "accent": None},
        "tone": "neutral",
        "motif": """Objects: laptops, dashboards, connected nodes, layered platforms,
data cards, cursors, code brackets. Materials: matte plastic and soft glass.
Lighting: clean studio light, crisp edges. Mood: precise, modern, trustworthy.""",
        "eyebrow_style": "upper",     # 영문 대문자 라벨
    },

    # ── 식음료 · F&B · 농식품
    "food": {
        "aliases": ["식음료", "f&b", "외식", "농식품", "식품", "카페", "요식", "먹거리"],
        "palette": {"hero": (176, 108, 58), "mid": (214, 163, 116), "pale": (247, 237, 226),
                    "ink": (46, 33, 25), "grey": (140, 124, 112), "line": (235, 226, 216)},
        "fonts": {"head": "serif_chosun", "body": "pretendard", "accent": "hand_malang"},
        "tone": "warm",
        "motif": """Objects: ingredients, packaging, tableware, market stalls, delivery boxes,
harvest crates. Materials: warm ceramic, kraft paper, natural wood grain.
Lighting: soft warm daylight, gentle golden rim light. Mood: appetizing, honest, handcrafted.""",
        "eyebrow_style": "mixed",
    },

    # ── 제조 · 건설 · 설비
    "manufacturing": {
        "aliases": ["제조", "건설", "설비", "공정", "기계", "산업", "플랜트", "생산"],
        "palette": {"hero": (30, 58, 95), "mid": (78, 116, 160), "pale": (222, 231, 240),
                    "ink": (18, 24, 33), "grey": (116, 126, 140), "line": (224, 229, 236)},
        "fonts": {"head": "paperlogy", "body": "paperlogy", "accent": None},
        "tone": "formal",
        "motif": """Objects: machinery, conveyor lines, gears, blueprints, safety helmets,
modular structures, precision instruments. Materials: brushed metal, matte steel, concrete.
Lighting: controlled industrial light with defined shadows. Mood: solid, engineered, reliable.""",
        "eyebrow_style": "upper",
    },

    # ── 교육 · 연수 · 인재개발
    "education": {
        "aliases": ["교육", "연수", "인재", "학습", "강의", "아카데미", "훈련", "에듀"],
        "palette": {"hero": (32, 130, 118), "mid": (94, 179, 168), "pale": (219, 242, 238),
                    "ink": (20, 38, 36), "grey": (118, 136, 133), "line": (223, 236, 234)},
        "fonts": {"head": "pretendard", "body": "pretendard", "accent": "hand_malang"},
        "tone": "warm",
        "motif": """Objects: open books, graduation caps, whiteboards, growing plants,
building blocks, milestone paths, lightbulbs. Materials: soft matte, paper texture.
Lighting: bright even daylight. Mood: encouraging, clear, growth-oriented.""",
        "eyebrow_style": "mixed",
    },

    # ── 복지 · 돌봄 · 사회적경제
    "welfare": {
        "aliases": ["복지", "돌봄", "사회적경제", "협동조합", "비영리", "커뮤니티", "봉사"],
        "palette": {"hero": (15, 118, 110), "mid": (20, 184, 166), "pale": (204, 251, 241),
                    "ink": (20, 32, 30), "grey": (118, 132, 130), "line": (226, 232, 231)},
        "fonts": {"head": "pretendard", "body": "pretendard", "accent": "hand_letter"},
        "tone": "warm",
        "motif": """Objects: clasped hands, circles of figures, shelters, bridges, shared tables,
interlocking rings, care symbols. Materials: soft rounded forms, gentle matte.
Lighting: warm diffuse light, no harsh shadow. Mood: inclusive, safe, human.""",
        "eyebrow_style": "mixed",
    },

    # ── 문화 · 예술 · 콘텐츠
    "culture": {
        "aliases": ["문화", "예술", "콘텐츠", "공연", "전시", "음악", "미술", "창작"],
        "palette": {"hero": (109, 60, 168), "mid": (158, 118, 210), "pale": (238, 230, 250),
                    "ink": (32, 22, 46), "grey": (130, 120, 145), "line": (232, 226, 240)},
        "fonts": {"head": "serif_ridi", "body": "pretendard", "accent": None},
        "tone": "neutral",
        "motif": """Objects: stage lights, instruments, frames, archives, film reels,
sound waves, gallery walls. Materials: velvet, brushed brass, deep matte.
Lighting: dramatic directional light with soft falloff. Mood: expressive, curated, atmospheric.""",
        "eyebrow_style": "upper",
    },

    # ── 공공 · 정책 · 행정
    "public": {
        "aliases": ["공공", "정책", "행정", "지자체", "기관", "관공서", "보고서"],
        "palette": {"hero": (20, 40, 110), "mid": (72, 104, 176), "pale": (223, 231, 245),
                    "ink": (16, 22, 36), "grey": (114, 124, 140), "line": (222, 228, 238)},
        "fonts": {"head": "noto", "body": "noto", "accent": None},
        "tone": "formal",
        "motif": """Objects: civic buildings, documents with seals, organizational charts,
regional maps, checklists, podiums. Materials: matte stone, official paper.
Lighting: even neutral light, minimal drama. Mood: authoritative, orderly, accountable.""",
        "eyebrow_style": "upper",
    },

    # ── 의료 · 헬스케어
    "medical": {
        "aliases": ["의료", "헬스", "병원", "건강", "바이오", "제약", "케어"],
        "palette": {"hero": (18, 132, 168), "mid": (86, 180, 208), "pale": (216, 240, 247),
                    "ink": (16, 32, 40), "grey": (116, 132, 140), "line": (222, 234, 238)},
        "fonts": {"head": "pretendard", "body": "pretendard", "accent": None},
        "tone": "formal",
        "motif": """Objects: cross symbols, monitoring charts, molecules, capsules,
stethoscopes, clean modular pods. Materials: polished white, soft cyan glass.
Lighting: bright clinical light, very clean. Mood: precise, hygienic, reassuring.""",
        "eyebrow_style": "upper",
    },

    # ── 유통 · 리테일 · 커머스
    "retail": {
        "aliases": ["유통", "리테일", "커머스", "쇼핑", "판매", "물류", "이커머스"],
        "palette": {"hero": (232, 90, 60), "mid": (245, 148, 122), "pale": (253, 232, 226),
                    "ink": (40, 24, 20), "grey": (138, 122, 116), "line": (240, 230, 226)},
        "fonts": {"head": "gmarket", "body": "pretendard", "accent": None},
        "tone": "neutral",
        "motif": """Objects: shopping carts, parcel boxes, storefronts, price tags,
delivery trucks, shelf displays. Materials: glossy cardboard, bright plastic.
Lighting: energetic bright light, punchy contrast. Mood: dynamic, accessible, commercial.""",
        "eyebrow_style": "upper",
    },
}

DEFAULT = "it"


def resolve(name):
    """도메인명/별칭 → 프리셋 키"""
    if not name:
        return DEFAULT
    q = str(name).strip().lower()
    if q in PRESETS:
        return q
    for key, v in PRESETS.items():
        for a in v["aliases"]:
            if a in q or q in a:
                return key
    return DEFAULT


def preset(name=None):
    """도메인명 → 전체 스타일 묶음

    preset("식음료") → {key, palette, fonts, tone, motif, ...}
    """
    key = resolve(name)
    p = dict(PRESETS[key])
    p["key"] = key
    p["query"] = name
    return p


def style_block(name=None):
    """씬 프롬프트에 넣을 STYLE 블록 생성"""
    p = preset(name)
    pal = p["palette"]

    def hexc(c):
        return "#%02X%02X%02X" % c

    tone_line = {
        "formal": "Composed and authoritative. Restrained, no playful exaggeration.",
        "neutral": "Confident and modern. Balanced between warm and precise.",
        "warm": "Approachable and human. Soft edges, inviting without being childish.",
    }[p["tone"]]

    return """A single premium 3D-rendered CONCEPT SCENE for a business presentation slide.

RENDER STYLE:
- High-end 3D render, Apple-keynote / premium brand quality.
- CAMERA: 35mm equivalent, slightly above eye level, three-quarter view, gentle perspective.
  The subject sits at the optical centre with breathing room; no extreme wide-angle distortion.
- LIGHTING: soft key light from upper-left at ~45 degrees, wide fill from the right to keep
  shadows open, subtle rim light separating the subject from the white background.
  One dominant light direction only — never flat ambient, never harsh contrast.
- MATERIALS: matte surfaces with fine micro-roughness; specular highlights are soft and broad,
  never mirror-sharp. Rounded bevels catch a thin light edge. Solid objects feel weighty.
- SHADOW: soft contact shadow directly beneath each object, gradually diffusing outward.
  No hard drop shadows, no floating objects without grounding.
- DEPTH: mild depth of field — background elements slightly softer than the hero object.
- NOT flat vector, NOT cartoon, NOT clay-toy, NOT line icons, NOT isometric grid art.

PALETTE (strict — %(key)s domain):
  hero %(hero)s · mid %(mid)s · pale %(pale)s
  ink %(ink)s · grey %(grey)s · white
The hero colour leads; everything else stays neutral.

DOMAIN MOTIF:
%(motif)s

TONE: %(tone_line)s

BACKGROUND: pure white, generous empty space.
""" % {
        "key": p["key"],
        "hero": hexc(pal["hero"]), "mid": hexc(pal["mid"]), "pale": hexc(pal["pale"]),
        "ink": hexc(pal["ink"]), "grey": hexc(pal["grey"]),
        "motif": p["motif"], "tone_line": tone_line,
    }


def listing():
    print("=== 도메인 프리셋 %d종 ===" % len(PRESETS))
    for k, v in PRESETS.items():
        pal = v["palette"]["hero"]
        print("  %-14s hero=rgb%-16s font=%-12s tone=%-8s %s"
              % (k, str(pal), v["fonts"]["head"], v["tone"], v["aliases"][0]))


if __name__ == "__main__":
    listing()
    print()
    for q in ["식음료", "협동조합", "AI 스타트업", "병원", "공연 기획"]:
        p = preset(q)
        print("  %-12s → %-14s hero=%s font=%s"
              % (q, p["key"], p["palette"]["hero"], p["fonts"]["head"]))

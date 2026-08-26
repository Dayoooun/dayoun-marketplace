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

    # ── 뷰티 · 화장품 · 코스메틱
    "beauty": {
        "aliases": ["뷰티", "화장품", "코스메틱", "스킨케어", "세정", "미역", "해조류", "기장"],
        "palette": {"hero": (27, 82, 99), "mid": (107, 162, 170), "pale": (224, 240, 239),
                    "ink": (18, 30, 34), "grey": (118, 136, 138), "line": (226, 236, 236)},
        "fonts": {"head": "pretendard", "body": "pretendard", "accent": None},
        "tone": "warm",
        "motif": """Objects: seaweed fronds, sea-salt crystals, solid cleansing bars,
botanical extracts in glass vessels, kraft-paper packaging, coastal pebbles,
ceramic dishes, linen pouches. Materials: hand-pressed soap surfaces,
translucent dried kelp, unglazed stoneware, natural linen texture.
Lighting: golden-hour warmth through a clean window, soft reflected light off
water or stone. Mood: artisanal, coastal, quietly luxurious, honest.""",
        "eyebrow_style": "mixed",
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


# ══════════════════════════════════════════════════════════
# 인포그래픽 프롬프트 (2026-08-19 확정)
#
# 실측 결과:
#   v1 맨몸 flat → 한글 OK지만 디자인 밋밋
#   v2~v4 빈 도형만 → Pillow가 0.1초에 하는 걸 15분 73k토큰으로 했다
#   v5~v6 3D 일러스트 → 예쁘지만 정보 전달 기능 없음
#   v7 flat 인포그래픽+한글 → 구조 좋고 깔끔 (문서 본문용)
#   v8 3D 인포그래픽+한글 → 정보 전달 + 시각 임팩트 (표지·강조용)
#
# 핵심 원칙:
#   1. "structured information graphic with Korean text" 선언
#   2. 실제 한글 콘텐츠를 프롬프트에 전부 넣는다
#   3. 라벨 분리(Pillow 합성) 불필요 — Codex가 한글을 직접 정확히 그린다
#   4. 스타일은 사용자가 고른다. 임의로 정하지 않는다.
# ══════════════════════════════════════════════════════════

_STYLE_HEADER = """Generate a single premium infographic image for a business plan document.
This is a STRUCTURED INFORMATION GRAPHIC with Korean text.
"""

STYLE_3D = """%(header)s
VISUAL QUALITY — subtle 3D depth and tactile materiality,
like a Toss or Apple keynote data card:
- Cards and panels feel like frosted glass or soft matte ceramic floating above the surface.
- Each element casts a realistic but gentle diffused shadow on the white ground.
- Subtle inner glow or light edge at the top gives volume to every shape.
- Rounded corners are generous, like physical objects you could pick up.
- Light comes from upper-left, soft and warm, wrapping around edges.
- The overall feel is premium product photography of data objects on a white table.
- NOT flat vector. NOT cartoon. NOT isometric pixel art. Think Apple Vision Pro UI.

PALETTE (strict — %(key)s domain):
  Hero: %(hero)s (glossy or solid, for the most important element)
  Mid: %(mid)s (matte, for secondary elements)
  Pale: %(pale)s (frosted/translucent, for backgrounds and cards)
  Ink: %(ink)s (text colour)
  White ground, very subtle ambient occlusion near objects.

RULES:
- All Korean text MUST be perfectly rendered and correctly spelled. This is critical.
- Numbers are extra-large display weight. Headings bold. Body regular weight.
- Every element has realistic 3D depth — they are objects, not flat rectangles.
- No decorative illustrations or icons unless the layout explicitly calls for them.
- Background is pure white with subtle ground shadows.
- No title area, no watermark, no logo, no page furniture.
"""

STYLE_FLAT = """%(header)s
VISUAL QUALITY — clean flat editorial design, Toss app quality:
- Typography leads. The text IS the design. No decorative texture.
- Cards are solid flat fills with generous rounded corners and clean edges.
- Shadows are minimal and neutral, or absent entirely. Elevation comes from
  colour contrast and spacing, never from heavy drop shadows.
- Thin hairline dividers where separation is needed. No borders on cards.
- Generous whitespace between sections. Everything sits on a strict grid.
- Calm, confident, trustworthy. Zero visual noise.
- NOT 3D. NOT glossy. NOT textured. NOT skeuomorphic. Pure flat information design.

PALETTE (strict — %(key)s domain):
  Hero: %(hero)s (solid fill, for the most important element)
  Mid: %(mid)s (secondary elements)
  Pale: %(pale)s (card backgrounds)
  Ink: %(ink)s (text colour)
  Pure white ground.

RULES:
- All Korean text MUST be perfectly rendered and correctly spelled. This is critical.
- Numbers are extra-large display weight. Headings bold. Body regular weight.
- Alignment is precise. Equal spacing, shared baselines, consistent padding.
- No decorative illustrations or icons unless the layout explicitly calls for them.
- Background is pure white, completely flat.
- No title area, no watermark, no logo, no page furniture.
"""

STYLES = {
    "3d": STYLE_3D,
    "flat": STYLE_FLAT,
}

STYLE_GUIDE = {
    "3d": "입체감 있는 유리·세라믹 질감. 표지, 강조 페이지, 발표 자료에 어울린다.",
    "flat": "깔끔한 평면 편집 디자인. 문서 본문, 여러 장 반복 삽입에 어울린다.",
}


def diagram_block(name=None, kind="flow", content="", style=None):
    """인포그래픽 프롬프트 블록.

    Codex 이미지 생성으로 한글 텍스트가 포함된 구조적 정보 디자인을 만든다.

    Args:
        name: 도메인 (beauty, it, food 등). 팔레트를 결정한다.
        kind: 인포그래픽 유형 (현재 미사용, 향후 유형별 구조 지시 확장용).
        content: 실제 한글 콘텐츠. 프롬프트의 CONTENT 섹션에 그대로 들어간다.
        style: `3d` 또는 `flat`. **반드시 지정해야 한다.**
              생략하면 ValueError로 막는다 — 에이전트가 사용자 대신
              시각 스타일을 정하면 안 되기 때문이다(2026-08-19 사용자 지시).
    """
    if style is None:
        raise ValueError(
            "style을 지정해야 합니다. 사용자에게 먼저 물어보세요.\n"
            + "\n".join(
                "  %-5s : %s" % (key, STYLE_GUIDE[key]) for key in STYLES
            )
        )
    if style not in STYLES:
        raise ValueError(
            "unknown style: %s (expected one of %s)"
            % (style, ", ".join(sorted(STYLES)))
        )

    p = preset(name)
    pal = p["palette"]

    def hexc(c):
        return "#%02X%02X%02X" % c

    header = STYLES[style] % {
        "header": _STYLE_HEADER.strip(),
        "key": p["key"],
        "hero": hexc(pal["hero"]), "mid": hexc(pal["mid"]),
        "pale": hexc(pal["pale"]), "ink": hexc(pal["ink"]),
    }

    content_block = "\nCONTENT:\n%s\n" % content.strip() if content.strip() else ""

    return header + content_block


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

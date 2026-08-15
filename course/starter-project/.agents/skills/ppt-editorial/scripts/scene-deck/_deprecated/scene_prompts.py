# -*- coding: utf-8 -*-
"""v3 — 내용에 최적화된 구도 배치
   기준 덱 분석: 좌우2단이 기본이되 내용 성격에 따라 구도를 바꾼다.
   씬 안에 라벨을 박아 정보량을 올린다.
"""
import os, json

BASE = os.path.dirname(os.path.abspath(__file__))

BASE_STYLE = """A single premium 3D-rendered CONCEPT SCENE for a business presentation slide.

RENDER STYLE:
- High-end 3D render, soft studio lighting, clean matte surfaces, gentle specular highlights.
- Rounded tactile geometry with real weight. Soft contact shadows. Subtle depth of field.
- NOT flat vector, NOT cartoon, NOT clay-toy, NOT line icons. Apple-keynote / fintech quality.

PALETTE (strict):
  primary blue #2B6EF2 · lighter blue #6FA0FA · pale blue #DCE7FD
  white · light grey #F1F3F6 · ink #161D2B
  (a single warm accent #FF6B4A may be used ONLY where explicitly requested)
Blue is the hero colour.

BACKGROUND: pure white, generous empty space.
"""

TAIL = """
Use ONLY the image-generation capability - ABSOLUTELY NO Python/PIL/code drawing.
Korean text inside the image must be perfectly rendered — no '?', no broken glyphs.
결과를 반드시 __out.png 로 저장하고 크기를 출력하라. PIL 드로잉 금지, 이미지 생성만.
"""

# 구도별 씬 — 각 슬라이드 내용에 최적화
SCENES = [
    # 01 문제제기 — 대비 구도 (좌우 분단) + 라벨
    ("s1_gap", "4:3 landscape", """
COMPOSITION — SPLIT CONTRAST (two worlds that never meet):
Two separate elevated platforms with a wide chasm between them, viewed three-quarter.
LEFT platform: a stack of business documents and a small bar-chart board.
RIGHT platform: a monitor panel showing code brackets.
A broken bridge juts from each side but the two halves do not reach each other.

TEXT LABELS rendered in the image (bold Korean gothic, ink colour, small):
  above the left platform:  "경영"
  above the right platform: "기술"
The empty gap between them is the visual focus."""),

    # 02 솔루션 — 가로 프로세스 플로우 (단계 진행)
    ("s2_flow", "16:9 wide", """
COMPOSITION — HORIZONTAL PROCESS FLOW (four sequential steps, left to right):
Four rounded pedestals in a row, each carrying one object, connected by a dashed blue path
with small arrow markers between them.
  step 1: a magnifier over a small chart board
  step 2: a network of three connected nodes
  step 3: a monitor with code brackets
  step 4: an upward arrow rising from a small bar chart
Each pedestal is slightly lower/higher to suggest forward motion.

TEXT LABELS under each pedestal (bold Korean gothic, ink, small):
  "경영 진단"  "AI 설계"  "실행 개발"  "성과 검증"
Wide panoramic framing, objects evenly spaced."""),

    # 03 실적 — 중앙 집중 + 수치 강조
    ("s3_stack", "4:3 landscape", """
COMPOSITION — CENTRAL ACCUMULATION (built up over time):
A tall stack of rounded layered plates rising like a column, each layer slightly rotated,
gradating from deep blue at the bottom to white at the top.
An award ribbon medal rests on the summit.
Small rounded check badges float around the column at varied depths.

NO text labels in this image."""),

    # 04 차별성 — 벤다이어그램 교집합 (비교·병합)
    ("s4_venn", "4:3 landscape", """
COMPOSITION — OVERLAPPING CIRCLES (the rare intersection):
Two large translucent circles overlapping in the centre, rendered as soft 3D glass discs
lying on a white surface. Left circle pale blue, right circle light grey-blue.
The INTERSECTION is filled with solid vivid blue and slightly raised, clearly the hero area.
A small 3D figure or glowing marker stands in the intersection.

TEXT LABELS rendered in the image (bold Korean gothic, small):
  left circle:   "경영 컨설팅"
  right circle:  "개발 역량"
  intersection (white text on blue): "둘 다"
"""),

    # 05 검증 — 제품 쇼케이스 (좌우 2단용)
    ("s5_saas", "4:3 landscape", """
COMPOSITION — SHIPPED PRODUCT SHOWCASE:
A laptop floating three-quarter view, screen showing a clean abstract SaaS dashboard
built from simple blue and grey blocks — one line chart, one donut, two list rows.
Around it, three small rounded UI cards and a cursor float at different depths.
Soft shadow beneath grounds the composition.

NO text labels in this image."""),
]


def main():
    out = os.path.join(BASE, "scenes3")
    os.makedirs(out, exist_ok=True)
    jobs = []
    for name, ratio, body in SCENES:
        jobs.append({
            "label": name,
            "refs": [],
            "out": os.path.join("scenes3", "%s.png" % name),
            "prompt": BASE_STYLE + body + "\n\nOutput %s framing.\n" % ratio + TAIL,
        })
    p = os.path.join(BASE, "jobs_v3.json")
    json.dump(jobs, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("v3 씬 %d개 → %s" % (len(jobs), p))


if __name__ == "__main__":
    main()

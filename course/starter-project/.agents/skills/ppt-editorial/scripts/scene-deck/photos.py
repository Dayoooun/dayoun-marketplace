# -*- coding: utf-8 -*-
"""사용자 실사진 삽입 (2026-08-01 G005)

## 철칙 D 준수
실사진은 **코드 후합성이 아니라 codex에 전달해 씬 안에서 함께 그리게 한다.**
코드로 붙이면 3D 렌더 씬 위에 사진이 스티커처럼 떠 보인다.
codex가 사진을 받으면 그 사진에 맞는 조명·그림자·원근으로 주변을 그려준다.

## 처리 흐름
1. `analyze()` — 사진 성격 판정 (인물/제품/현장/문서) + 비율
2. `plan()` — 개수·성격에 따라 구도와 배치 규칙 결정
3. `prompt_block()` — codex에 넘길 사진 통합 지시문 생성
4. `prep()` — 개인정보 처리(얼굴 블러 옵션) + 리사이즈 후 refs로 전달
"""
import os, math

try:
    from PIL import Image
except ImportError:
    Image = None


# ══════════════════════════════════════════════════════════
# 1. 사진 분석
# ══════════════════════════════════════════════════════════
def analyze(path):
    """사진 1장의 기본 성격 판정"""
    im = Image.open(path)
    w, h = im.size
    ratio = w / h
    orient = "landscape" if ratio > 1.25 else ("portrait" if ratio < 0.8 else "square")

    # 얼굴 검출 (opencv 있으면)
    faces = 0
    try:
        import cv2, numpy as np
        cas = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        g = cv2.cvtColor(np.array(im.convert("RGB")), cv2.COLOR_RGB2GRAY)
        faces = len(cas.detectMultiScale(g, 1.1, 5))
    except Exception:
        pass

    kind = "person" if faces else "object"
    return {"path": path, "w": w, "h": h, "ratio": round(ratio, 2),
            "orient": orient, "faces": faces, "kind": kind}


# ══════════════════════════════════════════════════════════
# 2. 배치 계획
# ══════════════════════════════════════════════════════════
# 사진 개수 → 배치 규칙
ARRANGE = {
    1: ("hero", "단일 히어로 — 씬의 주인공으로 크게",
        "L 또는 A 구도. 사진을 씬 중심에 두고 주변을 3D 요소로 감싼다."),
    2: ("compare", "2장 비교 — 전/후, A/B",
        "S 또는 C 구도. 좌우 대칭으로 놓고 가운데 대비 요소를 넣는다."),
    3: ("sequence", "3장 시퀀스 — 과정·단계",
        "W 구도. 가로로 흐르게 배치하고 사이에 화살표/경로를 넣는다."),
    4: ("grid", "4장 그리드 — 라인업·포트폴리오",
        "F 또는 T 구도. 2×2 격자로 균등 배치, 각 칸에 라벨."),
}


def plan(paths):
    """사진 목록 → 배치 계획"""
    metas = [analyze(p) for p in paths]
    n = len(metas)
    key = min(n, 4)
    mode, desc, layout = ARRANGE[key]
    has_face = any(m["faces"] for m in metas)
    return {"count": n, "mode": mode, "desc": desc, "layout": layout,
            "metas": metas, "has_face": has_face,
            "orients": [m["orient"] for m in metas]}


# ══════════════════════════════════════════════════════════
# 3. codex 프롬프트 블록 (철칙 D — 씬 안에서 함께 그린다)
# ══════════════════════════════════════════════════════════
INTEGRATE = {
    "hero": """PHOTO INTEGRATION — SINGLE HERO:
The provided photograph is the subject of this scene. Do NOT paste it flat.
Place it inside a rendered 3D frame or device mockup (a rounded card, a monitor, a
product stand) so it belongs to the scene. Match the photograph's own lighting direction
when lighting the surrounding 3D elements. Add a soft contact shadow beneath the frame.
Surround it with a few small rendered accent objects that support the message.""",

    "compare": """PHOTO INTEGRATION — TWO-UP COMPARISON:
Place the two provided photographs side by side inside matching rendered frames of equal size,
left and right, with a clear gap. Between them place a rendered divider or arrow element.
Both frames share identical lighting, bevel and shadow treatment so the comparison reads fairly.""",

    "sequence": """PHOTO INTEGRATION — HORIZONTAL SEQUENCE:
Place the provided photographs in rendered frames arranged left to right in order,
each on its own low pedestal, connected by a dashed path with small arrow markers.
Frames are equal size; slight height variation suggests progression.""",

    "grid": """PHOTO INTEGRATION — GRID LINEUP:
Place the provided photographs in a clean 2x2 grid of identical rendered frames,
even spacing, all sharing the same bevel, lighting and shadow.
The grid sits as one unified object on a soft rendered base.""",
}

PRIVACY = """
★ PRIVACY: Do not add, invent or enhance any facial detail beyond what the provided
photograph already contains. Never render name tags, phone numbers, emails, or SNS handles.
"""


def prompt_block(pl, labels=None):
    """배치 계획 → codex 씬 프롬프트에 삽입할 블록"""
    b = INTEGRATE[pl["mode"]]
    if labels:
        b += "\n\nTEXT LABELS (bold Korean gothic, ink, small) under each frame:\n  " + \
             "  ".join('"%s"' % x for x in labels)
    if pl["has_face"]:
        b += PRIVACY
    return "\n" + b + "\n"


# ══════════════════════════════════════════════════════════
# 4. 전처리 — 리사이즈 · 얼굴 블러(옵션)
# ══════════════════════════════════════════════════════════
def prep(paths, out_dir, max_side=1600, blur_faces=False):
    """codex에 넘길 사진을 정리. 반환=전처리된 경로 목록"""
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for i, p in enumerate(paths, 1):
        im = Image.open(p).convert("RGB")
        if max(im.size) > max_side:
            r = max_side / max(im.size)
            im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        if blur_faces:
            im = _blur_faces(im)
        q = os.path.join(out_dir, "photo_%02d.png" % i)
        im.save(q)
        out.append(q)
    return out


def _blur_faces(im):
    """얼굴 영역 블러 (opencv 있을 때만)"""
    try:
        import cv2, numpy as np
        from PIL import ImageFilter
        arr = np.array(im)
        cas = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        g = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        for (x, y, w, h) in cas.detectMultiScale(g, 1.1, 5):
            box = (x, y, x + w, y + h)
            region = im.crop(box).filter(ImageFilter.GaussianBlur(radius=max(4, w // 8)))
            im.paste(region, box)
    except Exception:
        pass
    return im


def describe(pl):
    """계획 요약 출력"""
    print("=== 사진 배치 계획 ===")
    print("  장수: %d → 모드: %s" % (pl["count"], pl["mode"]))
    print("  %s" % pl["desc"])
    print("  권장 구도: %s" % pl["layout"])
    print("  얼굴 포함: %s" % ("예 (개인정보 지시 자동 삽입)" if pl["has_face"] else "아니오"))
    for m in pl["metas"]:
        print("    %-28s %dx%d %-9s faces=%d"
              % (os.path.basename(m["path"])[:28], m["w"], m["h"], m["orient"], m["faces"]))


if __name__ == "__main__":
    print("사진 배치 규칙")
    for n, (mode, desc, lay) in ARRANGE.items():
        print("  %d장 → %-9s %s" % (n, mode, desc))
        print("           %s" % lay)

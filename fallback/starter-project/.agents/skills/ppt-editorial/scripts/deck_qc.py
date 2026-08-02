# -*- coding: utf-8 -*-
"""덱 조립 전 자동 검수 게이트 (2026-07-27 신설)

콘택트시트 육안 검수로는 못 잡는 결함을 픽셀로 검출한다.
실측 사고 3건에서 도출:
  ① 종횡비 불일치 — codex가 1장만 2:1로 뱉어 PPTX에서 찌그러짐
  ② 우/좌 여백 소실 — 콘텐츠가 슬라이드 끝에 붙어 답답하고 텍스트가 잘림
  ③ SAFE ZONE 침범 — 본문이 상단 제목·하단 밴드와 겹침

사용:
  python deck_qc.py <슬라이드폴더> [--safe-top 0.163] [--safe-bot 0.845]
  python deck_qc.py <폴더> --body        # 크롬 합성 전(본문만) 검사
  python deck_qc.py <폴더> --cover 01    # 표지 sid 지정(풀블리드라 여백 검사 제외)

종료코드 0=통과 / 1=FAIL 존재
"""
import os, sys, glob, argparse
import numpy as np
from PIL import Image

# 씬덱 하네스 규격(layout_engine.M = W*0.030)과 정합. 여기보다 좁으면 오탐이 난다.
# 실측: M=0.030 설계값에 정확히 맞은 슬라이드가 LEFT_LIMIT 0.035에서 FAIL로 찍혔다.
# 렌더 안티에일리어싱을 감안해 0.004 여유를 둔다.
SCENE_DECK_MARGIN = 0.030
RIGHT_LIMIT = 1.0 - SCENE_DECK_MARGIN + 0.004   # 0.974
LEFT_LIMIT  = SCENE_DECK_MARGIN - 0.004         # 0.026
RATIO_TOL   = 0.02       # 종횡비 허용 오차


def bounds(im, y0=0.0, y1=1.0):
    """지정 세로 구간에서 콘텐츠 bbox 비율 반환 (l, r, t, b)"""
    a = np.array(im.convert("L")).astype(int)
    H, W = a.shape
    band = a[int(H * y0):int(H * y1)]
    if band.size == 0:
        return None
    # 배경색은 최빈값이 아니라 **가장자리 색**으로 잡는다.
    # 카드가 화면 대부분을 덮는 레이아웃(스탯 3분할 등)에서는 카드색이 최빈값이 되어
    # 진짜 배경(흰색)이 콘텐츠로 판정되는 오탐이 난다. (2026-08-01 실측)
    edge = np.concatenate([band[:, :3].ravel(), band[:, -3:].ravel(),
                           band[:2, :].ravel(), band[-2:, :].ravel()])
    bg = int(np.bincount(edge).argmax())
    c = np.abs(band - bg) > 14
    cols = np.nonzero(c.sum(axis=0) > band.shape[0] * 0.015)[0]
    rows = np.nonzero(c.sum(axis=1) > W * 0.015)[0]
    if len(cols) == 0 or len(rows) == 0:
        return None
    return (cols.min() / W, cols.max() / W,
            (rows.min() + int(H * y0)) / H, (rows.max() + int(H * y0)) / H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--safe-top", type=float, default=0.163)
    ap.add_argument("--safe-bot", type=float, default=0.845)
    ap.add_argument("--cover", default="01", help="표지 sid(여백 검사 제외), 없으면 none")
    ap.add_argument("--body", action="store_true",
                    help="★크롬 합성 전 본문 폴더에만 쓴다. 완성 슬라이드에 쓰면 "
                         "크롬(eyebrow·하단선)을 침범으로 오인해 전건 오탐이 난다")
    a = ap.parse_args()

    if a.body:
        print("※ --body 는 크롬 합성 '전' 본문 검사용이다.")
        print("  완성 슬라이드(크롬 포함)에 쓰면 상단 eyebrow·하단 구분선을")
        print("  SAFE ZONE 침범으로 오인해 전건 WARN이 난다.")
        print("  완성본은 --body 없이 실행하라.\n")

    files = sorted(glob.glob(os.path.join(a.folder, "slide_*.png")))
    if not files:
        print("슬라이드 없음:", a.folder); sys.exit(1)

    sizes = {}
    fails, warns = [], []

    print("=" * 66)
    print("덱 검수 :", a.folder, "(%d장)" % len(files))
    print("=" * 66)

    for p in files:
        sid = os.path.splitext(os.path.basename(p))[0].split("_")[-1]
        im = Image.open(p).convert("RGB")
        W, H = im.size
        sizes.setdefault((W, H), []).append(sid)

        if sid == a.cover:
            print(" %s  표지 — 여백 검사 제외 (%dx%d)" % (sid, W, H))
            continue

        # 좌우 여백은 SAFE ZONE 안쪽(본문)만 본다.
        # 크롬 밴드는 풀블리드가 정상이므로 포함하면 오탐(2026-08-01 실측).
        b = bounds(im, a.safe_top + 0.01, a.safe_bot - 0.01)
        if b is None:
            warns.append((sid, "콘텐츠 미검출"))
            print(" %s  [WARN] 콘텐츠 미검출" % sid); continue
        l, r, t, bt = b
        msgs = []
        if r > RIGHT_LIMIT:
            fails.append((sid, "우측 여백 부족 %.3f" % r)); msgs.append("우 %.3f ✗" % r)
        else:
            msgs.append("우 %.3f" % r)
        if l < LEFT_LIMIT:
            fails.append((sid, "좌측 여백 부족 %.3f" % l)); msgs.append("좌 %.3f ✗" % l)
        else:
            msgs.append("좌 %.3f" % l)

        if a.body:                       # 크롬 전이면 상하단 침범 검사
            fb = bounds(im)
            if fb:
                _, _, ft, fbm = fb
                if ft < a.safe_top - 0.01:
                    warns.append((sid, "상단 SAFE ZONE 침범 %.3f" % ft)); msgs.append("상 %.3f !" % ft)
                if fbm > a.safe_bot + 0.01:
                    warns.append((sid, "하단 SAFE ZONE 침범 %.3f" % fbm)); msgs.append("하 %.3f !" % fbm)

        print(" %s  %s" % (sid, "  ".join(msgs)))

    # ── 종횡비 통일 검사
    print("-" * 66)
    if len(sizes) == 1:
        W, H = next(iter(sizes))
        print("크기 통일 : %dx%d (비율 %.3f)" % (W, H, W / H))
    else:
        base = max(sizes, key=lambda k: len(sizes[k]))
        br = base[0] / base[1]
        for sz, ids in sizes.items():
            if abs(sz[0] / sz[1] - br) > RATIO_TOL:
                for i in ids:
                    fails.append((i, "종횡비 불일치 %dx%d (기준 %dx%d)" % (sz[0], sz[1], base[0], base[1])))
        print("크기 종류 %d개 :" % len(sizes),
              ", ".join("%dx%d(%s)" % (s[0], s[1], ",".join(v)) for s, v in sizes.items()))

    print("-" * 66)
    if fails:
        print("FAIL %d건" % len(fails))
        for sid, m in fails:
            print("  - %s : %s" % (sid, m))
    if warns:
        print("WARN %d건" % len(warns))
        for sid, m in warns:
            print("  - %s : %s" % (sid, m))
    if not fails and not warns:
        print("통과 — 조립 진행 가능")
    print("=" * 66)

    print("\n※ 이 검수로도 못 잡는 것: 한글 깨짐·오타·패널 안 텍스트 잘림.")
    print("  → 우측 1/3을 2배 확대 크롭해 육안 확인할 것 (콘택트시트로는 안 보임).")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()

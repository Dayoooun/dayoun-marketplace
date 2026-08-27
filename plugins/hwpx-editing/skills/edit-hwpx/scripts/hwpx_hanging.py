#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HWPX 표 셀 내어쓰기(hanging indent) — 한글 COM 없이 macOS 에서 적용.

rhwp 는 표 셀 문단의 `paraPr` margin `intent` 를 렌더에 반영한다(2026-08-27 실측).
"표 셀은 intent 가 무시되므로 한글 COM 후처리 필수"라는 통설은 오진이었다.

핵심은 **접힌 줄을 그 문단 첫 글자 x 에 맞추는 것**이다. 접두사 폭이 패턴마다
다르므로 단일 intent 로는 전부 어긋난다 (HWPUNIT = pt × 100):

    '□ 1. …'                 13.50pt → 1350
    '○ (라벨) …'              13.50pt → 1350
    '　- …' (전각공백+대시)    17.25pt → 1725

그래서 2패스로 돈다:
  ① 원본을 rhwp 로 렌더해 문단별 (줄 시작 x, 첫 글자 x) 를 PDF 좌표로 실측
  ② 패턴별 |intent| = (첫 글자 x − 셀 좌측 x) × 100 을 역산해 전용 paraPr 주입

사용:
    python hwpx_hanging.py <입력.hwpx> <출력.hwpx> [--markers □ ○] [--rhwp <경로>]
    python hwpx_hanging.py --check <파일.pdf>      # 정렬 게이트 (MISS 0 이어야 통과)
"""
import argparse
import collections
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

MARKERS = "\u25a1\u25cb-"        # □ ○ -
TOL = 0.6                        # pt. 정렬 검사 허용치
MAX_GAP = 4.0                    # pt. 마커 줄과 이 이상 벌어지면 다른 문단
FALLBACK_INTENT = -1350


# ───────────────────────── zip ─────────────────────────
def unpack(src, wd):
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    zipfile.ZipFile(src).extractall(wd)


def repack(wd, out):
    with zipfile.ZipFile(out, "w") as zf:
        zf.write(os.path.join(wd, "mimetype"), "mimetype", zipfile.ZIP_STORED)
        for root, _, files in os.walk(wd):
            for f in files:
                if f == "mimetype":
                    continue
                fu = os.path.join(root, f)
                zf.write(fu, os.path.relpath(fu, wd).replace("\\", "/"),
                         zipfile.ZIP_DEFLATED)


# ───────────────────────── 측정 ─────────────────────────
def find_rhwp(explicit=None):
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "..", "bin", "rhwp"),
                 os.path.expanduser("~/.claude/skills/consulting-report/bin/rhwp"),
                 shutil.which("rhwp")):
        if cand and os.path.exists(cand):
            return os.path.abspath(cand)
    raise RuntimeError("rhwp 바이너리를 찾을 수 없다. --rhwp 로 경로를 준다.")


def marker_lines(pdf_path):
    """PDF 에서 (페이지, 선행공백, 마커, 줄시작x, 첫글자x, y_top, y_bot, 원문) 목록."""
    import pymupdf
    rows = []
    doc = pymupdf.open(pdf_path)
    for pno, page in enumerate(doc):
        for blk in page.get_text("rawdict")["blocks"]:
            for line in blk.get("lines", []):
                chars = [c for sp in line["spans"] for c in sp["chars"]]
                if not chars:
                    continue
                text = "".join(c["c"] for c in chars)
                body = text.lstrip(" \u3000")
                bb = chars[0]["bbox"]
                if not body:
                    continue
                if body[0] in MARKERS:
                    i = len(text) - len(body) + 1          # 선행공백 + 마커 1글자
                    while i < len(chars) and chars[i]["c"] in (" ", "\u3000"):
                        i += 1
                    x_txt = chars[i]["bbox"][0] if i < len(chars) else None
                else:
                    x_txt = None
                rows.append((pno, text[:len(text) - len(body)],
                             body[0] if body[0] in MARKERS else None,
                             bb[0], x_txt, bb[1], bb[3], text))
    doc.close()
    return rows


def measure_intents(src_hwpx, wd, rhwp):
    """접두사 패턴별 필요한 |intent| 를 HWPUNIT 로 실측. 실패 시 {}.

    ★ 기준점은 줄 시작 x 가 아니라 **셀 좌측**이다. 전각공백 들여쓰기는 렌더 시
    글자가 아니라 여백으로 흡수돼 PDF 텍스트에 남지 않는다. 줄 시작을 기준 삼으면
    전각공백 폭이 빠져 접힌 줄이 마커 위치에 걸린다.

    rhwp 는 문단마다 별도 블록을 만들므로 블록 bbox 도 기준이 못 된다
    (자기 들여쓰기와 같아진다). 페이지 내 마커 줄들의 최소 x 를 쓴다.
    """
    try:
        import pymupdf  # noqa: F401
    except ImportError:
        return {}
    pdf = os.path.join(wd, "_measure.pdf")
    subprocess.run([rhwp, "export-pdf", src_hwpx, "-o", pdf, "--profile", "print"],
                   capture_output=True, text=True, timeout=900)
    if not os.path.exists(pdf) or os.path.getsize(pdf) == 0:
        return {}
    rows = [r for r in marker_lines(pdf) if r[2] and r[4] is not None]
    os.remove(pdf)
    if not rows:
        return {}
    left = {}
    for pno, _, _, x_line, _, _, _, _ in rows:
        left[pno] = min(left.get(pno, x_line), x_line)
    samples = collections.defaultdict(list)
    for pno, lead, mark, _, x_txt, _, _, _ in rows:
        samples[(lead, mark)].append(round((x_txt - left[pno]) * 100))
    return {k: collections.Counter(v).most_common(1)[0][0]
            for k, v in samples.items()}


# ───────────────────────── 적용 ─────────────────────────
def clone_parapr(header_xml, src_id, intent):
    """paraPr[src_id] 를 복제해 margin intent 만 바꾼 새 paraPr 주입."""
    m = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % src_id, header_xml, re.S)
    if not m:
        raise ValueError("paraPr %s 없음" % src_id)
    new_id = str(max(int(x) for x in
                     re.findall(r'<hh:paraPr id="(\d+)"', header_xml)) + 1)
    new = re.sub(r'\bid="\d+"', 'id="%s"' % new_id, m.group(0), count=1)
    if "<hc:intent" in new:
        # hp:case / hp:default 양쪽 margin 을 모두 갱신해야 한글·rhwp 가 같이 본다
        new = re.sub(r'(<hh:margin><hc:intent value=")-?\d+(")',
                     r'\g<1>%d\2' % intent, new)
    else:
        new = new.replace("<hh:margin>",
                          '<hh:margin><hc:intent value="%d" unit="HWPUNIT"/>' % intent)
    header_xml = re.sub(r'(</hh:paraPr>)(?!.*</hh:paraPr>)', r'\1' + new,
                        header_xml, flags=re.S)
    header_xml = re.sub(r'(<hh:paraProperties itemCnt=")(\d+)(")',
                        lambda mm: mm.group(1) + str(int(mm.group(2)) + 1) + mm.group(3),
                        header_xml, count=1)
    return new_id, header_xml


def prefix_key(text):
    lead = text[:len(text) - len(text.lstrip(" \u3000"))]
    body = text.lstrip(" \u3000")
    return (lead, body[0]) if body else None


def hanging_cells(src_hwpx, out_hwpx, wd, markers=("\u25a1",), rhwp=None,
                  measure=True, strip_lineseg=False):
    """marker 를 포함한 표 셀 문단에 내어쓰기만 적용 (볼드·폰트 불변).

    strip_lineseg 는 기본 False. lineseg 를 지우면 `vertRelTo="PARA"` 부동 서명이
    앵커 기준을 잃고 떠오른다. rhwp 는 lineseg 가 남아 있어도 intent 를 반영한다.
    """
    unpack(src_hwpx, wd)
    hp = os.path.join(wd, "Contents", "header.xml")
    sp = os.path.join(wd, "Contents", "section0.xml")
    h = Path(hp).read_text(encoding="utf-8")
    s = Path(sp).read_text(encoding="utf-8")

    widths = measure_intents(src_hwpx, wd, find_rhwp(rhwp)) if measure else {}

    def width_of(key):
        if key in widths:
            return widths[key]
        # XML 키 ('\u3000','-') 와 측정 키 ('','-') 가 어긋난다 → 마커만으로 폴백
        same = [w for (lead, mark), w in widths.items() if mark == key[1]]
        return max(same) if same else None

    combos = {}
    for m in re.finditer(r"<hp:tc\b.*?</hp:tc>", s, re.S):
        if not any(mk in m.group(0) for mk in markers):
            continue
        for pm in re.finditer(r'<hp:p id="[^"]*" paraPrIDRef="(\d+)".*?</hp:p>',
                              m.group(0), re.S):
            t = re.search(r"<hp:t>([^<]*)</hp:t>", pm.group(0))
            k = prefix_key(t.group(1)) if t else None
            if k:
                combos[(pm.group(1), k)] = None
    if not combos:
        raise ValueError("marker %r 를 가진 셀에 문단이 없다" % (markers,))

    for (old_ppr, key) in list(combos):
        w = width_of(key)
        intent = -w if w else FALLBACK_INTENT
        pid, h = clone_parapr(h, old_ppr, intent)
        combos[(old_ppr, key)] = (pid, intent)
    Path(hp).write_text(h, encoding="utf-8")

    def fix_cell(cell):
        def sub_p(pm):
            blk, ppr = pm.group(0), pm.group(1)
            t = re.search(r"<hp:t>([^<]*)</hp:t>", blk)
            k = prefix_key(t.group(1)) if t else None
            hit = combos.get((ppr, k)) if k else None
            if hit:
                blk = blk.replace('paraPrIDRef="%s"' % ppr,
                                  'paraPrIDRef="%s"' % hit[0], 1)
            if strip_lineseg:
                blk = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "",
                             blk, flags=re.S)
            return blk
        return re.sub(r'<hp:p id="[^"]*" paraPrIDRef="(\d+)".*?</hp:p>',
                      sub_p, cell, flags=re.S)

    parts, pos, n = [], 0, 0
    for m in re.finditer(r"<hp:tc\b.*?</hp:tc>", s, re.S):
        if not any(mk in m.group(0) for mk in markers):
            continue
        parts.append(s[pos:m.start()])
        parts.append(fix_cell(m.group(0)))
        pos = m.end()
        n += 1
    parts.append(s[pos:])
    Path(sp).write_text("".join(parts), encoding="utf-8")
    ET.parse(sp)
    repack(wd, out_hwpx)
    return {"cells": n, "measured": bool(widths),
            "intents": {"%s%s" % k: v[1] for k, v in combos.items()}}


# ───────────────────────── 검증 ─────────────────────────
def check_alignment(pdf_path):
    """접힌 줄이 그 문단 첫 글자 x 에 붙었는지 대조. (ok, miss) 반환."""
    rows = marker_lines(pdf_path)
    by_page = collections.defaultdict(list)
    for r in rows:
        by_page[r[0]].append(r)
    ok = miss = 0
    for pno in sorted(by_page):
        anchor = None                      # (본문 x, 직전 줄 아래 y)
        for _, _, mark, x_line, x_txt, y_top, y_bot, text in sorted(
                by_page[pno], key=lambda r: (round(r[5], 1), round(r[3], 2))):
            if mark:
                anchor = (x_txt, y_bot) if x_txt is not None else None
                continue
            if anchor is None:
                continue
            if y_top - anchor[1] > MAX_GAP:      # 다른 표·제목 셀
                anchor = None
                continue
            delta = round(x_line - anchor[0], 2)
            if abs(delta) < TOL:
                ok += 1
            else:
                miss += 1
                print("  MISS p%d  d=%+.2fpt  wrap_x=%.2f  anchor_x=%.2f | %s"
                      % (pno + 1, delta, x_line, anchor[0], text[:34]))
            anchor = (anchor[0], y_bot)          # 3줄 이상 접힘도 이어서 검사
    print("접힌 줄 정렬: OK %d / MISS %d" % (ok, miss))
    return ok, miss


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="입력 .hwpx (또는 --check 사용 시 .pdf)")
    ap.add_argument("out", nargs="?", help="출력 .hwpx")
    ap.add_argument("--markers", nargs="+", default=["\u25a1"],
                    help="대상 셀을 고르는 마커 (기본: □)")
    ap.add_argument("--rhwp", help="rhwp 바이너리 경로")
    ap.add_argument("--no-measure", action="store_true",
                    help="실측 없이 폴백 intent 사용")
    ap.add_argument("--check", action="store_true",
                    help="PDF 의 접힌 줄 정렬만 검사")
    a = ap.parse_args()

    if a.check:
        _, miss = check_alignment(a.src)
        return 0 if miss == 0 else 1

    if not a.out:
        ap.error("출력 경로가 필요하다")
    wd = os.path.join(os.path.dirname(os.path.abspath(a.out)) or ".", "_hwpx_hang")
    info = hanging_cells(a.src, a.out, wd, markers=tuple(a.markers),
                         rhwp=a.rhwp, measure=not a.no_measure)
    shutil.rmtree(wd, ignore_errors=True)
    print("셀 %d개 / 실측 %s" % (info["cells"], info["measured"]))
    for k, v in sorted(info["intents"].items()):
        print("  %s = %d" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())

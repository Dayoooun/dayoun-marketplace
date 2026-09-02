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

# 실무 문서 493건 전수 스캔으로 확인한 불릿 기호 (2026-08-27).
# 이 목록에 없는 글자로 시작하는 문단은 서술문으로 보고 건드리지 않는다.
BULLETS = "\u25a1\u25cb-\u25cf\u25aa\u00b7\u203b\u25e6"   # □ ○ - ● ▪ · ※ ◦
MARKERS = BULLETS                # 정렬 검사에서 앵커로 인정할 기호
# 정렬 허용치 (pt). 실측상 완전히 맞은 줄은 오차 0.00~0.08pt 로 떨어지지만,
# 글자폭 반올림으로 한 글자의 1/10 남짓(≈1.0pt)이 남는 문단이 섞인다.
# 1.5pt = 8pt 본문 한 글자의 약 1/7 — 육안으로 구분되지 않는 폭이다.
TOL = 1.5
# 마커 줄과 세로로 얼마나 벌어지면 다른 문단으로 볼지 — **글자 높이 배수**다.
# 고정 pt 는 못 쓴다. 행간이 문서마다 다르다 (부산신보 2회차 ~0pt, 경남신보
# 중간결과보고서 7.2pt). 줄 높이의 이 배수를 넘으면 끊긴 것으로 본다.
MAX_GAP_RATIO = 1.2
FALLBACK_INTENT = -1350
# 새 항목의 시작으로 보는 줄 — 접힌 줄일 수 없다.
# 좌표만으로는 못 거른다: 비지단 결과보고서의 `2. …` 제목은 불릿 좌측에서 정확히
# 글자 한 칸(-10pt) 왼쪽이라 어떤 x 창을 잡아도 경계에 걸린다. 내용으로 판정한다.
#
# 한 자리 번호만 본다. 두 자리 이상은 접힌 줄의 일부일 확률이 높다 —
# 부산신보 `… 이체 2026. 6.` / `16. 완납` 이 실제 사례다. 문서 목차가 10 항목을
# 넘는 경우는 이 서식들에 없다(실측 최대 6).
HEADING_RE = re.compile(r"^\s*[(\[]?\d[.)\]]")
# 정렬 허용치를 넓혀야 하는 문단 정렬. JUSTIFY 는 자간을 늘려 줄을 맞추므로
# 마지막 줄에 글자폭 반올림이 누적된다 (거제 멘토링보고서 실측 최대 1.72pt).
JUSTIFY_TOL = 2.0


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
    """paraPr[src_id] 를 복제해 margin intent·left 를 바꾼 새 paraPr 주입.

    ★ 한/글은 `intent` 를 `left` 안에서만 쓴다 (2026-09-03 한컴 2024 PDF 실측,
      consulting-report/knowledge/runtime/hanging-indent.md '한컴 축 실측').
      접힘 = left, 첫 줄 = left + intent. `left=0` 이면 첫 줄이 셀 밖으로 못
      나가 0 으로 잘리고 **내어쓰기가 사라진다**. rhwp 는 `|intent|` 만으로 접힘을
      그리므로 맥에서는 멀쩡해 보여 2026-08-28~09-02 내내 놓쳤다.
      그래서 `hp:case`·`hp:default` **양쪽 모두** `left = |intent|` 로 둔다.
    """
    m = re.search(r'<hh:paraPr id="%s".*?</hh:paraPr>' % src_id, header_xml, re.S)
    if not m:
        raise ValueError("paraPr %s 없음" % src_id)
    new_id = str(max(int(x) for x in
                     re.findall(r'<hh:paraPr id="(\d+)"', header_xml)) + 1)
    new = re.sub(r'\bid="\d+"', 'id="%s"' % new_id, m.group(0), count=1)
    left = abs(intent)

    def fix_margin(mm):
        # 요소 순서에 의존하지 않는다 — intent/left 가 어느 자리에 있든 값만 바꾸고,
        # 없으면 앞에 끼워 넣는다. (레드팀 C3: left 가 intent 앞에 오는 문서 존재 가능)
        body = mm.group(1)
        body, n_i = re.subn(r'(<hc:intent\b[^>]*\bvalue=")-?\d+(")', r'\g<1>%d\2' % intent, body)
        body, n_l = re.subn(r'(<hc:left\b[^>]*\bvalue=")-?\d+(")', r'\g<1>%d\2' % left, body)
        if not n_l:
            body = '<hc:left value="%d" unit="HWPUNIT"/>' % left + body
        if not n_i:
            body = '<hc:intent value="%d" unit="HWPUNIT"/>' % intent + body
        return "<hh:margin>" + body + "</hh:margin>"

    # hp:case / hp:default 양쪽 margin 을 모두 갱신해야 한글·rhwp 가 같이 본다
    new = re.sub(r"<hh:margin>(.*?)</hh:margin>", fix_margin, new, flags=re.S)
    header_xml = re.sub(r'(</hh:paraPr>)(?!.*</hh:paraPr>)', r'\1' + new,
                        header_xml, flags=re.S)
    header_xml = re.sub(r'(<hh:paraProperties itemCnt=")(\d+)(")',
                        lambda mm: mm.group(1) + str(int(mm.group(2)) + 1) + mm.group(3),
                        header_xml, count=1)
    return new_id, header_xml


def prefix_key(text, bullets=None):
    """(선행공백, 마커) 키. 마커로 시작하지 않는 문단은 None (대상 아님).

    내어쓰기는 **불릿 문단에만** 건다. 일반 서술 문단에 걸면 접힌 줄이 첫 글자
    위치로 당겨져 오히려 어긋난다 — 경남신보 중간결과보고서에서 재현됐다
    (`동`·`유`·`자`·`김` 같은 본문 첫 글자가 마커로 오인됐다).
    """
    bullets = BULLETS if bullets is None else bullets
    lead = text[:len(text) - len(text.lstrip(" \u3000"))]
    body = text.lstrip(" \u3000")
    if not body or body[0] not in bullets:
        return None
    return (lead, body[0])


def hanging_cells(src_hwpx, out_hwpx, wd, markers=("\u25a1",), rhwp=None,
                  measure=True, strip_lineseg=False, rounds=3):
    """marker 를 포함한 표 셀 문단에 내어쓰기만 적용 (볼드·폰트 불변).

    `measure=True` 면 **수렴할 때까지 반복 보정**한다. 1패스 실측만으로는 원본이
    이미 intent 를 갖고 있는 문서에서 틀린다 — 접두사 폭을 재도 그 폭 자체가
    기존 intent 로 이동한 뒤의 값이기 때문이다.

    실측(경남신보 중간결과보고서): paraPr 20 은 이미 `intent=-3660` 이고 접힌 줄이
    본문(x=183.4)보다 5.7pt 더 들어가 있었다. 1패스는 이걸 못 고친다. 그래서
    적용 → 렌더 → 남은 오차(pt×100)만큼 intent 를 더하는 과정을 `rounds` 회 돈다.

    ⛔ rhwp 는 `<hp:switch>` 의 **`hp:case`(HwpUnitChar) 만 읽고 `hp:default` 는
    무시한다**(6종 변형 렌더 대조로 확정). 두 분기 값이 다른 문서가 실제로 있으므로
    (경남신보 case=-3660 / default=-7320) 양쪽을 같은 값으로 맞춰 써야 한글과
    rhwp 가 같은 결과를 낸다.

    strip_lineseg 는 기본 False. lineseg 를 지우면 `vertRelTo="PARA"` 부동 서명이
    앵커 기준을 잃고 떠오른다. rhwp 는 lineseg 가 남아 있어도 intent 를 반영한다.
    """
    binary = find_rhwp(rhwp) if measure else None
    info = _hanging_pass(src_hwpx, out_hwpx, wd, markers, binary,
                         measure, strip_lineseg, deltas=None)
    if not measure:
        return info

    # 남은 오차를 재고 intent 를 보정한다 — 오차가 TOL 안이면 즉시 멈춘다
    for _ in range(max(0, rounds - 1)):
        deltas = _residual_deltas(out_hwpx, wd, binary)
        if not deltas:
            break
        info = _hanging_pass(src_hwpx, out_hwpx, wd, markers, binary,
                             measure, strip_lineseg, deltas=info_deltas(info, deltas))
    return info


def info_deltas(info, deltas):
    """직전 패스의 intent 에 이번 오차를 더해 누적 보정값을 만든다."""
    merged = dict(info.get("deltas") or {})
    for key, d in deltas.items():
        merged[key] = merged.get(key, 0) + d
    return merged


def iter_wrapped(rows):
    """접힌 줄만 골라 (접두사키, 본문x 대비 오차, 원문, 페이지) 로 흘린다.

    접힌 줄 판정 세 조건 — 보정과 검증이 같은 기준을 써야 하므로 여기 한 곳에 둔다:
      ① 직전이 불릿 줄일 것
      ② 세로로 바로 이어질 것 (y 간격 ≤ 글자높이 × MAX_GAP_RATIO)
      ③ 불릿 좌측 ~ 본문 x 사이(±한 글자)에 있을 것

    ③ 은 양쪽 경계가 다 필요하다. 하한을 0 으로 두면 내어쓰기 전 문서의 접힌 줄
    (불릿보다 왼쪽)을 놓치고, 한 글자 이상 왼쪽까지 열면 같은 셀의 다음 항목 제목
    (`1.`·`2.`)을 삼킨다. 상한이 없으면 가운데 정렬된 이웃 표 제목이 잡힌다.
    """
    import collections
    by_page = collections.defaultdict(list)
    for r in rows:
        by_page[r[0]].append(r)
    for pno in sorted(by_page):
        anchor = None      # (본문x, 문단좌측x, 직전줄 아래y, 글자높이, 접두사키)
        for _, lead, mark, x_line, x_txt, y_top, y_bot, text in sorted(
                by_page[pno], key=lambda r: (round(r[5], 1), round(r[3], 2))):
            height = max(y_bot - y_top, 1.0)
            if mark:
                anchor = ((x_txt, x_line, y_bot, height, (lead, mark))
                          if x_txt is not None else None)
                continue
            if anchor is None or not text.strip():
                continue
            if HEADING_RE.match(text):       # `2. …` 는 새 항목 제목이다
                anchor = None
                continue
            if y_top - anchor[2] > anchor[3] * MAX_GAP_RATIO:
                anchor = None
                continue
            if not (anchor[1] - anchor[3] * 1.2 <= x_line
                    <= anchor[0] + anchor[3] * 1.2):
                anchor = None
                continue
            yield anchor[4], round(x_line - anchor[0], 2), text, pno
            anchor = (anchor[0], anchor[1], y_bot, anchor[3], anchor[4])


def _residual_deltas(pdf_source, wd, rhwp):
    """현재 산출물의 접힌 줄 오차를 접두사 패턴별 HWPUNIT 보정값으로 환산.

    반환 {(선행공백, 마커): 보정값}. 전부 허용치 안이면 {}.
    """
    import collections
    pdf = os.path.join(wd, "_residual.pdf")
    subprocess.run([rhwp, "export-pdf", pdf_source, "-o", pdf, "--profile", "print"],
                   capture_output=True, text=True, timeout=900)
    if not os.path.exists(pdf) or os.path.getsize(pdf) == 0:
        return {}
    rows = marker_lines(pdf)
    os.remove(pdf)

    acc = collections.defaultdict(list)
    for key, delta, _text, _pno in iter_wrapped(rows):
        acc[key].append(delta)

    out = {}
    for key, ds in acc.items():
        med = sorted(ds)[len(ds) // 2]
        if abs(med) >= TOL:
            # intent 가 음수일수록 접힌 줄이 오른쪽으로 간다 (실측: 0→x152.5,
            # -1000→x162.5, -2000→x172.5 = 1pt 당 100 unit). 접힌 줄이 목표보다
            # 왼쪽이면(med<0) intent 를 더 빼야 하므로 보정값도 음수가 된다.
            out[key] = int(round(med * 100))
    return out


def lookup(table, key, default=None):
    """접두사 패턴 키로 값을 찾되, 없으면 **마커만** 같은 항목으로 폴백한다.

    XML 키는 (`'\\u3000'`, `-`) 처럼 선행공백을 갖지만 PDF 측정 키는 (`''`, `-`) 다.
    전각·반각 공백은 렌더 시 여백으로 흡수돼 글자로 남지 않기 때문이다.
    폴백이 없으면 들여쓰기된 불릿이 통째로 보정에서 빠진다.
    """
    if key in table:
        return table[key]
    same = [v for (_lead, mark), v in table.items() if mark == key[1]]
    if not same:
        return default
    # 절댓값이 가장 큰 쪽 = 들여쓰기가 가장 깊은 관측치
    return max(same, key=abs)


def iter_cells(s):
    """`<hp:tc>`~`</hp:tc>` 를 **최상위 셀 단위**로 (start, end) 낸다.

    `re.finditer(r"<hp:tc\\b.*?</hp:tc>")` 는 셀 안에 표(참고이미지 중첩표)가
    있으면 안쪽 `</hp:tc>` 에서 끊겨 바깥 셀의 뒷부분 문단을 통째로 놓친다.
    실측(2026-09-03, 쇼미 6장): `○ (2) 검색 노출 기반 점검` 이하 10개 문단이
    보정에서 빠졌다. 깊이를 세어 0 으로 돌아올 때가 진짜 끝이다.
    """
    depth, start = 0, 0
    for m in re.finditer(r"<hp:tc\b|</hp:tc>", s):
        if m.group().startswith("<hp:tc"):
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                yield start, m.end()


def _hanging_pass(src_hwpx, out_hwpx, wd, markers, rhwp, measure,
                  strip_lineseg, deltas):
    """1회 적용. `deltas` 는 접두사 패턴별 누적 보정값(HWPUNIT)."""
    deltas = deltas or {}
    unpack(src_hwpx, wd)
    hp = os.path.join(wd, "Contents", "header.xml")
    sp = os.path.join(wd, "Contents", "section0.xml")
    h = Path(hp).read_text(encoding="utf-8")
    s = Path(sp).read_text(encoding="utf-8")

    widths = measure_intents(src_hwpx, wd, rhwp) if measure else {}

    def width_of(key):
        return lookup(widths, key)

    combos = {}
    for cs, ce in iter_cells(s):
        cell = s[cs:ce]
        if not any(mk in cell for mk in markers):
            continue
        for pm in re.finditer(r'<hp:p id="[^"]*" paraPrIDRef="(\d+)".*?</hp:p>',
                              cell, re.S):
            t = re.search(r"<hp:t>([^<]*)</hp:t>", pm.group(0))
            k = prefix_key(t.group(1)) if t else None
            if k:
                combos[(pm.group(1), k)] = None
    if not combos:
        raise ValueError("marker %r 를 가진 셀에 문단이 없다" % (markers,))

    for (old_ppr, key) in list(combos):
        w = width_of(key)
        intent = -w if w else FALLBACK_INTENT
        intent += lookup(deltas, key, 0)   # 왼쪽으로 모자라면(음수) 더 뺀다
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
    for cs, ce in iter_cells(s):
        cell = s[cs:ce]
        if not any(mk in cell for mk in markers):
            continue
        parts.append(s[pos:cs])
        parts.append(fix_cell(cell))
        pos = ce
        n += 1
    parts.append(s[pos:])
    Path(sp).write_text("".join(parts), encoding="utf-8")
    ET.parse(sp)
    repack(wd, out_hwpx)
    return {"cells": n, "measured": bool(widths), "deltas": deltas,
            "intents": {"%s%s" % k: v[1] for k, v in combos.items()}}


# ───────────────────────── 검증 ─────────────────────────
def has_justify(hwpx_path):
    """문서에 JUSTIFY 문단 스타일이 있으면 True.

    JUSTIFY 는 자간을 늘려 줄 끝을 맞추므로 접힌 줄의 첫 글자 x 에 글자폭 반올림이
    누적된다. 거제 멘토링보고서(전 문단 JUSTIFY) 실측 최대 1.72pt.
    """
    try:
        with zipfile.ZipFile(hwpx_path) as z:
            head = z.read("Contents/header.xml").decode("utf-8", "ignore")
    except Exception:
        return False
    return 'horizontal="JUSTIFY"' in head


def check_alignment(pdf_path, verbose=True, source_hwpx=None):
    """접힌 줄이 그 문단 첫 글자 x 에 붙었는지 대조. (ok, miss) 반환.

    접힌 줄 판정은 `iter_wrapped` 가 한다 — 보정 패스와 같은 기준을 써야
    "게이트는 통과인데 눈으로 보면 안 맞는" 상태가 안 생긴다.

    `source_hwpx` 를 주면 JUSTIFY 문서에 완화된 허용치를 쓴다. 생략하면 PDF 옆의
    같은 이름 .hwpx 를 찾아본다.
    """
    if source_hwpx is None:
        cand = os.path.splitext(pdf_path)[0] + ".hwpx"
        source_hwpx = cand if os.path.exists(cand) else None
    tol = JUSTIFY_TOL if (source_hwpx and has_justify(source_hwpx)) else TOL

    ok = miss = 0
    for _key, delta, text, pno in iter_wrapped(marker_lines(pdf_path)):
        if abs(delta) < tol:
            ok += 1
            continue
        miss += 1
        if verbose:
            print("  MISS p%d  d=%+.2fpt | %s" % (pno + 1, delta, text[:40]))
    print("접힌 줄 정렬: OK %d / MISS %d (허용 %.1fpt)" % (ok, miss, tol))
    return ok, miss


def main():
    """Non-authoritative edit primitive used by hwpx_edit_driver.py."""
    print("직접 편집은 권한을 만들지 않습니다. hwpx_edit_driver.py operation을 사용하세요.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

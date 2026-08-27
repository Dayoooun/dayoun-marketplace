#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HWPX 빌드 후 무결성 검증.

편집한 HWPX 가 "열리기는 하는데 화면이 깨진" 상태인지 기계적으로 잡는다.
검사 항목은 전부 실제로 발생했던 사고에서 나온 것이다.

사용:
    python3 hwpx_verify.py <파일.hwpx>
    python3 hwpx_verify.py <파일.hwpx> --donor <도너.hwpx>

--donor 를 주면 도너 문서의 고유 정보(업체명·사업자번호 등)와 이미지가
결과물에 잔존하는지까지 검사한다. 교차 도너 빌드에서 필수.

종료코드: 0 = 전부 통과, 1 = FAIL 존재
"""
import argparse
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

SECTION_RE = re.compile(r"Contents/section\d+\.xml$")
PIC_RE = re.compile(r"<hp:pic\b.*?</hp:pic>", re.S)
PLACEHOLDER_RE = re.compile(r"\{[가-힣A-Za-z][가-힣A-Za-z0-9 _]*\}")

# orgSz 는 원본 기준 크기라 보통 10만 단위다. 픽셀값(수천)이 들어가면 배율이 튄다.
ORGSZ_MIN = 20000


class Report:
    def __init__(self):
        self.rows = []

    def add(self, ok, name, detail=""):
        self.rows.append(("PASS" if ok else "FAIL", name, detail))

    def warn(self, name, detail=""):
        self.rows.append(("WARN", name, detail))

    def render(self):
        width = max((len(r[1]) for r in self.rows), default=10) + 2
        for status, name, detail in self.rows:
            print("  [%s] %-*s %s" % (status, width, name, detail))
        n_fail = sum(1 for r in self.rows if r[0] == "FAIL")
        n_warn = sum(1 for r in self.rows if r[0] == "WARN")
        n_pass = sum(1 for r in self.rows if r[0] == "PASS")
        print("\n  PASS %d / WARN %d / FAIL %d" % (n_pass, n_warn, n_fail))
        return n_fail == 0


def sections(z):
    return [n for n in z.namelist() if SECTION_RE.search(n)]


def all_text(xml):
    return re.sub(r"<[^>]+>", "", xml)


def check_zip_layout(z, rep):
    names = z.namelist()
    rep.add(bool(names) and names[0] == "mimetype",
            "mimetype 첫 엔트리",
            "" if names and names[0] == "mimetype" else "실제: %s" % (names[0] if names else "(없음)"))
    if "mimetype" in names:
        info = z.getinfo("mimetype")
        rep.add(info.compress_type == zipfile.ZIP_STORED,
                "mimetype 무압축(STORED)",
                "" if info.compress_type == zipfile.ZIP_STORED else "compress_type=%d" % info.compress_type)


def check_xml_valid(z, rep):
    for name in sections(z):
        try:
            ET.fromstring(z.read(name))
            rep.add(True, "XML 유효 [%s]" % os.path.basename(name))
        except ET.ParseError as exc:
            rep.add(False, "XML 유효 [%s]" % os.path.basename(name), str(exc)[:70])


def check_manifest(z, rep):
    """매니페스트에 파일 없는 항목이 남으면 한글이 그림을 검게 그린다."""
    hpf = "Contents/content.hpf"
    if hpf not in z.namelist():
        rep.warn("매니페스트", "content.hpf 없음")
        return
    manifest = z.read(hpf).decode("utf-8", "replace")
    refs = re.findall(r'<opf:item[^>]*href="(BinData/[^"]+)"', manifest)
    missing = [r for r in refs if r not in z.namelist()]
    rep.add(not missing, "매니페스트 유령 항목",
            "" if not missing else "%d건: %s" % (len(missing), ", ".join(missing[:4])))

    listed = set(refs)
    orphan = [n for n in z.namelist() if n.startswith("BinData/") and n not in listed]
    if orphan:
        rep.warn("매니페스트 미등록 파일", "%d건: %s" % (len(orphan), ", ".join(orphan[:4])))


def check_placeholders(z, rep):
    hits = []
    for name in sections(z):
        text = all_text(z.read(name).decode("utf-8", "replace"))
        hits += PLACEHOLDER_RE.findall(text)
    hits = sorted(set(hits))
    rep.add(not hits, "미치환 placeholder",
            "" if not hits else "%d종: %s" % (len(hits), ", ".join(hits[:5])))


def check_shapes(z, rep):
    """부동 개체 배치 규칙 (references/hwpx-structure.md §2, §3)."""
    total = 0
    no_pos = []
    bad_org = []
    for name in sections(z):
        xml = z.read(name).decode("utf-8", "replace")
        for m in PIC_RE.finditer(xml):
            blk = m.group(0)
            total += 1
            iid = re.search(r'binaryItemIDRef="(\w+)"', blk)
            iid = iid.group(1) if iid else "?"

            pos = re.search(r"<hp:pos\b[^>]*>", blk)
            tac = re.search(r'treatAsChar="(\d)"', pos.group(0)) if pos else None
            if pos and tac and tac.group(1) == "0":
                v = re.search(r'vertOffset="(-?\d+)"', pos.group(0))
                h = re.search(r'horzOffset="(-?\d+)"', pos.group(0))
                if not v or not h:
                    no_pos.append(iid)

            org = re.search(r'<hp:orgSz width="(\d+)" height="(\d+)"', blk)
            if org and (int(org.group(1)) < ORGSZ_MIN or int(org.group(2)) < ORGSZ_MIN):
                bad_org.append("%s(%sx%s)" % (iid, org.group(1), org.group(2)))

    if total == 0:
        rep.warn("그림 개체", "0개")
        return
    rep.add(not no_pos, "부동 개체 hp:pos 존재",
            "" if not no_pos else "누락 %d건: %s" % (len(no_pos), ", ".join(no_pos[:4])))
    rep.add(not bad_org, "orgSz 정상범위(>=%d)" % ORGSZ_MIN,
            "" if not bad_org else "이상 %d건: %s — 픽셀값을 넣으면 배율이 튄다" % (len(bad_org), ", ".join(bad_org[:3])))


def check_table_as_char(z, rep):
    """표·그림의 treatAsChar 가 규칙에 맞는지 검사 (references/hwpx-structure.md §10).

    규칙 (실무 문서 10건 + 사용자 최종본 실측):
      표
        - 제목·헤더·업체정보 표 → 1 (글자처럼)
          부동이면 표와 부동 그림이 다른 좌표계에 놓여 서명이 엉뚱한 칸 위로 간다.
        - 본문 서술 표(2행1열), 증빙자료 표 → 0 (부동)
          길어서 페이지를 넘겨야 한다. 1이면 페이지 경계에서 잘린다.
      그림
        - 표 안 사진 → 1 (글자처럼). 부동이면 셀을 벗어나 표가 깨진다.
        - 서명·직인(부동 개체) → 0. 앵커 문단 기준으로 자유 배치해야 한다.
    """
    bad_tbl = []
    bad_pic = []
    for name in sections(z):
        xml = z.read(name).decode("utf-8", "replace")

        for m in re.finditer(r'<hp:tbl\b[^>]*rowCnt="(\d+)"[^>]*colCnt="(\d+)"[^>]*>', xml):
            rows, cols = int(m.group(1)), int(m.group(2))
            head = "".join(re.findall(r'<hp:t>([^<]{1,14})</hp:t>',
                                      xml[m.start():m.start() + 2500]))[:16]
            seg = xml[m.start():m.start() + 900]
            pos = re.search(r"<hp:pos\b[^>]*>", seg)
            if not pos:
                continue
            tac = re.search(r'treatAsChar="(\d)"', pos.group(0))
            if not tac:
                continue
            # 페이지를 넘겨야 하는 표만 부동(0):
            #   - 본문 서술(2행1열): 내용이 길다
            #   - 증빙자료 표 중 4행 이상: 사진이 많아 여러 장에 걸친다
            #     (3행 이하는 한 장에 들어가므로 1이 맞다 — 실측 2건)
            if rows == 2 and cols == 1:
                want = "0"
            elif "증빙자료" in head:
                want = "0" if rows >= 4 else "1"
            else:
                want = "1"
            if tac.group(1) != want:
                kind = "본문" if (rows == 2 and cols == 1) else ("증빙%d행" % rows if "증빙자료" in head else "제목·헤더")
                bad_tbl.append("%dx%d(%s: %s→%s)" % (rows, cols, kind, tac.group(1), want))

        # 표 안 사진: treatAsChar=1 이어야 셀에 물린다
        for m in re.finditer(r'<hp:tc\b[^>]*>(.*?)</hp:tc>', xml, re.S):
            for p in re.finditer(r'<hp:pic\b.*?</hp:pic>', m.group(1), re.S):
                pos = re.search(r"<hp:pos\b[^>]*>", p.group(0))
                if not pos:
                    continue
                tac = re.search(r'treatAsChar="(\d)"', pos.group(0))
                iid = re.search(r'binaryItemIDRef="(\w+)"', p.group(0))
                if tac and tac.group(1) == "0":
                    bad_pic.append(iid.group(1) if iid else "?")

    if bad_tbl or bad_pic or True:
        rep.add(not bad_tbl, "표 treatAsChar 규칙 (제목·헤더=1 / 본문·증빙=0)",
                "" if not bad_tbl else "위반 %d건: %s" % (len(bad_tbl), ", ".join(bad_tbl[:4])))
        rep.add(not bad_pic, "표 안 사진 글자처럼(treatAsChar=1)",
                "" if not bad_pic else "부동 %d건: %s — 셀을 벗어나 표가 깨진다"
                % (len(bad_pic), ", ".join(bad_pic[:5])))


def check_signature_anchor(z, rep):
    """부동 서명·직인의 앵커 문단 검사 (references/hwpx-structure.md §11).

    서명이 `treatAsChar=0`(부동) 이고 표 밖에 있어도, **앵커 문단이
    표 안 문단**이면 `vertRelTo="PARA"` 기준이 그 셀이 돼 셀을 밀어낸다.
    → 표가 세로로 늘어나 비뜼어진다 (쇼미더브이알 2회차에서 발생).

    정상 5건은 전부 앵커가 문단 idx 0(제목 문단)이다.
    """
    bad = []
    for name in sections(z):
        xml = z.read(name).decode("utf-8", "replace")
        for m in re.finditer(r"<hp:pic\b.*?</hp:pic>", xml, re.S):
            blk = m.group(0)
            pos = re.search(r"<hp:pos\b[^>]*>", blk)
            if not pos:
                continue
            tac = re.search(r'treatAsChar="(\d)"', pos.group(0))
            if not tac or tac.group(1) != "0":
                continue                      # 인라인 그림은 대상 아니다
            if 'vertRelTo="PARA"' not in pos.group(0):
                continue
            p0 = xml.rfind("<hp:p ", 0, m.start())
            if p0 < 0:
                continue
            idx = xml[:p0].count("<hp:p ")
            if idx != 0:
                iid = re.search(r'binaryItemIDRef="(\w+)"', blk)
                bad.append("%s(앵커 문단 idx=%d)" % (iid.group(1) if iid else "?", idx))

    rep.add(not bad, "부동 서명·직인 앵커 = 제목 문단(idx 0)",
            "" if not bad else "%d건: %s — 표가 늘어난다" % (len(bad), ", ".join(bad[:3])))


def check_aspect(z, rep):
    """curSz 비율이 원본 이미지 비율과 맞는지 (Pillow 있을 때만)."""
    try:
        from PIL import Image
        import io as _io
    except ImportError:
        rep.warn("curSz 비율 검사", "Pillow 미설치 — 건너뜀")
        return

    bad = []
    checked = 0
    for name in sections(z):
        xml = z.read(name).decode("utf-8", "replace")
        for m in PIC_RE.finditer(xml):
            blk = m.group(0)
            iid = re.search(r'binaryItemIDRef="(\w+)"', blk)
            cur = re.search(r'<hp:curSz width="(\d+)" height="(\d+)"', blk)
            if not iid or not cur:
                continue
            target = [n for n in z.namelist()
                      if n.lower().startswith("bindata/" + iid.group(1).lower() + ".")]
            if not target:
                continue
            try:
                iw, ih = Image.open(_io.BytesIO(z.read(target[0]))).size
            except Exception:
                continue
            cw, ch = int(cur.group(1)), int(cur.group(2))
            if ch == 0 or ih == 0:
                continue
            checked += 1
            if abs(cw / ch - iw / ih) > 0.06:
                bad.append("%s(표시 %.2f vs 원본 %.2f)" % (iid.group(1), cw / ch, iw / ih))
    if checked == 0:
        return
    rep.add(not bad, "curSz 비율 = 원본 비율 (%d개 검사)" % checked,
            "" if not bad else "불일치 %d건: %s" % (len(bad), ", ".join(bad[:3])))


def donor_fingerprints(z):
    """도너 문서에서 고유 식별자(사업자번호·전화번호)와 이미지 ID 를 뽑는다."""
    text = ""
    for name in sections(z):
        text += all_text(z.read(name).decode("utf-8", "replace"))
    biz = set(re.findall(r"\b\d{3}-\d{2}-\d{5}\b", text))
    tel = set(re.findall(r"\b01[016-9]-\d{3,4}-\d{4}\b", text))
    imgs = set()
    for name in sections(z):
        imgs |= set(re.findall(r'binaryItemIDRef="(\w+)"', z.read(name).decode("utf-8", "replace")))
    return biz, tel, imgs


def check_donor_residue(z, donor_path, rep):
    with zipfile.ZipFile(donor_path) as dz:
        d_biz, d_tel, _ = donor_fingerprints(dz)
        d_bins = {os.path.basename(n): dz.read(n)
                  for n in dz.namelist() if n.startswith("BinData/")}

    text = ""
    for name in sections(z):
        text += all_text(z.read(name).decode("utf-8", "replace"))
    o_biz, o_tel, _ = donor_fingerprints(z)

    left_biz = sorted(d_biz & o_biz)
    left_tel = sorted((d_tel & o_tel) - {"010-8575-1548"})   # 컨설턴트 본인 번호는 정상 공유
    rep.add(not left_biz, "도너 사업자번호 잔존",
            "" if not left_biz else ", ".join(left_biz))
    rep.add(not left_tel, "도너 연락처 잔존",
            "" if not left_tel else ", ".join(left_tel))

    same = []
    for n in z.namelist():
        if not n.startswith("BinData/"):
            continue
        base = os.path.basename(n)
        if base in d_bins and d_bins[base] == z.read(n):
            same.append(base)
    if same:
        rep.warn("도너와 동일한 이미지", "%d건: %s — 의도한 공용 이미지인지 확인" % (len(same), ", ".join(same[:5])))


def main():
    ap = argparse.ArgumentParser(description="HWPX 빌드 후 무결성 검증")
    ap.add_argument("hwpx")
    ap.add_argument("--donor", help="교차 도너 빌드 시 원본 문서 — 잔존 오염을 함께 검사")
    args = ap.parse_args()

    if not os.path.exists(args.hwpx):
        print("파일 없음:", args.hwpx)
        return 2

    print("\n=== HWPX 검증: %s ===" % os.path.basename(args.hwpx))
    rep = Report()
    with zipfile.ZipFile(args.hwpx) as z:
        check_zip_layout(z, rep)
        check_xml_valid(z, rep)
        check_manifest(z, rep)
        check_placeholders(z, rep)
        check_shapes(z, rep)
        check_table_as_char(z, rep)
        check_signature_anchor(z, rep)
        check_aspect(z, rep)
        if args.donor:
            if os.path.exists(args.donor):
                check_donor_residue(z, args.donor, rep)
            else:
                rep.warn("도너 검사", "도너 파일 없음: %s" % args.donor)

    ok = rep.render()
    if not ok:
        print("\n  ❌ FAIL 존재 — 제출 금지. 위 항목 수정 후 재검증.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

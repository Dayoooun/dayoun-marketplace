from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "plugins"
    / "hwpx-editing"
    / "skills"
    / "edit-hwpx"
    / "scripts"
    / "hwpx_hanging.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("hwpx_hanging", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hwpx_hanging"] = mod
    spec.loader.exec_module(mod)
    return mod


H = _load()

NS = (
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"'
)

MARGIN = (
    "<hh:margin>"
    '<hc:intent value="0" unit="HWPUNIT"/>'
    '<hc:left value="0" unit="HWPUNIT"/>'
    '<hc:right value="0" unit="HWPUNIT"/>'
    "</hh:margin>"
)

HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<hh:head %s>"
    '<hh:refList><hh:paraProperties itemCnt="2">'
    '<hh:paraPr id="7">%s</hh:paraPr>'
    '<hh:paraPr id="24"><hp:switch><hp:case>%s</hp:case>'
    "<hp:default>%s</hp:default></hp:switch></hh:paraPr>"
    "</hh:paraProperties></hh:refList></hh:head>"
) % (NS, MARGIN, MARGIN, MARGIN)


def _para(pid, text, ppr="24"):
    return (
        '<hp:p id="%s" paraPrIDRef="%s" styleIDRef="0">'
        '<hp:run charPrIDRef="11"><hp:t>%s</hp:t></hp:run>'
        "<hp:linesegarray><hp:lineseg textpos=\"0\"/></hp:linesegarray>"
        "</hp:p>"
    ) % (pid, ppr, text)


def _section(cells):
    body = "".join("<hp:tc>%s</hp:tc>" % c for c in cells)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<hp:sec %s><hp:tbl>%s</hp:tbl></hp:sec>" % (NS, body)
    )


def _make_hwpx(path, cells):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/hwp+zip", zipfile.ZIP_STORED)
        z.writestr("Contents/header.xml", HEADER)
        z.writestr("Contents/section0.xml", _section(cells))


TARGET_CELL = "".join(
    [
        _para("1", "\u25a1 1. \uc218\ud589 \uac1c\uc694"),
        _para("2", "\u25cb (\ubaa9\uc801) \uc810\uac80\ud568"),
        _para("3", "\u3000- \uc9d1\ud589\ud56d\ubaa9 : \uc124\ube44\ud22c\uc790"),
    ]
)
OTHER_CELL = _para("9", "\uc99d\ube59\uc790\ub8cc(\uc0ac\uc9c4 \ub4f1)", ppr="7")


class PrefixKeyTest(unittest.TestCase):
    def test_splits_leading_whitespace_from_marker(self):
        self.assertEqual(H.prefix_key("\u25a1 1. \uac1c\uc694"), ("", "\u25a1"))
        self.assertEqual(H.prefix_key("\u3000- \ud56d\ubaa9"), ("\u3000", "-"))
        self.assertEqual(H.prefix_key("\u3000\u3000- \uae4a\uc740"), ("\u3000\u3000", "-"))

    def test_returns_none_for_blank(self):
        self.assertIsNone(H.prefix_key("   "))

    def test_rejects_narrative_paragraphs(self):
        # 마커 없는 서술문에 내어쓰기를 걸면 접힌 줄이 첫 글자로 당겨져 어긋난다.
        # 경남신보 중간결과보고서에서 `동`·`유`·`자`·`김` 이 마커로 오인됐다.
        for text in ("\ub3d9\ub85c\uba85 \uc8fc\uc18c",      # 동로명 주소
                     "\uae40 \ub2e4 \uc724",                  # 김 다 윤
                     "1. \uc218\ud589 \uac1c\uc694",          # 번호 제목
                     "     \uc720\uc9c0\ub418\ub294"):        # 들여쓴 서술문
            self.assertIsNone(H.prefix_key(text), text)

    def test_accepts_every_surveyed_bullet(self):
        # 실무 문서 493건 스캔에서 나온 기호는 전부 대상이어야 한다
        for mark in "\u25a1\u25cb-\u25cf\u25aa\u00b7\u203b\u25e6":
            self.assertEqual(H.prefix_key(mark + " \ud56d\ubaa9"), ("", mark))


class LookupTest(unittest.TestCase):
    """PDF 측정 키에는 선행공백이 없다 — 마커 폴백이 없으면 보정이 누락된다."""

    TABLE = {("", "-"): 1327, ("", "\u25a1"): 1350}

    def test_exact_key_wins(self):
        self.assertEqual(H.lookup(self.TABLE, ("", "-")), 1327)

    def test_falls_back_to_marker_only(self):
        # XML 은 ('   ', '-') 인데 측정은 ('', '-') 뿐이다
        self.assertEqual(H.lookup(self.TABLE, ("   ", "-")), 1327)
        self.assertEqual(H.lookup(self.TABLE, ("\u3000", "-")), 1327)

    def test_returns_default_for_unknown_marker(self):
        self.assertIsNone(H.lookup(self.TABLE, ("", "\u203b")))
        self.assertEqual(H.lookup(self.TABLE, ("", "\u203b"), 0), 0)

    def test_prefers_largest_magnitude(self):
        table = {("", "-"): -100, ("\u3000", "-"): -900}
        self.assertEqual(H.lookup(table, ("\u3000\u3000", "-")), -900)


class CloneParaPrTest(unittest.TestCase):
    def test_updates_both_switch_branches(self):
        new_id, header = H.clone_parapr(HEADER, "24", -1725)
        self.assertEqual(new_id, "25")
        block = re.search(
            r'<hh:paraPr id="25".*?</hh:paraPr>', header, re.S
        ).group(0)
        intents = re.findall(r'<hh:margin><hc:intent value="(-?\d+)"', block)
        # hp:case 와 hp:default 양쪽이 같은 값이어야 한글과 rhwp 가 같이 본다
        self.assertEqual(intents, ["-1725", "-1725"])
        # 한/글은 intent 를 left 안에서만 쓴다(접힘=left). left=0 이면 한/글에서
        # 내어쓰기가 사라진다 — 2026-09-03 한컴 2024 PDF 6조합 실측(c3 만 성립).
        lefts = re.findall(r'<hc:intent value="-?\d+"[^>]*/><hc:left value="(-?\d+)"', block)
        self.assertEqual(lefts, ["1725", "1725"])

    def test_left_equals_abs_intent_without_switch(self):
        # hp:switch 없이 margin 만 있는 paraPr 에도 left 가 들어가야 한다
        header = HEADER.replace(
            re.search(r'<hp:switch>.*?</hp:switch>', HEADER, re.S).group(0),
            '<hh:margin><hc:left value="0" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/></hh:margin>')
        _, h2 = H.clone_parapr(header, "24", -1350)
        block = re.search(r'<hh:paraPr id="25".*?</hh:paraPr>', h2, re.S).group(0)
        self.assertIn('<hc:intent value="-1350" unit="HWPUNIT"/><hc:left value="1350" unit="HWPUNIT"/>', block)

    def test_leaves_source_parapr_untouched(self):
        _, header = H.clone_parapr(HEADER, "24", -1350)
        original = re.search(
            r'<hh:paraPr id="24".*?</hh:paraPr>', header, re.S
        ).group(0)
        self.assertNotIn('value="-1350"', original)

    def test_bumps_item_count(self):
        _, header = H.clone_parapr(HEADER, "24", -1350)
        self.assertIn('<hh:paraProperties itemCnt="3"', header)

    def test_rejects_unknown_parapr(self):
        with self.assertRaises(ValueError):
            H.clone_parapr(HEADER, "999", -1350)


class HangingCellsTest(unittest.TestCase):
    """rhwp 렌더 없이(measure=False) XML 변형만 검증한다."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "in.hwpx"
        self.out = self.dir / "out.hwpx"
        _make_hwpx(self.src, [TARGET_CELL, OTHER_CELL])

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, **kw):
        return H.hanging_cells(
            str(self.src), str(self.out), str(self.dir / "wd"),
            markers=("\u25a1",), measure=False, **kw
        )

    def _out_xml(self, name):
        with zipfile.ZipFile(self.out) as z:
            return z.read("Contents/" + name).decode("utf-8")

    def test_assigns_distinct_parapr_per_prefix(self):
        info = self._run()
        self.assertEqual(info["cells"], 1)
        self.assertFalse(info["measured"])
        section = self._out_xml("section0.xml")
        refs = re.findall(r'<hp:p id="([123])" paraPrIDRef="(\d+)"', section)
        by_id = dict(refs)
        # □ 와 ○ 는 접두사 폭이 같지만 키가 달라 별도 사본을 받는다
        self.assertEqual(len(set(by_id.values())), 3)
        self.assertNotIn("24", by_id.values())

    def test_applies_fallback_intent_without_measurement(self):
        self._run()
        header = self._out_xml("header.xml")
        for pid in ("25", "26", "27"):
            block = re.search(
                r'<hh:paraPr id="%s".*?</hh:paraPr>' % pid, header, re.S
            ).group(0)
            self.assertIn('value="%d"' % H.FALLBACK_INTENT, block)

    def test_does_not_touch_cells_without_marker(self):
        self._run()
        section = self._out_xml("section0.xml")
        self.assertIn('<hp:p id="9" paraPrIDRef="7"', section)

    def test_keeps_linesegarray_by_default(self):
        # lineseg 를 지우면 vertRelTo="PARA" 부동 서명이 앵커를 잃는다
        self._run()
        self.assertIn("<hp:linesegarray>", self._out_xml("section0.xml"))

    def test_strips_linesegarray_only_inside_marker_cells(self):
        # 문서 전체에서 지우면 부동 서명이 앵커를 잃는다 → 대상 셀에만 적용된다
        self._run(strip_lineseg=True)
        section = self._out_xml("section0.xml")
        end = section.index("</hp:tc>") + len("</hp:tc>")
        target, rest = section[:end], section[end:]
        self.assertNotIn("<hp:linesegarray>", target)
        self.assertIn("<hp:linesegarray>", rest)

    def test_output_is_valid_xml_and_zip(self):
        self._run()
        with zipfile.ZipFile(self.out) as z:
            self.assertEqual(z.namelist()[0], "mimetype")
            self.assertEqual(z.getinfo("mimetype").compress_type,
                             zipfile.ZIP_STORED)
            for name in ("Contents/header.xml", "Contents/section0.xml"):
                ET.fromstring(z.read(name))

    def test_raises_when_marker_absent(self):
        empty = self.dir / "empty.hwpx"
        _make_hwpx(empty, [OTHER_CELL])
        with self.assertRaises(ValueError):
            H.hanging_cells(str(empty), str(self.dir / "x.hwpx"),
                            str(self.dir / "wd2"), markers=("\u25a1",),
                            measure=False)


class IterWrappedTest(unittest.TestCase):
    """접힌 줄 판정 — 오탐 3종이 실제 문서에서 나왔으므로 전부 고정한다.

    행 형식은 marker_lines() 와 같다:
      (페이지, 선행공백, 마커, 줄시작x, 첫글자x, y_top, y_bot, 원문)
    """

    H12 = 12.0        # 글자 높이 12pt (본문 8pt 기준 실측값)

    def _bullet(self, y, x=70.0, txt_x=83.0, text="- \ud56d\ubaa9"):
        return (0, "", "-", x, txt_x, y, y + self.H12, text)

    def _plain(self, y, x, text="\uc774\uc5b4\uc9c0\ub294"):
        return (0, "", None, x, None, y, y + self.H12, text)

    def test_detects_wrapped_line(self):
        rows = [self._bullet(100.0), self._plain(112.0, 83.0)]
        got = list(H.iter_wrapped(rows))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0][1], 0.0)          # 본문 x 와 정확히 일치

    def test_reports_deviation(self):
        rows = [self._bullet(100.0), self._plain(112.0, 70.0)]
        self.assertEqual(list(H.iter_wrapped(rows))[0][1], -13.0)

    def test_ignores_line_too_far_below(self):
        # 다음 표·다음 문단. 글자 높이의 1.2배를 넘으면 끊긴 것으로 본다
        rows = [self._bullet(100.0), self._plain(100.0 + 12.0 + 20.0, 83.0)]
        self.assertEqual(list(H.iter_wrapped(rows)), [])

    def test_ignores_neighbouring_centered_title(self):
        # 부산신보 「증빙자료(사진 등)」 x=257.7 vs 앵커 x=70.8
        rows = [self._bullet(100.0),
                self._plain(112.0, 257.7, "\uc99d\ube59\uc790\ub8cc")]
        self.assertEqual(list(H.iter_wrapped(rows)), [])

    def test_ignores_next_numbered_heading(self):
        # 경남신보 같은 셀의 `1.`·`2.` 제목 — 불릿보다 한 글자 이상 왼쪽
        rows = [self._bullet(100.0, x=170.0, txt_x=183.0),
                self._plain(112.0, 152.5, "2. \uc5c5\ub85c\ub4dc")]
        self.assertEqual(list(H.iter_wrapped(rows)), [])

    def test_tracks_three_line_wrap(self):
        rows = [self._bullet(100.0),
                self._plain(112.0, 83.0),
                self._plain(124.0, 83.0)]
        self.assertEqual(len(list(H.iter_wrapped(rows))), 2)

    def test_skips_blank_line(self):
        rows = [self._bullet(100.0), self._plain(112.0, 83.0, "   ")]
        self.assertEqual(list(H.iter_wrapped(rows)), [])


class ReceiptGuidanceTest(unittest.TestCase):
    def test_skill_requires_receipt_bound_init_operation_validation(self):
        skill = (
            ROOT / "plugins" / "hwpx-editing" / "skills" / "edit-hwpx" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for required in (
            "hwpx_edit_driver.py",
            "hwpx-edit-init-payload",
            "hwpx-edit-operation-payload",
            "hwpx-edit-validation-payload",
            "--input-ref",
            "--input-sha256",
            "--init-receipt-ref",
            "--init-receipt-sha256",
            "--operation-receipt-ref",
            "--operation-receipt-sha256",
            "--tool-source-sha256",
            "verified snapshot",
            "dayoun-handoff-v1",
            "bundled `_contracts`와 `_dependencies`",
            "원본은 절대 덮어쓰지 않습니다",
            "self-validation",
        ):
            self.assertIn(required, skill)

    def test_skill_rejects_legacy_path_only_authority(self):
        skill = (
            ROOT / "plugins" / "hwpx-editing" / "skills" / "edit-hwpx" / "SKILL.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("python3 scripts/hwpx_verify.py", skill)
        self.assertNotIn("python scripts/hwpx_hanging.py in.hwpx out.hwpx", skill)
        self.assertNotIn("python scripts/hwpx_hanging.py out.pdf --check", skill)

if __name__ == "__main__":
    unittest.main()

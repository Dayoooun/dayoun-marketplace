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


if __name__ == "__main__":
    unittest.main()

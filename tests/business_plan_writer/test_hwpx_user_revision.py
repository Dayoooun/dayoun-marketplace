from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "business-plan-writer"
SCRIPTS = PLUGIN / "skills" / "fill-hwpx-template" / "scripts"
DEMO = PLUGIN / "assets" / "demo" / "demo-business-plan.hwpx"
STYLE = SCRIPTS / "hwpx_style_integrity.py"
PREVIEW = SCRIPTS / "hwpx_preview_sync.py"
REVISION = SCRIPTS / "hwpx_revision.py"
FONTS = SCRIPTS / "install_bundled_fonts.py"
FONT_BUNDLE = PLUGIN / "assets" / "fonts" / "pretendard"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
    )


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def replace_member(source: Path, output: Path, member: str, data: bytes) -> None:
    with zipfile.ZipFile(source) as archive:
        with zipfile.ZipFile(output, "w") as target:
            for info in archive.infolist():
                target.writestr(
                    info,
                    data if info.filename == member else archive.read(info.filename),
                )


def swapped_para_order(source: Path, output: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        root = ET.fromstring(archive.read("Contents/header.xml"))
    container = next(
        node for node in root.iter() if local_name(node.tag) == "paraProperties"
    )
    definitions = [
        node for node in list(container) if local_name(node.tag) == "paraPr"
    ]
    self_contained = len(definitions) >= 2
    if not self_contained:
        raise AssertionError("demo fixture needs at least two paraPr definitions")
    first_index = list(container).index(definitions[-2])
    second_index = list(container).index(definitions[-1])
    children = list(container)
    children[first_index], children[second_index] = (
        children[second_index],
        children[first_index],
    )
    container[:] = children
    replace_member(
        source,
        output,
        "Contents/header.xml",
        ET.tostring(root, encoding="utf-8", xml_declaration=True),
    )


class HwpxUserRevisionTests(unittest.TestCase):
    def test_style_validator_blocks_definition_array_swap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            swapped = root / "swapped.hwpx"
            swapped_para_order(DEMO, swapped)
            blocked = run_script(STYLE, "validate", str(swapped))
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("array order must be consecutive", blocked.stdout)
            blocked_lock = run_script(
                REVISION,
                "lock",
                str(swapped),
                "--canonical-output",
                str(root / "should-not-lock.hwpx"),
                "--receipt",
                str(root / "should-not-lock.json"),
            )
            self.assertNotEqual(blocked_lock.returncode, 0)
            self.assertIn("style integrity", blocked_lock.stdout)
            self.assertFalse((root / "should-not-lock.hwpx").exists())

    def test_preview_sync_is_exact_and_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.hwpx"
            second = root / "second.hwpx"
            before = run_script(PREVIEW, "validate", str(DEMO))
            self.assertNotEqual(before.returncode, 0)
            first_run = run_script(
                PREVIEW,
                "sync",
                str(DEMO),
                "--output",
                str(first),
            )
            second_run = run_script(
                PREVIEW,
                "sync",
                str(first),
                "--output",
                str(second),
            )
            self.assertEqual(first_run.returncode, 0, first_run.stdout)
            self.assertEqual(second_run.returncode, 0, second_run.stdout)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            verified = run_script(PREVIEW, "validate", str(second))
            self.assertEqual(verified.returncode, 0, verified.stdout)
            self.assertIn('"previewMatchesBody": true', verified.stdout)

    def test_user_edited_canonical_blocks_deleted_block_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "canonical.hwpx"
            receipt = root / "canonical.json"
            removed = root / "removed.json"
            removed.write_text(
                json.dumps(
                    {
                        "removedBlocks": [
                            {
                                "anchor": "o 근거 원문",
                                "scope": "Q1-Q4",
                                "restoreWithoutApproval": False,
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            locked = run_script(
                REVISION,
                "lock",
                str(DEMO),
                "--canonical-output",
                str(canonical),
                "--receipt",
                str(receipt),
                "--removed-blocks",
                str(removed),
            )
            self.assertEqual(locked.returncode, 0, locked.stdout)
            self.assertEqual(canonical.read_bytes(), DEMO.read_bytes())
            valid = run_script(
                REVISION,
                "validate",
                str(canonical),
                "--receipt",
                str(receipt),
                "--candidate",
                str(canonical),
            )
            self.assertEqual(valid.returncode, 0, valid.stdout)

            with zipfile.ZipFile(canonical) as archive:
                section_root = ET.fromstring(
                    archive.read("Contents/section0.xml")
                )
            sample_paragraph = next(
                node
                for node in section_root.iter()
                if local_name(node.tag) == "p"
                and any(local_name(child.tag) == "t" for child in node.iter())
            )
            sample_run = next(
                node
                for node in sample_paragraph.iter()
                if local_name(node.tag) == "run"
                and any(local_name(child.tag) == "t" for child in node.iter())
            )
            sample_text = next(
                node
                for node in sample_run.iter()
                if local_name(node.tag) == "t"
            )
            restored_paragraph = ET.Element(
                sample_paragraph.tag,
                {"paraPrIDRef": sample_paragraph.get("paraPrIDRef", "0")},
            )
            restored_run = ET.Element(
                sample_run.tag,
                {"charPrIDRef": sample_run.get("charPrIDRef", "0")},
            )
            restored_text = ET.Element(sample_text.tag)
            restored_text.text = "o 근거 원문"
            restored_run.append(restored_text)
            restored_paragraph.append(restored_run)
            section_root.append(restored_paragraph)
            restored_section = ET.tostring(
                section_root,
                encoding="utf-8",
                xml_declaration=True,
            )
            restored = root / "restored.hwpx"
            replace_member(
                canonical,
                restored,
                "Contents/section0.xml",
                restored_section,
            )
            blocked = run_script(
                REVISION,
                "validate",
                str(canonical),
                "--receipt",
                str(receipt),
                "--candidate",
                str(restored),
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("restored removed block", blocked.stdout)

    def test_bundled_pretendard_verifies_and_installs_isolated(self) -> None:
        verified = run_script(FONTS, "verify-bundle")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn('"version": "1.3.9"', verified.stdout)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "fonts"
            first = run_script(
                FONTS,
                "install",
                "--target-dir",
                str(target),
            )
            self.assertEqual(first.returncode, 0, first.stdout)
            before = {
                path.name: path.read_bytes() for path in target.glob("*.otf")
            }
            second = run_script(
                FONTS,
                "install",
                "--target-dir",
                str(target),
            )
            self.assertEqual(second.returncode, 0, second.stdout)
            after = {
                path.name: path.read_bytes() for path in target.glob("*.otf")
            }
            self.assertEqual(before, after)
            checked = run_script(
                FONTS,
                "check",
                "--target-dir",
                str(target),
            )
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertIn('"registered": true', checked.stdout)

    def test_tampered_font_bundle_blocks(self) -> None:
        spec = importlib.util.spec_from_file_location("font_installer", FONTS)
        if spec is None or spec.loader is None:
            raise AssertionError("cannot load font installer")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            copied = Path(directory) / "pretendard"
            shutil.copytree(FONT_BUNDLE, copied)
            font = copied / "Pretendard-Regular.otf"
            font.write_bytes(font.read_bytes() + b"tampered")
            _manifest, errors = module.load_bundle(copied)
            self.assertTrue(errors)
            self.assertTrue(any("digest mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

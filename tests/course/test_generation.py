from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_course import compare_directories, file_sha256  # noqa: E402


class CourseGenerationTests(unittest.TestCase):
    def test_text_line_endings_do_not_create_generated_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            actual = root / "actual"
            expected.mkdir()
            actual.mkdir()
            (expected / "manifest.json").write_bytes(b'{\n  "ok": true\n}\n')
            (actual / "manifest.json").write_bytes(b'{\r\n  "ok": true\r\n}\r\n')

            self.assertEqual(compare_directories(expected, actual), [])

    def test_manifest_member_hashes_ignore_text_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lf = root / "lf.txt"
            crlf = root / "crlf.txt"
            lf.write_bytes(b"first\nsecond\n")
            crlf.write_bytes(b"first\r\nsecond\r\n")

            self.assertEqual(file_sha256(lf), file_sha256(crlf))

    def test_text_content_and_binary_drift_remain_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            actual = root / "actual"
            expected.mkdir()
            actual.mkdir()
            (expected / "copy.txt").write_text("approved\n", encoding="utf-8")
            (actual / "copy.txt").write_text("changed\n", encoding="utf-8")
            (expected / "asset.bin").write_bytes(b"\x00\x01")
            (actual / "asset.bin").write_bytes(b"\x00\x02")

            self.assertEqual(
                compare_directories(expected, actual),
                ["drift:asset.bin", "drift:copy.txt"],
            )


if __name__ == "__main__":
    unittest.main()

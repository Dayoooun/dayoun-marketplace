from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_course import compare_directories, copy_tree, file_sha256  # noqa: E402


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


    def test_unicode_normalization_does_not_create_generated_drift(self) -> None:
        # macOS(APFS)는 파일명을 NFD 로 저장하고 Linux/Windows 는 NFC 를 유지한다.
        # 경로를 정규화하지 않고 비교하면 같은 한글 파일이 서로 다른 키가 되어
        # 내용이 동일한데도 전 파일이 missing+unexpected 로 잡힌다.
        import unicodedata

        name = "사업정보표.md"
        self.assertNotEqual(
            unicodedata.normalize("NFC", name),
            unicodedata.normalize("NFD", name),
            "테스트 전제: 이 이름은 NFC 와 NFD 표현이 달라야 한다",
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = root / "expected"
            actual = root / "actual"
            expected.mkdir()
            actual.mkdir()
            body = "# 사업정보\n"
            (expected / unicodedata.normalize("NFC", name)).write_text(body, encoding="utf-8")
            (actual / unicodedata.normalize("NFD", name)).write_text(body, encoding="utf-8")

            self.assertEqual(compare_directories(expected, actual), [])

    def test_generated_manifest_keys_are_nfc(self) -> None:
        # 매니페스트 키가 플랫폼별로 갈리면 macOS 에서 만든 코스 킷과
        # Linux CI 가 만든 것의 digest 집합이 달라진다.
        import json
        import unicodedata

        manifest = json.loads((ROOT / "course" / "manifest.json").read_text(encoding="utf-8"))
        not_normalized = [
            key for key in manifest["members"] if not unicodedata.is_normalized("NFC", key)
        ]
        self.assertEqual(not_normalized, [], "manifest 키가 NFC 가 아니다")


    def test_copy_tree_normalizes_generated_names_to_nfc(self) -> None:
        # 원본이 macOS 에서 NFD 로 저장돼 있어도 생성물은 NFC 여야 한다.
        # shutil.copytree 는 원본 이름을 그대로 쓰므로 NFD 가 그대로 번져
        # git index(NFC)·Linux CI 와 어긋난다.
        import unicodedata

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "src"
            target = root / "dst"
            nfd_dir = source / unicodedata.normalize("NFD", "검토결과")
            nfd_dir.mkdir(parents=True)
            (nfd_dir / unicodedata.normalize("NFD", "내용검토.md")).write_text(
                "x\n", encoding="utf-8"
            )
            (source / "__pycache__").mkdir()
            (source / "__pycache__" / "a.pyc").write_text("skip", encoding="utf-8")

            target.mkdir()
            copy_tree(source, target)

            not_normalized = [
                path.name
                for path in target.rglob("*")
                if not unicodedata.is_normalized("NFC", path.name)
            ]
            self.assertEqual(not_normalized, [], "생성물 이름이 NFC 가 아니다")
            self.assertTrue((target / "검토결과" / "내용검토.md").is_file())
            self.assertFalse((target / "__pycache__").exists(), "__pycache__ 는 제외한다")


if __name__ == "__main__":
    unittest.main()

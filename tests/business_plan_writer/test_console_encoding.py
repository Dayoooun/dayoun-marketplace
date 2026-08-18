"""한글을 출력하는 CLI 가 Windows 콘솔에서 죽지 않는지 검사한다.

Windows 콘솔·CI 러너의 기본 인코딩은 cp1252/cp949 다. main() 이 stdout 을
UTF-8 로 올리지 않은 채 한글을 print 하면 UnicodeEncodeError 로 죽는다.
실측: CI Windows 러너에서 advance_stage.py 가
'charmap' codec can't encode characters 로 실패했다.

리눅스·macOS 에서는 재현되지 않아 로컬 테스트만으로는 놓친다.
그래서 소스에 보강이 들어있는지 정적으로 검사한다.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / "plugins" / "business-plan-writer"

KOREAN = re.compile(r"[가-힣]")
MAIN_DEF = re.compile(r"^def main\(", re.M)
UTF8_GUARD = re.compile(
    r'reconfigure\(\s*encoding="utf-8"|configure_utf8'
)


def cli_modules() -> list[Path]:
    """main() 을 가진 스킬 스크립트."""
    found = []
    for path in sorted(PLUGIN.rglob("*.py")):
        if "__pycache__" in path.parts or "_deprecated" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if MAIN_DEF.search(text):
            found.append(path)
    return found


class ConsoleEncodingTests(unittest.TestCase):
    def test_korean_printing_clis_configure_utf8_output(self) -> None:
        offenders = []

        for path in cli_modules():
            text = path.read_text(encoding="utf-8")

            # 한글을 콘솔로 내보내는가. print 인자뿐 아니라 json.dumps 로
            # 한글 데이터를 찍는 경우도 포함해야 해서, print 호출이 있고
            # 파일에 한글 문자열 리터럴이 있으면 대상으로 본다.
            prints = "print(" in text
            has_korean = bool(KOREAN.search(text))
            if not (prints and has_korean):
                continue

            if not UTF8_GUARD.search(text):
                offenders.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(
            offenders,
            [],
            "한글을 출력하는데 UTF-8 콘솔 보강이 없습니다. "
            "Windows CI 에서 UnicodeEncodeError 로 죽습니다:\n  "
            + "\n  ".join(offenders),
        )

    def test_cli_modules_are_actually_discovered(self) -> None:
        # 탐색이 0건이면 위 테스트가 조용히 통과한다.
        self.assertGreater(len(cli_modules()), 5)


if __name__ == "__main__":
    unittest.main()

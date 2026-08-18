"""라이브 수업 시연이 독립 환경에서 같은 결과를 내는지 검증한다.

저장소 작업본이 아니라 빌드한 릴리스 아티팩트만 풀어서 실행한다.
같은 입력이면 두 실행의 단계별 digest 가 모두 같아야 하고,
승인·방향 게이트를 되돌리는 회귀는 BLOCK 으로 잡혀야 한다.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_release_artifacts import build_target, declared_version  # noqa: E402
from rehearse_live_class import RehearsalError, rehearse  # noqa: E402

FIXTURES = ROOT / "tests" / "course" / "fixtures" / "live-class"
CREATE_SCRIPT = "skills/setup-business-plan-project/scripts/create_project.py"


def build_writer_archive(directory: Path) -> Path:
    target = "business-plan-writer"
    build_target(target, declared_version(target), directory)
    archives = sorted(directory.glob("*.zip"))
    if len(archives) != 1:
        raise AssertionError(f"기대한 아티팩트가 하나가 아닙니다: {archives}")
    return archives[0]


def repack(source: Path, destination: Path, relative: str, old: str, new: str) -> bool:
    """아티팩트 사본에 회귀를 심는다. 변이 지점이 없으면 False."""
    with tempfile.TemporaryDirectory(prefix="rehearsal-mutate-") as temp:
        work = Path(temp)
        with zipfile.ZipFile(source) as archive:
            archive.extractall(work)
        target = work / relative
        text = target.read_text(encoding="utf-8")
        if old not in text:
            return False
        target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as out:
            for path in sorted(work.rglob("*")):
                if path.is_file():
                    out.write(path, path.relative_to(work).as_posix())
    return True


class LiveClassRehearsalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="rehearsal-suite-")
        base = Path(cls._temp.name)
        cls.archive = build_writer_archive(base / "artifacts")
        cls.demo_inputs = FIXTURES / "inputs"
        cls.template = FIXTURES / "template.hwpx"

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_two_independent_runs_produce_identical_results(self) -> None:
        first = rehearse(self.archive, self.demo_inputs, self.template, "a")
        second = rehearse(self.archive, self.demo_inputs, self.template, "b")

        self.assertEqual(first["steps"], second["steps"])
        self.assertEqual(first["shape"]["version"], declared_version("business-plan-writer"))
        self.assertEqual(len(first["shape"]["skills"]), 7)

    def test_stage_and_approval_gates_stay_closed(self) -> None:
        result = rehearse(self.archive, self.demo_inputs, self.template, "gates")
        details = result["details"]

        self.assertTrue(details["skipBlocked"], "승인 단계로 건너뛰기가 막히지 않았습니다")
        self.assertTrue(details["evidenceRequired"], "증거 없는 완료가 막히지 않았습니다")
        self.assertNotEqual(details["hwpxFillReturncode"], 0, "미승인 HWPX 치환이 통과했습니다")

    def test_rehearsal_catches_regressions(self) -> None:
        mutations = {
            "default-mode-demo": (
                'choices=("DEMO", "PARTIAL", "REAL"),\n        default="REAL",',
                'choices=("DEMO", "PARTIAL", "REAL"),\n        default="DEMO",',
            ),
            "interview-table-removed": (
                "| 결정 항목 | 상태 | 자료에서 확인한 내용 | 모호한 지점 | 사용자 결정 | 근거 파일·위치 |",
                "| 결정 항목 | 상태 |",
            ),
            "worker-source-fields-removed": (
                "- 발표일·기준일·확인일: {확인필요}",
                "- 날짜: {확인필요}",
            ),
            "research-open-before-direction": (
                '"direction_confirmed": false,',
                '"direction_confirmed": true,',
            ),
        }

        with tempfile.TemporaryDirectory(prefix="rehearsal-regressions-") as temp:
            base = Path(temp)
            for name, (old, new) in mutations.items():
                with self.subTest(regression=name):
                    mutated = base / f"{name}.zip"
                    self.assertTrue(
                        repack(self.archive, mutated, CREATE_SCRIPT, old, new),
                        f"변이 지점을 찾지 못했습니다: {name}",
                    )
                    with self.assertRaises(RehearsalError):
                        rehearse(mutated, self.demo_inputs, self.template, name)


if __name__ == "__main__":
    unittest.main()
